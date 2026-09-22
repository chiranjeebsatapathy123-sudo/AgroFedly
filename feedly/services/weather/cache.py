from datetime import timedelta
from django.utils import timezone
from ...models import WeatherObservation, WeatherForecast, Farm, FarmField
from .client import OpenWeatherClient

class WeatherCacheManager:
    CACHE_EXPIRY_MINUTES = 30
    
    @classmethod
    def get_current_weather(cls, organization=None, farm=None, field=None, lat=None, lon=None, city=None):
        if not lat and not lon and not city:
            return None
            
        # 1. Check DB Cache
        query = WeatherObservation.objects.all().order_by('-observed_at')
        if lat and lon:
            query = query.filter(latitude=lat, longitude=lon)
        if farm:
            query = query.filter(farm=farm)
        if field:
            query = query.filter(field=field)
            
        latest = query.first()
        if latest and latest.observed_at >= timezone.now() - timedelta(minutes=cls.CACHE_EXPIRY_MINUTES):
            return cls._serialize_observation(latest)
            
        # 2. Fetch fresh data
        data = OpenWeatherClient.fetch_current(lat=lat, lon=lon, city=city)
        if not data:
            return cls._serialize_observation(latest) if latest else None
            
        # Extract lat/lon from response if we used city
        resolved_lat = data.get('coord', {}).get('lat', lat or 0.0)
        resolved_lon = data.get('coord', {}).get('lon', lon or 0.0)

        # 3. Save to Cache
        obs = WeatherObservation.objects.create(
            organization=organization,
            farm=farm,
            field=field,
            latitude=resolved_lat,
            longitude=resolved_lon,
            temperature=data['main']['temp'],
            feels_like=data['main'].get('feels_like'),
            humidity=data['main'].get('humidity'),
            pressure=data['main'].get('pressure'),
            wind_speed=data.get('wind', {}).get('speed'),
            wind_direction=data.get('wind', {}).get('deg'),
            cloud_cover=data.get('clouds', {}).get('all'),
            precipitation=data.get('rain', {}).get('1h', 0.0) if 'rain' in data else 0.0,
            condition=data['weather'][0]['description'] if data.get('weather') else 'Unknown'
        )
        return cls._serialize_observation(obs)

    @classmethod
    def get_forecast(cls, farm=None, field=None, lat=None, lon=None):
        if not lat or not lon:
            return []
            
        # For simplicity in this phase, we skip complex parsing of 5-day forecast.
        # It's prepared for database extension but returns empty now to avoid fake data.
        return []

    @classmethod
    def _serialize_observation(cls, obs):
        return {
            'temperature': obs.temperature,
            'feels_like': obs.feels_like,
            'humidity': obs.humidity,
            'precipitation': obs.precipitation,
            'rainfall': obs.precipitation, # Alias for backwards compatibility
            'wind_speed': obs.wind_speed,
            'condition': obs.condition.title(),
            'weather': obs.condition.title(), # Alias
            'observed_at': obs.observed_at.isoformat(),
            'is_live': True
        }
