from django.core.management.base import BaseCommand
from feedly.models import Organization, OrganizationMember, AgriculturalProduce, ProcessingRecord, BuyerDemand
from django.contrib.auth.models import User
import datetime
from django.utils import timezone

class Command(BaseCommand):
    help = 'Loads sample agriculture and supply chain data without corrupting existing records.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Checking for existing demo data...")

        # Create Farmer/Supplier Organization
        user, _ = User.objects.get_or_create(username="demo_farmer", defaults={"email": "farmer@example.com"})
        if user.check_password('password'):
            pass # keep password if exists
        else:
            user.set_password('password')
            user.save()
            
        supplier, created_supp = Organization.objects.get_or_create(
            name="Green Valley Farms (Demo)",
            defaults={
                "organization_type": "SUPPLIER",
                "address": "Bhubaneswar Outskirts",
                "email": "farmer@greenvalley.test",
                "is_active": True
            }
        )
        OrganizationMember.objects.get_or_create(user=user, organization=supplier, role="OWNER", is_active=True)

        # Create NGO/Buyer Organization
        buyer_user, _ = User.objects.get_or_create(username="demo_ngo", defaults={"email": "ngo@example.com"})
        buyer_user.set_password('password')
        buyer_user.save()
        
        ngo, created_ngo = Organization.objects.get_or_create(
            name="City Relief NGO (Demo)",
            defaults={
                "organization_type": "NGO",
                "address": "Bhubaneswar Center",
                "email": "ngo@cityrelief.test",
                "is_active": True
            }
        )
        OrganizationMember.objects.get_or_create(user=buyer_user, organization=ngo, role="OWNER", is_active=True)

        self.stdout.write(self.style.SUCCESS('Organizations verified/created.'))

        # Add Produce
        if not AgriculturalProduce.objects.filter(supplier=supplier).exists():
            prod1 = AgriculturalProduce.objects.create(
                supplier=supplier,
                name="Fresh Tomatoes",
                category="Vegetables",
                crop_type="Roma",
                quantity=500.0,
                unit="kg",
                available_quantity=500.0,
                harvest_date=timezone.now().date() - datetime.timedelta(days=1),
                location="Bhubaneswar",
                expected_shelf_life_days=7,
                storage_condition="Cold Storage",
                quality_status="Grade A"
            )
            AgriculturalProduce.objects.create(
                supplier=supplier,
                name="Wheat",
                category="Grains",
                crop_type="Durum",
                quantity=1000.0,
                unit="kg",
                available_quantity=1000.0,
                harvest_date=timezone.now().date() - datetime.timedelta(days=30),
                location="Cuttack",
                expected_shelf_life_days=365,
                storage_condition="Dry Silo",
                quality_status="Grade B"
            )
            self.stdout.write(self.style.SUCCESS('Produce added.'))
            
            # Add Processing Record for Tomato
            ProcessingRecord.objects.create(
                input_produce=prod1,
                input_quantity=100.0,
                processing_type="Pureeing",
                output_product="Tomato Puree Cans",
                output_quantity=90.0,
                processing_facility="Green Valley Processing Unit",
                status="Completed",
                waste_quantity=10.0
            )
            prod1.available_quantity -= 100.0
            prod1.save()
            self.stdout.write(self.style.SUCCESS('Processing record added.'))
            
        if not BuyerDemand.objects.filter(organization=ngo).exists():
            BuyerDemand.objects.create(
                organization=ngo,
                produce_name="Tomatoes",
                required_quantity=50.0,
                unit="kg",
                quality_requirement="Grade A",
                location="Bhubaneswar",
                required_date=timezone.now().date() + datetime.timedelta(days=2),
            )
            self.stdout.write(self.style.SUCCESS('Buyer demand added.'))

        self.stdout.write(self.style.SUCCESS('Demo data load complete! You can log in with "demo_farmer" or "demo_ngo" / password.'))
