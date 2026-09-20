import os
import re

views_dir = r"c:\Users\chira\Downloads\Nutrusafe\Annadata\feedly\views"
bypass_condition = r"not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and "

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: if role not in [...]
    # We only want to patch it if it hasn't been patched already
    # Negative lookbehind to ensure we don't double patch
    content = re.sub(
        r"(?<!and\s)if role not in (\[.*?\]):", 
        f"if {bypass_condition}role not in \\1:", 
        content
    )
    
    # Pattern 2: if request.user.profile.role not in [...]
    content = re.sub(
        r"(?<!and\s)if request\.user\.profile\.role not in (\[.*?\]):", 
        f"if {bypass_condition}request.user.profile.role not in \\1:", 
        content
    )
    
    # Pattern 3: if request.membership.role not in {...}
    content = re.sub(
        r"(?<!and\s)if request\.membership\.role not in (\{.*?\})|(\[.*?\]):", 
        f"if {bypass_condition}request.membership.role not in \\1\\2:", 
        content
    )
    
    # Pattern 4: if role == 'FARMER' (when used to restrict access with an else: Permission denied)
    # This one is tricky. Let's just fix the specific ones if needed.
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {filepath}")
    else:
        print(f"No changes for {filepath}")

for filename in os.listdir(views_dir):
    if filename.endswith(".py"):
        patch_file(os.path.join(views_dir, filename))
