WORKSPACE_CONFIGS = {
    'AGRICULTURE': {
        'id': 'AGRICULTURE',
        'name': 'Agriculture',
        'icon': 'fas fa-seedling',
        'sidebar': [
            {'label': 'Dashboard', 'url_name': 'workspace_agri_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': 'Farms & Fields', 'url_name': 'agri_farm_list', 'icon': 'fas fa-tractor'},
            {'label': 'Produce', 'url_name': 'agri_produce_list', 'icon': 'fas fa-leaf'},
            {'label': 'Yield Predictor', 'url_name': 'agri_yield_predictor', 'icon': 'fas fa-chart-line'},
            {'label': 'Weather', 'url_name': 'agri_weather_page', 'icon': 'fas fa-cloud-sun'},
            {'label': 'Market Trends', 'url_name': 'agri_market_trends', 'icon': 'fas fa-chart-bar'},
            {'label': 'Disease Scanner', 'url_name': 'agri_disease_scanner', 'icon': 'fas fa-bug'},
        ],
        'color': '#10b981'
    },
    'KITCHEN': {
        'id': 'KITCHEN',
        'name': 'Kitchen',
        'icon': 'fas fa-utensils',
        'sidebar': [
            {'label': 'Dashboard', 'url_name': 'workspace_kitchen_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': 'Production', 'url_name': 'kitchen_dashboard', 'icon': 'fas fa-fire'},
            {'label': 'Inventory', 'url_name': 'kitchen_inventory', 'icon': 'fas fa-boxes'},
            {'label': 'Surplus', 'url_name': 'surplus_list', 'icon': 'fas fa-gift'},
            {'label': 'Analytics', 'url_name': 'kitchen_analytics', 'icon': 'fas fa-chart-line'},
        ],
        'color': '#f59e0b'
    },
    'REDISTRIBUTION': {
        'id': 'REDISTRIBUTION',
        'name': 'Redistribution',
        'icon': 'fas fa-hands-helping',
        'sidebar': [
            {'label': 'Dashboard', 'url_name': 'workspace_redistribution_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': 'Surplus Board', 'url_name': 'surplus_list', 'icon': 'fas fa-list'},
            {'label': 'My Requests', 'url_name': 'redistribution_dashboard', 'icon': 'fas fa-clipboard-list'},
            {'label': 'AI Matching', 'url_name': 'redistribution_ai_match', 'icon': 'fas fa-robot', 'disabled': True},
        ],
        'color': '#8b5cf6'
    },
    'LOGISTICS': {
        'id': 'LOGISTICS',
        'name': 'Logistics',
        'icon': 'fas fa-truck',
        'sidebar': [
            {'label': 'Dashboard', 'url_name': 'workspace_logistics_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': 'Active Deliveries', 'url_name': 'delivery_control', 'icon': 'fas fa-route'},
            {'label': 'Vehicle Tracking', 'url_name': 'logistics_vehicles', 'icon': 'fas fa-map-marker-alt', 'disabled': True},
        ],
        'color': '#3b82f6'
    },
    'ADMIN': {
        'id': 'ADMIN',
        'name': 'Administration',
        'icon': 'fas fa-cogs',
        'sidebar': [
            {'label': 'Dashboard', 'url_name': 'workspace_admin_dashboard', 'icon': 'fas fa-chart-pie'},
            {'label': 'Users & Roles', 'url_name': 'organization_admin_members', 'icon': 'fas fa-users'},
            {'label': 'Security', 'url_name': 'admin_security', 'icon': 'fas fa-shield-alt', 'disabled': True},
            {'label': 'Integrations', 'url_name': 'integration_health', 'icon': 'fas fa-plug'},
        ],
        'color': '#ef4444'
    }
}
