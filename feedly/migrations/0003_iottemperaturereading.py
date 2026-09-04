from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("feedly", "0002_alter_organization_options_alter_delivery_quantity_and_more")]
    operations = [migrations.CreateModel(
        name="IoTTemperatureReading",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("sensor_name", models.CharField(default="Manual / IoT Sensor", max_length=100)),
            ("food_name", models.CharField(max_length=100)),
            ("temperature", models.FloatField()),
            ("unit", models.CharField(default="°C", max_length=10)),
            ("location", models.CharField(blank=True, max_length=150)),
            ("status", models.CharField(choices=[("SAFE", "Safe"), ("ALERT", "Alert")], default="SAFE", max_length=10)),
            ("recorded_at", models.DateTimeField(auto_now_add=True)),
        ],
        options={"ordering": ["-recorded_at"]},
    )]
