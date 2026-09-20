import os
import sys
import django

sys.path.append(r"c:\Users\chira\Downloads\Nutrusafe\Annadata")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AgroFedly.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from feedly.views.delivery import delivery_control
from django.contrib.messages.storage.fallback import FallbackStorage

User = get_user_model()
u = User.objects.get(username="Chiranjeebsatapathy")

req = RequestFactory().get("/workspace/logistics/dashboard/")
req.user = u
req.session = {'active_workspace': 'LOGISTICS'}
req._messages = FallbackStorage(req)

try:
    delivery_control(req)
except Exception as e:
    import traceback
    traceback.print_exc()
