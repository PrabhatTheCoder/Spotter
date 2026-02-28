import pandas as pd
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.contrib.gis.geos import Point

from app.models import FuelStation, FuelPriceUpload
from app.services import geocode_address
from app.helper import APP_NAME, handle_error_log, handle_info_log

REQUIRED_COLUMNS = [
    "OPIS Truckstop ID",
    "Truckstop Name",
    "Address",
    "City",
    "State",
    "Rack ID",
    "Retail Price",
]


@shared_task(
    queue="maintenance",
    rate_limit="1/s",
)
def geocode_stations(batch_size=100):
    """
    Runs periodically via Celery Beat.
    Processes limited batch each time.
    """

    city_states = list(
        FuelStation.objects
        .filter(location__isnull=True)
        .values_list("city", "state")
        .distinct()[:batch_size]
    )

    if not city_states:
        return "NO_PENDING_RECORDS"

    for city, state in city_states:
        try:
            lat_lng = geocode_address(f"{city}, {state}")

            if not lat_lng:
                continue

            lat, lng = lat_lng

            FuelStation.objects.filter(
                city=city,
                state=state,
                location__isnull=True
            ).update(
                location=Point(lng, lat, srid=4326),
                geocoded_at=timezone.now()
            )

        except Exception:
            continue

    return f"Processed {len(city_states)} city batches"



@shared_task(
    bind=True,
    queue="maintenance",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def process_fuel_upload(self, upload_id):
    upload = FuelPriceUpload.objects.get(id=upload_id)
    upload.status = FuelPriceUpload.Status.PROCESSING
    upload.save(update_fields=["status"])

    try:
        file_path = upload.file.path
        df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)

        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        upload.total_records = len(df)
        upload.save(update_fields=["total_records"])

        stations = [
            FuelStation(
                opis_id=row["OPIS Truckstop ID"],
                truckstop_name=row["Truckstop Name"],
                address=row["Address"],
                city=row["City"],
                state=row["State"],
                rack_id=row.get("Rack ID"),
                retail_price=row["Retail Price"],
            )
            for _, row in df.iterrows()
        ]

        with transaction.atomic():
            created = FuelStation.objects.bulk_create(
                stations,
                ignore_conflicts=True,
                batch_size=1000
            )

        after_count = FuelStation.objects.count()
        upload.inserted_records = after_count - upload.total_records 

        upload.status = FuelPriceUpload.Status.COMPLETED
        upload.processed_at = timezone.now()
        upload.save()

        geocode_stations.delay()

    except Exception as e:
        upload.status = FuelPriceUpload.Status.FAILED
        upload.error_message = str(e)
        upload.save()
        handle_error_log(e, view_name="process_fuel_upload", app_name=APP_NAME)