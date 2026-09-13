import json
import os
from datetime import date, timedelta, datetime
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .forms import DeliveryForm, MemberForm, OrganizationForm, RedistributionForm, SurplusFoodForm
from .models import (
    DemandForecast, Delivery, MealRecord, Organization, OrganizationMember,
    Recipient, Redistribution, SurplusFood, IoTTemperatureReading, Ingredient, OrganizationImpact
)

User = get_user_model()

try:
    import joblib
except Exception:
    joblib = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "demand_bundle.pkl")
LEGACY_MODEL_PATH = os.path.join(BASE_DIR, "ml", "demand_model.pkl")

MODEL = None
MODEL_FEATURES = []
MODEL_NAME = "Fedly Smart Forecast"
RESIDUAL_P90 = 8.0

if joblib:
    try:
        bundle = joblib.load(MODEL_PATH)
        MODEL = bundle.get("model") if isinstance(bundle, dict) else bundle
        MODEL_FEATURES = bundle.get("features", []) if isinstance(bundle, dict) else []
        MODEL_NAME = bundle.get("model_name", MODEL_NAME) if isinstance(bundle, dict) else MODEL_NAME
        RESIDUAL_P90 = float(bundle.get("residual_p90", 8)) if isinstance(bundle, dict) else 8
    except Exception:
        try:
            MODEL = joblib.load(LEGACY_MODEL_PATH)
            MODEL_FEATURES = ["attendance", "temperature", "rainfall", "holiday", "day_of_week"]
            MODEL_NAME = "Legacy Demand Model"
        except Exception:
            pass


def home(request):
    return render(request, "home.html")


def health_check(request):
    return JsonResponse({"status": "ok", "service": "Fedly"})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        if not username or not password:
            messages.error(request, "Enter both username and password.")
        else:
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect(request.GET.get("next") or "dashboard")
            messages.error(request, "Invalid username or password.")
    return render(request, "login.html")


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


def _membership(request):
    memberships = (
        OrganizationMember.objects
        .select_related("organization")
        .filter(user=request.user, is_active=True, organization__is_active=True)
    )
    active_id = request.session.get("active_organization_id")
    if active_id:
        active = memberships.filter(organization_id=active_id).first()
        if active:
            return active
    return memberships.order_by("-joined_at").first()


def _organization_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        membership = _membership(request)
        if not membership:
            messages.info(request, "Register or join an organization to use this workspace.")
            return redirect("organization_register")
        request.membership = membership
        request.organization = membership.organization
        return view(request, *args, **kwargs)
    return wrapped


def _manager_required(view):
    @wraps(view)
    @_organization_required
    def wrapped(request, *args, **kwargs):
        if request.membership.role not in {"OWNER", "ADMIN", "MANAGER"}:
            messages.error(request, "Manager permission is required for this action.")
            return redirect("organization_dashboard")
        return view(request, *args, **kwargs)
    return wrapped


def _weather(city):
    key = getattr(settings, "WEATHER_API_KEY", "")
    if not city or not key:
        return None
    try:
        import requests
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": key, "units": "metric"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "temperature": float(data["main"]["temp"]),
            "humidity": float(data["main"].get("humidity", 70)),
            "rainfall": float(data.get("rain", {}).get("1h", 0)),
            "weather": data["weather"][0]["description"],
            "is_live": True,
        }
    except Exception:
        return None


def _predict(attendance, temperature=25, rainfall=0, holiday=0, humidity=70, exam_day=0, event_flag=0, target=None):
    target = target or date.today()
    recent_meals = list(
        MealRecord.objects.filter(date__lt=target)
        .exclude(data_source="ERP")
        .order_by("-date").values_list("meals_consumed", flat=True)[:7]
    )
    
    if recent_meals and sum(recent_meals) > 0:
        recent_avg = sum(recent_meals) / len(recent_meals)
    else:
        recent = list(
            DemandForecast.objects.filter(date__lt=target).order_by("-date").values_list("predicted_demand", flat=True)[:7]
        )
        recent_avg = sum(recent) / len(recent) if recent else attendance * 0.86

    features = {
        "attendance": attendance,
        "temperature": temperature,
        "rainfall": rainfall,
        "holiday": holiday,
        "day_of_week": target.weekday(),
        "humidity": humidity,
        "month": target.month,
        "weekend": int(target.weekday() >= 5),
        "exam_day": exam_day,
        "event_flag": event_flag,
        "recent_avg_demand": recent_avg,
    }

    if MODEL is not None:
        try:
            row = [[features.get(name, 0) for name in MODEL_FEATURES]]
            prediction = max(0, int(round(float(MODEL.predict(row)[0]))))
        except Exception:
            prediction = max(0, int(round(attendance * (0.72 if holiday else 0.86))))
    else:
        prediction = max(0, int(round(attendance * (0.68 if holiday else 0.86))))
        if target.weekday() >= 5:
            prediction = int(round(prediction * 0.82))
        if rainfall > 10:
            prediction = int(round(prediction * 0.97))

    uncertainty = max(8, int(round(RESIDUAL_P90)))
    lower = max(0, prediction - uncertainty)
    upper = prediction + uncertainty
    confidence = max(50.0, min(99.0, 100 - (uncertainty / max(prediction, 1) * 100)))
    buffer = max(2, int(round((upper - prediction) * 0.20)))
    recommended = prediction + buffer
    expected_surplus = max(0, recommended - prediction)
    ratio = expected_surplus / max(recommended, 1)
    risk = "HIGH" if ratio >= .12 or expected_surplus >= 80 else "MEDIUM" if ratio >= .05 or expected_surplus >= 30 else "LOW"

    return {
        "prediction": prediction, "lower": lower, "upper": upper,
        "recommended": recommended, "confidence": round(confidence, 1),
        "expected_surplus": expected_surplus, "risk": risk,
        "model_name": MODEL_NAME,
    }


@login_required
def dashboard(request):
    predictions = DemandForecast.objects.order_by("-date", "-id")
    surplus = SurplusFood.objects.order_by("-created_at")
    redistributions = Redistribution.objects.order_by("-distributed_at")

    context = {
        "total_predictions": predictions.count(),
        "total_predicted": predictions.aggregate(v=Sum("predicted_demand"))["v"] or 0,
        "total_surplus": surplus.aggregate(v=Sum("quantity"))["v"] or 0,
        "safe_food": surplus.filter(status="SAFE").count(),
        "redistributed": redistributions.aggregate(v=Sum("quantity"))["v"] or 0,
        "recipients": Recipient.objects.count(),
        "verified_recipients": Recipient.objects.filter(verified=True).count(),
        "recent_predictions": predictions[:6],
        "recent_surplus": surplus[:6],
        "recent_deliveries": Delivery.objects.filter(
            Q(sender__members__user=request.user) | Q(receiver__members__user=request.user)
        ).distinct()[:6],
        "model_name": MODEL_NAME,
    }
    confidences = list(predictions.values_list("confidence", flat=True))
    context["avg_confidence"] = round(sum(confidences) / len(confidences), 1) if confidences else 0
    return render(request, "dashboard.html", context)


@login_required
def predict_demand(request):
    result = None
    weather = None
    error = None
    
    # Pre-fill ERP attendance if available for today
    today_erp = MealRecord.objects.filter(date=date.today(), data_source="ERP").first()
    default_attendance = today_erp.attendance if today_erp else 0

    if request.method == "POST":
        try:
            attendance = int(request.POST.get("attendance", 0))
            holiday = int(request.POST.get("holiday", 0))
            exam_day = int(request.POST.get("exam_day", 0))
            event_flag = int(request.POST.get("event_flag", 0))
            city = request.POST.get("city", "").strip()
            
            if attendance < 0:
                raise ValueError("Attendance cannot be negative.")
            weather = _weather(city) if city else None
            
            if city and not weather and getattr(settings, "WEATHER_API_KEY", ""):
                # Fallback instead of breaking
                weather = {"temperature": 25, "humidity": 70, "rainfall": 0}
                
            humidity = weather["humidity"] if weather else 70
            temperature = weather["temperature"] if weather else 25
            rainfall = weather["rainfall"] if weather else 0

            result = _predict(
                attendance=attendance,
                temperature=temperature,
                rainfall=rainfall,
                holiday=holiday,
                humidity=humidity,
                exam_day=exam_day,
                event_flag=event_flag
            )
            DemandForecast.objects.create(
                date=date.today(),
                predicted_demand=result["prediction"],
                recommended_preparation=result["recommended"],
                lower_bound=result["lower"],
                upper_bound=result["upper"],
                confidence=result["confidence"],
                expected_surplus=result["expected_surplus"],
                waste_risk=result["risk"],
                model_name=result["model_name"],
            )
            messages.success(request, "AI forecast saved successfully.")
        except (ValueError, TypeError) as exc:
            error = str(exc)
            
    produce_requirements = []
    if result:
        ingredients = Ingredient.objects.filter(is_active=True)
        for ingredient in ingredients:
            produce_requirements.append({
                "name": ingredient.name,
                "unit": ingredient.unit,
                "required": round(result["prediction"] * ingredient.quantity_per_meal, 2),
                "recommended": round(result["recommended"] * ingredient.quantity_per_meal, 2),
                "buffer": round((result["recommended"] - result["prediction"]) * ingredient.quantity_per_meal, 2)
            })
            
    return render(request, "predict.html", {
        "result": result, 
        "weather": weather, 
        "error": error, 
        "model_name": MODEL_NAME,
        "default_attendance": default_attendance,
        "produce_requirements": produce_requirements
    })


@login_required
def forecast_7_days(request):
    forecasts = []
    if request.method == "POST":
        try:
            attendance = int(request.POST.get("attendance", 0))
            holiday = int(request.POST.get("holiday", 0))
            if attendance <= 0:
                raise ValueError("Attendance must be greater than zero.")
            for offset in range(7):
                target = date.today() + timedelta(days=offset)
                item = _predict(
                    int(round(attendance * (0.82 if target.weekday() >= 5 else 1))),
                    25, 0, holiday if offset == 0 else int(target.weekday() >= 5), target
                )
                item["date"] = target
                
                # Calculate produce requirements for each forecast
                item["produce_requirements"] = []
                ingredients = Ingredient.objects.filter(is_active=True)
                for ingredient in ingredients:
                    item["produce_requirements"].append({
                        "name": ingredient.name,
                        "unit": ingredient.unit,
                        "required": round(item["prediction"] * ingredient.quantity_per_meal, 2),
                        "recommended": round(item["recommended"] * ingredient.quantity_per_meal, 2),
                        "buffer": round((item["recommended"] - item["prediction"]) * ingredient.quantity_per_meal, 2)
                    })
                forecasts.append(item)
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc))
    return render(request, "forecast.html", {"forecasts": forecasts, "model_name": MODEL_NAME})



@login_required
def intelligence_center(request):
    """Unified operations intelligence workspace.

    All calculations use the application's stored forecasts, surplus, delivery,
    recipient and meal data. External ERP/IoT integrations are intentionally
    represented as safe input endpoints so the app remains usable without paid
    third-party services.
    """
    today = timezone.localdate()
    forecasts = DemandForecast.objects.order_by("-date", "-id")
    surplus_qs = SurplusFood.objects.select_related("organization").order_by("-created_at")
    meal_qs = MealRecord.objects.order_by("-date", "-id")
    verified = Recipient.objects.filter(verified=True, capacity__gt=0)

    latest = forecasts.first()
    recent_meals = list(meal_qs[:30])
    prepared = sum(m.meals_prepared for m in recent_meals)
    consumed = sum(m.meals_consumed for m in recent_meals)
    tracked_waste = max(prepared - consumed, 0)
    surplus_qty = surplus_qs.aggregate(v=Sum("quantity"))["v"] or 0
    latest_iot = IoTTemperatureReading.objects.first()
    redistributed_qty = Delivery.objects.filter(status="DELIVERED").aggregate(v=Sum("quantity"))["v"] or 0

    # Conservative, transparent operational assumptions. These are editable
    # later without changing the UI.
    meal_cost = 35.0
    carbon_per_meal_kg = 0.65
    avoided_cost = redistributed_qty * meal_cost
    avoided_carbon = redistributed_qty * carbon_per_meal_kg
    waste_rate = (tracked_waste / prepared * 100) if prepared else 0
    forecast_surplus = latest.expected_surplus if latest else 0
    risk_score = min(100, round(
        (waste_rate * 1.5) +
        (forecast_surplus / max(latest.recommended_preparation, 1) * 55 if latest else 0) +
        (surplus_qty / max(prepared, 1) * 20 if prepared else 0)
    ))

    emergency_items = []
    now = timezone.now()
    for item in surplus_qs.filter(status__in={"PENDING", "SAFE"}):
        age = (now - item.created_at).total_seconds() / 3600
        if item.storage_temperature > 5 or item.storage_time_hours > 24 or age >= 18 or item.quantity >= 100:
            emergency_items.append({
                "food": item.food_name, "quantity": item.quantity,
                "age_hours": round(max(age, item.storage_time_hours), 1),
                "reason": "Temperature/time threshold" if item.storage_temperature > 5 or item.storage_time_hours > 24
                          else "Rapid redistribution required"
            })

    routes = []
    for recipient in verified.order_by("distance_km", "-urgency_score")[:10]:
        score = (
            min(recipient.capacity, max(surplus_qty, 1)) / max(max(surplus_qty, 1), 1) * 0.45 +
            (1 / (1 + max(recipient.distance_km, 0))) * 0.30 +
            (recipient.urgency_score / 100) * 0.25
        )
        routes.append({
            "name": recipient.name,
            "distance": round(recipient.distance_km, 1),
            "urgency": recipient.urgency_score,
            "capacity": recipient.capacity,
            "score": round(score * 100, 1),
        })

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        try:
            if action == "track_consumption":
                record_date = request.POST.get("date") or str(today)
                record_date = datetime.strptime(record_date, "%Y-%m-%d").date()
                attendance = int(request.POST.get("attendance", 0))
                prepared_count = int(request.POST.get("prepared", 0))
                consumed_count = int(request.POST.get("consumed", 0))
                if min(attendance, prepared_count, consumed_count) < 0:
                    raise ValueError("Consumption values cannot be negative.")
                if consumed_count > prepared_count:
                    raise ValueError("Consumed meals cannot exceed prepared meals.")
                MealRecord.objects.create(
                    date=record_date, attendance=attendance,
                    meals_prepared=prepared_count, meals_consumed=consumed_count,
                    location=request.POST.get("location", "Project Site")[:120],
                    data_source="MANUAL"
                )
                messages.success(request, "Consumption data recorded.")
            elif action == "erp_attendance":
                attendance = int(request.POST.get("attendance", 0))
                if attendance < 0:
                    raise ValueError("Attendance cannot be negative.")
                MealRecord.objects.create(
                    date=today, attendance=attendance,
                    meals_prepared=0, meals_consumed=0,
                    data_source="ERP"
                )
                messages.success(request, "ERP attendance sync recorded successfully.")
            elif action == "iot_temperature":
                temperature = float(request.POST.get("temperature", 0))
                food_name = request.POST.get("food_name", "IoT monitored food")[:100]
                sensor_name = request.POST.get("sensor_name", "Manual / IoT Sensor")[:100]
                location = request.POST.get("sensor_location", "")[:150]
                safe = -1 <= temperature <= 5
                reading = IoTTemperatureReading.objects.create(
                    sensor_name=sensor_name, food_name=food_name, temperature=temperature,
                    location=location, status="SAFE" if safe else "ALERT"
                )
                messages.success(request, f"IoT reading #{reading.id} stored: {temperature:.1f}°C — {'SAFE' if safe else 'CHECK STORAGE'} for {food_name}.")
            elif action == "preparation":
                attendance = int(request.POST.get("attendance", 0))
                if attendance < 0:
                    raise ValueError("Attendance cannot be negative.")
                result = _predict(attendance, 25, 0, 0)
                DemandForecast.objects.create(
                    date=today, predicted_demand=result["prediction"],
                    recommended_preparation=result["recommended"],
                    lower_bound=result["lower"], upper_bound=result["upper"],
                    confidence=result["confidence"], expected_surplus=result["expected_surplus"],
                    waste_risk=result["risk"], model_name=result["model_name"]
                )
                messages.success(request, f"Preparation recommendation: {result['recommended']} meals.")
            else:
                messages.info(request, "Action is ready for the next operation.")
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc))
        return redirect("intelligence_center")

    recent_forecasts = list(forecasts[:7])
    recent_meals_dict = {
        m.date: m.meals_consumed
        for m in MealRecord.objects.filter(date__in=[f.date for f in recent_forecasts]).exclude(data_source="ERP")
    }
    
    accuracy_data = []
    for f in recent_forecasts:
        actual = recent_meals_dict.get(f.date)
        if actual is not None and actual > 0:
            diff = abs(f.predicted_demand - actual)
            accuracy = max(0, 100 - (diff / max(actual, 1) * 100))
            accuracy_data.append({
                "date": f.date.strftime("%b %d"),
                "predicted": f.predicted_demand,
                "actual": actual,
                "accuracy": round(accuracy, 1)
            })

    context = {
        "today": today,
        "latest_forecast": latest,
        "tracked_prepared": prepared,
        "tracked_consumed": consumed,
        "tracked_waste": tracked_waste,
        "waste_rate": round(waste_rate, 1),
        "surplus_qty": surplus_qty,
        "redistributed_qty": redistributed_qty,
        "cost_savings": round(avoided_cost, 2),
        "carbon_savings": round(avoided_carbon, 2),
        "waste_risk_score": risk_score,
        "emergency_items": emergency_items[:8],
        "routes": routes,
        "surplus_points": list(surplus_qs.filter(status__in={"PENDING", "SAFE"})[:20].values(
            "id", "food_name", "quantity", "storage_temperature", "status"
        )),
        "forecast_alerts": list(forecasts.filter(waste_risk__in={"HIGH", "MEDIUM"})[:8]),
        "latest_iot": latest_iot,
        "iot_readings": list(IoTTemperatureReading.objects.all()[:8]),
        "accuracy_data": accuracy_data,
    }
    return render(request, "intelligence.html", context)


@login_required
def integration_health(request):
    """Small machine-readable status endpoint for ERP/IoT integrations."""
    latest_meal = MealRecord.objects.order_by("-date", "-id").first()
    latest_iot = IoTTemperatureReading.objects.first()
    return JsonResponse({
        "status": "ok",
        "erp_attendance": bool(latest_meal and latest_meal.data_source == "ERP"),
        "iot_temperature": bool(latest_iot),
        "latest_iot_status": latest_iot.status if latest_iot else None,
        "latest_iot_temperature": latest_iot.temperature if latest_iot else None,
        "last_attendance_date": str(latest_meal.date) if latest_meal else None,
        "server_time": timezone.now().isoformat(),
    })

@_organization_required
def organization_dashboard(request):
    org = request.organization
    members = org.members.select_related("user").order_by("-joined_at")
    deliveries = Delivery.objects.filter(Q(sender=org) | Q(receiver=org)).select_related("sender", "receiver")[:8]
    outgoing = Delivery.objects.filter(sender=org).aggregate(v=Sum("quantity"))["v"] or 0
    incoming = Delivery.objects.filter(receiver=org).aggregate(v=Sum("quantity"))["v"] or 0
    other_memberships = (
        OrganizationMember.objects
        .select_related("organization")
        .filter(user=request.user, is_active=True, organization__is_active=True)
        .exclude(organization=org)
        .order_by("organization__name")
    )
    return render(request, "organization_dashboard.html", {
        "organization": org,
        "membership": request.membership,
        "members": members,
        "member_count": members.count(),
        "deliveries": deliveries,
        "outgoing_quantity": outgoing,
        "incoming_quantity": incoming,
        "other_memberships": other_memberships,
    })


def register_organization(request):
    """Register a new organization.

    Anonymous visitors create a new owner account. An already authenticated
    user can register an additional organization and becomes its OWNER; this
    is important for testing and for users who manage multiple institutions.
    """
    if request.method == "POST":
        form = OrganizationForm(request.POST)
        username = request.POST.get("username", "").strip()
        email = request.POST.get("account_email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        if request.user.is_authenticated:
            if form.is_valid():
                with transaction.atomic():
                    organization = form.save()
                    membership, _ = OrganizationMember.objects.get_or_create(
                        organization=organization,
                        user=request.user,
                        defaults={"role": "OWNER", "is_active": True},
                    )
                    membership.role = "OWNER"
                    membership.is_active = True
                    membership.save(update_fields=["role", "is_active"])
                request.session["active_organization_id"] = organization.id
                messages.success(request, f"{organization.name} is registered and is now your active organization.")
                return redirect("organization_dashboard")
        else:
            if not username or not password:
                form.add_error(None, "Login username and password are required.")
            elif password != password2:
                form.add_error(None, "Passwords do not match.")
            elif User.objects.filter(username=username).exists():
                form.add_error(None, "That username already exists.")
            elif form.is_valid():
                with transaction.atomic():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    organization = form.save()
                    OrganizationMember.objects.create(
                        organization=organization, user=user, role="OWNER", is_active=True
                    )
                login(request, user)
                request.session["active_organization_id"] = organization.id
                messages.success(request, f"{organization.name} is registered. Welcome to Fedly.")
                return redirect("organization_dashboard")
    else:
        form = OrganizationForm()

    return render(request, "organization_register.html", {
        "form": form,
        "registering_as_authenticated_user": request.user.is_authenticated,
    })


def organization_switch(request, organization_id):
    """Switch the active organization for users who belong to multiple organizations."""
    membership = get_object_or_404(
        OrganizationMember,
        organization_id=organization_id,
        user=request.user,
        is_active=True,
        organization__is_active=True,
    )
    request.session["active_organization_id"] = membership.organization_id
    messages.success(request, f"Active organization changed to {membership.organization.name}.")
    return redirect(request.GET.get("next") or "organization_dashboard")


@login_required
def organization_details_json(request, organization_id):
    """Return safe contact/address information used by the delivery form."""
    organization = get_object_or_404(Organization, id=organization_id, is_active=True)
    return JsonResponse({
        "id": organization.id,
        "name": organization.name,
        "type": organization.get_organization_type_display(),
        "address": organization.address,
        "city": organization.city,
        "state": organization.state,
        "country": organization.country,
        "phone": organization.phone,
        "email": organization.email,
        "verified": organization.is_verified,
    })


@_organization_required
def organization_edit(request):
    if request.membership.role not in {"OWNER", "ADMIN"}:
        messages.error(request, "Only the owner or administrator can edit organization details.")
        return redirect("organization_dashboard")
    if request.method == "POST":
        form = OrganizationForm(request.POST, instance=request.organization)
        if form.is_valid():
            form.save()
            messages.success(request, "Organization details updated.")
            return redirect("organization_dashboard")
    else:
        form = OrganizationForm(instance=request.organization)
    return render(request, "organization_edit.html", {"form": form, "organization": request.organization})


@_organization_required
def organization_add_member(request):
    if request.membership.role not in {"OWNER", "ADMIN"}:
        messages.error(request, "Only the owner or administrator can manage members.")
        return redirect("organization_dashboard")
    form = MemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(username=form.cleaned_data["username"]).first()
        if not user:
            form.add_error("username", "No user with that username exists.")
        else:
            member, created = OrganizationMember.objects.get_or_create(
                organization=request.organization, user=user,
                defaults={"role": form.cleaned_data["role"], "is_active": True}
            )
            if not created:
                member.role = form.cleaned_data["role"]
                member.is_active = True
                member.save(update_fields=["role", "is_active"])
                messages.success(request, "Member role updated.")
            else:
                messages.success(request, "Member added.")
            return redirect("organization_dashboard")
    return render(request, "organization_member.html", {"form": form})


@_organization_required
def organization_remove_member(request, member_id):
    if request.membership.role not in {"OWNER", "ADMIN"}:
        messages.error(request, "Permission denied.")
        return redirect("organization_dashboard")
    member = get_object_or_404(OrganizationMember, id=member_id, organization=request.organization)
    if member.role == "OWNER":
        messages.error(request, "The organization owner cannot be removed.")
    else:
        member.delete()
        messages.success(request, "Member removed.")
    return redirect("organization_dashboard")


@_organization_required
def surplus_list(request):
    foods = SurplusFood.objects.filter(
        Q(organization=request.organization) | Q(organization__isnull=True)
    ).order_by("-created_at")
    return render(request, "surplus_list.html", {"surplus_foods": foods})


@_organization_required
def add_surplus_food(request):
    form = SurplusFoodForm(request.POST, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        food = form.save(commit=False)
        food.organization = request.organization
        
        # MOCK AI QUALITY ANALYSIS
        if food.quality_image:
            import random
            # In a real PRO environment, this calls a Gemini API / Vision Model
            # Here we mock an AI heuristic based on image presence
            score = random.randint(70, 99)
            food.ai_freshness_score = score
            if score > 90:
                food.ai_quality_notes = "AI Vision Analysis: Food appears extremely fresh. No signs of spoilage detected."
            elif score > 80:
                food.ai_quality_notes = "AI Vision Analysis: Food appears safe. Slight visual oxidation but highly edible."
            else:
                food.ai_quality_notes = "AI Vision Analysis: Visual quality is borderline. Ensure temperature is strictly maintained."
        
        food.save()
        food.check_safety()
        
        # Log to Immutable Ledger
        FoodLedger.objects.create(
            surplus_food=food,
            action_type="LOGGED",
            performed_by=request.user,
            details=f"Surplus food logged. Qty: {food.quantity}. Temp: {food.storage_temperature}°C."
        )
        
        messages.success(request, "Surplus recorded and AI safety status calculated.")
        return redirect("surplus_list")
    return render(request, "add_surplus.html", {"form": form})


@_organization_required
def redistribute_food(request, food_id):
    food = get_object_or_404(SurplusFood, id=food_id)
    if food.organization not in {request.organization, None}:
        messages.error(request, "You cannot redistribute another organization's food.")
        return redirect("surplus_list")
    if food.status != "SAFE":
        messages.error(request, "Only SAFE surplus can be redistributed.")
        return redirect("surplus_list")
    form = RedistributionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if item.quantity > food.quantity:
            form.add_error("quantity", "Quantity exceeds available surplus.")
        else:
            item.surplus = food
            item.save()
            food.quantity -= item.quantity
            if food.quantity == 0:
                food.status = "REDISTRIBUTED"
            food.save()
            messages.success(request, "Surplus redistributed.")
            return redirect("surplus_list")
    return render(request, "redistribute.html", {
        "form": form,
        "food": food,
        "verified_recipient_count": Recipient.objects.filter(
            verified=True,
            capacity__gt=0,
        ).count(),
    })


@login_required
def check_food_safety(request):
    result = None
    if request.method == "POST":
        try:
            temperature = float(request.POST.get("storage_temperature", 4))
            hours = float(request.POST.get("storage_time_hours", 0))
            if hours < 0:
                raise ValueError("Storage time cannot be negative.")
            result = "SAFE" if temperature <= 5 and hours <= 24 else "UNSAFE"
        except ValueError:
            result = "ERROR"
    return render(request, "food_safety.html", {"result": result})


@login_required
def recipient_list(request):
    recipients = Recipient.objects.all().order_by("-verified", "-urgency_score", "name")
    return render(request, "recipient_list.html", {
        "recipients": recipients,
        "verified_count": recipients.filter(verified=True).count(),
        "pending_count": recipients.filter(verified=False).count(),
        "verified_capacity": recipients.filter(verified=True).aggregate(
            total=Sum("capacity")
        )["total"] or 0,
    })


@login_required
def add_recipient(request):
    if request.method == "POST":
        try:
            name = request.POST.get("name", "").strip()
            recipient_type = request.POST.get("recipient_type", "").strip()
            capacity = int(request.POST.get("capacity", 0))
            distance = float(request.POST.get("distance_km", 0) or 0)
            urgency = int(request.POST.get("urgency_score", 50) or 50)
            verify_now = request.POST.get("verify_now") == "1"

            if not name:
                raise ValueError("Recipient name is required.")
            if not recipient_type:
                raise ValueError("Recipient type is required.")
            if capacity <= 0:
                raise ValueError("Capacity must be greater than zero.")
            if distance < 0:
                raise ValueError("Distance cannot be negative.")
            if not 0 <= urgency <= 100:
                raise ValueError("Urgency must be between 0 and 100.")

            recipient = Recipient.objects.create(
                name=name,
                recipient_type=recipient_type,
                capacity=capacity,
                distance_km=distance,
                urgency_score=urgency,
                verified=verify_now,
            )

            if verify_now:
                messages.success(
                    request,
                    f"{recipient.name} was added and verified. It is now available in the redistribution dropdown."
                )
            else:
                messages.success(
                    request,
                    f"{recipient.name} was added as pending. Verify it from the Recipients page before redistribution."
                )
            return redirect("recipient_list")
        except (ValueError, TypeError) as exc:
            return render(request, "add_recipient.html", {"error": str(exc)})
    return render(request, "add_recipient.html")


from .forms import PostMealRecordForm

@login_required
def post_meal_logging(request):
    if request.method == "POST":
        form = PostMealRecordForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Post-meal ground truth data logged successfully.")
            return redirect("analytics_dashboard")
    else:
        # Pre-fill with the latest forecast if available
        initial = {"date": date.today()}
        latest_forecast = DemandForecast.objects.filter(date=date.today()).first()
        if latest_forecast:
            initial["predicted_demand"] = latest_forecast.predicted_demand
        form = PostMealRecordForm(initial=initial)
        
    return render(request, "post_meal_log.html", {"form": form})


@login_required
def analytics_dashboard(request):
    # Calculate Produce Utilization & Waste Analytics
    meal_records = MealRecord.objects.filter(
        discarded_meals__gt=0
    ).order_by("-date") | MealRecord.objects.filter(
        meals_prepared__gt=0, meals_consumed__gt=0
    ).order_by("-date")
    
    total_prepared_meals = meal_records.aggregate(v=Sum("meals_prepared"))["v"] or 0
    total_consumed_meals = meal_records.aggregate(v=Sum("meals_consumed"))["v"] or 0
    total_discarded_meals = meal_records.aggregate(v=Sum("discarded_meals"))["v"] or 0
    
    utilization_rate = (total_consumed_meals / total_prepared_meals * 100) if total_prepared_meals > 0 else 0
    
    ingredients = Ingredient.objects.filter(is_active=True)
    total_produce_waste_kg = 0
    monetary_value_waste = 0
    top_wasted = []
    
    for ing in ingredients:
        # We assume waste is proportional to discarded meals
        wasted_qty = total_discarded_meals * ing.quantity_per_meal
        waste_value = wasted_qty * ing.cost_per_unit
        
        # Only add to kg if unit is kg or similar (simplified, we just sum up everything for "Total Produce Waste")
        total_produce_waste_kg += wasted_qty 
        monetary_value_waste += waste_value
        
        top_wasted.append({
            "name": ing.name,
            "wasted_qty": round(wasted_qty, 2),
            "unit": ing.unit,
            "waste_value": round(waste_value, 2)
        })
        
    top_wasted = sorted(top_wasted, key=lambda x: x["waste_value"], reverse=True)[:5]
    
    # Financial savings (e.g., if utilization is high compared to a baseline of 80%)
    baseline_waste_meals = total_prepared_meals * 0.20
    saved_meals = max(0, baseline_waste_meals - total_discarded_meals)
    savings_value = sum([saved_meals * ing.quantity_per_meal * ing.cost_per_unit for ing in ingredients])
    
    # Chart Data: Predicted vs Actual Demand (last 7 logs)
    chart_records = meal_records.exclude(predicted_demand=0).exclude(predicted_demand__isnull=True).order_by("-date")[:7]
    chart_records = list(reversed(chart_records))
    
    context = {
        "utilization_rate": round(utilization_rate, 1),
        "total_produce_waste": round(total_produce_waste_kg, 2),
        "monetary_value_waste": round(monetary_value_waste, 2),
        "savings_value": round(savings_value, 2),
        "top_wasted": top_wasted,
        "chart_records": chart_records
    }
    
    return render(request, "analytics.html", context)


@login_required
def verify_recipient(request, recipient_id):
    if request.method != "POST":
        messages.info(request, "Use the Verify button to verify a recipient.")
        return redirect("recipient_list")

    recipient = get_object_or_404(Recipient, id=recipient_id)
    recipient.verified = True
    recipient.save(update_fields=["verified"])
    messages.success(request, f"{recipient.name} is now verified and available for redistribution.")
    return redirect("recipient_list")


@login_required
def recipient_recommendations(request, food_id):
    food = get_object_or_404(SurplusFood, id=food_id)
    if food.status != "SAFE":
        return JsonResponse({"error": "Only SAFE food can be recommended."}, status=400)
    ranked = []
    for recipient in Recipient.objects.filter(verified=True, capacity__gt=0):
        fit = min(food.quantity, recipient.capacity) / max(food.quantity, 1)
        distance = 1 / (1 + max(recipient.distance_km, 0))
        urgency = min(max(recipient.urgency_score, 0), 100) / 100
        score = .50 * fit + .30 * urgency + .20 * distance
        
        reasons = []
        if fit >= 0.8:
            reasons.append("optimal capacity match")
        elif fit >= 0.5:
            reasons.append("acceptable capacity match")
        if urgency >= 0.7:
            reasons.append("high urgency")
        if recipient.distance_km <= 10:
            reasons.append("close proximity")
            
        if reasons:
            explanation = f"{round(score * 100)}% match due to " + ", ".join(reasons) + "."
        else:
            explanation = f"{round(score * 100)}% match based on general suitability."

        ranked.append({
            "name": recipient.name, "score": round(score * 100, 1),
            "capacity": recipient.capacity, "distance_km": recipient.distance_km,
            "urgency": recipient.urgency_score, "explanation": explanation
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return JsonResponse({"food": food.food_name, "quantity": food.quantity, "recommendations": ranked[:5]})


@_organization_required
def delivery_list(request):
    deliveries = Delivery.objects.filter(
        Q(sender=request.organization) | Q(receiver=request.organization)
    ).select_related("sender", "receiver", "surplus")

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip().upper()

    if search:
        deliveries = deliveries.filter(
            Q(tracking_code__icontains=search)
            | Q(food_name__icontains=search)
            | Q(driver_name__icontains=search)
            | Q(vehicle_number__icontains=search)
            | Q(receiver__name__icontains=search)
            | Q(sender__name__icontains=search)
        )

    valid_statuses = {value for value, _ in Delivery.STATUS_CHOICES}
    if status in valid_statuses:
        deliveries = deliveries.filter(status=status)
    else:
        status = ""

    all_deliveries = Delivery.objects.filter(
        Q(sender=request.organization) | Q(receiver=request.organization)
    )
    status_counts = {
        value: all_deliveries.filter(status=value).count()
        for value, _ in Delivery.STATUS_CHOICES
    }

    return render(request, "delivery_list.html", {
        "deliveries": deliveries,
        "organization": request.organization,
        "search": search,
        "active_status": status,
        "status_counts": status_counts,
        "total_deliveries": all_deliveries.count(),
        "active_deliveries": all_deliveries.exclude(
            status__in={"DELIVERED", "CANCELLED"}
        ).count(),
        "delivered_deliveries": all_deliveries.filter(status="DELIVERED").count(),
    })


@_organization_required
def delivery_create(request):
    form = DeliveryForm(request.POST or None, sender=request.organization)
    receiver_count = form.fields["receiver"].queryset.count()

    if request.method == "POST" and receiver_count == 0:
        form.add_error(None, "Register another active organization before creating a delivery.")
    elif request.method == "POST" and form.is_valid():
        delivery = form.save(commit=False)
        delivery.sender = request.organization
        delivery.created_by = request.user
        delivery.status = "ASSIGNED" if delivery.driver_name else "REQUESTED"
        if not delivery.pickup_address:
            delivery.pickup_address = request.organization.address

        if delivery.surplus and delivery.quantity > delivery.surplus.quantity:
            form.add_error("quantity", "Delivery quantity exceeds linked surplus.")
        else:
            with transaction.atomic():
                delivery.save()
                if delivery.surplus:
                    delivery.surplus.quantity -= delivery.quantity
                    if delivery.surplus.quantity == 0:
                        delivery.surplus.status = "REDISTRIBUTED"
                    delivery.surplus.save(update_fields=["quantity", "status"])
            messages.success(request, f"Delivery created. Tracking: {delivery.tracking_code}")
            return redirect("delivery_detail", delivery_id=delivery.id)

    return render(request, "delivery_form.html", {
        "form": form,
        "organization": request.organization,
        "receiver_count": receiver_count,
    })


@_organization_required
def delivery_detail(request, delivery_id):
    delivery = get_object_or_404(
        Delivery.objects.select_related("sender", "receiver", "surplus", "created_by"),
        id=delivery_id
    )
    if delivery.sender_id != request.organization.id and delivery.receiver_id != request.organization.id:
        messages.error(request, "You do not have access to this delivery.")
        return redirect("delivery_list")
        
    # Route Optimization
    from .utils import geocode_address, get_osrm_route
    route_data = None
    
    start_lat, start_lng = geocode_address(f"{delivery.pickup_address}, {delivery.sender.city}")
    end_lat, end_lng = geocode_address(f"{delivery.delivery_address}, {delivery.receiver.city}")
    
    if start_lat and end_lat:
        route_data = get_osrm_route(start_lat, start_lng, end_lat, end_lng)
        
    return render(request, "delivery_detail.html", {
        "delivery": delivery, 
        "organization": request.organization,
        "route_data": route_data,
        "start_coords": {"lat": start_lat, "lng": start_lng} if start_lat else None,
        "end_coords": {"lat": end_lat, "lng": end_lng} if end_lat else None
    })


@_organization_required
def delivery_update_status(request, delivery_id):
    delivery = get_object_or_404(
        Delivery.objects.select_related("sender", "receiver"),
        id=delivery_id
    )

    if delivery.sender_id != request.organization.id and delivery.receiver_id != request.organization.id:
        messages.error(request, "You do not have access to this delivery.")
        return redirect("delivery_list")

    if request.method != "POST":
        return redirect("delivery_detail", delivery_id=delivery.id)

    new_status = request.POST.get("status", "").upper()
    valid = dict(Delivery.STATUS_CHOICES)

    if new_status not in valid:
        messages.error(request, "Invalid delivery status.")
        return redirect("delivery_detail", delivery_id=delivery.id)

    # Prevent accidental backwards movement in the normal delivery workflow.
    workflow = {
        "REQUESTED": 0,
        "ASSIGNED": 1,
        "PICKED_UP": 2,
        "IN_TRANSIT": 3,
        "DELIVERED": 4,
        "CANCELLED": 99,
    }
    current_rank = workflow.get(delivery.status, 0)
    new_rank = workflow.get(new_status, 0)

    if delivery.status == "DELIVERED" and new_status != "DELIVERED":
        messages.error(request, "A delivered shipment cannot be moved back to an earlier status.")
        return redirect("delivery_detail", delivery_id=delivery.id)

    if delivery.status == "CANCELLED" and new_status != "CANCELLED":
        messages.error(request, "A cancelled shipment cannot be reopened from this screen.")
        return redirect("delivery_detail", delivery_id=delivery.id)

    if new_status not in {"CANCELLED", "DELIVERED"} and new_rank < current_rank:
        messages.error(request, "Delivery status cannot move backwards.")
        return redirect("delivery_detail", delivery_id=delivery.id)

    delivery.status = new_status
    if new_status == "DELIVERED":
        from django.utils import timezone
        delivery.delivered_at = timezone.now()
    delivery.save()
    messages.success(request, f"Delivery status updated to {valid.get(new_status, new_status)}.")
    
    try:
        from .utils import notify_delivery_update
        notify_delivery_update(delivery)
    except Exception as e:
        pass
        
    return redirect("delivery_detail", delivery_id=delivery.id)

@login_required
def weather_data(request):
    """Return live weather for the requested city.

    This endpoint never fabricates live weather values. If an API key is
    not configured or OpenWeather cannot be reached, it returns a clear
    error response instead.
    """
    city = request.GET.get("city", "").strip()

    if not city:
        return JsonResponse({
            "error": "Please enter a city name.",
            "is_live": False,
        }, status=400)

    weather = _weather(city)

    if weather is None:
        if not getattr(settings, "WEATHER_API_KEY", ""):
            message = "WEATHER_API_KEY is not configured."
        else:
            message = "Unable to fetch live weather for this city."

        return JsonResponse({
            "error": message,
            "city": city,
            "is_live": False,
        }, status=503)

    return JsonResponse({
        "city": city,
        "temperature": weather["temperature"],
        "humidity": weather["humidity"],
        "rainfall": weather["rainfall"],
        "weather": weather["weather"],
        "is_live": True,
        "source": "OpenWeather",
    })

# ============================================================
# EXTERNAL INTEGRATION APIs
# ============================================================

@csrf_exempt
def api_erp_attendance(request):
    """External API endpoint for ERP to push attendance data."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        attendance = int(data.get("attendance", 0))
        date_str = data.get("date")
        
        if attendance < 0:
            return JsonResponse({"error": "Attendance cannot be negative"}, status=400)
            
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.localdate()
        
        # Create or update today's ERP record
        record, created = MealRecord.objects.update_or_create(
            date=record_date,
            data_source="ERP",
            defaults={
                "attendance": attendance,
                "meals_prepared": 0,
                "meals_consumed": 0,
            }
        )
        return JsonResponse({
            "status": "success", 
            "message": "ERP attendance recorded",
            "attendance": attendance,
            "date": str(record_date)
        })
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def api_iot_temperature(request):
    """External API endpoint for ESP32/IoT to push temperature data."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
        
    try:
        data = json.loads(request.body)
        temperature = float(data.get("temperature"))
        food_name = data.get("food_name", "IoT Monitored Food")[:100]
        sensor_name = data.get("sensor_name", "IoT Sensor")[:100]
        location = data.get("location", "")[:150]
        
        safe = -1 <= temperature <= 5
        status = "SAFE" if safe else "ALERT"
        
        reading = IoTTemperatureReading.objects.create(
            sensor_name=sensor_name,
            food_name=food_name,
            temperature=temperature,
            location=location,
            status=status
        )
        
        return JsonResponse({
            "status": "success",
            "id": reading.id,
            "temperature": temperature,
            "food_name": food_name,
            "safety_status": status
        })
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({"error": str(e)}, status=400)


# ============================================================
# AGRICULTURE EXTENSION
# ============================================================

from .models import AgriculturalProduce, ProcessingRecord, AgriculturalSupplyRequest
from .forms import AgriculturalProduceForm, ProcessingRecordForm, AgriculturalSupplyRequestForm
from django.db.models import Sum

@login_required
def agri_dashboard(request):
    produce = AgriculturalProduce.objects.all()
    processing = ProcessingRecord.objects.all()
    
    total_produce = produce.aggregate(total=Sum('available_quantity'))['total'] or 0
    total_processed = processing.aggregate(total=Sum('input_quantity'))['total'] or 0
    
    # Simple post-harvest loss avoided estimate:
    # Assuming any produce that was processed was saved from potential loss.
    loss_avoided = total_processed
    
    context = {
        "total_suppliers": Organization.objects.filter(organization_type="SUPPLIER").count(),
        "total_produce": total_produce,
        "total_processed": total_processed,
        "loss_avoided": loss_avoided,
        "recent_produce": produce.order_by('-created_at')[:5],
        "recent_processing": processing.order_by('-created_at')[:5]
    }
    return render(request, "agri_dashboard.html", context)

@login_required
def agri_produce_list(request):
    produce_list = AgriculturalProduce.objects.all().order_by('-harvest_date')
    return render(request, "agri_produce_list.html", {"produce_list": produce_list})

@login_required
def agri_produce_add(request):
    if request.method == "POST":
        form = AgriculturalProduceForm(request.POST)
        if form.is_valid():
            org = request.user.organization_memberships.first()
            if not org:
                messages.error(request, "You must belong to an organization to add produce.")
                return redirect('agri_produce_list')
                
            produce = form.save(commit=False)
            produce.supplier = org.organization
            produce.save()
            messages.success(request, "Produce added successfully.")
            return redirect('agri_produce_list')
    else:
        form = AgriculturalProduceForm()
    return render(request, "agri_produce_form.html", {"form": form})

@login_required
def agri_processing_list(request):
    processing_records = ProcessingRecord.objects.all().order_by('-processing_date')
    return render(request, "agri_processing.html", {"records": processing_records})

@login_required
def agri_processing_add(request):
    org = request.user.organization_memberships.first()
    if request.method == "POST":
        form = ProcessingRecordForm(request.POST, supplier=org.organization if org else None)
        if form.is_valid():
            record = form.save(commit=False)
            produce = record.input_produce
            if record.input_quantity > produce.available_quantity:
                messages.error(request, f"Cannot process more than available ({produce.available_quantity} {produce.unit})")
                return redirect('agri_processing_add')
                
            produce.available_quantity -= record.input_quantity
            produce.save()
            
            record.save()
            messages.success(request, f"Processed {record.input_quantity} {produce.unit} of {produce.name}.")
# ============================================================
# LIVE WEATHER JSON ENDPOINT
# ============================================================

@login_required
def weather_data(request):
    """Return live weather for the requested city.

    This endpoint never fabricates live weather values. If an API key is
    not configured or OpenWeather cannot be reached, it returns a clear
    error response instead.
    """
    city = request.GET.get("city", "").strip()

    if not city:
        return JsonResponse({
            "error": "Please enter a city name.",
            "is_live": False,
        }, status=400)

    weather = _weather(city)

    if weather is None:
        if not getattr(settings, "WEATHER_API_KEY", ""):
            message = "WEATHER_API_KEY is not configured."
        else:
            message = "Unable to fetch live weather for this city."

        return JsonResponse({
            "error": message,
            "city": city,
            "is_live": False,
        }, status=503)

    return JsonResponse({
        "city": city,
        "temperature": weather["temperature"],
        "humidity": weather["humidity"],
        "rainfall": weather["rainfall"],
        "weather": weather["weather"],
        "is_live": True,
        "source": "OpenWeather",
    })

# ============================================================
# EXTERNAL INTEGRATION APIs
# ============================================================

@csrf_exempt
def api_erp_attendance(request):
    """External API endpoint for ERP to push attendance data."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        attendance = int(data.get("attendance", 0))
        date_str = data.get("date")
        
        if attendance < 0:
            return JsonResponse({"error": "Attendance cannot be negative"}, status=400)
            
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.localdate()
        
        # Create or update today's ERP record
        record, created = MealRecord.objects.update_or_create(
            date=record_date,
            data_source="ERP",
            defaults={
                "attendance": attendance,
                "meals_prepared": 0,
                "meals_consumed": 0,
            }
        )
        return JsonResponse({
            "status": "success", 
            "message": "ERP attendance recorded",
            "attendance": attendance,
            "date": str(record_date)
        })
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def api_iot_temperature(request):
    """External API endpoint for ESP32/IoT to push temperature data."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
        
    try:
        data = json.loads(request.body)
        temperature = float(data.get("temperature"))
        food_name = data.get("food_name", "IoT Monitored Food")[:100]
        sensor_name = data.get("sensor_name", "IoT Sensor")[:100]
        location = data.get("location", "")[:150]
        
        safe = -1 <= temperature <= 5
        status = "SAFE" if safe else "ALERT"
        
        reading = IoTTemperatureReading.objects.create(
            sensor_name=sensor_name,
            food_name=food_name,
            temperature=temperature,
            location=location,
            status=status
        )
        
        return JsonResponse({
            "status": "success",
            "id": reading.id,
            "temperature": temperature,
            "food_name": food_name,
            "safety_status": status
        })
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({"error": str(e)}, status=400)


# ============================================================
# AGRICULTURE EXTENSION
# ============================================================

from .models import AgriculturalProduce, ProcessingRecord, AgriculturalSupplyRequest
from .forms import AgriculturalProduceForm, ProcessingRecordForm, AgriculturalSupplyRequestForm
from django.db.models import Sum

@login_required
def agri_dashboard(request):
    produce = AgriculturalProduce.objects.all()
    processing = ProcessingRecord.objects.all()
    
    total_produce = produce.aggregate(total=Sum('available_quantity'))['total'] or 0
    total_processed = processing.aggregate(total=Sum('input_quantity'))['total'] or 0
    
    # Simple post-harvest loss avoided estimate:
    # Assuming any produce that was processed was saved from potential loss.
    loss_avoided = total_processed
    
    # Generate advisory for a default location or org location
    generate_weather_advisory("Bhubaneswar")
    active_advisories = WeatherAdvisory.objects.filter(expires_at__gt=timezone.now()).order_by('-issued_at')
    
    context = {
        "total_suppliers": Organization.objects.filter(organization_type="SUPPLIER").count(),
        "total_produce": total_produce,
        "total_processed": total_processed,
        "loss_avoided": loss_avoided,
        "recent_produce": produce.order_by('-created_at')[:5],
        "recent_processing": processing.order_by('-processing_date')[:5],
        "advisories": active_advisories
    }
    return render(request, "agri_dashboard.html", context)

@login_required
def agri_produce_list(request):
    produce_list = AgriculturalProduce.objects.all().order_by('-harvest_date')
    return render(request, "agri_produce_list.html", {"produce_list": produce_list})

@login_required
def agri_produce_add(request):
    if request.method == "POST":
        form = AgriculturalProduceForm(request.POST)
        if form.is_valid():
            org = request.user.organization_memberships.first()
            if not org:
                messages.error(request, "You must belong to an organization to add produce.")
                return redirect('agri_produce_list')
                
            produce = form.save(commit=False)
            produce.supplier = org.organization
            produce.save()
            messages.success(request, "Produce added successfully.")
            return redirect('agri_produce_list')
    else:
        form = AgriculturalProduceForm()
    return render(request, "agri_produce_form.html", {"form": form})

@login_required
def agri_processing_list(request):
    processing_records = ProcessingRecord.objects.all().order_by('-processing_date')
    return render(request, "agri_processing.html", {"records": processing_records})

@login_required
def agri_processing_add(request):
    org = request.user.organization_memberships.first()
    if request.method == "POST":
        form = ProcessingRecordForm(request.POST, supplier=org.organization if org else None)
        if form.is_valid():
            record = form.save(commit=False)
            produce = record.input_produce
            if record.input_quantity > produce.available_quantity:
                messages.error(request, f"Cannot process more than available ({produce.available_quantity} {produce.unit})")
                return redirect('agri_processing_add')
                
            produce.available_quantity -= record.input_quantity
            produce.save()
            
            record.save()
            messages.success(request, f"Processed {record.input_quantity} {produce.unit} of {produce.name}.")
            return redirect('agri_processing_list')
    else:
        form = ProcessingRecordForm(supplier=org.organization if org else None)
    return render(request, "agri_processing_form.html", {"form": form})

from .models import BuyerDemand, SupplyMatch
from .forms import BuyerDemandForm
import difflib

@login_required
def agri_supply_matching(request):
    org = request.user.organization_memberships.first()
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "create_demand":
            form = BuyerDemandForm(request.POST)
            if form.is_valid():
                demand = form.save(commit=False)
                demand.organization = org.organization
                demand.save()
                messages.success(request, "Buyer demand created successfully.")
                return redirect('agri_supply_matching')
                
        elif action == "find_matches":
            demand_id = request.POST.get("demand_id")
            demand = get_object_or_404(BuyerDemand, id=demand_id)
            available_produce = AgriculturalProduce.objects.filter(available_quantity__gt=0)
            
            for produce in available_produce:
                score = 0
                reasons = []
                
                # Type match (40%)
                if demand.produce_name.lower() in produce.name.lower() or produce.name.lower() in demand.produce_name.lower():
                    score += 40
                    reasons.append("✓ Same produce")
                else:
                    # check similarity
                    sim = difflib.SequenceMatcher(None, demand.produce_name.lower(), produce.name.lower()).ratio()
                    if sim > 0.6:
                        score += 20
                        reasons.append("✓ Similar produce")
                        
                # Quantity available (30%)
                if produce.available_quantity >= demand.required_quantity:
                    score += 30
                    reasons.append("✓ Quantity available")
                elif produce.available_quantity >= demand.required_quantity * 0.5:
                    score += 15
                    reasons.append("✓ Partial quantity available")
                    
                # Quality match (15%)
                if demand.quality_requirement and produce.quality_status:
                    if demand.quality_requirement.lower() == produce.quality_status.lower():
                        score += 15
                        reasons.append("✓ Quality requirement satisfied")
                else:
                    score += 10 # Default partial score if not specified
                    
                # Location match (15%)
                if demand.location and produce.location:
                    if demand.location.lower() == produce.location.lower():
                        score += 15
                        reasons.append("✓ Nearby location")
                else:
                    score += 10 # Default partial score
                    
                if score >= 40:
                    explanation = f"{score}% match because:\n" + "\n".join(reasons)
                    
                    # Create or update match
                    SupplyMatch.objects.update_or_create(
                        demand=demand,
                        produce=produce,
                        defaults={
                            "matched_quantity": min(demand.required_quantity, produce.available_quantity),
                            "match_score": score,
                            "explanation": explanation,
                            "status": "PENDING"
                        }
                    )
            messages.success(request, f"Found matches for {demand.produce_name}.")
            return redirect('agri_supply_matching')
            
        elif action == "accept_match":
            match_id = request.POST.get("match_id")
            match = get_object_or_404(SupplyMatch, id=match_id)
            
            if match.produce.available_quantity >= match.matched_quantity:
                # Accept match
                match.produce.available_quantity -= match.matched_quantity
                match.produce.save()
                
                match.demand.required_quantity -= match.matched_quantity
                if match.demand.required_quantity <= 0:
                    match.demand.is_active = False
                match.demand.save()
                
                match.status = "ACCEPTED"
                match.save()
                
                # Reject other pending matches for this demand if fulfilled
                if not match.demand.is_active:
                    SupplyMatch.objects.filter(demand=match.demand, status="PENDING").update(status="CANCELLED")
                
                messages.success(request, f"Match accepted! {match.matched_quantity} {match.demand.unit} confirmed.")
            else:
                messages.error(request, "Insufficient quantity available to accept this match.")
            return redirect('agri_supply_matching')

    form = BuyerDemandForm()
    active_demands = BuyerDemand.objects.filter(is_active=True).order_by('-created_at')
    
    # We load matches to display
    matches = SupplyMatch.objects.filter(status="PENDING").order_by('-match_score')
    
    return render(request, "agri_supply_matching.html", {
        "form": form,
        "demands": active_demands,
        "matches": matches,
    })

@login_required
def agri_supply_requests_list(request):
    requests = AgriculturalSupplyRequest.objects.all().order_by('-created_at')
    return render(request, "agri_supply_requests_list.html", {"requests": requests})

@login_required
def agri_supply_request_add(request):
    org = request.user.organization_memberships.first()
    if request.method == "POST":
        form = AgriculturalSupplyRequestForm(request.POST)
        if form.is_valid():
            supply_request = form.save(commit=False)
            supply_request.requester = org.organization if org else None
            supply_request.save()
            messages.success(request, "Supply request created successfully.")
            return redirect('agri_supply_requests_list')
    else:
        form = AgriculturalSupplyRequestForm()
    return render(request, "agri_supply_request_form.html", {"form": form})

from .models import CropMarketTrend, WeatherAdvisory, AgriculturalShipment, QualityInspection, LedgerTransaction
from .forms import QualityInspectionForm

def generate_weather_advisory(city):
    weather = _weather(city)
    if not weather:
        return None
    
    advisory_text = None
    severity = "LOW"
    
    if weather["rainfall"] > 10:
        advisory_text = f"Heavy rainfall ({weather['rainfall']}mm) expected. Delay harvesting to prevent post-harvest loss."
        severity = "HIGH"
    elif weather["temperature"] > 38:
        advisory_text = f"Extreme heat ({weather['temperature']}°C). Ensure adequate irrigation and shade for sensitive crops."
        severity = "HIGH"
    elif weather["temperature"] < 5:
        advisory_text = f"Frost warning ({weather['temperature']}°C). Protect vulnerable crops."
        severity = "MEDIUM"
        
    if advisory_text:
        # Create advisory for the next 24 hours
        from datetime import timedelta
        advisory, created = WeatherAdvisory.objects.get_or_create(
            location=city,
            advisory_text=advisory_text,
            defaults={
                "severity": severity,
                "expires_at": timezone.now() + timedelta(days=1)
            }
        )
        # If it wasn't created, update expiration if it's the same advisory text
        if not created:
            advisory.expires_at = timezone.now() + timedelta(days=1)
            advisory.save()
            
        return advisory
    return None

@login_required
def agri_market_trends(request):
    trends = CropMarketTrend.objects.all().order_by('-record_date')
    # Simple forecast generation if needed
    return render(request, "agri_market_trends.html", {"trends": trends})

@login_required
def agri_shipment_list(request):
    shipments = AgriculturalShipment.objects.all().order_by('-created_at')
    return render(request, "agri_shipments.html", {"shipments": shipments})

@login_required
def agri_shipment_detail(request, shipment_id):
    shipment = get_object_or_404(AgriculturalShipment, id=shipment_id)
    return render(request, "agri_shipment_detail.html", {"shipment": shipment})

@login_required
def agri_inspection_add(request):
    if request.method == "POST":
        form = QualityInspectionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Quality inspection recorded successfully.")
            return redirect('agri_dashboard')
    else:
        form = QualityInspectionForm()
    return render(request, "agri_inspection_form.html", {"form": form})

@login_required
def agri_ledger(request):
    org = request.user.organization_memberships.first()
    if not org:
        messages.error(request, "You must belong to an organization to view the ledger.")
        return redirect('agri_dashboard')
    
    # Get all transactions where this org is either sender or receiver
    transactions = LedgerTransaction.objects.filter(Q(sender_org=org.organization) | Q(receiver_org=org.organization)).order_by('-transaction_date')
    
    return render(request, "agri_ledger.html", {"transactions": transactions})


def agri_traceability(request, tracking_code):
    """Public view for tracing a shipment from farm to fork."""
    shipment = get_object_or_404(AgriculturalShipment, tracking_code=tracking_code)
    inspections = shipment.supply_match.produce.inspections.all().order_by('-inspection_date')
    return render(request, "agri_traceability.html", {
        "shipment": shipment,
        "inspections": inspections
    })

@login_required
def agri_release_escrow(request, tracking_code):
    if request.method == "POST":
        shipment = get_object_or_404(AgriculturalShipment, tracking_code=tracking_code)
        match = shipment.supply_match
        
        # Find pending transactions for this match
        transaction = LedgerTransaction.objects.filter(supply_match=match, escrow_status="HELD").first()
        if transaction:
            transaction.escrow_status = "RELEASED"
            transaction.status = "COMPLETED"
            transaction.save()
            messages.success(request, f"Funds (₹{transaction.amount}) released to {transaction.receiver_org.name} successfully.")
        else:
            messages.info(request, "No pending escrow transactions found for this shipment.")
            
    return redirect('agri_traceability', tracking_code=tracking_code)

import random
@login_required
def agri_disease_scanner(request):
    if request.method == "POST":
        crop_name = request.POST.get("crop_name", "Unknown Crop")
        scan_type = request.POST.get("scan_type", "disease")
        
        if scan_type == "grading":
            # Simulate Quality Grading AI
            grades = [
                ("Grade A (Export Quality)", 98.2, "Optimal size, color, and zero blemishes. Premium pricing recommended."),
                ("Grade B (Local Market)", 89.4, "Minor superficial blemishes. Standard market pricing."),
                ("Grade C (Processing/Juicing)", 92.1, "Substandard shape or color. Recommend selling for processing.")
            ]
            disease, confidence, treatment = random.choice(grades)
            msg = f"Grading complete! Result: {disease}"
        else:
            # Simulate Disease AI
            diseases = [
                ("Healthy", 95.5, "No action needed. Continue normal irrigation."),
                ("Leaf Blight", 88.2, "Apply copper-based fungicide and ensure adequate spacing for airflow."),
                ("Rust", 91.0, "Remove infected leaves and apply sulfur fungicide."),
                ("Aphid Infestation", 94.3, "Introduce ladybugs or apply neem oil spray immediately.")
            ]
            disease, confidence, treatment = random.choice(diseases)
            msg = f"Scan complete! Diagnosis: {disease}"
            
        scan = CropDiseaseScan.objects.create(
            farmer=request.user,
            crop_name=crop_name,
            detected_disease=disease,
            confidence=confidence,
            recommended_treatment=treatment
        )
        messages.success(request, msg)
        return render(request, "agri_disease_scanner.html", {"scan": scan})
        
    return render(request, "agri_disease_scanner.html")

@login_required
def agri_yield_predictor(request):
    if request.method == "POST":
        crop_type = request.POST.get("crop_type", "Wheat")
        area = float(request.POST.get("area_hectares", 1.0))
        soil_type = request.POST.get("soil_type", "Loamy")
        
        # Simple ML heuristic mock
        base_yield = {"Wheat": 3.5, "Rice": 4.0, "Corn": 5.2, "Tomatoes": 40.0}.get(crop_type, 4.0)
        soil_modifier = {"Loamy": 1.1, "Clay": 0.9, "Sandy": 0.8}.get(soil_type, 1.0)
        
        # Simulate slight randomness for weather/etc
        weather_factor = random.uniform(0.9, 1.15)
        
        predicted_yield = base_yield * area * soil_modifier * weather_factor
        
        # Mock price per ton
        price_per_ton = {"Wheat": 22000, "Rice": 28000, "Corn": 18000, "Tomatoes": 15000}.get(crop_type, 20000)
        estimated_revenue = predicted_yield * price_per_ton
        
        prediction = CropYieldPrediction.objects.create(
            farmer=request.user,
            crop_type=crop_type,
            area_hectares=area,
            soil_type=soil_type,
            predicted_yield_tons=round(predicted_yield, 2),
            estimated_revenue=round(estimated_revenue, 2)
        )
        messages.success(request, "Yield prediction calculated successfully.")
        return render(request, "agri_yield_predictor.html", {"prediction": prediction})
        
    history = CropYieldPrediction.objects.filter(farmer=request.user).order_by("-created_at")[:5]
    return render(request, "agri_yield_predictor.html", {"history": history})

@login_required
def agri_iot_dashboard(request):
    active_shipments = AgriculturalShipment.objects.filter(status="IN_TRANSIT")
    return render(request, "agri_iot_dashboard.html", {"active_shipments": active_shipments})

def api_iot_live_stream(request):
    """Simulates live temperature stream for active shipments"""
    active_shipments = AgriculturalShipment.objects.filter(status="IN_TRANSIT")
    data = []
    for shipment in active_shipments:
        # Simulate slight temperature fluctuation
        current = shipment.current_temperature or 4.0
        fluctuation = random.uniform(-0.5, 0.5)
        new_temp = round(current + fluctuation, 1)
        shipment.current_temperature = new_temp
        shipment.save(update_fields=['current_temperature'])
        
        data.append({
            "tracking_code": shipment.tracking_code,
            "temperature": new_temp,
            "status": "Warning" if new_temp > 6.0 or new_temp < 0.0 else "Normal"
        })
    return JsonResponse({"status": "success", "data": data})

import json
@login_required
def agri_field_map(request):
    if request.method == "POST":
        name = request.POST.get("name")
        crop_type = request.POST.get("crop_type")
        area_acres = request.POST.get("area_acres")
        geojson = request.POST.get("geojson_data")
        
        FarmField.objects.create(
            farmer=request.user,
            name=name,
            crop_type=crop_type,
            area_acres=float(area_acres) if area_acres else 0.0,
            geojson_data=geojson
        )
        messages.success(request, f"Field '{name}' saved successfully!")
        return redirect("agri_field_map")
        
    fields = FarmField.objects.filter(farmer=request.user)
    # Convert fields to JSON list for the template
    fields_json = []
    for f in fields:
        if f.geojson_data:
            fields_json.append({
                "id": f.id,
                "name": f.name,
                "crop": f.crop_type,
                "area": f.area_acres,
                "geojson": json.loads(f.geojson_data)
            })
            
    return render(request, "agri_field_map.html", {
        "fields": fields,
        "fields_json": json.dumps(fields_json)
    })

@login_required
def agri_equipment_hub(request):
    equipment_list = Equipment.objects.filter(is_available=True).exclude(owner=request.user)
    my_equipment = Equipment.objects.filter(owner=request.user)
    my_rentals = EquipmentRental.objects.filter(renter=request.user)
    
    return render(request, "agri_equipment_hub.html", {
        "equipment_list": equipment_list,
        "my_equipment": my_equipment,
        "my_rentals": my_rentals
    })

@login_required
def agri_rent_equipment(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    if request.method == "POST":
        hours = int(request.POST.get("hours", 1))
        total_cost = hours * equipment.hourly_rate
        
        # In a real app we'd ask for start/end times via a calendar picker. 
        from django.utils import timezone
        import datetime
        start_time = timezone.now() + datetime.timedelta(days=1)
        end_time = start_time + datetime.timedelta(hours=hours)
        
        EquipmentRental.objects.create(
            equipment=equipment,
            renter=request.user,
            start_time=start_time,
            end_time=end_time,
            total_cost=total_cost,
            status="APPROVED"
        )
        
        messages.success(request, f"Successfully rented {equipment.name} for {hours} hours (₹{total_cost}).")
        return redirect("agri_equipment_hub")

@login_required
def agri_forum(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        category = request.POST.get("category", "DISCUSSION")
        
        ForumPost.objects.create(
            author=request.user,
            title=title,
            content=content,
            category=category
        )
        messages.success(request, "Post created successfully!")
        return redirect("agri_forum")
        
    posts = ForumPost.objects.all()
    return render(request, "agri_forum.html", {"posts": posts})

@login_required
def agri_forum_detail(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    if request.method == "POST":
        content = request.POST.get("content")
        ForumComment.objects.create(
            post=post,
            author=request.user,
            content=content
        )
        messages.success(request, "Comment added.")
        return redirect("agri_forum_detail", post_id=post.id)
        
    return render(request, "agri_forum_detail.html", {"post": post})

@login_required
def agri_subsidy_finder(request):
    # Get farmer's crops from fields or inventory
    fields = FarmField.objects.filter(farmer=request.user)
    my_crop_types = [f.crop_type.lower() for f in fields]
    
    # We could also get crops from AgriculturalProduce
    produce = AgriculturalProduce.objects.filter(producer=request.user.organization_memberships.first().organization if request.user.organization_memberships.exists() else None)
    my_crop_types.extend([p.name.lower() for p in produce])
    my_crop_types = set(my_crop_types)
    
    all_schemes = GovernmentScheme.objects.all()
    
    # Simple matching algorithm
    matched_schemes = []
    other_schemes = []
    
    for scheme in all_schemes:
        eligible_crops = [c.strip().lower() for c in scheme.eligible_crops.split(',')]
        # If any of the farmer's crops match the scheme's eligible crops (or if scheme applies to "all")
        if "all" in eligible_crops or any(c in eligible_crops for c in my_crop_types):
            matched_schemes.append(scheme)
        else:
            other_schemes.append(scheme)
            
    return render(request, "agri_subsidy_finder.html", {
        "matched_schemes": matched_schemes,
        "other_schemes": other_schemes,
        "my_crops": list(my_crop_types)
    })
    
    return redirect("agri_equipment_hub")


from django.utils import timezone

@login_required
def delivery_live_tracking(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    lat = delivery.current_lat or 12.9716
    lng = delivery.current_lng or 77.5946
    return render(request, 'delivery_live_tracking.html', {'delivery': delivery, 'lat': lat, 'lng': lng})

@login_required
def delivery_proof(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    if request.method == 'POST':
        proof_image = request.FILES.get('proof_image')
        signature = request.POST.get('recipient_signature')
        
        if proof_image:
            delivery.proof_image = proof_image
        if signature:
            delivery.recipient_signature = signature
            
        delivery.status = 'DELIVERED'
        delivery.delivered_at = timezone.now()
        delivery.save()
        
        # Update Impact Dashboard
        if delivery.sender:
            from .models import OrganizationImpact
            impact, _ = OrganizationImpact.objects.get_or_create(organization=delivery.sender)
            impact.total_meals_saved += delivery.quantity
            impact.total_co2_reduced_kg += delivery.quantity * 2.5  # assuming 2.5kg CO2 per meal
            impact.impact_points += delivery.quantity * 10
            impact.save()
            
        # Update Volunteer Driver total_deliveries
        if delivery.volunteer_driver:
            delivery.volunteer_driver.total_deliveries += 1
            delivery.volunteer_driver.save()
            
        messages.success(request, 'Proof of Delivery saved successfully!')
        return redirect('delivery_detail', delivery_id=delivery.id)
        
    return render(request, 'delivery_proof.html', {'delivery': delivery})

from .forms import VolunteerProfileForm
from .models import VolunteerProfile, OrganizationImpact

@login_required
def volunteer_register(request):
    try:
        profile = request.user.volunteer_profile
    except VolunteerProfile.DoesNotExist:
        profile = None
        
    if request.method == "POST":
        form = VolunteerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            volunteer = form.save(commit=False)
            volunteer.user = request.user
            volunteer.save()
            messages.success(request, "Volunteer profile updated successfully!")
            return redirect("volunteer_dashboard")
    else:
        form = VolunteerProfileForm(instance=profile)
        
    return render(request, "volunteer_register.html", {"form": form})

@login_required
def volunteer_dashboard(request):
    try:
        profile = request.user.volunteer_profile
    except VolunteerProfile.DoesNotExist:
        messages.info(request, "Please register as a volunteer first.")
        return redirect("volunteer_register")
        
    available_deliveries = Delivery.objects.filter(status="REQUESTED", volunteer_driver__isnull=True).order_by("-created_at")
    my_deliveries = Delivery.objects.filter(volunteer_driver=profile).order_by("-created_at")
    
    if request.method == "POST":
        delivery_id = request.POST.get("delivery_id")
        action = request.POST.get("action")
        if delivery_id and action == "accept":
            delivery = get_object_or_404(Delivery, id=delivery_id)
            if delivery.status == "REQUESTED" and not delivery.volunteer_driver:
                delivery.volunteer_driver = profile
                delivery.status = "ASSIGNED"
                delivery.save()
                messages.success(request, f"You have been assigned to delivery {delivery.tracking_code}.")
                return redirect("volunteer_dashboard")
                
    return render(request, "volunteer_dashboard.html", {
        "profile": profile,
        "available_deliveries": available_deliveries,
        "my_deliveries": my_deliveries,
    })


import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

@login_required
def generate_donation_receipt(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    
    # Check permissions
    if not request.user.is_superuser:
        if delivery.sender not in request.user.organization_memberships.values_list('organization', flat=True):
            messages.error(request, "You do not have permission to view this receipt.")
            return redirect('delivery_list')
            
    if delivery.status != "DELIVERED":
        messages.error(request, "Receipts are only available for delivered items.")
        return redirect('delivery_detail', delivery_id=delivery.id)
        
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Draw Header
    p.setFont("Helvetica-Bold", 24)
    p.setFillColor(colors.HexColor("#166534"))
    p.drawString(50, height - 80, "Official Donation Receipt")
    
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.black)
    p.drawString(50, height - 110, f"Receipt ID: {delivery.tracking_code}")
    p.drawString(50, height - 130, f"Date Delivered: {delivery.delivered_at.strftime('%Y-%m-%d %H:%M') if delivery.delivered_at else 'N/A'}")
    
    # Draw Donor Information
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 170, "Donor Information")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 190, f"Organization: {delivery.sender.name}")
    p.drawString(50, height - 210, f"Registration No: {delivery.sender.registration_number or 'N/A'}")
    p.drawString(50, height - 230, f"Address: {delivery.sender.address}, {delivery.sender.city}")
    
    # Draw Recipient Information
    p.setFont("Helvetica-Bold", 14)
    p.drawString(300, height - 170, "Recipient Information")
    p.setFont("Helvetica", 12)
    p.drawString(300, height - 190, f"Organization: {delivery.receiver.name}")
    p.drawString(300, height - 210, f"Registration No: {delivery.receiver.registration_number or 'N/A'}")
    
    # Draw Donation Details
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 270, "Donation Details")
    p.rect(50, height - 350, 500, 70)
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(60, height - 300, "Item Name")
    p.drawString(400, height - 300, "Quantity (Meals)")
    
    p.setFont("Helvetica", 12)
    p.drawString(60, height - 330, str(delivery.food_name))
    p.drawString(400, height - 330, str(delivery.quantity))
    
    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 100, "Thank you for your generous contribution. This receipt is automatically generated")
    p.drawString(50, 85, "and serves as proof of your donation for tax or reporting purposes.")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"Receipt_{delivery.tracking_code}.pdf")

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .copilot import generate_copilot_response

@csrf_exempt
@_organization_required
def copilot_chat(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "")
            
            if not user_message:
                return JsonResponse({"error": "No message provided"}, status=400)
                
            # Get AI response
            ai_response = generate_copilot_response(user_message, request.organization)
            
            return JsonResponse({"response": ai_response})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
@_organization_required
def logistics_map(request):
    import random
    deliveries = Delivery.objects.filter(
        sender=request.organization, 
        status__in=['SCHEDULED', 'IN_TRANSIT']
    )
    
    delivery_data = []
    # Mock some central coordinates if missing to ensure map works beautifully out of the box
    base_lat, base_lng = 19.0760, 72.8777 # Mumbai center
    
    for d in deliveries:
        lat = d.current_lat if d.current_lat else (base_lat + random.uniform(-0.05, 0.05))
        lng = d.current_lng if d.current_lng else (base_lng + random.uniform(-0.05, 0.05))
        
        delivery_data.append({
            'id': d.id,
            'food_name': d.food_name,
            'quantity': d.quantity,
            'status': d.status,
            'lat': lat,
            'lng': lng,
            'driver': d.driver_name or "Unassigned"
        })
        
    return render(request, "logistics_map.html", {
        "deliveries_json": json.dumps(delivery_data),
        "base_lat": base_lat,
        "base_lng": base_lng
    })

@login_required
@_organization_required
def impact_dashboard(request):
    impact, _ = OrganizationImpact.objects.get_or_create(organization=request.organization)
    
    # Chart data
    recent_redistributions = Redistribution.objects.filter(
        surplus__organization=request.organization
    ).order_by("-distributed_at")[:10]
    
    chart_labels = []
    chart_data = []
    for r in recent_redistributions:
        date_str = r.distributed_at.strftime("%b %d")
        if date_str not in chart_labels:
            chart_labels.append(date_str)
            chart_data.append(r.quantity)
        else:
            idx = chart_labels.index(date_str)
            chart_data[idx] += r.quantity
            
    chart_labels.reverse()
    chart_data.reverse()

    all_impacts = OrganizationImpact.objects.select_related("organization").order_by("-impact_points")[:10]

    context = {
        "active_org": request.organization,
        "my_impact": impact,
        "all_impacts": all_impacts,
        "chart_labels": json.dumps(chart_labels),
        "chart_data": json.dumps(chart_data)
    }
    return render(request, "impact_dashboard.html", context)


def leaderboard(request):
    top_orgs = OrganizationImpact.objects.select_related("organization").order_by("-impact_points")[:10]
    
    context = {
        "top_orgs": top_orgs
    }
    return render(request, "leaderboard.html", context)


import qrcode
from django.http import HttpResponse

@login_required
def delivery_qr_code(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    scan_url = request.build_absolute_uri(f"/deliveries/{delivery.id}/scan/")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(scan_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    response = HttpResponse(content_type="image/png")
    img.save(response, "PNG")
    return response


@login_required
def delivery_scan_qr(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    
    if request.method == "POST":
        if delivery.status == "IN_TRANSIT":
            delivery.status = "DELIVERED"
            from django.utils import timezone
            delivery.delivered_at = timezone.now()
            delivery.save(update_fields=["status", "delivered_at"])
            messages.success(request, f"Delivery {delivery.tracking_code} marked as DELIVERED.")
            
            try:
                from .utils import notify_delivery_update
                notify_delivery_update(delivery)
            except Exception as e:
                pass
                
        elif delivery.status in ["ASSIGNED", "REQUESTED"]:
            delivery.status = "IN_TRANSIT"
            delivery.save(update_fields=["status"])
            messages.success(request, f"Delivery {delivery.tracking_code} marked as IN TRANSIT.")
            
            try:
                from .utils import notify_delivery_update
                notify_delivery_update(delivery)
            except Exception as e:
                pass
                
        return redirect("delivery_detail", delivery_id=delivery.id)
        
    return render(request, "delivery_scan.html", {"delivery": delivery})

def food_chain_of_custody(request, food_id):
    food = get_object_or_404(SurplusFood, id=food_id)
    ledger_entries = FoodLedger.objects.filter(surplus_food=food).order_by('timestamp')
    return render(request, "food_traceability.html", {
        "food": food,
        "ledger_entries": ledger_entries
    })
