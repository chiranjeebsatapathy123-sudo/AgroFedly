from django.utils import timezone
from datetime import timedelta
import random

def predict_kitchen_demand(kitchen, meal_session, date, expected_attendance=0, event_mode="Normal"):
    """
    Dummy AI demand prediction service.
    In a real scenario, this would query a trained ML model.
    """
    from feedly.models import MealRecord
    
    # Get historical records
    history = MealRecord.objects.filter(kitchen=kitchen, meal_session=meal_session).order_by('-date')[:30]
    
    if len(history) < 5:
        return {
            "status": "insufficient_data",
            "message": "Not enough data for a reliable forecast.",
            "forecast": None,
            "confidence": 0
        }
        
    # Dummy calculation based on history and expected attendance
    avg_consumption = sum([r.meals_consumed for r in history]) / len(history)
    
    base_forecast = avg_consumption
    if expected_attendance > 0:
        base_forecast = expected_attendance * 0.95 # Assuming 95% turn up
        
    if event_mode == "Festival":
        base_forecast *= 1.2
    elif event_mode == "Exam":
        base_forecast *= 0.8
        
    return {
        "status": "success",
        "forecast": int(base_forecast),
        "confidence": 85,
        "message": "Forecast generated successfully."
    }

def evaluate_surplus_safety(surplus_record, organization_rules=None):
    """
    Evaluate if the surplus food is safe for redistribution.
    """
    if not surplus_record.preparation_record:
        surplus_record.safety_status = "NOT_ELIGIBLE"
        surplus_record.safety_alert = "No preparation record found."
        surplus_record.save()
        return False
        
    prep_time = surplus_record.preparation_record.preparation_time
    time_elapsed = (timezone.now() - prep_time).total_seconds() / 3600.0
    
    # Example rules
    max_hours = 4.0
    max_temp = 5.0 # Celsius for cold storage, but let's assume general safety
    
    if time_elapsed > max_hours:
        surplus_record.safety_status = "EXPIRED"
        surplus_record.safety_alert = f"Time elapsed ({time_elapsed:.1f}h) exceeds safety limit ({max_hours}h)."
        surplus_record.save()
        return False
        
    if surplus_record.measured_temperature and surplus_record.measured_temperature > max_temp and surplus_record.storage_temperature <= 4.0:
        surplus_record.safety_status = "NOT_ELIGIBLE"
        surplus_record.safety_alert = f"Temperature ({surplus_record.measured_temperature}°C) is unsafe."
        surplus_record.save()
        return False
        
    surplus_record.safety_status = "ELIGIBLE"
    surplus_record.is_safe = True
    surplus_record.safety_alert = "Passed safety checks."
    surplus_record.save()
    return True
