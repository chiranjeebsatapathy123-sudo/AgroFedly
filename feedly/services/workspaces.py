from django.utils.translation import gettext_lazy as _

WORKSPACE_CONFIGS = {
    'AGRICULTURE': {
        'id': 'AGRICULTURE',
        'name': _('Agriculture'),
        'icon': 'fas fa-seedling',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_agri_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Farms & Fields'), 'url_name': 'agri_farm_list', 'icon': 'fas fa-tractor'},
            {'label': _('Produce'), 'url_name': 'agri_produce_list', 'icon': 'fas fa-leaf'},
            {'label': _('Yield Predictor'), 'url_name': 'agri_yield_predictor', 'icon': 'fas fa-chart-line'},
            {'label': _('Weather'), 'url_name': 'agri_weather_page', 'icon': 'fas fa-cloud-sun'},
            {'label': _('Market Trends'), 'url_name': 'agri_market_trends', 'icon': 'fas fa-chart-bar'},
            {'label': _('Disease Scanner'), 'url_name': 'agri_disease_scanner', 'icon': 'fas fa-bug'},
        ],
        'color': '#10b981'
    },
    'KITCHEN': {
        'id': 'KITCHEN',
        'name': _('Kitchen'),
        'icon': 'fas fa-utensils',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_kitchen_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Production'), 'url_name': 'kitchen_production', 'icon': 'fas fa-fire'},
            {'label': _('Inventory'), 'url_name': 'kitchen_inventory', 'icon': 'fas fa-boxes'},
            {'label': _('Surplus'), 'url_name': 'surplus_list', 'icon': 'fas fa-gift'},
            {'label': _('Analytics'), 'url_name': 'kitchen_analytics', 'icon': 'fas fa-chart-line'},
        ],
        'color': '#f59e0b'
    },
    'REDISTRIBUTION': {
        'id': 'REDISTRIBUTION',
        'name': _('Redistribution'),
        'icon': 'fas fa-hands-helping',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_redistribution_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Surplus Board'), 'url_name': 'surplus_list', 'icon': 'fas fa-list'},
            {'label': _('My Requests'), 'url_name': 'recipient_request_center', 'icon': 'fas fa-clipboard-list'},
            {'label': _('AI Matching'), 'url_name': 'recipient_recommendations', 'icon': 'fas fa-robot'},
        ],
        'color': '#8b5cf6'
    },
    'LOGISTICS': {
        'id': 'LOGISTICS',
        'name': _('Logistics'),
        'icon': 'fas fa-truck',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_logistics_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Active Deliveries'), 'url_name': 'delivery_control', 'icon': 'fas fa-route'},
            {'label': _('Vehicle Tracking'), 'url_name': 'logistics_map', 'icon': 'fas fa-map-marker-alt'},
        ],
        'color': '#3b82f6'
    },
    'ADMIN': {
        'id': 'ADMIN',
        'name': _('Administration'),
        'icon': 'fas fa-cogs',
        'sidebar': [
            {'label': _('Dashboard'), 'url_name': 'workspace_admin_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': _('Users & Roles'), 'url_name': 'organization_admin_members', 'icon': 'fas fa-users'},
            {'label': _('Security'), 'url_name': 'security_center', 'icon': 'fas fa-shield-alt'},
            {'label': _('Integrations'), 'url_name': 'integration_health', 'icon': 'fas fa-plug'},
        ],
        'color': '#ef4444'
    }
}
