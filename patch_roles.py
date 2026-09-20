import os
import re

views_dir = r"c:\Users\chira\Downloads\Nutrusafe\Annadata\feedly\views"
bypass_condition = r"not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and "

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # We use exact match replacements instead of broad regex to avoid catastrophic matches
    
    # 1. if role not in ['FARMER', 'FPO']:
    content = re.sub(
        r"(?<!and\s)if role not in (\[.*?\]):", 
        f"if {bypass_condition}role not in \\1:", 
        content
    )
    
    # 2. if request.user.profile.role not in [...]
    content = re.sub(
        r"(?<!and\s)if request\.user\.profile\.role not in (\[.*?\]):", 
        f"if {bypass_condition}request.user.profile.role not in \\1:", 
        content
    )
    
    # 3. if request.membership.role not in {'OWNER', 'ADMIN'}:
    # Only match if it's explicitly 'request.membership.role not in'
    content = re.sub(
        r"(?<!and\s)if request\.membership\.role not in (\{.*?\}|\[.*?\]):", 
        f"if {bypass_condition}request.membership.role not in \\1:", 
        content
    )
    
    # 4. Handle "if role != 'SUPER_ADMIN':" specifically if it exists and wasn't patched already
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {filepath}")
    else:
        print(f"No changes for {filepath}")

for filename in os.listdir(views_dir):
    if filename.endswith(".py"):
        patch_file(os.path.join(views_dir, filename))
