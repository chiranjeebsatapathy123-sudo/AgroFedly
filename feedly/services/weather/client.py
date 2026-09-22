import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class OpenWeatherClient:
    BASE_URL = getattr(settings, 'WEATHER_API_BASE_URL', 'https://api.openweathermap.org/data/2.5')
    
    @classmethod
    def get_api_key(cls):
        return getattr(settings, 'WEATHER_API_KEY', None)

    @classmethod
    def fetch_current(cls, lat: float = None, lon: float = None, city: str = None):
        api_key = cls.get_api_key()
        if not api_key:
            logger.error("Weather API key is missing.")
            return None
        
        try:
            url = f"{cls.BASE_URL}/weather"
            params = {'appid': api_key, 'units': 'metric'}
            if lat and lon:
                params['lat'] = lat
                params['lon'] = lon
            elif city:
                params['q'] = city
            else:
                return None
                
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Weather API fetch_current failed: {e}")
            return None
