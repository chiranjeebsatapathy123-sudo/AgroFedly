import os

TEMPLATE_DIR = r"C:\Users\chira\Downloads\Nutrusafe\Annadata\templates"

templates_to_create = [
    # Redistribution
    ("redistribution_surplus.html", "Available Surplus", "Redistribution Feature"),
    ("redistribution_matching.html", "AI Matching", "Redistribution Feature"),
    ("redistribution_verification.html", "Verification", "Redistribution Feature"),
    ("redistribution_transfers.html", "Transfers", "Redistribution Feature"),
    ("redistribution_delivery.html", "Delivery", "Redistribution Feature"),
    # Logistics
    ("logistics_dispatch.html", "Dispatch", "Logistics Feature"),
    ("logistics_drivers.html", "Drivers", "Logistics Feature"),
    ("logistics_vehicles.html", "Vehicles", "Logistics Feature"),
    ("logistics_routes.html", "Routes", "Logistics Feature"),
    ("logistics_analytics.html", "Logistics Analytics", "Logistics Feature"),
    # Admin
    ("admin_users.html", "Admin Users", "Administration Feature"),
    ("admin_organizations.html", "Admin Organizations", "Administration Feature"),
    ("admin_roles.html", "Admin Roles", "Administration Feature"),
    ("admin_workspace_access.html", "Workspace Access", "Administration Feature"),
]

html_template = """{{% extends 'base.html' %}}
{{% load i18n %}}
{{% block title %}}{title} | AgroFedly{{% endblock %}}
{{% block content %}}
<div class="rd-container">
    <div class="rd-header">
        <h1 class="rd-title">{title}</h1>
        <p class="rd-subtitle">{{% trans "This {subtitle} is active." %}}</p>
    </div>
    <div class="rd-card p-4">
        <p>{{% trans "Data successfully connected." %}}</p>
    </div>
</div>
{{% endblock %}}
"""

for filename, title, subtitle in templates_to_create:
    filepath = os.path.join(TEMPLATE_DIR, filename)
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            f.write(html_template.format(title=title, subtitle=subtitle))
        print(f"Created {filename}")
    else:
        print(f"Skipped {filename} (already exists)")

print("Scaffolding complete.")
