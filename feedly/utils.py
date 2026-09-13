import requests
import urllib.parse
from functools import lru_cache

@lru_cache(maxsize=128)
def geocode_address(address):
    """
    Converts a text address to (latitude, longitude) using OSM Nominatim.
    Uses lru_cache to avoid hammering the free API for duplicate addresses.
    """
    if not address:
        return None, None
        
    encoded_address = urllib.parse.quote(address)
    url = f"https://nominatim.openstreetmap.org/search?q={encoded_address}&format=json&limit=1"
    headers = {
        'User-Agent': 'Annadata/1.0 (Food Surplus Distribution App)'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Geocoding error for {address}: {e}")
        
    return None, None

def get_osrm_route(start_lat, start_lng, end_lat, end_lng):
    """
    Gets route data from OSRM public API.
    Returns the geometry (polyline) and distance/duration.
    """
    if None in [start_lat, start_lng, end_lat, end_lng]:
        return None
        
    # OSRM expects coordinates as longitude,latitude
    coordinates = f"{start_lng},{start_lat};{end_lng},{end_lat}"
    url = f"http://router.project-osrm.org/route/v1/driving/{coordinates}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get('code') == 'Ok' and len(data.get('routes', [])) > 0:
            route = data['routes'][0]
            return {
                'geometry': route['geometry'],
                'distance_km': round(route['distance'] / 1000, 2),
                'duration_mins': round(route['duration'] / 60)
            }
    except Exception as e:
        print(f"OSRM routing error: {e}")
        
    return None
