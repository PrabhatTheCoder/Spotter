import os
from celery import Celery
from kombu import Queue
from decouple import config
from celery.schedules import crontab


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spotter.settings")

app = Celery("spotter")

app.conf.broker_url = config("CELERY_BROKER_URL")
app.conf.result_backend = config("CELERY_RESULT_BACKEND")

app.conf.accept_content = ["json"]
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.timezone = config("TIME_ZONE", default="UTC")

app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1
app.conf.task_reject_on_worker_lost = True

app.conf.task_queues = (
    Queue("celery"),
    # Queue("route_processing"),
    Queue("maintenance"),
)
app.conf.task_default_queue = "celery"

app.autodiscover_tasks()
CELERY_TASK_ROUTES = {
    "app.tasks.tasks.process_fuel_upload": {"queue": "maintenance"},
    "app.tasks.tasks.geocode_stations": {"queue": "maintenance"},
}

app.conf.beat_schedule = {
    "geocode-every-10-seconds": {
        "task": "app.tasks.tasks.geocode_stations",
        "schedule": 10.0,  # every 10 seconds
        "options": {"queue": "maintenance"},
    },
}