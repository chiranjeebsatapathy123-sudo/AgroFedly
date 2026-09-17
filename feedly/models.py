from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
import uuid

class MealRecord(models.Model):
    date = models.DateField(db_index=True)
    attendance = models.PositiveIntegerField(default=0)
    meals_prepared = models.PositiveIntegerField(default=0)
    meals_consumed = models.PositiveIntegerField(default=0)
    holiday = models.BooleanField(default=False)
    rainfall = models.FloatField(default=0.0, validators=[MinValueValidator(0)])
    temperature = models.FloatField(default=25.0)
    humidity = models.FloatField(default=70.0)
    meal_type = models.CharField(max_length=50, default="Mixed")
    exam_day = models.BooleanField(default=False)
    event_flag = models.BooleanField(default=False)
    location = models.CharField(max_length=120, default="Project Site")
    data_source = models.CharField(max_length=30, default="PROJECT_PROVIDED")
    
    # SIH26197 Additions
    predicted_demand = models.PositiveIntegerField(default=0, null=True, blank=True)
    safety_buffer_percent = models.FloatField(default=5.0)
    recommended_production = models.PositiveIntegerField(default=0, null=True, blank=True)
    leftover_meals = models.PositiveIntegerField(default=0, null=True, blank=True)
    discarded_meals = models.PositiveIntegerField(default=0, null=True, blank=True)

    # Phase 8: Kitchen Additions
    kitchen = models.ForeignKey('Kitchen', on_delete=models.SET_NULL, null=True, blank=True, related_name="meal_records")
    expected_attendance = models.PositiveIntegerField(default=0)
    meal_session = models.CharField(max_length=50, default="Lunch") # Breakfast, Lunch, Dinner, Snack
    event_mode = models.CharField(max_length=100, default="Normal") # Normal, Exam, Festival, etc.

    def __str__(self):
        return str(self.date)

class DemandForecast(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="demandforecasts", null=True, blank=True)
    date = models.DateField()
    predicted_demand = models.PositiveIntegerField(default=0)
    recommended_preparation = models.PositiveIntegerField(default=0)
    lower_bound = models.PositiveIntegerField(default=0)
    upper_bound = models.PositiveIntegerField(default=0)
    confidence = models.FloatField(default=0.0)
    expected_surplus = models.PositiveIntegerField(default=0)
    waste_risk = models.CharField(max_length=20, default="LOW")
    model_name = models.CharField(max_length=100, default="FedlyFallback")

    def __str__(self):
        return f"{self.date} — {self.predicted_demand}"

class Organization(models.Model):
    ORGANIZATION_TYPES = [
        ("COMPANY", "Company"),
        ("COLLEGE", "College"),
        ("SCHOOL", "School"),
        ("HOSPITAL", "Hospital"),
        ("NGO", "NGO / Non-Profit"),
        ("INSTITUTION", "Other Institution"),
        ("SUPPLIER", "Agricultural Supplier / Farmer"),
    ]

    name = models.CharField(max_length=200)
    organization_type = models.CharField(max_length=30, choices=ORGANIZATION_TYPES)
    registration_number = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="India")
    
    # Onboarding Status
    onboarding_step = models.IntegerField(default=1)
    onboarding_completed = models.BooleanField(default=False)
    website = models.URLField(blank=True)
    capacity = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class OrganizationImpact(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="impact")
    total_meals_saved = models.PositiveIntegerField(default=0)
    total_co2_reduced_kg = models.FloatField(default=0.0)
    impact_points = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.organization.name} Impact"

class OrganizationMember(models.Model):
    ROLE_CHOICES = [
        ("OWNER", "Owner"),
        ("ADMIN", "Administrator"),
        ("MANAGER", "Manager"),
        ("STAFF", "Staff"),
        ("VIEWER", "Viewer"),
    ]
    STATUS_CHOICES = [
        ("INVITED", "Invited"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("REMOVED", "Removed"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships", null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="STAFF")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    is_active = models.BooleanField(default=True) # DEPRECATED: Use status
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_member",
            )
        ]

    def __str__(self):
        return f"{self.user.username} — {self.organization.name}"

class VolunteerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="volunteer_profile")
    phone = models.CharField(max_length=30, blank=True)
    vehicle_type = models.CharField(max_length=50, blank=True, help_text="e.g., Bike, Car, Van")
    vehicle_number = models.CharField(max_length=50, blank=True)
    is_available = models.BooleanField(default=True)
    total_deliveries = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (Volunteer)"

class Recipient(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="recipients", null=True, blank=True)
    name = models.CharField(max_length=150)
    recipient_type = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(default=0)
    verified = models.BooleanField(default=False)
    distance_km = models.FloatField(default=0.0, validators=[MinValueValidator(0)])
    urgency_score = models.PositiveIntegerField(default=50, validators=[MaxValueValidator(100)])

    def __str__(self):
        return self.name

class SurplusFood(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SAFE", "Safe"),
        ("WARNING", "Warning"),
        ("UNSAFE", "Unsafe"),
        ("REDISTRIBUTED", "Redistributed"),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name="surplus_food"
    )
    food_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    storage_temperature = models.FloatField(default=4.0)
    storage_time_hours = models.FloatField(default=0.0, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    
    # AI Quality Control fields
    quality_image = models.ImageField(upload_to="surplus_quality/", null=True, blank=True)
    ai_freshness_score = models.IntegerField(null=True, blank=True, help_text="AI calculated freshness out of 100")
    ai_quality_notes = models.TextField(blank=True, help_text="AI vision analysis notes")
    
    is_safe = models.BooleanField(default=False)
    safety_alert = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Phase 8: Kitchen Additions
    kitchen = models.ForeignKey('Kitchen', on_delete=models.SET_NULL, null=True, blank=True, related_name="surplus_records")
    preparation_record = models.ForeignKey('PreparationRecord', on_delete=models.SET_NULL, null=True, blank=True, related_name="surplus_records")
    measured_temperature = models.FloatField(null=True, blank=True)
    safety_status = models.CharField(max_length=50, default="PENDING_CHECK") # PENDING_CHECK, ELIGIBLE, NOT_ELIGIBLE, EXPIRED

    def check_safety(self, user=None):
        from feedly.services.food_safety import evaluate_food_safety
        evaluate_food_safety(self, user=user)

    def __str__(self):
        return self.food_name

class Redistribution(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="redistributions", null=True, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    surplus = models.ForeignKey(SurplusFood, on_delete=models.CASCADE, related_name="redistributions")
    recipient = models.ForeignKey(Recipient, on_delete=models.CASCADE, related_name="redistributions")
    distributed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.surplus.food_name} → {self.recipient.name}"

class IoTTemperatureReading(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="iottemperaturereadings", null=True, blank=True)
    STATUS_CHOICES = [("SAFE", "Safe"), ("ALERT", "Alert")]
    sensor_name = models.CharField(max_length=100, default="Manual / IoT Sensor")
    food_name = models.CharField(max_length=100)
    temperature = models.FloatField()
    unit = models.CharField(max_length=10, default="°C")
    location = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="SAFE")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.food_name} — {self.temperature}{self.unit}"

class Delivery(models.Model):
    STATUS_CHOICES = [
        ("REQUESTED", "Requested"),
        ("ASSIGNED", "Driver Assigned"),
        ("PICKED_UP", "Picked Up"),
        ("IN_TRANSIT", "In Transit"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    sender = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="outgoing_deliveries")
    receiver = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="incoming_deliveries")
    surplus = models.ForeignKey(SurplusFood, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    food_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    recipient_contact = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    volunteer_driver = models.ForeignKey('VolunteerProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_deliveries')
    vehicle_number = models.CharField(max_length=50, blank=True)
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)
    proof_image = models.ImageField(upload_to="delivery_proofs/", null=True, blank=True)
    recipient_signature = models.TextField(blank=True, help_text="Base64 encoded signature image data")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="REQUESTED", db_index=True)
    tracking_code = models.CharField(max_length=20, unique=True, editable=False)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = f"ANN-{uuid.uuid4().hex[:8].upper()}"
            
        if self.pk:
            # Enforce state machine rules for existing records
            old_instance = Delivery.objects.get(pk=self.pk)
            old_status = old_instance.status
            new_status = self.status
            
            valid_transitions = {
                'REQUESTED': ['ASSIGNED', 'CANCELLED'],
                'ASSIGNED': ['PICKED_UP', 'CANCELLED'],
                'PICKED_UP': ['IN_TRANSIT', 'CANCELLED'],
                'IN_TRANSIT': ['DELIVERED', 'CANCELLED'],
                'DELIVERED': [],
                'CANCELLED': []
            }
            
            if old_status != new_status and new_status not in valid_transitions.get(old_status, []):
                raise ValueError(f"Illegal transition from {old_status} to {new_status}.")
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_code} — {self.food_name}"

class Ingredient(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="ingredients", null=True, blank=True)
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, default="kg")
    quantity_per_meal = models.FloatField(help_text="Quantity required per meal")
    cost_per_unit = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class AgriculturalProduce(models.Model):
    supplier = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="produce_inventory", null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="individual_produce", null=True, blank=True)
    farm = models.ForeignKey('FarmField', on_delete=models.SET_NULL, null=True, blank=True, related_name='produces')
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100)
    crop_type = models.CharField(max_length=100)
    batch_number = models.CharField(max_length=50, blank=True)
    quantity = models.FloatField(validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=20, default="kg")
    available_quantity = models.FloatField(validators=[MinValueValidator(0)])
    harvest_date = models.DateField()
    location = models.CharField(max_length=150, blank=True)
    expected_shelf_life_days = models.PositiveIntegerField(default=7)
    storage_condition = models.CharField(max_length=100, default="Room Temperature")
    quality_status = models.CharField(max_length=50, default="Good")
    processing_status = models.CharField(max_length=50, default="RAW")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.available_quantity} {self.unit})"

    def risk_level(self):
        from datetime import date
        days_passed = (date.today() - self.harvest_date).days
        remaining = self.expected_shelf_life_days - days_passed
        if remaining > 5:
            return "Low"
        elif remaining > 2:
            return "Medium"
        else:
            return "High"

class ProcessingRecord(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="processingrecords", null=True, blank=True)
    input_produce = models.ForeignKey(AgriculturalProduce, on_delete=models.CASCADE, related_name="processing_records")
    input_quantity = models.FloatField(validators=[MinValueValidator(0.1)])
    processing_type = models.CharField(max_length=150)
    output_product = models.CharField(max_length=150)
    output_quantity = models.FloatField(validators=[MinValueValidator(0)])
    processing_date = models.DateField(auto_now_add=True)
    processing_facility = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=50, default="Completed")
    waste_quantity = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def processing_yield_percent(self):
        if self.input_quantity > 0:
            return round((self.output_quantity / self.input_quantity) * 100, 1)
        return 0
        
    @property
    def processing_loss_percent(self):
        if self.input_quantity > 0:
            return round(((self.input_quantity - self.output_quantity) / self.input_quantity) * 100, 1)
        return 0

    def __str__(self):
        return f"{self.processing_type}: {self.input_produce.name} → {self.output_product}"

class AgriculturalSupplyRequest(models.Model):
    STATUS_CHOICES = [
        ("REQUESTED", "Requested"),
        ("VERIFIED", "Verified"),
        ("DISPATCHED", "Dispatched"),
        ("IN_TRANSIT", "In Transit"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]
    requester = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="supply_requests")
    produce = models.ForeignKey(AgriculturalProduce, on_delete=models.CASCADE, related_name="supply_requests")
    requested_quantity = models.FloatField(validators=[MinValueValidator(0.1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="REQUESTED")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.requester.name} requested {self.requested_quantity} of {self.produce.name}"

class BuyerDemand(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="buyer_demands", null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="individual_demands", null=True, blank=True)
    produce_name = models.CharField(max_length=150)
    required_quantity = models.FloatField(validators=[MinValueValidator(0.1)])
    unit = models.CharField(max_length=20, default="kg")
    quality_requirement = models.CharField(max_length=50, blank=True, help_text="e.g., Grade A")
    location = models.CharField(max_length=150, blank=True)
    required_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.organization.name} needs {self.required_quantity} {self.unit} of {self.produce_name}"

class SupplyMatch(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("CANCELLED", "Cancelled"),
    ]
    demand = models.ForeignKey(BuyerDemand, on_delete=models.CASCADE, related_name="matches")
    produce = models.ForeignKey(AgriculturalProduce, on_delete=models.CASCADE, related_name="matches")
    matched_quantity = models.FloatField(validators=[MinValueValidator(0.1)])
    match_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    explanation = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Match: {self.demand.produce_name} ({self.match_score}%)"

class QualityInspection(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="qualityinspections", null=True, blank=True)
    inspector_name = models.CharField(max_length=150)
    inspection_date = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    passed = models.BooleanField(default=True)
    produce = models.ForeignKey('AgriculturalProduce', on_delete=models.CASCADE, related_name='inspections')

class CropDiseaseScan(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="cropdiseasescans", null=True, blank=True)
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    crop_name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='disease_scans/', null=True, blank=True)
    detected_disease = models.CharField(max_length=150)
    confidence = models.FloatField()
    recommended_treatment = models.TextField()
    scanned_at = models.DateTimeField(auto_now_add=True)

class AgriculturalShipment(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="agriculturalshipments", null=True, blank=True)
    tracking_code = models.CharField(unique=True, max_length=20)
    supply_match = models.ForeignKey('SupplyMatch', on_delete=models.CASCADE, related_name='shipments')
    status = models.CharField(max_length=20, default='IN_TRANSIT')
    current_temperature = models.FloatField(blank=True, null=True)
    dispatched_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class GovernmentScheme(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField()
    eligible_crops = models.CharField(max_length=250)
    max_funding = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    application_link = models.URLField(blank=True)

class Equipment(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="equipments", null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    equipment_type = models.CharField(max_length=100)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=150)
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='equipment/', null=True, blank=True)

class EquipmentRental(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="equipmentrentals", null=True, blank=True)
    equipment = models.ForeignKey('Equipment', on_delete=models.CASCADE, related_name='rentals')
    renter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='equipment_rentals')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='REQUESTED')
    created_at = models.DateTimeField(auto_now_add=True)

class Farm(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='farms_list', null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='individual_farms_list', null=True, blank=True)
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255, blank=True)
    area_acres = models.FloatField(default=0.0)
    soil_type = models.CharField(max_length=100, blank=True, null=True)
    irrigation_type = models.CharField(max_length=100, blank=True, null=True)
    ownership_type = models.CharField(max_length=100, blank=True, null=True)
    geojson_boundary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class FarmField(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='fields', null=True, blank=True)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='farms', null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='individual_farms', null=True, blank=True)
    name = models.CharField(max_length=150)
    crop_type = models.CharField(max_length=100)
    area_acres = models.FloatField()
    soil_type = models.CharField(max_length=100, blank=True, null=True)
    irrigation_type = models.CharField(max_length=100, blank=True, null=True)
    planting_date = models.DateField(null=True, blank=True)
    expected_harvest_date = models.DateField(null=True, blank=True)
    health_status = models.CharField(max_length=50, default='Good')
    geojson_data = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class FieldActivity(models.Model):
    field = models.ForeignKey(FarmField, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=100)
    date = models.DateField()
    notes = models.TextField(blank=True)
    quantity = models.CharField(max_length=100, blank=True)
    attachment = models.ImageField(upload_to='field_activities/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.activity_type} on {self.field.name}"

class FarmInput(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='inputs')
    input_type = models.CharField(max_length=100)
    name = models.CharField(max_length=150)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20)
    low_stock_threshold = models.FloatField(default=0.0)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class FarmEvent(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=100)
    date = models.DateField()
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class WeatherAdvisory(models.Model):
    location = models.CharField(max_length=150)
    advisory_text = models.TextField()
    severity = models.CharField(max_length=50)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

class CropMarketTrend(models.Model):
    crop_name = models.CharField(max_length=150)
    record_date = models.DateField()
    price_per_kg = models.FloatField()
    region = models.CharField(max_length=150)
    is_forecast = models.BooleanField(default=False)

class LedgerTransaction(models.Model):
    sender_org = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='sent_transactions')
    receiver_org = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='received_transactions')
    supply_match = models.ForeignKey('SupplyMatch', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='COMPLETED')
    reference_id = models.CharField(max_length=100, unique=True)
    escrow_status = models.CharField(max_length=20, default='RELEASED')

class CropYieldPrediction(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="cropyieldpredictions", null=True, blank=True)
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='yield_predictions')
    crop_type = models.CharField(max_length=100)
    area_hectares = models.DecimalField(max_digits=10, decimal_places=2)
    soil_type = models.CharField(max_length=100)
    predicted_yield_tons = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

class FoodLedger(models.Model):
    """Immutable blockchain-style ledger for tracing food chain of custody"""
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="foodledgers", null=True, blank=True)
    surplus_food = models.ForeignKey('SurplusFood', on_delete=models.CASCADE, related_name='ledger_entries')
    action_type = models.CharField(max_length=50, help_text="e.g. LOGGED, DISPATCHED, DELIVERED, TEMPERATURE_CHECK")
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    previous_hash = models.CharField(max_length=64, blank=True)
    block_hash = models.CharField(max_length=64, blank=True)
    details = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        if not self.block_hash:
            import hashlib
            last_entry = FoodLedger.objects.filter(surplus_food=self.surplus_food).order_by('-timestamp').first()
            self.previous_hash = last_entry.block_hash if last_entry else "0" * 64
            
            data_string = f"{self.surplus_food.id}{self.action_type}{self.details}{self.previous_hash}".encode('utf-8')
            self.block_hash = hashlib.sha256(data_string).hexdigest()
        super().save(*args, **kwargs)


# ----------------- PHASE 2: NEXT-GEN FEATURES -----------------

class MarketPricePrediction(models.Model):
    crop_name = models.CharField(max_length=100)
    current_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    predicted_price_next_week = models.DecimalField(max_digits=10, decimal_places=2)
    predicted_price_month = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_score = models.IntegerField(help_text="0-100")
    recommendation = models.CharField(max_length=50, choices=(
        ('SELL_NOW', 'Sell Now'),
        ('HOLD', 'Hold for Better Price'),
        ('SELL_PARTIAL', 'Sell Partial')
    ))
    updated_at = models.DateTimeField(auto_now=True)

class Warehouse(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="warehouses", null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="warehouses")
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255)
    total_palettes = models.IntegerField()
    available_palettes = models.IntegerField()
    price_per_palette_day = models.DecimalField(max_digits=10, decimal_places=2)
    current_temp_celsius = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

class WarehouseBooking(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="warehousebookings", null=True, blank=True)
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="warehouse_bookings")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    palettes = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50, choices=(
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active / Stored'),
        ('COMPLETED', 'Completed')
    ), default='PENDING')

# ----------------- PHASE 3: SUPER APP FEATURES -----------------

class DroneImagery(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="droneimageries", null=True, blank=True)
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="drone_maps")
    scan_date = models.DateTimeField(auto_now_add=True)
    image_url = models.URLField(max_length=500, blank=True)
    ndvi_score = models.DecimalField(max_digits=5, decimal_places=2, help_text="-1.0 to 1.0")
    issues_detected = models.TextField(blank=True, help_text="AI output string")
    status = models.CharField(max_length=50, default="ANALYZED")

class InfrastructureProject(models.Model):
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=200)
    description = models.TextField()
    goal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    roi_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="e.g. 15.0 for 15%")
    status = models.CharField(max_length=50, choices=(
        ('FUNDING', 'Funding Active'),
        ('FUNDED', 'Fully Funded'),
        ('COMPLETED', 'Project Completed')
    ), default='FUNDING')

class SoilTest(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="soiltests", null=True, blank=True)
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="soil_tests")
    test_date = models.DateField(auto_now_add=True)
    npk_nitrogen = models.DecimalField(max_digits=5, decimal_places=2)
    npk_phosphorus = models.DecimalField(max_digits=5, decimal_places=2)
    npk_potassium = models.DecimalField(max_digits=5, decimal_places=2)
    ph_level = models.DecimalField(max_digits=4, decimal_places=2)
    ai_recommendation = models.TextField(blank=True)

class SMSAlert(models.Model):
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sms_alerts")
    alert_type = models.CharField(max_length=100)
    message = models.TextField()
    is_sent = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

# ----------------- PHASE 4: ORGANIZATION ENTERPRISE FEATURES -----------------

class FleetRoute(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="fleet_routes")
    driver_name = models.CharField(max_length=150)
    vehicle_plate = models.CharField(max_length=50)
    optimized_path_json = models.TextField(help_text="JSON array of stops in optimized order")
    total_distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=(
        ('PENDING', 'Pending Dispatch'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed')
    ), default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

class ESGReport(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="esg_reports")
    report_month = models.CharField(max_length=50, help_text="e.g. October 2026")
    total_food_rescued_kg = models.DecimalField(max_digits=10, decimal_places=2)
    total_meals_provided = models.IntegerField()
    carbon_emissions_saved_kg = models.DecimalField(max_digits=10, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)

# ----------------- PHASE 5: CONSUMER & COMMUNITY ECOSYSTEM -----------------

# ----------------- PHASE 6: GLOBAL & FUTURE-TECH EXPANSION -----------------

class ProduceTraceabilityLedger(models.Model):
    """SIH Traceability Ledger: Single source of truth for tracking food lifecycle."""
    transaction_id = models.CharField(max_length=100, unique=True)
    transaction_type = models.CharField(max_length=100) # e.g. CREATED, HARVESTED, PROCESSED, STORED, SURPLUS, ALLOCATED, DELIVERED
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey('Organization', on_delete=models.SET_NULL, null=True, blank=True)
    produce = models.ForeignKey(AgriculturalProduce, on_delete=models.SET_NULL, null=True, blank=True)
    surplus = models.ForeignKey(SurplusFood, on_delete=models.SET_NULL, null=True, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    quantity = models.FloatField(default=0.0)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type} - {self.timestamp}"

class StorageRecord(models.Model):
    STATUS_CHOICES = [
        ("SAFE", "Safe - Optimal Conditions"),
        ("MONITOR", "Monitor - Nearing Threshold"),
        ("ATTENTION", "Attention Required - Deviation Detected"),
        ("CRITICAL", "Critical - Spoilage Risk"),
    ]
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="storage_records")
    produce = models.ForeignKey(AgriculturalProduce, on_delete=models.CASCADE, related_name="storage_records", null=True, blank=True)
    surplus = models.ForeignKey(SurplusFood, on_delete=models.CASCADE, related_name="storage_records", null=True, blank=True)
    batch_number = models.CharField(max_length=50)
    location = models.CharField(max_length=150)
    quantity = models.FloatField(validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=20, default="kg")
    entry_time = models.DateTimeField(auto_now_add=True)
    temperature_celsius = models.FloatField(default=4.0)
    humidity_percent = models.FloatField(default=60.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SAFE")
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Storage: {self.batch_number} at {self.location}"

# Phase 11: Ecosystem Coordination (Multi-Org Alliances & Control Tower)
class EcosystemAlliance(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class AllianceMember(models.Model):
    alliance = models.ForeignKey(EcosystemAlliance, on_delete=models.CASCADE, related_name='members')
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='alliances')
    joined_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=50, default="Member") # Admin, Member
    
    class Meta:
        unique_together = ('alliance', 'organization')

class SharedTask(models.Model):
    STATUS_CHOICES = (
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )
    alliance = models.ForeignKey(EcosystemAlliance, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='created_shared_tasks')
    assigned_to = models.ForeignKey('Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_shared_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=50)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Notification: {self.message[:20]}"

class AIRecommendation(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('VIEWED', 'Viewed'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='ai_recommendations')
    title = models.CharField(max_length=250)
    category = models.CharField(max_length=100)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    reason = models.TextField()
    recommended_action = models.TextField()
    potential_impact = models.CharField(max_length=250, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    feedback_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.priority}] {self.title}"

class AdminLog(models.Model):
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_logs')
    action = models.CharField(max_length=255)
    target_model = models.CharField(max_length=100, blank=True)
    target_object_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin_user.username} - {self.action} at {self.timestamp}"

class AIAuditLog(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='ai_audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    request_intent = models.CharField(max_length=250)
    ai_module = models.CharField(max_length=100)
    model_version = models.CharField(max_length=100, default='AgroFedly AI 1.0')
    inputs_snapshot = models.TextField(blank=True, help_text="JSON representation of inputs")
    recommendation = models.TextField()
    confidence = models.CharField(max_length=50, blank=True)
    action_requested = models.CharField(max_length=200, blank=True)
    user_decision = models.CharField(max_length=50, blank=True)
    execution_result = models.CharField(max_length=50, blank=True)
    failure_reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.ai_module} at {self.timestamp.strftime('%H:%M:%S')}"

# ----------------------------------------------------------------------------
# PHASE 19 MODELS
# ----------------------------------------------------------------------------

class SystemEvent(models.Model):
    """Logs system events for the Digital Twin and Timelines."""
    SEVERITY_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='system_events')
    event_type = models.CharField(max_length=100) # e.g., 'SurplusDetected', 'StorageAnomaly'
    entity_id = models.CharField(max_length=50, blank=True, null=True) # e.g., 'Produce Batch #482'
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='INFO')
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.timestamp} - {self.event_type}"

class WorkflowRule(models.Model):
    """Configures rules for AI Workflow Engine."""
    AUTOMATION_CHOICES = [
        ('MANUAL', 'Manual'),
        ('SUPERVISED', 'Supervised Automation'),
        ('AUTOMATED', 'Automated'),
    ]
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    trigger_event = models.CharField(max_length=100)
    conditions_json = models.JSONField(default=dict, blank=True)
    automation_level = models.CharField(max_length=20, choices=AUTOMATION_CHOICES, default='SUPERVISED')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class WorkflowExecution(models.Model):
    """Logs execution of workflows."""
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name="workflowexecutions", null=True, blank=True)
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('WAITING_APPROVAL', 'Waiting for Approval'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    rule = models.ForeignKey(WorkflowRule, on_delete=models.CASCADE)
    triggering_event = models.ForeignKey(SystemEvent, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    execution_log = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"Execution of {self.rule.name} - {self.status}"

class UserTask(models.Model):
    """Tasks for the My Tasks center (approvals, reviews, etc.)."""
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    action_url = models.CharField(max_length=255, blank=True, null=True)
    related_entity = models.CharField(max_length=100, blank=True, null=True) # e.g., 'Redistribution #12'
    
    def __str__(self):
        return self.title

class DataImport(models.Model):
    """Logs data imports."""
    STATUS_CHOICES = [
        ('UPLOADING', 'Uploading'),
        ('MAPPING', 'Mapping Columns'),
        ('VALIDATING', 'Validating'),
        ('IMPORTING', 'Importing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    import_type = models.CharField(max_length=50) # 'PRODUCE', 'RECIPIENTS', etc.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPLOADING')
    total_rows = models.IntegerField(default=0)
    imported_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    mapping_config = models.JSONField(default=dict, blank=True)
    errors_log = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.filename} - {self.status}"


import uuid

class OrganizationInvitation(models.Model):
    ROLE_CHOICES = OrganizationMember.ROLE_CHOICES
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("EXPIRED", "Expired"),
        ("REVOKED", "Revoked"),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="STAFF")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_invitations")

    def __str__(self):
        return f"Invite {self.email} to {self.organization.name} ({self.status})"


class TenantAuditLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_logs')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='performed_actions')
    action = models.CharField(max_length=50)
    entity_name = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} on {self.entity_name} by {self.actor} at {self.timestamp}"


import secrets

class APIKey(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=8, unique=True, editable=False)
    hashed_key = models.CharField(max_length=128, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    scopes = models.JSONField(default=list, blank=True) # e.g. ["produce:read", "surplus:write"]
    
    def __str__(self):
        return f"{self.name} ({self.prefix}...)"

class Webhook(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='webhooks')
    endpoint_url = models.URLField()
    secret = models.CharField(max_length=64, default=secrets.token_urlsafe)
    events = models.JSONField(default=list) # e.g. ["produce.created", "surplus.detected"]
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Webhook {self.endpoint_url} for {self.organization.name}"

# ----------------- AGROFEDLY 2.0: ROLE-BASED AUTHENTICATION -----------------

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('FARMER', 'Farmer'),
        ('FPO', 'Farmer Organization / FPO'),
        ('OFFICER', 'Agriculture Officer'),
        ('AGRIBUSINESS', 'Agribusiness'),
        ('NGO', 'NGO / Redistribution'),
        ('RESEARCHER', 'Researcher'),
        ('ADMIN', 'Administrator'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='FARMER')
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    
    # Role-specific IDs or metadata
    organization_id = models.CharField(max_length=100, blank=True, help_text="For FPO, Agribusiness, NGO")
    official_id = models.CharField(max_length=100, blank=True, help_text="For Agriculture Officer")
    researcher_id = models.CharField(max_length=100, blank=True, help_text="For Researchers")
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

# ----------------- PHASE 4: AI PLATFORM MODELS -----------------

class AIModelRegistry(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('TESTING', 'Testing'),
        ('ARCHIVED', 'Archived')
    ]
    model_name = models.CharField(max_length=100)
    purpose = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    input_schema = models.JSONField(default=dict, blank=True)
    output_schema = models.JSONField(default=dict, blank=True)
    training_metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TESTING')
    last_updated = models.DateTimeField(auto_now=True)
    evaluation_metrics = models.JSONField(default=dict, blank=True)
    feature_information = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.model_name} (v{self.version}) - {self.status}"

class AIChatHistory(models.Model):
    ROLE_CHOICES = [
        ('USER', 'User'),
        ('AI', 'AI')
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_chats')
    message_role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    context_used = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

class AIInsight(models.Model):
    CATEGORY_CHOICES = [
        ('WEATHER', 'Weather Insight'),
        ('CROP', 'Crop Insight'),
        ('MARKET', 'Market Insight'),
        ('YIELD', 'Yield Insight'),
        ('OPERATIONAL', 'Operational Insight'),
        ('SURPLUS', 'Surplus Insight')
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_insights', null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ai_insights', null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    summary = models.TextField()
    reason = models.TextField()
    data_context = models.JSONField(default=dict, blank=True)
    recommended_action = models.TextField(blank=True)
    confidence = models.CharField(max_length=20, blank=True) # High, Medium, Low
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

class SmartAlert(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='smart_alerts', null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='smart_alerts', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    trigger_source = models.CharField(max_length=100) # Weather, Activity, Crop, etc.
    action_url = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return self.title


# ==========================================
# PHASE 8: KITCHEN & FOOD-SURPLUS INTELLIGENCE
# ==========================================

class Kitchen(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="kitchens")
    name = models.CharField(max_length=200)
    kitchen_type = models.CharField(max_length=100, default="Hostel")
    location = models.CharField(max_length=200, blank=True)
    operating_hours = models.CharField(max_length=100, blank=True)
    daily_meal_capacity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.organization.name}"

class PreparationRecord(models.Model):
    meal_record = models.ForeignKey('MealRecord', on_delete=models.CASCADE, related_name="preparations")
    kitchen = models.ForeignKey(Kitchen, on_delete=models.CASCADE, related_name="preparations")
    food_item = models.CharField(max_length=150)
    planned_qty = models.FloatField(default=0.0)
    prepared_qty = models.FloatField(default=0.0)
    served_qty = models.FloatField(default=0.0)
    unit = models.CharField(max_length=20, default="kg")
    preparation_time = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def remaining_qty(self):
        return max(0.0, self.prepared_qty - self.served_qty)

    def __str__(self):
        return f"{self.food_item} for {self.meal_record.date}"

class KitchenInventory(models.Model):
    kitchen = models.ForeignKey(Kitchen, on_delete=models.CASCADE, related_name="inventory")
    ingredient = models.CharField(max_length=150)
    quantity = models.FloatField(default=0.0)
    unit = models.CharField(max_length=20, default="kg")
    batch_id = models.CharField(max_length=100, blank=True)
    purchase_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    storage_location = models.CharField(max_length=100, blank=True)
    supplier = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=30, default="ACTIVE")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ingredient} ({self.quantity} {self.unit})"

class KitchenAlert(models.Model):
    kitchen = models.ForeignKey(Kitchen, on_delete=models.CASCADE, related_name="alerts")
    severity = models.CharField(max_length=30, default="INFO")
    reason = models.CharField(max_length=255)
    source = models.CharField(max_length=100, default="SYSTEM")
    action_required = models.CharField(max_length=255, blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.severity}: {self.reason}"
