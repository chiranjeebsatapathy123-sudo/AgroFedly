from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
import uuid


class MealRecord(models.Model):
    date = models.DateField()
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
    leftover_meals = models.PositiveIntegerField(default=0, null=True, blank=True)
    discarded_meals = models.PositiveIntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return str(self.date)


class DemandForecast(models.Model):
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


class OrganizationMember(models.Model):
    ROLE_CHOICES = [
        ("OWNER", "Owner"),
        ("ADMIN", "Administrator"),
        ("MANAGER", "Food Manager"),
        ("STAFF", "Staff"),
        ("VIEWER", "Viewer"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="STAFF")
    is_active = models.BooleanField(default=True)
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


class Recipient(models.Model):
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    is_safe = models.BooleanField(default=False)
    safety_alert = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def check_safety(self):
        if self.storage_temperature <= 5 and self.storage_time_hours <= 24:
            self.is_safe = True
            self.status = "SAFE"
            self.safety_alert = "Safe for redistribution."
        elif self.storage_temperature <= 8 and self.storage_time_hours <= 36:
            self.is_safe = False
            self.status = "WARNING"
            self.safety_alert = "Marginal conditions. Rapid redistribution or manual check required."
        else:
            self.is_safe = False
            self.status = "UNSAFE"
            reasons = []
            if self.storage_temperature > 8:
                reasons.append("temperature too high")
            if self.storage_time_hours > 36:
                reasons.append("storage time exceeded")
            self.safety_alert = "Unsafe: " + " and ".join(reasons) + "."
            
        self.save(update_fields=["is_safe", "status", "safety_alert"])

    def __str__(self):
        return self.food_name


class Redistribution(models.Model):
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    surplus = models.ForeignKey(SurplusFood, on_delete=models.CASCADE, related_name="redistributions")
    recipient = models.ForeignKey(Recipient, on_delete=models.CASCADE, related_name="redistributions")
    distributed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.surplus.food_name} → {self.recipient.name}"


class IoTTemperatureReading(models.Model):
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

    sender = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="outgoing_deliveries")
    receiver = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="incoming_deliveries")
    surplus = models.ForeignKey(SurplusFood, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    food_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    recipient_contact = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    vehicle_number = models.CharField(max_length=50, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="REQUESTED")
    tracking_code = models.CharField(max_length=20, unique=True, editable=False)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = f"ANN-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_code} — {self.food_name}"


class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, default="kg")
    quantity_per_meal = models.FloatField(help_text="Quantity required per meal")
    cost_per_unit = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class AgriculturalProduce(models.Model):
    supplier = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="produce_inventory")
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100)
    crop_type = models.CharField(max_length=100)
    quantity = models.FloatField(validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=20, default="kg")
    available_quantity = models.FloatField(validators=[MinValueValidator(0)])
    harvest_date = models.DateField()
    location = models.CharField(max_length=150, blank=True)
    expected_shelf_life_days = models.PositiveIntegerField(default=7)
    storage_condition = models.CharField(max_length=100, default="Room Temperature")
    quality_status = models.CharField(max_length=50, default="Good")
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
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("PROCESSING", "Processing"),
        ("SUPPLIED", "Supplied"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    requester = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="supply_requests")
    produce = models.ForeignKey(AgriculturalProduce, on_delete=models.CASCADE, related_name="supply_requests")
    requested_quantity = models.FloatField(validators=[MinValueValidator(0.1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.requester.name} requested {self.requested_quantity} of {self.produce.name}"


class BuyerDemand(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="buyer_demands")
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


