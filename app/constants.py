from django.db import models
from decouple import config
import os

class FuelImportStatus(models.TextChoices):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

class FuelStationGeoStatus(models.TextChoices):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

APP_NAME = "app"

GEOCODE_URL = config("GEOCODE_URL", default="https://geocode.maps.co/search")
GEOCODE_API_KEY = config("GEOCODE_API_KEY")
TRUCK_RANGE_MILES = 500
MPG = 10
CACHE_TTL = 60 * 60 * 24  # 24 hours

OSRM_BASE_URL = os.environ.get("OSRM_BASE_URL", "http://router.project-osrm.org")
OSRM_TIMEOUT = 30
ROUTE_CACHE_TTL = 60 * 60 * 24 

REQUIRED_COLUMNS = [
    "OPIS Truckstop ID",
    "Truckstop Name",
    "Address",
    "City",
    "State",
    "Rack ID",
    "Retail Price",
]