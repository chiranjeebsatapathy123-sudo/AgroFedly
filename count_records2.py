import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedora.settings')
django.setup()

from django.contrib.auth import get_user_model
from feedly.models import (
    DemandForecast, Delivery, MealRecord, Organization, OrganizationMember,
    Recipient, Redistribution, SurplusFood, IoTTemperatureReading,
)

User = get_user_model()

counts = {
    "Users": User.objects.count(),
    "Organizations": Organization.objects.count(),
    "Organization Members": OrganizationMember.objects.count(),
    "Meals": MealRecord.objects.count(),
    "Demand Forecasts": DemandForecast.objects.count(),
    "Recipients": Recipient.objects.count(),
    "Surplus Food": SurplusFood.objects.count(),
    "Redistribution Records": Redistribution.objects.count(),
    "IoT Temperature Readings": IoTTemperatureReading.objects.count(),
    "Deliveries": Delivery.objects.count(),
}

print("=== DB_RECORD_COUNTS ===")
for model_name, count in counts.items():
    print(f"{model_name}: {count}")
print("=== END_DB_RECORD_COUNTS ===")
