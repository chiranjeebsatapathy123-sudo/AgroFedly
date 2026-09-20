from django import forms
from .models import (
    Delivery, Organization, OrganizationMember, Recipient,
    Redistribution, SurplusFood, VolunteerProfile,
)


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name", "organization_type", "registration_number", "email",
            "phone", "address", "city", "state", "country", "website", "capacity",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Organization name"}),
            "registration_number": forms.TextInput(attrs={"placeholder": "Registration / ID number"}),
            "email": forms.EmailInput(attrs={"placeholder": "Official email"}),
            "phone": forms.TextInput(attrs={"placeholder": "Contact number"}),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Full address"}),
            "city": forms.TextInput(attrs={"placeholder": "City"}),
            "state": forms.TextInput(attrs={"placeholder": "State"}),
            "country": forms.TextInput(attrs={"placeholder": "Country"}),
            "website": forms.URLInput(attrs={"placeholder": "https://example.com"}),
            "capacity": forms.NumberInput(attrs={"min": 0, "placeholder": "People served"}),
        }


class SurplusFoodForm(forms.ModelForm):
    class Meta:
        model = SurplusFood
        fields = ["food_name", "quantity", "storage_temperature", "storage_time_hours", "quality_image"]
        widgets = {
            "food_name": forms.TextInput(attrs={"placeholder": "e.g. Cooked rice"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "storage_temperature": forms.NumberInput(attrs={"step": "0.1", "placeholder": "°C"}),
            "storage_time_hours": forms.NumberInput(attrs={"step": "0.1", "min": 0}),
            "quality_image": forms.FileInput(attrs={"accept": "image/*"}),
        }


class RedistributionForm(forms.ModelForm):
    class Meta:
        model = Redistribution
        fields = ["quantity", "recipient"]
        widgets = {"quantity": forms.NumberInput(attrs={"min": 1})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recipient"].queryset = Recipient.objects.filter(
            verified=True,
            capacity__gt=0,
        ).order_by("-urgency_score", "name")
        self.fields["recipient"].empty_label = (
            "Select verified recipient"
            if self.fields["recipient"].queryset.exists()
            else "No verified recipients available — add/verify one first"
        )
        self.fields["recipient"].widget.attrs.update({
            "class": "recipient-select",
        })


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = [
            "receiver", "surplus", "food_name", "quantity", "pickup_address",
            "delivery_address", "recipient_contact", "driver_name",
            "vehicle_number", "scheduled_at", "notes",
        ]
        widgets = {
            "receiver": forms.Select(),
            "surplus": forms.Select(),
            "food_name": forms.TextInput(attrs={"placeholder": "Food / meal name"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "pickup_address": forms.Textarea(attrs={"rows": 2, "placeholder": "Pickup location"}),
            "delivery_address": forms.Textarea(attrs={"rows": 2, "placeholder": "Delivery location"}),
            "recipient_contact": forms.TextInput(attrs={"placeholder": "Contact number"}),
            "driver_name": forms.TextInput(attrs={"placeholder": "Driver name"}),
            "vehicle_number": forms.TextInput(attrs={"placeholder": "Vehicle number"}),
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Delivery instructions"}),
        }

    def __init__(self, *args, sender=None, **kwargs):
        super().__init__(*args, **kwargs)

        if sender:
            receiver_qs = (
                Organization.objects
                .filter(is_active=True)
                .exclude(pk=sender.pk)
                .order_by("-is_verified", "name")
            )
            self.fields["surplus"].queryset = (
                SurplusFood.objects
                .filter(organization=sender, status="SAFE", quantity__gt=0)
                .order_by("-created_at")
            )
        else:
            receiver_qs = Organization.objects.filter(is_active=True).order_by("-is_verified", "name")
            self.fields["surplus"].queryset = SurplusFood.objects.filter(
                status="SAFE", quantity__gt=0
            ).order_by("-created_at")

        self.fields["receiver"].queryset = receiver_qs
        self.fields["receiver"].label = "Receiving organization"
        self.fields["receiver"].empty_label = (
            "No other active organizations registered"
            if sender and not receiver_qs.exists()
            else "Select receiving organization"
        )
        self.fields["receiver"].widget.attrs.update({
            "class": "org-select",
            "data-org-details-url": "/organizations/__ID__/details/",
        })
        self.fields["surplus"].required = False
        self.fields["surplus"].empty_label = "Optional — link safe surplus"


class MemberForm(forms.Form):
    username = forms.CharField(max_length=150, label="Existing username")
    role = forms.ChoiceField(choices=OrganizationMember.ROLE_CHOICES)


from .models import MealRecord

class PostMealRecordForm(forms.ModelForm):
    class Meta:
        model = MealRecord
        fields = [
            "date", "meal_type", "predicted_demand", 
            "meals_prepared", "meals_consumed", 
            "leftover_meals", "discarded_meals"
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "meal_type": forms.TextInput(attrs={"placeholder": "e.g. Lunch"}),
            "predicted_demand": forms.NumberInput(attrs={"min": 0}),
            "meals_prepared": forms.NumberInput(attrs={"min": 0}),
            "meals_consumed": forms.NumberInput(attrs={"min": 0}),
            "leftover_meals": forms.NumberInput(attrs={"min": 0}),
            "discarded_meals": forms.NumberInput(attrs={"min": 0}),
        }

    def clean(self):
        cleaned_data = super().clean()
        prepared = cleaned_data.get("meals_prepared")
        consumed = cleaned_data.get("meals_consumed")

        if prepared is not None and consumed is not None:
            if consumed > prepared:
                self.add_error("meals_consumed", "Consumed meals cannot exceed prepared meals.")

        return cleaned_data

from .models import AgriculturalProduce, ProcessingRecord, AgriculturalSupplyRequest

class AgriculturalProduceForm(forms.ModelForm):
    class Meta:
        model = AgriculturalProduce
        fields = [
            "farm", "batch_number", "name", "category", "crop_type", "quantity", "unit",
            "available_quantity", "harvest_date", "location", "expected_shelf_life_days",
            "storage_condition", "quality_status", "processing_status"
        ]
        widgets = {
            "harvest_date": forms.DateInput(attrs={"type": "date"}),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Tomato"}),
            "category": forms.TextInput(attrs={"placeholder": "e.g. Vegetables"}),
            "crop_type": forms.TextInput(attrs={"placeholder": "e.g. Roma"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Farm location"}),
            "quantity": forms.NumberInput(attrs={"min": 0, "step": "0.1"}),
            "available_quantity": forms.NumberInput(attrs={"min": 0, "step": "0.1"}),
        }

class ProcessingRecordForm(forms.ModelForm):
    class Meta:
        model = ProcessingRecord
        fields = [
            "input_produce", "input_quantity", "processing_type", 
            "output_product", "output_quantity", "processing_facility",
            "status", "waste_quantity"
        ]
        widgets = {
            "input_quantity": forms.NumberInput(attrs={"min": 0, "step": "0.1"}),
            "output_quantity": forms.NumberInput(attrs={"min": 0, "step": "0.1"}),
            "waste_quantity": forms.NumberInput(attrs={"min": 0, "step": "0.1"}),
        }
        
    def __init__(self, *args, supplier=None, **kwargs):
        super().__init__(*args, **kwargs)
        if supplier:
            self.fields["input_produce"].queryset = AgriculturalProduce.objects.filter(supplier=supplier)

class AgriculturalSupplyRequestForm(forms.ModelForm):
    class Meta:
        model = AgriculturalSupplyRequest
        fields = ["produce", "requested_quantity"]
        widgets = {
            "requested_quantity": forms.NumberInput(attrs={"min": 0.1, "step": "0.1"})
        }

from .models import BuyerDemand

class BuyerDemandForm(forms.ModelForm):
    class Meta:
        model = BuyerDemand
        fields = [
            "produce_name", "required_quantity", "unit",
            "quality_requirement", "location", "required_date"
        ]
        widgets = {
            "required_date": forms.DateInput(attrs={"type": "date"}),
            "produce_name": forms.TextInput(attrs={"placeholder": "e.g. Tomato"}),
            "required_quantity": forms.NumberInput(attrs={"min": 0.1, "step": "0.1"}),
        }

from .models import QualityInspection



from .models import QualityInspection

class QualityInspectionForm(forms.ModelForm):
    class Meta:
        model = QualityInspection
        fields = ["produce", "inspector_name", "grade", "notes", "passed"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

class VolunteerProfileForm(forms.ModelForm):
    class Meta:
        model = VolunteerProfile
        fields = ["phone", "vehicle_type", "vehicle_number", "is_available"]
        widgets = {
            "phone": forms.TextInput(attrs={"placeholder": "Contact number"}),
            "vehicle_type": forms.TextInput(attrs={"placeholder": "e.g., Bike, Car, Van"}),
            "vehicle_number": forms.TextInput(attrs={"placeholder": "Vehicle registration number"}),
        }

from .models import Farm, FarmField, FieldActivity, FarmInput

class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['name', 'location', 'area_acres', 'soil_type', 'irrigation_type', 'ownership_type', 'geojson_boundary']
        widgets = {
            'geojson_boundary': forms.HiddenInput(),
            'soil_type': forms.Select(choices=[
                ('Clay', 'Clay'),
                ('Sandy', 'Sandy'),
                ('Silty', 'Silty'),
                ('Peaty', 'Peaty'),
                ('Chalky', 'Chalky'),
                ('Loamy', 'Loamy'),
            ])
        }

class FarmFieldForm(forms.ModelForm):
    class Meta:
        model = FarmField
        fields = ['farm', 'name', 'crop_type', 'area_acres', 'soil_type', 'irrigation_type', 'planting_date', 'expected_harvest_date', 'health_status', 'geojson_data']
        widgets = {
            'geojson_data': forms.HiddenInput(),
            'planting_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_harvest_date': forms.DateInput(attrs={'type': 'date'}),
            'soil_type': forms.Select(choices=[
                ('Clay', 'Clay'),
                ('Sandy', 'Sandy'),
                ('Silty', 'Silty'),
                ('Peaty', 'Peaty'),
                ('Chalky', 'Chalky'),
                ('Loamy', 'Loamy'),
            ])
        }

class FieldActivityForm(forms.ModelForm):
    class Meta:
        model = FieldActivity
        fields = ['field', 'activity_type', 'date', 'quantity', 'notes', 'attachment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class FarmInputForm(forms.ModelForm):
    class Meta:
        model = FarmInput
        fields = ['farm', 'input_type', 'name', 'quantity', 'unit', 'low_stock_threshold', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

from .models import LogisticsDriver

class LogisticsDriverForm(forms.ModelForm):
    class Meta:
        model = LogisticsDriver
        fields = ['name', 'license_type', 'status', 'rating', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Driver Name'}),
            'license_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CDL Class A'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '5'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
        }


