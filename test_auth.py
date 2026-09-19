import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AgroFedly.settings")
django.setup()

from django.contrib.auth import authenticate, get_user_model
User = get_user_model()
from django.test import RequestFactory

factory = RequestFactory()
request = factory.post('/login/', {'username': 'Chiranjeebsatapathy', 'password': 'chira@138'})

user = authenticate(request, username='Chiranjeebsatapathy', password='chira@138')
print(f"Authenticated user: {user}")

if not user:
    print("Authentication failed.")
    u = User.objects.get(username='Chiranjeebsatapathy')
    print(f"User check_password: {u.check_password('chira@138')}")
