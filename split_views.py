import ast
import os
import collections

VIEWS_DIR = 'feedly/views'
SERVICES_DIR = 'feedly/services'

# Ensure directories exist
os.makedirs(VIEWS_DIR, exist_ok=True)
os.makedirs(SERVICES_DIR, exist_ok=True)

with open('feedly/views.py', 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

# Extract imports and global variables
common_nodes = []
functions = {}

for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # Handle duplicates: keep the LAST one (the latter overrides the former in python)
        functions[node.name] = node
    elif isinstance(node, ast.ClassDef):
        functions[node.name] = node
    else:
        common_nodes.append(node)

common_code = ast.unparse(common_nodes)
common_code = common_code.replace("from .forms", "from ..forms")
common_code = common_code.replace("from .models", "from ..models")
common_code = common_code.replace("from .utils", "from ..utils")

# Define mapping of functions to modules
MODULE_MAP = {
    'auth': ['login_view', 'logout_view'],
    'dashboard': ['home', 'dashboard', 'intelligence_center'],
    'organization': ['organization_dashboard', 'register_organization', 'organization_switch', 
                     'organization_details_json', 'organization_edit', 'organization_add_member', 
                     'organization_remove_member', 'logistics_map', 'impact_dashboard', 'leaderboard',
                     'org_fleet_routing', 'org_grants', 'org_shift_scheduler', 'org_esg_report',
                     '_membership', '_organization_required', '_manager_required'],
    'food': ['surplus_list', 'add_surplus_food', 'check_food_safety', 'post_meal_logging', 'food_chain_of_custody'],
    'redistribution': ['redistribute_food', 'recipient_list', 'add_recipient', 'verify_recipient', 'recipient_recommendations'],
    'delivery': ['delivery_list', 'delivery_create', 'delivery_detail', 'delivery_update_status', 
                 'delivery_live_tracking', 'delivery_proof', 'generate_donation_receipt', 'delivery_qr_code', 'delivery_scan_qr'],
    'analytics': ['analytics_dashboard'],
    'api': ['health_check', 'api_erp_attendance', 'api_iot_temperature', 'api_iot_live_stream', 'copilot_chat', 
            'predict_demand', 'forecast_7_days', '_predict', '_weather', 'weather_data'],
    'integrations': ['integration_health'],
    'community': ['volunteer_register', 'volunteer_dashboard', 'user_ai_recipe', 'user_food_swap', 'user_carbon_tracker',
                  'user_fridge_locator', 'user_farm_tour', 'user_agri_tourism', 'system_disaster_relief', 'system_blockchain_explorer',
                  'ecosystem_coordination', 'create_alliance', 'join_alliance'],
    'agriculture': [name for name in functions.keys() if name.startswith('agri_')] + ['generate_weather_advisory'],
}

# Generate modules
modules_code = collections.defaultdict(list)

for func_name, node in functions.items():
    assigned = False
    for mod, func_list in MODULE_MAP.items():
        if func_name in func_list:
            modules_code[mod].append(ast.unparse(node))
            assigned = True
            break
    if not assigned:
        modules_code['misc'].append(ast.unparse(node))

for mod, func_codes in modules_code.items():
    mod_path = os.path.join(VIEWS_DIR, f"{mod}.py")
    with open(mod_path, 'w', encoding='utf-8') as f:
        f.write(common_code + "\n\n")
        f.write("\n\n".join(func_codes) + "\n")

# Create __init__.py for views
init_path = os.path.join(VIEWS_DIR, "__init__.py")
with open(init_path, 'w', encoding='utf-8') as f:
    for mod in modules_code.keys():
        f.write(f"from .{mod} import *\n")

print(f"Refactored views into {len(modules_code)} modules.")
if 'misc' in modules_code:
    print(f"Unassigned functions went to misc.py. Count: {len(modules_code['misc'])}")
