from rest_framework.response import Response
from app.helper import handle_error_log, handle_info_log
import inspect
import uuid
import concurrent.futures
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from app.tasks.tasks import process_fuel_upload
from app.models import FuelPriceUpload
from app.constants import APP_NAME
from app.serializers import RouteRequestSerializer
from app.services import ( geocode_address, fetch_route, build_route_line, get_stations_near_route, 
                          optimize_fuel_stops, calculate_fuel_cost, build_geojson,)




class FuelUploadView(APIView):

    def post(self, request):

        file_obj = request.FILES.get("file")

        if not file_obj:
            return Response(
                {"error": "File required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        upload = FuelPriceUpload.objects.create(file=file_obj)

        process_fuel_upload.delay(upload.id)

        return Response(
            {
                "upload_id": upload.id,
                "status": upload.status
            },
            status=status.HTTP_202_ACCEPTED
        )



class RouteOptimizeAPI(APIView):

    def get(self, request):
        view_name = inspect.currentframe().f_code.co_name
        try:
            serializer = RouteRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            start_address = serializer.validated_data["start"]
            end_address = serializer.validated_data["end"]

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                f_start = executor.submit(geocode_address, start_address)
                f_end = executor.submit(geocode_address, end_address)
                start_geo = f_start.result()
                end_geo = f_end.result()

            if not start_geo:
                return Response({"error": f"Could not geocode: {start_address}"}, status=400)
            if not end_geo:
                return Response({"error": f"Could not geocode: {end_address}"}, status=400)

            route = fetch_route(start_geo[0], start_geo[1], end_geo[0], end_geo[1])
            if not route:
                return Response({"error": "Route not found"}, status=404)

            polyline = route["polyline"]
            total_miles = route["distance_miles"]

            route_line = build_route_line(polyline)
            stations = get_stations_near_route(route_line, total_miles)
            stops = optimize_fuel_stops(stations, total_miles)
            cost = calculate_fuel_cost(stops, total_miles)
            geojson = build_geojson(polyline, stops, start_geo, end_geo, start_address, end_address)

            return Response({
                "start": start_address,
                "end": end_address,
                "total_distance_miles": round(total_miles, 2),
                "total_fuel_cost_usd": cost,
                "optimized_stops": stops,
                "map": geojson
            })
        except Exception as e:
            handle_error_log(str(e), view_name, app_name=APP_NAME)
            return Response({"error": "An error occurred while processing the request."}, status=500)
