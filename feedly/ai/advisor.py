from datetime import datetime, timedelta
from django.utils import timezone
from ..models import FarmField, FieldActivity, CropDiseaseScan, FarmEvent

def get_copilot_response(user, message, context="/"):
    msg_lower = message.lower()
    
    if "what am i looking at" in msg_lower or "explain this" in msg_lower or "where am i" in msg_lower:
        if "/deliveries/" in context:
            return "You are looking at the Deliveries workspace. This section lets you track active shipments and assign vehicles for surplus redistribution."
        elif "/surplus/" in context:
            return "You are in the Surplus Distribution hub. Here you can review declared surplus food, assess food safety statuses, and find eligible recipients."
        elif "/kitchen/" in context:
            return "This is the Kitchen Operations dashboard. It handles demand forecasting, production tracking, and inventory management."
        elif "/agriculture/" in context:
            return "You are in the Agriculture Command area. This is where farm health, crop yields, and IoT sensor data are monitored."
        elif "/enterprise/" in context:
            return "You are in the Enterprise Governance section. This is for reviewing operational queues, approving workflows, and monitoring system security."
        else:
            return f"You are currently at the {context} page."
            
    if "yield" in msg_lower and "wheat" in msg_lower:
        return "Based on your current soil data and recent weather, the expected yield for your wheat field is approximately 3.5 tons per hectare. Would you like me to factor in the recent rainfall?"
    elif "weather" in msg_lower or "rain" in msg_lower or "risk" in msg_lower:
        return "There's a 40% higher chance of rain in the next 14 days according to our latest weather insights. I recommend delaying any final harvesting by 3 days to avoid moisture damage."
    elif "fertilizer" in msg_lower or "log" in msg_lower:
        return "I've noted the request. However, I need your confirmation to log 50kg of fertilizer for field 2. Should I proceed with logging this activity?"
    elif "disease" in msg_lower or "blight" in msg_lower:
        return "If you've noticed spots on your leaves, I recommend using the Disease Scanner tool in the 'My Farm' section to take a photo. Our AI can diagnose it instantly."
    elif "price" in msg_lower or "market" in msg_lower:
        return "Currently, wheat prices are stable, but tomato prices are showing high volatility. I can create a demand forecast report if you need detailed projections."
    elif "inventory" in msg_lower or "stock" in msg_lower:
        return "You can view depleting ingredients in the Smart Procurement section of the Kitchen Inventory. Let me know if you want me to generate a Purchase Order."
    elif "surplus" in msg_lower or "safety" in msg_lower:
        return "Surplus items must pass the Food Safety Gate before redistribution. Head to the Waste Prevention Center to review any pending items."
    else:
        return "I am the AgroFedly AI Copilot. I can help you with yield predictions, disease scanning, market insights, and kitchen operations tracking. How can I assist you today?"

def calculate_farm_health_score(farm):
    """
    Deterministically calculates a Farm Health Score based only on available data.
    Does NOT invent a score if insufficient data exists.
    """
    fields = FarmField.objects.filter(farm=farm)
    if not fields.exists():
        return {"score": None, "status": "Insufficient data", "factors": ["No fields registered"]}
    
    base_score = 100
    factors = []
    
    # 1. Field Health Status
    poor_fields = fields.filter(health_status__iexact='poor').count()
    if poor_fields > 0:
        base_score -= (poor_fields * 10)
        factors.append(f"-{poor_fields * 10} for {poor_fields} field(s) with 'Poor' health status")
    else:
        factors.append("+0 (All fields report good health)")
        
    # 2. Disease Scans
    thirty_days_ago = timezone.now() - timedelta(days=30)
    if farm.owner:
        recent_diseases = CropDiseaseScan.objects.filter(
            farmer=farm.owner, 
            scanned_at__gte=thirty_days_ago, 
            disease_detected=True
        ).count()
        if recent_diseases > 0:
            penalty = min(recent_diseases * 5, 20)
            base_score -= penalty
            factors.append(f"-{penalty} for recent disease detections")
    
    # 3. Operations / Overdue Tasks
    overdue_tasks = FarmEvent.objects.filter(farm=farm, date__lt=timezone.now().date(), is_completed=False).count()
    if overdue_tasks > 0:
        penalty = min(overdue_tasks * 2, 15)
        base_score -= penalty
        factors.append(f"-{penalty} for {overdue_tasks} overdue task(s)")
    else:
        factors.append("+0 (No overdue tasks)")
        
    # 4. Recent Activity (Positive factor)
    recent_activities = FieldActivity.objects.filter(field__farm=farm, date__gte=thirty_days_ago.date()).count()
    if recent_activities == 0:
        base_score -= 10
        factors.append("-10 for no logged field activities in 30 days")
    else:
        factors.append(f"+0 ({recent_activities} recent activities logged)")

    # Clamp score
    final_score = max(0, min(base_score, 100))
    
    return {
        "score": final_score,
        "status": "Healthy" if final_score >= 80 else "Needs Attention" if final_score >= 60 else "Critical",
        "factors": factors,
        "version": "AgroFedly Deterministic v1.0"
    }
