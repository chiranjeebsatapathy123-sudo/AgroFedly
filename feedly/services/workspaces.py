from django.utils.translation import gettext_lazy as _

WORKSPACE_CONFIGS = {
    'AGRICULTURE': {
        'id': 'AGRICULTURE',
        'name': _('Agriculture'),
        'icon': 'fas fa-seedling',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_agri_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Farms'), 'url_name': 'agri_farm_list', 'icon': 'fas fa-tractor'},
            {'label': _('Fields'), 'url_name': 'agri_field_list', 'icon': 'fas fa-map'},
            {'label': _('Crops'), 'url_name': 'agri_produce_list', 'icon': 'fas fa-leaf'},
            {'label': _('Production'), 'url_name': 'agri_production', 'icon': 'fas fa-box-open'},
            {'label': _('Weather'), 'url_name': 'agri_weather_page', 'icon': 'fas fa-cloud-sun'},
            {'label': _('Crop Health'), 'url_name': 'agri_disease_scanner', 'icon': 'fas fa-heartbeat'},
            {'label': _('Yield AI'), 'url_name': 'agri_yield_predictor', 'icon': 'fas fa-brain'},
            {'label': _('IoT'), 'url_name': 'agri_iot_dashboard', 'icon': 'fas fa-microchip'},
            {'label': _('Market'), 'url_name': 'agri_market_trends', 'icon': 'fas fa-chart-bar'},
            {'label': _('Equipment'), 'url_name': 'agri_equipment_hub', 'icon': 'fas fa-tools'},
            {'label': _('Analytics'), 'url_name': 'agri_analytics', 'icon': 'fas fa-chart-line'},
        ],
        'color': '#10b981'
    },
    'KITCHEN': {
        'id': 'KITCHEN',
        'name': _('Kitchen'),
        'icon': 'fas fa-utensils',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_kitchen_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Demand Forecast'), 'url_name': 'kitchen_demand_forecast', 'icon': 'fas fa-chart-line'},
            {'label': _('Meal Planning'), 'url_name': 'kitchen_meal_planning', 'icon': 'fas fa-calendar-alt'},
            {'label': _('Production'), 'url_name': 'kitchen_production', 'icon': 'fas fa-fire'},
            {'label': _('Inventory'), 'url_name': 'kitchen_inventory', 'icon': 'fas fa-boxes'},
            {'label': _('Food Safety'), 'url_name': 'kitchen_food_safety', 'icon': 'fas fa-shield-alt'},
            {'label': _('Surplus'), 'url_name': 'surplus_list', 'icon': 'fas fa-gift'},
            {'label': _('Redistribution'), 'url_name': 'kitchen_redistribution', 'icon': 'fas fa-hands-helping'},
            {'label': _('Analytics'), 'url_name': 'kitchen_analytics', 'icon': 'fas fa-chart-bar'},
        ],
        'color': '#f59e0b'
    },
    'REDISTRIBUTION': {
        'id': 'REDISTRIBUTION',
        'name': _('Redistribution'),
        'icon': 'fas fa-hands-helping',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_redistribution_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Available Surplus'), 'url_name': 'redistribution_surplus', 'icon': 'fas fa-box-open'},
            {'label': _('Recipient Requests'), 'url_name': 'recipient_request_center', 'icon': 'fas fa-clipboard-list'},
            {'label': _('AI Matching'), 'url_name': 'redistribution_matching', 'icon': 'fas fa-robot'},
            {'label': _('Verification'), 'url_name': 'redistribution_verification', 'icon': 'fas fa-check-circle'},
            {'label': _('Transfers'), 'url_name': 'redistribution_transfers', 'icon': 'fas fa-exchange-alt'},
            {'label': _('Delivery'), 'url_name': 'redistribution_delivery', 'icon': 'fas fa-truck'},
            {'label': _('Impact Analytics'), 'url_name': 'impact_dashboard', 'icon': 'fas fa-chart-line'},
        ],
        'color': '#8b5cf6'
    },
    'LOGISTICS': {
        'id': 'LOGISTICS',
        'name': _('Logistics'),
        'icon': 'fas fa-truck',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_logistics_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Deliveries'), 'url_name': 'delivery_list', 'icon': 'fas fa-box'},
            {'label': _('Dispatch'), 'url_name': 'logistics_dispatch', 'icon': 'fas fa-clipboard-check'},
            {'label': _('Drivers'), 'url_name': 'logistics_drivers', 'icon': 'fas fa-id-card'},
            {'label': _('Vehicles'), 'url_name': 'logistics_vehicles', 'icon': 'fas fa-car-side'},
            {'label': _('Routes'), 'url_name': 'logistics_routes', 'icon': 'fas fa-route'},
            {'label': _('Tracking'), 'url_name': 'delivery_control', 'icon': 'fas fa-map-marker-alt'},
            {'label': _('Analytics'), 'url_name': 'logistics_analytics', 'icon': 'fas fa-chart-line'},
        ],
        'color': '#3b82f6'
    },
    'ADMIN': {
        'id': 'ADMIN',
        'name': _('Administration'),
        'icon': 'fas fa-cogs',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_admin_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Users'), 'url_name': 'organization_admin_members', 'icon': 'fas fa-user'},
            {'label': _('Organizations'), 'url_name': 'admin_organizations', 'icon': 'fas fa-building'},
            {'label': _('Roles & Permissions'), 'url_name': 'admin_roles', 'icon': 'fas fa-key'},
            {'label': _('Workspace Access'), 'url_name': 'admin_workspace_access', 'icon': 'fas fa-door-open'},
            {'label': _('Audit Logs'), 'url_name': 'organization_admin_audit', 'icon': 'fas fa-history'},
            {'label': _('Security'), 'url_name': 'security_center', 'icon': 'fas fa-shield-alt'},
            {'label': _('Data Quality'), 'url_name': 'data_quality_center', 'icon': 'fas fa-database'},
            {'label': _('System Health'), 'url_name': 'system_health', 'icon': 'fas fa-heartbeat'},
            {'label': _('Settings'), 'url_name': 'organization_admin_settings', 'icon': 'fas fa-cog'},
        ],
        'color': '#ef4444'
    }
}
