import bisect
import hashlib
import requests
import numpy as np
from django.core.cache import cache
from django.contrib.gis.geos import LineString
from django.db import connection
from .helper import APP_NAME, handle_error_log, handle_info_log
from .constants import GEOCODE_URL, GEOCODE_API_KEY, CACHE_TTL, TRUCK_RANGE_MILES, MPG, GEOCODE_URL, GEOCODE_API_KEY


def _cache_key(prefix: str, *args) -> str:
    raw = f"{prefix}:{':'.join(str(a) for a in args)}"
    return hashlib.md5(raw.encode()).hexdigest()

session = requests.Session()

def geocode_address(address: str):
    if not address:
        return None

    cache_key = f"geo:{address.lower().strip()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        response = session.get(
            GEOCODE_URL,
            params={
                "q": f"{address}, USA",
                "api_key": GEOCODE_API_KEY,
                "limit": 1,
            },
            timeout=10
        )

        data = response.json()

        if not data:
            return None

        lat = float(data[0]["lat"])
        lng = float(data[0]["lon"])
        handle_info_log(f"Geocode API called for: {address} lat={data[0]['lat'] if data else 'None'}, lng={data[0]['lon'] if data else 'None'}", view_name="geocode_address", app_name=APP_NAME)

        cache.set(cache_key, (lat, lng), 604800)
        return lat, lng

    except Exception as e:
        handle_error_log(e, view_name="geocode_address", app_name=APP_NAME)
        return None


def fetch_route(start_lat, start_lng, end_lat, end_lng):
    key = _cache_key("route", start_lat, start_lng, end_lat, end_lng)
    cached = cache.get(key)
    if cached:
        return cached

    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}"
        resp = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson"},
            timeout=15
        )
        data = resp.json()
        route = data["routes"][0]
        result = {
            "polyline": route["geometry"]["coordinates"],
            "distance_miles": route["distance"] / 1609.34
        }
        cache.set(key, result, CACHE_TTL)
        return result
    except Exception as e:
        handle_error_log(e, view_name="fetch_route", app_name=APP_NAME)
        return None

def build_route_line(coords: list) -> LineString:
    arr = np.array(coords)
    if len(arr) > 200:
        idx = np.linspace(0, len(arr) - 1, 200, dtype=int)
        arr = arr[idx]
    return LineString(arr.tolist(), srid=4326)

def get_stations_near_route(route_line: LineString, osrm_distance_miles: float) -> list:
    key = _cache_key("stations", route_line.wkt[:100], round(osrm_distance_miles, 1))
    cached = cache.get(key)
    if cached:
        handle_info_log("Stations cache HIT", view_name="get_stations_near_route", app_name=APP_NAME)
        return cached

    route_wkt = route_line.wkt

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    fs.id,
                    fs.truckstop_name,
                    fs.retail_price,
                    ST_LineLocatePoint(
                        ST_GeomFromText(%s, 4326),
                        fs.location::geometry
                    ) * %s AS mile_marker,
                    ST_Y(fs.location::geometry) AS lat,
                    ST_X(fs.location::geometry) AS lng
                FROM fuel_stations fs
                WHERE
                    fs.location IS NOT NULL
                    AND fs.retail_price > 0
                    AND ST_DWithin(
                        fs.location,
                        ST_GeogFromText(%s),
                        8046
                    )
                ORDER BY mile_marker ASC
            """, [route_wkt, osrm_distance_miles, route_wkt])

            rows = cursor.fetchall()

        stations = [
            {
                "id": row[0],
                "truckstop_name": row[1],
                "retail_price": float(row[2]),
                "mile_marker": float(row[3]),
                "lat": float(row[4]),
                "lng": float(row[5]),
            }
            for row in rows
            if row[3] is not None
            and 0 <= float(row[3]) <= osrm_distance_miles
        ]

        cache.set(key, stations, CACHE_TTL)
        handle_info_log( f"Found {len(stations)} stations",view_name="get_stations_near_route", app_name=APP_NAME)
        return stations

    except Exception as e:
        handle_error_log(e, view_name="get_stations_near_route", app_name=APP_NAME)
        return []

def optimize_fuel_stops(stations: list, total_miles: float) -> list:
    if not stations:
        return []

    mile_markers = [s["mile_marker"] for s in stations]
    optimized = []
    current = 0.0

    while current < total_miles:
        remaining = total_miles - current
        window_end = current + TRUCK_RANGE_MILES

        left = bisect.bisect_right(mile_markers, current)
        right = bisect.bisect_right(mile_markers, window_end)
        reachable = stations[left:right]

        if reachable:
            best = min(reachable, key=lambda x: x["retail_price"])
        else:
            if right >= len(stations):
                break
            if left == 0:
                break
            best = stations[left - 1]

        if best["mile_marker"] <= current:
            break

        optimized.append(best)
        current = best["mile_marker"]

        if optimized and remaining <= TRUCK_RANGE_MILES:
            break

    return optimized

def calculate_fuel_cost(stops: list, total_miles: float) -> float:
    if not stops:
        return round((total_miles / MPG) * 3.5, 2) 

    total = 0.0
    prev = 0.0

    for stop in stops:
        segment = stop["mile_marker"] - prev
        total += (segment / MPG) * stop["retail_price"]
        prev = stop["mile_marker"]

    remaining = total_miles - prev
    if remaining > 0:
        total += (remaining / MPG) * stops[-1]["retail_price"]

    return round(total, 2)

def build_geojson(
        polyline: list,
        stops: list,
        start_geo: tuple,
        end_geo: tuple,
        start_address: str,
        end_address: str
    ) -> dict:

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": polyline},
            "properties": {"type": "route", "color": "#0066CC"}
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [start_geo[1], start_geo[0]]},
            "properties": {"type": "start", "label": start_address}
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [end_geo[1], end_geo[0]]},
            "properties": {"type": "end", "label": end_address}
        },
    ]

    for i, stop in enumerate(stops):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [stop["lng"], stop["lat"]]},
            "properties": {
                "type": "fuel_stop",
                "stop_number": i + 1,
                "name": stop["truckstop_name"],
                "price_per_gallon": stop["retail_price"],
                "mile_marker": round(stop["mile_marker"], 1),
            }
        })

    return {"type": "FeatureCollection", "features": features}