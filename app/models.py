import uuid
from django.db import models
from django.contrib.gis.db import models


class FuelPriceUpload(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    file = models.FileField(upload_to="fuel_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    total_records = models.IntegerField(default=0)
    inserted_records = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "fuel_price_uploads"


class FuelStation(models.Model):

    opis_id = models.IntegerField(unique=True, db_index=True)
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, db_index=True)
    rack_id = models.IntegerField(null=True, blank=True)
    retail_price = models.DecimalField(max_digits=6, decimal_places=4)

    location = models.PointField(geography=True,  null=True, blank=True, srid=4326, spatial_index=True )
    geocoded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fuel_stations"
        indexes = [
            models.Index(fields=["retail_price"]),
            models.Index(fields=["state", "retail_price"]),
        ]

    def __str__(self):
        return f"{self.truckstop_name} - {self.city}, {self.state} (${self.retail_price})"
