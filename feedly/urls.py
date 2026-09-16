from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # Static pages (Phase 21)
    path("ai/trust/", TemplateView.as_view(template_name="trust.html"), name="ai_trust"),
    path("resources/", TemplateView.as_view(template_name="resources.html"), name="resources"),

    path("", views.index, name="index"),
    path("product/", views.product, name="product"),
    path("solutions/", views.solutions, name="solutions"),
    path("ai/", views.ai, name="ai"),
    path("features/", views.features, name="features"),
    path("pricing/", views.pricing, name="pricing"),
    path("about/", views.about, name="about"),
    path("security/", views.security, name="security"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("contact/", views.contact, name="contact"),

    path("health/", views.health_check, name="health"),
    path("login/", views.login_view, name="login"),
    path("login/buyer/", views.login_view, kwargs={"persona": "buyer"}, name="login_buyer"),
    path("login/supplier/", views.login_view, kwargs={"persona": "supplier"}, name="login_supplier"),
    path("login/organization/", views.login_view, kwargs={"persona": "organization"}, name="login_organization"),
    path("login/farmer/", views.login_view, kwargs={"persona": "farmer"}, name="login_farmer"),
    path("login/user/", views.login_view, kwargs={"persona": "user"}, name="login_user"),
    path("logout/", views.logout_view, name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("predict/", views.predict_demand, name="predict_demand"),
    path("forecast/", views.forecast_7_days, name="forecast_7_days"),
    path("weather/", views.weather_data, name="weather_data"),
    path("intelligence/", views.intelligence_center, name="intelligence_center"),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
    path("story/", views.data_story, name="data_story"),
    path("logging/", views.post_meal_logging, name="post_meal_logging"),
    
    # Agriculture Extension Routes
    path("agriculture/", views.agri_dashboard, name="agri_dashboard"),
    path("agriculture/produce/", views.agri_produce_list, name="agri_produce_list"),
    path("agriculture/produce/add/", views.agri_produce_add, name="agri_produce_add"),
    path("agriculture/processing/", views.agri_processing_list, name="agri_processing_list"),
    path("agriculture/processing/add/", views.agri_processing_add, name="agri_processing_add"),
    path("agriculture/supply-matching/", views.agri_supply_matching, name="agri_supply_matching"),
    path("agriculture/requests/", views.agri_supply_requests_list, name="agri_supply_requests_list"),
    path("agriculture/requests/<int:request_id>/accept/", views.agri_supply_request_accept, name="agri_supply_request_accept"),
    path("agriculture/requests/add/", views.agri_supply_request_add, name="agri_supply_request_add"),
    path("agriculture/market-trends/", views.agri_market_trends, name="agri_market_trends"),
    path("agriculture/shipments/", views.agri_shipment_list, name="agri_shipment_list"),
    path("agriculture/shipments/<int:shipment_id>/", views.agri_shipment_detail, name="agri_shipment_detail"),
    path("agriculture/inspection/add/", views.agri_inspection_add, name="agri_inspection_add"),
    path("agriculture/scanner/", views.agri_disease_scanner, name="agri_disease_scanner"),
    path("agriculture/yield/", views.agri_yield_predictor, name="agri_yield_predictor"),
    path("agriculture/iot/", views.agri_iot_dashboard, name="agri_iot_dashboard"),
    path("agriculture/map/", views.agri_field_map, name="agri_field_map"),
    path("agriculture/equipment/", views.agri_equipment_hub, name="agri_equipment_hub"),
    path("agriculture/equipment/add/", views.agri_equipment_add, name="agri_equipment_add"),
    path("agriculture/equipment/<int:equipment_id>/rent/", views.agri_rent_equipment, name="agri_rent_equipment"),
    path("agriculture/advisor/", views.agri_ai_advisor, name="agri_ai_advisor"),
    path("agriculture/warehousing/", views.agri_warehousing, name="agri_warehousing"),
    path("agriculture/subsidies/", views.agri_subsidy_finder, name="agri_subsidy_finder"),
    path("api/iot/live/", views.api_iot_live_stream, name="api_iot_live_stream"),
    path("trace/<str:tracking_code>/", views.agri_traceability, name="agri_traceability"),
    path("trace/<str:tracking_code>/release/", views.agri_release_escrow, name="agri_release_escrow"),
    path("integrations/health/", views.integration_health, name="integration_health"),
    path("api/erp/attendance/", views.api_erp_attendance, name="api_erp_attendance"),
    path("api/iot/temperature/", views.api_iot_temperature, name="api_iot_temperature"),

    path("food-safety/", views.check_food_safety, name="food_safety"),
    path("surplus/", views.surplus_list, name="surplus_list"),
    path("surplus/add/", views.add_surplus_food, name="add_surplus"),
    path("surplus/<int:food_id>/redistribute/", views.redistribute_food, name="redistribute_food"),
    path("surplus/<int:food_id>/delete/", views.delete_surplus, name="delete_surplus"),
    path("surplus/<int:food_id>/trace/", views.food_chain_of_custody, name="food_traceability"),
    path("surplus/<int:food_id>/recommendations/", views.recipient_recommendations, name="recipient_recommendations"),

    path("recipients/", views.recipient_list, name="recipient_list"),
    path("recipients/add/", views.add_recipient, name="add_recipient"),
    path("recipients/<int:recipient_id>/verify/", views.verify_recipient, name="verify_recipient"),

    path("organizations/register/", views.register_organization, name="organization_register"),
    path("organizations/<int:organization_id>/details/", views.organization_details_json, name="organization_details_json"),
    path("organization/switch/<int:organization_id>/", views.organization_switch, name="organization_switch"),
    path("organization/", views.organization_dashboard, name="organization_dashboard"),
    path("organization/onboarding/", views.organization_onboarding, name="organization_onboarding"),
    path("organization/map/", views.logistics_map, name="logistics_map"),
    path("organization/edit/", views.organization_edit, name="organization_edit"),
    
    # Phase 22: Enterprise Administration Console
    path("organization/admin/", views.organization_admin_dashboard, name="organization_admin_dashboard"),
    path("organization/admin/members/", views.organization_admin_members, name="organization_admin_members"),
    path("organization/admin/audit/", views.organization_admin_audit, name="organization_admin_audit"),
    path("organization/admin/settings/", views.organization_admin_settings, name="organization_admin_settings"),
    
    path("organization/members/add/", views.organization_add_member, name="organization_add_member"),
    path("organization/members/<int:member_id>/remove/", views.organization_remove_member, name="organization_remove_member"),

    path("deliveries/", views.delivery_list, name="delivery_list"),
    path("deliveries/new/", views.delivery_create, name="delivery_create"),
    path("deliveries/<int:delivery_id>/", views.delivery_detail, name="delivery_detail"),
    path("deliveries/<int:delivery_id>/qr/", views.delivery_qr_code, name="delivery_qr_code"),
    path("deliveries/<int:delivery_id>/scan/", views.delivery_scan_qr, name="delivery_scan_qr"),
    path("deliveries/<int:delivery_id>/status/", views.delivery_update_status, name="delivery_update_status"),
    path("deliveries/<int:delivery_id>/track/", views.delivery_live_tracking, name="delivery_live_tracking"),
    path("deliveries/<int:delivery_id>/proof/", views.delivery_proof, name="delivery_proof"),
    
    path("volunteer/register/", views.volunteer_register, name="volunteer_register"),
    path("volunteer/dashboard/", views.volunteer_dashboard, name="volunteer_dashboard"),
    path("organization/impact/", views.impact_dashboard, name="impact_dashboard"),
    path("organization/leaderboard/", views.leaderboard, name="leaderboard"),
    path("deliveries/<int:delivery_id>/receipt/", views.generate_donation_receipt, name="generate_donation_receipt"),
    path("api/copilot/", views.copilot_chat, name="copilot_chat"),
    path("api/weather/", views.api_weather, name="api_weather"),
    path("api/search/", views.api_global_search, name="api_global_search"),
    path("data-quality/", views.data_quality_center, name="data_quality_center"),
    
    # AI Endpoints (Phase 18)
    path("api/ai/scenario/", views.api_ai_scenario, name="api_ai_scenario"),
    path("api/ai/action_preview/", views.api_ai_action_preview, name="api_ai_action_preview"),


    # Digital Twin (Phase 19)
    path("twin/", views.digital_twin, name="digital_twin"),
    path("passport/<str:batch_id>/", views.produce_passport, name="produce_passport"),
    path("import/", views.data_import, name="data_import"),
    
    # Community & Gamification
    # path("community/", views.community_hub, name="community_hub"),

    # PHASE 3 ROUTES
    # PHASE 3 ROUTES
    path("agriculture/skyview/", views.agri_skyview, name="agri_skyview"),
    path("agriculture/soil/", views.agri_soil, name="agri_soil"),
    path("agriculture/comms/", views.agri_comms, name="agri_comms"),

    # PHASE 4 ROUTES (ORGANIZATION)
    path("organization/routing/", views.org_fleet_routing, name="org_fleet_routing"),


    # PHASE 5 ROUTES (CONSUMER & COMMUNITY)
    path("user/recipe/", views.user_ai_recipe, name="user_ai_recipe"),
    # PHASE 6 ROUTES (GLOBAL & FUTURE-TECH)

    # Phase 11: Ecosystem Coordination
    path('org/ecosystem/', views.ecosystem_coordination, name='ecosystem_coordination'),
    path('org/ecosystem/create/', views.create_alliance, name='create_alliance'),
    path('org/ecosystem/join/', views.join_alliance, name='join_alliance'),
]
