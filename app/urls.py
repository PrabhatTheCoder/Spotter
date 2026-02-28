from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from app.views import FuelUploadView, RouteOptimizeAPI

urlpatterns = [
    path('upload-fuel-data/', FuelUploadView.as_view(), name='upload-fuel-data'),
    path('route-optimize/', RouteOptimizeAPI.as_view(), name='route-optimize'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
