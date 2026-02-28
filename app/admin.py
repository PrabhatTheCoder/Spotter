from django.contrib import admin
from django.utils.html import format_html
from django.contrib.gis.admin import GISModelAdmin
from .models import FuelPriceUpload, FuelStation

@admin.register(FuelPriceUpload)
class FuelPriceUploadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file",
        "status",
        "total_records",
        "inserted_records",
        "uploaded_at",
        "processed_at",
    )

    list_filter = ("status", "uploaded_at")
    search_fields = ("file", "error_message")
    readonly_fields = (
        "uploaded_at",
        "processed_at",
        "total_records",
        "inserted_records",
        "error_message",
    )

    ordering = ("-uploaded_at",)

@admin.register(FuelStation)
class FuelStationAdmin(GISModelAdmin):

    list_display = (
        "opis_id",
        "truckstop_name",
        "city",
        "state",
        "retail_price",
        "latitude",
        "longitude",
        "geocoded_status",
        "updated_at",
    )

    list_filter = ("state", "created_at", "updated_at")

    search_fields = (
        "truckstop_name",
        "city",
        "state",
        "address",
        "opis_id",
    )

    ordering = ("retail_price",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "geocoded_at",
        "latitude",
        "longitude",
    )

    list_per_page = 50
    show_full_result_count = False  # performance for large datasets

    # Map defaults (USA center)
    default_lon = -98.5795
    default_lat = 39.8283
    default_zoom = 4


    def latitude(self, obj):
        if obj.location:
            return round(obj.location.y, 6)
        return "-"

    latitude.short_description = "Latitude"
    latitude.admin_order_field = "location"

    def longitude(self, obj):
        if obj.location:
            return round(obj.location.x, 6)
        return "-"

    longitude.short_description = "Longitude"
    longitude.admin_order_field = "location"

    def geocoded_status(self, obj):
        if obj.location:
            return format_html(
                '<span style="color:white;background-color:green;'
                'padding:4px 8px;border-radius:6px;">YES</span>'
            )
        return format_html(
            '<span style="color:white;background-color:red;'
            'padding:4px 8px;border-radius:6px;">NO</span>'
        )

    geocoded_status.short_description = "Geocoded"