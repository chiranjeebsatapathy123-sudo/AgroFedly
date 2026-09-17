import os
import joblib
from django.conf import settings
from django.utils import timezone
from ..models import DemandForecast

# Lazy load ML model
MODEL = None
MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml', 'demand_bundle.pkl')
if os.path.exists(MODEL_PATH):
    try:
        MODEL = joblib.load(MODEL_PATH)
    except Exception:
        MODEL = None

class DemandForecastingPipeline:
    def __init__(self, organization):
        self.org = organization

    def predict_demand(self, attendance, temperature=25, rainfall=0, holiday=0, humidity=70, exam_day=0, event_flag=0, target_date=None):
        """
        Calculates demand forecast for the organization based on input parameters.
        Saves and returns a DemandForecast object.
        """
        if not target_date:
            target_date = timezone.localdate()

        prediction_data = {
            'attendance': attendance,
            'temperature': temperature,
            'rainfall': rainfall,
            'holiday': holiday,
            'humidity': humidity,
            'exam_day': exam_day,
            'event_flag': event_flag
        }
        
        predicted_meals = 0
        confidence = 0
        model_name = "AgroFedly Heuristic Engine v2"

        if MODEL and hasattr(MODEL, 'predict'):
            try:
                import pandas as pd
                df = pd.DataFrame([prediction_data])
                predicted_meals = int(MODEL.predict(df)[0])
                model_name = "AgroFedly ML v1 (RandomForest)"
                confidence = 85.0
            except Exception as e:
                # Fallback to heuristics if ML fails
                pass
                
        # Heuristic fallback if ML is unavailable or failed
        if predicted_meals == 0:
            base = attendance * 0.85
            if holiday: base *= 0.90
            if exam_day: base *= 1.10
            if event_flag: base *= 1.25
            if rainfall > 10: base *= 0.95
            predicted_meals = int(base)
            confidence = 70.0

        # Safety buffers
        safety_buffer = int(predicted_meals * 0.05)
        recommended = predicted_meals + safety_buffer
        lower = int(predicted_meals * 0.9)
        upper = int(predicted_meals * 1.15)
        
        expected_surplus = max(0, recommended - predicted_meals)
        risk = "LOW"
        if event_flag:
            risk = "HIGH"
        elif holiday or exam_day:
            risk = "MEDIUM"
            
        # Create or update the forecast for this org and date
        forecast, created = DemandForecast.objects.update_or_create(
            organization=self.org,
            date=target_date,
            defaults={
                'predicted_demand': predicted_meals,
                'recommended_preparation': recommended,
                'lower_bound': lower,
                'upper_bound': upper,
                'confidence': confidence,
                'expected_surplus': expected_surplus,
                'waste_risk': risk,
                'model_name': model_name
            }
        )
        
        return forecast
