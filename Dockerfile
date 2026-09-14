# Use official lightweight Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE AgroFedly.settings

# Set working directory
WORKDIR /app

# Install system dependencies (for building some python packages if needed)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install daphne redis celery psycopg2-binary

# Copy the rest of the application
COPY . /app/

# Expose port
EXPOSE 8000

# Start command using Daphne for ASGI
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "AgroFedly.asgi:application"]
