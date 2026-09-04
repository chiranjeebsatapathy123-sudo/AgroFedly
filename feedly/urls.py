from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("predict/", views.predict_demand, name="predict_demand"),
    path("forecast/", views.forecast_7_days, name="forecast_7_days"),
    path("weather/", views.weather_data, name="weather_data"),
    path("intelligence/", views.intelligence_center, name="intelligence_center"),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
    path("logging/", views.post_meal_logging, name="post_meal_logging"),
    
    # Agriculture Extension Routes
    path("agriculture/", views.agri_dashboard, name="agri_dashboard"),
    path("agriculture/produce/", views.agri_produce_list, name="agri_produce_list"),
    path("agriculture/produce/add/", views.agri_produce_add, name="agri_produce_add"),
    path("agriculture/processing/", views.agri_processing_list, name="agri_processing_list"),
    path("agriculture/processing/add/", views.agri_processing_add, name="agri_processing_add"),
    path("agriculture/supply-matching/", views.agri_supply_matching, name="agri_supply_matching"),

    path("integrations/health/", views.integration_health, name="integration_health"),
    path("api/erp/attendance/", views.api_erp_attendance, name="api_erp_attendance"),
    path("api/iot/temperature/", views.api_iot_temperature, name="api_iot_temperature"),

    path("food-safety/", views.check_food_safety, name="food_safety"),
    path("surplus/", views.surplus_list, name="surplus_list"),
    path("surplus/add/", views.add_surplus_food, name="add_surplus"),
    path("surplus/<int:food_id>/redistribute/", views.redistribute_food, name="redistribute_food"),
    path("surplus/<int:food_id>/recommendations/", views.recipient_recommendations, name="recipient_recommendations"),

    path("recipients/", views.recipient_list, name="recipient_list"),
    path("recipients/add/", views.add_recipient, name="add_recipient"),
    path("recipients/<int:recipient_id>/verify/", views.verify_recipient, name="verify_recipient"),

    path("organizations/register/", views.register_organization, name="organization_register"),
    path("organizations/<int:organization_id>/details/", views.organization_details_json, name="organization_details_json"),
    path("organization/switch/<int:organization_id>/", views.organization_switch, name="organization_switch"),
    path("organization/", views.organization_dashboard, name="organization_dashboard"),
    path("organization/edit/", views.organization_edit, name="organization_edit"),
    path("organization/members/add/", views.organization_add_member, name="organization_add_member"),
    path("organization/members/<int:member_id>/remove/", views.organization_remove_member, name="organization_remove_member"),

    path("deliveries/", views.delivery_list, name="delivery_list"),
    path("deliveries/new/", views.delivery_create, name="delivery_create"),
    path("deliveries/<int:delivery_id>/", views.delivery_detail, name="delivery_detail"),
    path("deliveries/<int:delivery_id>/status/", views.delivery_update_status, name="delivery_update_status"),
]
