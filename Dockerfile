# Base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /spotter_backend_project

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /spotter_backend_project/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /spotter_backend_project/

RUN chmod +x /spotter_backend_project/entrypoints.sh

EXPOSE 8000

CMD ["./entrypoints.sh"]