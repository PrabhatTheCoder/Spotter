#!/bin/bash

echo " Starting up the container..."
python manage.py wait_for_db


echo " Applying migrations..."
python manage.py makemigrations
python manage.py migrate

echo " Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn server..."
exec gunicorn spotter.wsgi:application --bind 0.0.0.0:8000