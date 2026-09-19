import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AgroFedly.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

u = User.objects.filter(username='Chiranjeebsatapathy').first()
print(f'User exists: {u is not None}')
if u:
    print(f'Is Active: {u.is_active}')
    print(f'Check Password (chira@138): {u.check_password("chira@138")}')
    print(f'Is Superuser: {u.is_superuser}')
    
    # Check Profile
    print(f'Has Profile: {hasattr(u, "profile")}')
    if hasattr(u, "profile"):
        print(f'Profile Status: {u.profile.account_status}')
