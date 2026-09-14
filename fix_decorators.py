import glob
import re

# Extract from organization.py
with open('feedly/views/organization.py', 'r', encoding='utf-8') as f:
    org_content = f.read()

# Using regex to extract the functions (assuming they are at the top)
func1 = re.search(r'def _membership\(.*?return memberships\.order_by\("-joined_at"\)\.first\(\)', org_content, re.DOTALL)
func2 = re.search(r'def _organization_required\(.*?return _wrapped_view', org_content, re.DOTALL)
func3 = re.search(r'def _manager_required\(.*?return _wrapped_view', org_content, re.DOTALL)

f1_str = func1.group(0) if func1 else ''
f2_str = func2.group(0) if func2 else ''
f3_str = func3.group(0) if func3 else ''

if not f1_str:
    print("Could not find _membership")
    
# 1. Update decorators.py
with open('feedly/decorators.py', 'r', encoding='utf-8') as f:
    dec_content = f.read()

dec_content = dec_content.replace('from .views import _organization_required', 'from .models import OrganizationMember\nfrom functools import wraps\nfrom django.shortcuts import redirect\nfrom django.contrib import messages')

with open('feedly/decorators.py', 'w', encoding='utf-8') as f:
    f.write(dec_content + '\n\n' + f1_str + '\n\n' + f2_str + '\n\n' + f3_str + '\n')

# Remove from organization.py
if func1: org_content = org_content.replace(f1_str, '')
if func2: org_content = org_content.replace(f2_str, '')
if func3: org_content = org_content.replace(f3_str, '')
with open('feedly/views/organization.py', 'w', encoding='utf-8') as f:
    f.write(org_content)

# 2. Add import to all views
for file in glob.glob('feedly/views/*.py'):
    if file.endswith('__init__.py'): continue
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'from ..decorators import' not in content:
        content = 'from ..decorators import _organization_required, _manager_required, _membership, require_org_role\n' + content
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
            
print("Fixed decorators")
