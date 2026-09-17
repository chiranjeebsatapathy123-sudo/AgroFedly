import logging
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from feedly.models import (
    Organization, OrganizationMember, Recipient, SurplusFood, 
    Delivery, Redistribution, ProduceTraceabilityLedger, SystemEvent,
    DemandForecast
)
from django.utils import timezone
from datetime import timedelta

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds the database with the deterministic SIH demo pitch dataset.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting SIH demo data seed...")
        now = timezone.now()

        try:
            # 1. Create Admin User
            user, created = User.objects.get_or_create(username="sih_admin", email="admin@sih2026.agro")
            user.set_password("sih2026")
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write("Created sih_admin user.")

            # 2. Create Organization
            org, _ = Organization.objects.get_or_create(
                name="SIH Operations HQ",
                defaults={
                    "organization_type": "COMPANY",
                    "address": "Hackathon Venue",
                    "city": "Bhubaneswar",
                    "state": "Odisha",
                    "country": "India",
                    "capacity": 10000,
                    "is_verified": True,
                    "is_active": True,
                    "onboarding_completed": True
                }
            )
            OrganizationMember.objects.get_or_create(
                user=user, organization=org, role="OWNER", status="ACTIVE"
            )
            self.stdout.write("Created SIH Operations HQ organization.")

            # 3. Create Demand Forecast (for intelligence dashboard signals)
            DemandForecast.objects.update_or_create(
                organization=org,
                date=now.date(),
                defaults={
                    "predicted_demand": 500,
                    "recommended_preparation": 550,
                    "lower_bound": 480,
                    "upper_bound": 580,
                    "confidence": 92.5,
                    "expected_surplus": 50,
                    "waste_risk": "LOW",
                    "model_name": "AgroFedly AI 2.0"
                }
            )

            # 4. Create NGO Recipient
            ngo, _ = Recipient.objects.get_or_create(
                organization=org,
                name="City Relief NGO",
                defaults={
                    "recipient_type": "NGO Shelter",
                    "capacity": 500,
                    "verified": True,
                    "distance_km": 5.2,
                    "urgency_score": 85
                }
            )
            self.stdout.write("Created City Relief NGO recipient.")

            # 5. Create Surplus Food (High freshness, Safe)
            surplus, _ = SurplusFood.objects.get_or_create(
                organization=org,
                food_name="SIH Excess Produce",
                defaults={
                    "quantity": 100,
                    "storage_temperature": 3.5,
                    "storage_time_hours": 2.0,
                    "status": "REDISTRIBUTED",
                    "ai_freshness_score": 96,
                    "ai_quality_notes": "Visually pristine. Optimal temperature maintained.",
                    "is_safe": True,
                    "safety_alert": "Safe for redistribution.",
                    "created_at": now - timedelta(hours=3)
                }
            )
            self.stdout.write("Created SIH Excess Produce surplus food.")

            # 6. Allocate Surplus to NGO
            redistribution, _ = Redistribution.objects.get_or_create(
                organization=org,
                surplus=surplus,
                recipient=ngo,
                defaults={"quantity": 100}
            )

            # 7. Create IN_TRANSIT Delivery (Crucial for Copilot demo)
            delivery_tracking_code = "ANN-SIH2026"
            delivery, _ = Delivery.objects.get_or_create(
                tracking_code=delivery_tracking_code,
                defaults={
                    "sender": org,
                    "receiver": org,  # Self-routed for demo simplicity
                    "surplus": surplus,
                    "food_name": surplus.food_name,
                    "quantity": 100,
                    "pickup_address": org.address,
                    "delivery_address": "City Relief NGO, Downtown",
                    "status": "IN_TRANSIT",
                    "driver_name": "SIH Logistics",
                    "current_lat": 20.296,
                    "current_lng": 85.824,
                    "created_by": user,
                    "created_at": now - timedelta(hours=1)
                }
            )
            # Ensure status is IN_TRANSIT (in case get_or_create got an existing one with different status)
            if delivery.status != "IN_TRANSIT":
                delivery.status = "IN_TRANSIT"
                delivery.save(update_fields=['status'])
            self.stdout.write(f"Created IN_TRANSIT delivery: {delivery_tracking_code}")

            # 8. Create Traceability Ledger Entries
            tx_id_1 = f"TX-{uuid.uuid4().hex[:8].upper()}"
            ProduceTraceabilityLedger.objects.get_or_create(
                transaction_id=tx_id_1,
                defaults={
                    "transaction_type": "QUALITY_CHECK",
                    "actor": user,
                    "organization": org,
                    "surplus": surplus,
                    "quantity": 100,
                    "details": "AI Safety evaluation passed. Status: SAFE. AI Freshness: 96/100.",
                    "timestamp": now - timedelta(hours=2)
                }
            )
            
            tx_id_2 = f"TX-{uuid.uuid4().hex[:8].upper()}"
            ProduceTraceabilityLedger.objects.get_or_create(
                transaction_id=tx_id_2,
                defaults={
                    "transaction_type": "DISPATCHED",
                    "actor": user,
                    "organization": org,
                    "surplus": surplus,
                    "quantity": 100,
                    "details": f"Dispatched 100 units to City Relief NGO. Tracking: {delivery_tracking_code}",
                    "timestamp": now - timedelta(hours=1)
                }
            )
            self.stdout.write("Created Traceability Ledger entries.")

            self.stdout.write(self.style.SUCCESS("Successfully seeded SIH demo data! Log in with 'sih_admin' / 'sih2026'."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error seeding demo data: {e}"))
            logger.exception(e)
