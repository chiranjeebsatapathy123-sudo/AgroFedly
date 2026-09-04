import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from feedly.models import (
    DemandForecast, Delivery, MealRecord, Organization, OrganizationMember,
    Recipient, Redistribution, SurplusFood, IoTTemperatureReading,
)
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds realistic demo data for the prototype.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting safe demo data generation...")

        # 1. Create a dummy organization for Receiving
        receiver_user, _ = User.objects.get_or_create(username='receiver_demo', defaults={'email': 'receiver@example.com'})
        if receiver_user.password == "":
            receiver_user.set_password("password123")
            receiver_user.save()

        receiver_org, created = Organization.objects.get_or_create(
            name="Demo Receiver NGO",
            defaults={
                "organization_type": "NGO",
                "email": "receiver@example.com",
                "address": "123 Receiver St",
                "city": "Demo City",
                "capacity": 500,
                "is_verified": True
            }
        )
        if created:
            OrganizationMember.objects.get_or_create(
                organization=receiver_org,
                user=receiver_user,
                defaults={"role": "OWNER"}
            )
            self.stdout.write("Created Demo Receiver NGO")
        else:
            self.stdout.write("Demo Receiver NGO already exists")

        # 2. Get main org (assuming it's the first one, or create one if none exists)
        main_org = Organization.objects.exclude(id=receiver_org.id).first()
        if not main_org:
            main_user, _ = User.objects.get_or_create(username='main_demo', defaults={'email': 'main@example.com'})
            if main_user.password == "":
                main_user.set_password("password123")
                main_user.save()
            main_org = Organization.objects.create(name="Main Tech Campus", organization_type="COMPANY", capacity=1000, is_verified=True)
            OrganizationMember.objects.create(organization=main_org, user=main_user, role="OWNER")
            self.stdout.write("Created Main Tech Campus org")
        else:
            self.stdout.write(f"Using existing main org: {main_org.name}")

        # 3. Create verified recipients
        recipient1, created = Recipient.objects.get_or_create(
            name="City Orphanage",
            defaults={"recipient_type": "Orphanage", "capacity": 150, "verified": True, "distance_km": 5.2, "urgency_score": 85}
        )
        recipient2, created = Recipient.objects.get_or_create(
            name="Downtown Soup Kitchen",
            defaults={"recipient_type": "Soup Kitchen", "capacity": 300, "verified": True, "distance_km": 2.1, "urgency_score": 90}
        )
        if created:
            self.stdout.write("Created verified recipients")
        
        # 4. Generate 30 days of historical meal records
        today = timezone.localdate()
        if not MealRecord.objects.exists():
            for i in range(30, -1, -1):
                date = today - timedelta(days=i)
                attendance = random.randint(300, 450)
                prepared = int(attendance * 0.86) + random.randint(10, 30)
                consumed = prepared - random.randint(5, max(10, int(prepared * 0.1)))
                MealRecord.objects.create(
                    date=date,
                    attendance=attendance,
                    meals_prepared=prepared,
                    meals_consumed=consumed,
                    temperature=26.5 + random.uniform(-2, 2),
                    humidity=65 + random.uniform(-10, 10),
                    meal_type="Mixed",
                    data_source="ERP" if random.random() > 0.5 else "MANUAL"
                )
            self.stdout.write("Generated 31 days of MealRecords")
        else:
            self.stdout.write("MealRecords already exist")

        # 5. Generate Surplus Food
        if not SurplusFood.objects.exists():
            surplus = SurplusFood.objects.create(
                organization=main_org,
                food_name="Vegetable Biryani",
                quantity=45,
                storage_temperature=4.0,
                storage_time_hours=2.5,
                status="SAFE",
                is_safe=True
            )
            SurplusFood.objects.create(
                organization=main_org,
                food_name="Dal Makhani",
                quantity=15,
                storage_temperature=2.0,
                storage_time_hours=1.0,
                status="SAFE",
                is_safe=True
            )
            self.stdout.write("Generated SurplusFood records")
        else:
            self.stdout.write("SurplusFood records already exist")

        # 6. Generate Forecasts if few exist
        if DemandForecast.objects.count() < 10:
            for i in range(30, 0, -1):
                date = today - timedelta(days=i)
                if not DemandForecast.objects.filter(date=date).exists():
                    DemandForecast.objects.create(
                        date=date,
                        predicted_demand=350 + random.randint(-20, 20),
                        recommended_preparation=380 + random.randint(-20, 20),
                        lower_bound=330,
                        upper_bound=400,
                        confidence=85.0 + random.uniform(-5, 5),
                        expected_surplus=30,
                        waste_risk="LOW",
                        model_name="FedlySmartForecast"
                    )
            self.stdout.write("Generated DemandForecast history")

        # 7. Generate IoT Readings
        if not IoTTemperatureReading.objects.exists():
            IoTTemperatureReading.objects.create(
                sensor_name="Storage Room A",
                food_name="Vegetable Biryani",
                temperature=3.5,
                unit="°C",
                location="Main Kitchen Fridge",
                status="SAFE"
            )
            self.stdout.write("Generated IoT Temperature Reading")

        self.stdout.write(self.style.SUCCESS("Demo data generation complete!"))
