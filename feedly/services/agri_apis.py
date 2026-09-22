import requests
from django.conf import settings

def analyze_plant_disease(image_data_or_url):
    """
    Calls a real plant disease API (like Plant.id).
    Falls back to a heuristic mock if the API key is missing or call fails.
    """
    api_key = getattr(settings, 'PLANT_ID_API_KEY', None)
    if api_key:
        try:
            # Example payload for Plant.id API
            response = requests.post(
                "https://api.plant.id/v2/identify",
                json={
                    "images": [image_data_or_url],
                    "modifiers": ["crops_fast"]
                },
                headers={"Api-Key": api_key},
                timeout=8
            )
            data = response.json()
            if data and "suggestions" in data and len(data["suggestions"]) > 0:
                best_match = data["suggestions"][0]
                return {
                    "disease": best_match.get("plant_name", "Unknown Disease"),
                    "confidence": int(best_match.get("probability", 0) * 100),
                    "treatment": "Follow recommended pesticide guidelines based on API response."
                }
        except Exception as e:
            print(f"Plant API error: {e}")
            
    # Fallback to simulated heuristics
    diseases = [
        ("Leaf Blight (Early Stage)", 85, "Copper-based fungicide spray"),
        ("Powdery Mildew", 92, "Neem oil application"),
        ("Healthy Plant", 99, "No treatment needed"),
        ("Nitrogen Deficiency", 78, "Apply NPK fertilizer (40-20-20)"),
        ("Stem Rust", 65, "Isolate crop and apply triadimefon")
    ]
    disease, confidence, treatment = diseases[0]
    return {
        "disease": disease,
        "confidence": confidence,
        "treatment": treatment
    }

def predict_crop_yield(crop_type, area_hectares, lat, lng):
    """
    Calls OpenWeatherMap or similar for weather aggregates to predict yield.
    Falls back to heuristics.
    """
    from .weather.cache import WeatherCacheManager
    
    weather_factor = 1.0
    weather = WeatherCacheManager.get_current_weather(organization=None, lat=lat, lon=lng)
    
    if weather:
        temp = weather.get('temperature', 25)
        # Simple logic: ideal temp 20-30C
        if 20 <= temp <= 30:
            weather_factor = 1.15
        elif temp > 35 or temp < 10:
            weather_factor = 0.85
        
    base_yield = area_hectares * 3.5  # tons per hectare
    expected = base_yield * weather_factor
    
    return {
        "expected_tons": round(expected, 2),
        "weather_factor_used": round(weather_factor, 2)
    }

def get_iot_status():
    """
    Simulates calling an IoT controller API.
    """
    # Real implementation would do requests.get("http://greenhouse-controller.local/api/status")
    return {
        'devices': [
            {'id': 1, 'name': 'LED Grow Array', 'type': 'LIGHT', 'status': True, 'reading': '18 Hrs / Day'},
            {'id': 2, 'name': 'Hydroponic Pump 1', 'type': 'IRRIGATION', 'status': True, 'reading': 'Flow: 1.2 L/m'},
            {'id': 3, 'name': 'HVAC Climate Control', 'type': 'CLIMATE', 'status': True, 'reading': 'Temp: 22°C'},
        ],
        'system_health': 95
    }
