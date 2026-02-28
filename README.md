# 🚛 Fuel Route Optimizer API

A production-ready Django REST API that calculates the most cost-effective fuel stops for truck routes across the USA. Deployed on AWS EC2 with Docker.

---

## 📋 Features

- Takes start and end locations within the USA
- Returns optimal fuel stops based on lowest fuel prices
- Assumes 500-mile maximum vehicle range
- Calculates total fuel cost at 10 MPG
- Returns a GeoJSON map with the full route and fuel stop markers
- Parallel geocoding with ThreadPoolExecutor
- Multi-layer Redis caching (geocoding, routing, stations)
- Background CSV processing via Celery

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.10 |
| **Framework** | Django 5.1 + Django REST Framework |
| **Database** | PostgreSQL 17 + PostGIS 3.5 |
| **Spatial Queries** | PostGIS (`ST_DWithin`, `ST_LineLocatePoint`) |
| **Cache** | Redis 7 |
| **Task Queue** | Celery + Celery Beat |
| **Routing API** | OSRM — free, 1 API call per route |
| **Geocoding API** | geocode.maps.co — free |
| **Server** | Gunicorn |
| **Containerization** | Docker + Docker Compose |
| **Cloud** | AWS EC2 (Ubuntu 24.04) |
| **Logging** | Custom structured logging |

---

## ☁️ AWS Deployment

This project is deployed on **AWS EC2**.

| Setting | Value |
|---------|-------|
| **Instance Type** | t2.medium |
| **OS** | Ubuntu 24.04 LTS |
| **Base URL** | `http://54.183.160.135:8000` |

### Security Group Inbound Rules

| Type | Port | Source |
|------|------|--------|
| SSH | 22 | Your IP |
| Custom TCP | 8000 | 0.0.0.0/0 |

### Connect to EC2

```bash
ssh -i your-key.pem ubuntu@54.183.160.135
```

### Deploy on EC2

```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone and run
git clone https://github.com/PrabhatTheCoder/Spotter.git
cd Spotter
chmod +x entrypoints.sh
nano .env
docker-compose up --build -d
```

---

## 🚀 Local Setup & Installation

### Prerequisites

- Docker
- Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/PrabhatTheCoder/Spotter.git
cd Spotter
```

### 2. Fix entrypoint permissions

```bash
chmod +x entrypoints.sh
```

### 3. Create `.env` file

```bash
nano .env
```

Paste the following and save — `Ctrl+X` → `Y` → `Enter`:

```env
REDIS_HOST_ONLY=redis
REDIS_PORT_ONLY=6379
REDIS_HOST=redis://redis:6379/1

DATABASE_NAME=route_optimizer
DATABASE_USER=postgres
DATABASE_PASSWORD=admin
DATABASE_HOST=db
DATABASE_PORT=5432

CELERY_BROKER_URL=redis://redis:6379/2
CELERY_RESULT_BACKEND=redis://redis:6379/2

GEOCODE_URL=https://geocode.maps.co/search
GEOCODE_API_KEY=your-secret-key-here
```

### 4. Start containers

```bash
# First time — build and start
docker-compose up --build

# Run in background
docker-compose up --build -d

# Start without rebuild
docker-compose up -d

# Stop containers
docker-compose down

# View logs
docker-compose logs -f django
docker-compose logs -f celery_worker

# Enter Django container
docker-compose exec django bash
```

### 5. Upload fuel prices CSV

```
POST http://localhost:8000/api/upload-fuel-data/
Content-Type: multipart/form-data

file: <your CSV file>
```

---

## 📡 API Endpoints

> **Base URL (Production):** `http://54.183.160.135:8000`
> **Base URL (Local):** `http://localhost:8000`
>
> 📮 Postman Collection: [Download here](https://github.com/PrabhatTheCoder/Spotter/blob/be733a353084da352bc92435cdadded4ea91ce76/Spotter.postman_collection.json)

---

### `POST /api/route-optimize/`

Returns optimal fuel stops and route map.

**Request:**
```json
{
    "start": "New York",
    "end": "Los Angeles"
}
```

**Response:**
```json
{
    "start": "New York",
    "end": "Los Angeles",
    "total_distance_miles": 2798.18,
    "total_fuel_cost_usd": 868.94,
    "optimized_stops": [
        {
            "id": 7865,
            "truckstop_name": "SHEETZ #791",
            "retail_price": 3.0657,
            "mile_marker": 410.3,
            "lat": 41.1001272,
            "lng": -80.8571741
        }
    ],
    "map": {
        "type": "FeatureCollection",
        "features": [...]
    }
}
```

---

### `POST /api/upload-fuel-data/`

Upload fuel prices CSV file.

**Request:**
```
multipart/form-data
file: fuel_prices.csv
```

**Response:**
```json
{
    "upload_id": 1,
    "status": "PENDING"
}
```

---

## 🗺️ Map Response (GeoJSON)

The `map` field returns a GeoJSON `FeatureCollection` compatible with Leaflet, Mapbox, or geojson.io:

- **Route** — full LineString polyline in `#0066CC` blue
- **Start marker** — Point with label
- **End marker** — Point with label
- **Fuel stop markers** — Points with name, price per gallon, and mile marker

---

## ⚙️ How It Works

```
1. Geocode start + end simultaneously (parallel ThreadPoolExecutor, cached 7 days)
        ↓
2. Fetch route from OSRM (1 API call, cached 24hr)
        ↓
3. Sample route to 200 points, build PostGIS LineString
        ↓
4. Query fuel stations within 5 miles of route (PostGIS ST_DWithin)
        ↓
5. Calculate mile markers using ST_LineLocatePoint
        ↓
6. Greedy optimizer — cheapest station in each 500-mile window (bisect O log N)
        ↓
7. Calculate total fuel cost per segment (10 MPG)
        ↓
8. Return stops + GeoJSON map
```

---

## 🧠 Optimization Logic

- Vehicle starts with a full tank (500-mile range)
- At each step, finds the **cheapest station** reachable within current range
- Prefers stations at least **100 miles ahead** to avoid unnecessary stops
- Stops only when destination is within remaining range
- `bisect` binary search used for O(log N) window lookups

---

## ⚡ Caching Strategy

| Data | Cache TTL |
|------|-----------|
| Geocoding results | 7 days |
| OSRM route | 24 hours |
| Station query results | 24 hours |

---

## 📁 Project Structure

```
app/
├── models.py         # FuelStation, FuelPriceUpload models
├── views.py          # RouteOptimizeAPI, FuelUploadView
├── services.py       # Geocoding, routing, optimizer, GeoJSON builder
├── serializers.py    # Request validation
├── constants.py      # TRUCK_RANGE_MILES, MPG, API keys
├── helper.py         # Custom structured logging
├── tasks/
│   └── tasks.py      # Celery: CSV processing, geocoding
└── urls.py

spotter/
├── settings.py
├── urls.py
└── celery.py

docker-compose.yml
Dockerfile
requirements.txt
entrypoints.sh
Spotter.postman_collection.json
```

---

## 🐳 Docker Services

| Service | Description |
|---------|-------------|
| `django` | Main API server (Gunicorn on port 8000) |
| `db` | PostgreSQL 17 + PostGIS 3.5 |
| `redis` | Cache + Celery broker |
| `celery_worker` | Background tasks (geocoding, CSV processing) |
| `celery_beat` | Scheduled tasks |

---

## 📦 CSV Format

| Column | Description |
|--------|-------------|
| OPIS Truckstop ID | Unique station ID |
| Truckstop Name | Station name |
| Address | Street address |
| City | City |
| State | 2-letter state code |
| Rack ID | Rack identifier |
| Retail Price | Price per gallon (USD) |

---

## ✅ Example Postman Tests

**NY → DC (short route):**
```json
{
    "start": "New York",
    "end": "Washington DC"
}
// Returns 1 fuel stop, ~$70 total cost
```

**NY → LA (long route):**
```json
{
    "start": "New York",
    "end": "Los Angeles"
}
// Returns 5-6 fuel stops, ~$870 total cost
```
