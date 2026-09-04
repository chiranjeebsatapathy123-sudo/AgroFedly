from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="DemandForecast",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("predicted_demand", models.PositiveIntegerField(default=0)),
                ("recommended_preparation", models.PositiveIntegerField(default=0)),
                ("lower_bound", models.PositiveIntegerField(default=0)),
                ("upper_bound", models.PositiveIntegerField(default=0)),
                ("confidence", models.FloatField(default=0.0)),
                ("expected_surplus", models.PositiveIntegerField(default=0)),
                ("waste_risk", models.CharField(default="LOW", max_length=20)),
                ("model_name", models.CharField(default="AnnadataFallback", max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name="MealRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("attendance", models.PositiveIntegerField(default=0)),
                ("meals_prepared", models.PositiveIntegerField(default=0)),
                ("meals_consumed", models.PositiveIntegerField(default=0)),
                ("holiday", models.BooleanField(default=False)),
                ("rainfall", models.FloatField(default=0.0)),
                ("temperature", models.FloatField(default=25.0)),
                ("humidity", models.FloatField(default=70.0)),
                ("meal_type", models.CharField(default="Mixed", max_length=50)),
                ("exam_day", models.BooleanField(default=False)),
                ("event_flag", models.BooleanField(default=False)),
                ("location", models.CharField(default="Project Site", max_length=120)),
                ("data_source", models.CharField(default="PROJECT_PROVIDED", max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("organization_type", models.CharField(choices=[("COMPANY", "Company"), ("COLLEGE", "College"), ("SCHOOL", "School"), ("HOSPITAL", "Hospital"), ("NGO", "NGO / Non-Profit"), ("INSTITUTION", "Other Institution")], max_length=30)),
                ("registration_number", models.CharField(blank=True, max_length=100)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(default="India", max_length=100)),
                ("website", models.URLField(blank=True)),
                ("capacity", models.PositiveIntegerField(default=0)),
                ("is_verified", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Recipient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("recipient_type", models.CharField(max_length=100)),
                ("capacity", models.PositiveIntegerField(default=0)),
                ("verified", models.BooleanField(default=False)),
                ("distance_km", models.FloatField(default=0.0)),
                ("urgency_score", models.PositiveIntegerField(default=50)),
            ],
        ),
        migrations.CreateModel(
            name="SurplusFood",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("food_name", models.CharField(max_length=100)),
                ("quantity", models.PositiveIntegerField()),
                ("storage_temperature", models.FloatField(default=4.0)),
                ("storage_time_hours", models.FloatField(default=0.0)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("SAFE", "Safe"), ("UNSAFE", "Unsafe"), ("REDISTRIBUTED", "Redistributed")], default="PENDING", max_length=20)),
                ("is_safe", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="surplus_food", to="feedly.organization")),
            ],
        ),
        migrations.CreateModel(
            name="OrganizationMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("OWNER", "Owner"), ("ADMIN", "Administrator"), ("MANAGER", "Food Manager"), ("STAFF", "Staff"), ("VIEWER", "Viewer")], default="STAFF", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="feedly.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("organization", "user"), name="unique_organization_member")]},
        ),
        migrations.CreateModel(
            name="Redistribution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("distributed_at", models.DateTimeField(auto_now_add=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="redistributions", to="feedly.recipient")),
                ("surplus", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="redistributions", to="feedly.surplusfood")),
            ],
        ),
        migrations.CreateModel(
            name="Delivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("food_name", models.CharField(max_length=150)),
                ("quantity", models.PositiveIntegerField()),
                ("pickup_address", models.TextField()),
                ("delivery_address", models.TextField()),
                ("recipient_contact", models.CharField(blank=True, max_length=50)),
                ("driver_name", models.CharField(blank=True, max_length=100)),
                ("vehicle_number", models.CharField(blank=True, max_length=50)),
                ("scheduled_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("REQUESTED", "Requested"), ("ASSIGNED", "Driver Assigned"), ("PICKED_UP", "Picked Up"), ("IN_TRANSIT", "In Transit"), ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled")], default="REQUESTED", max_length=20)),
                ("tracking_code", models.CharField(editable=False, max_length=20, unique=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("receiver", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_deliveries", to="feedly.organization")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_deliveries", to="feedly.organization")),
                ("surplus", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deliveries", to="feedly.surplusfood")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
