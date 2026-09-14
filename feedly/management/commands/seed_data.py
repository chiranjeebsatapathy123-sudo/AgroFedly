import os
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from feedly.models import (
    AgriculturalProduce, SurplusFood, CommunityFridge, 
    P2PFoodSwap, DisasterZone, AgriTourismListing, 
    GreenhouseDevice
)
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with realistic mock data for Phase 1-6.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting data seed...")

        # Create base users if they don't exist
        farmer, _ = User.objects.get_or_create(username="farmer_john", email="john@farm.com")
        farmer.set_password("password123")
        farmer.persona = "farmer"
        farmer.save()

        user, _ = User.objects.get_or_create(username="consumer_jane", email="jane@gmail.com")
        user.set_password("password123")
        user.persona = "user"
        user.save()

        # Seed Produce Inventory
        if not AgriculturalProduce.objects.exists():
            AgriculturalProduce.objects.create(farmer=farmer, crop_name="Organic Tomatoes", quantity_kg=500, price_per_kg=45)
            AgriculturalProduce.objects.create(farmer=farmer, crop_name="Basmati Rice", quantity_kg=2000, price_per_kg=80)
            self.stdout.write("Seeded Produce Inventory.")

        # Seed Community Fridges
        if not CommunityFridge.objects.exists():
            CommunityFridge.objects.create(name="Central Park Fridge", location_address="123 Park Ave", status="FULL")
            CommunityFridge.objects.create(name="Downtown Shelter Fridge", location_address="45 Main St", status="LOW")
            self.stdout.write("Seeded Community Fridges.")

        # Seed Food Swaps
        if not P2PFoodSwap.objects.exists():
            P2PFoodSwap.objects.create(user=user, item_name="Homegrown Zucchini", quantity="3 large", status="AVAILABLE")
            self.stdout.write("Seeded Food Swaps.")

        # Seed Disaster Zones
        if not DisasterZone.objects.exists():
            DisasterZone.objects.create(name="Kerala Floods 2026", urgency_level="CRITICAL", lat=10.85, lng=76.27, required_meals=50000, meals_fulfilled=12000)
            DisasterZone.objects.create(name="Assam River Overflow", urgency_level="HIGH", lat=26.20, lng=92.93, required_meals=15000, meals_fulfilled=8000)
            self.stdout.write("Seeded Disaster Zones.")

        # Seed Agri Tourism
        if not AgriTourismListing.objects.exists():
            AgriTourismListing.objects.create(farmer=farmer, title="Weekend Organic Farm Stay", description="Stay in our farm.", price_per_night=2500, activity_type="FARM_STAY")
            AgriTourismListing.objects.create(farmer=farmer, title="Mango Picking Tour", description="Pick mangoes.", price_per_night=800, activity_type="TOUR")
            self.stdout.write("Seeded Agri Tourism.")

        # Seed Greenhouse Devices
        if not GreenhouseDevice.objects.exists():
            GreenhouseDevice.objects.create(farmer=farmer, name="LED Grow Array", device_type="LIGHT", status=True, reading="18 Hrs / Day")
            GreenhouseDevice.objects.create(farmer=farmer, name="Hydroponic Pump", device_type="IRRIGATION", status=False, reading="Flow: 0 L/m")
            self.stdout.write("Seeded Greenhouse Devices.")

        self.stdout.write(self.style.SUCCESS("Successfully seeded all mock data!"))
