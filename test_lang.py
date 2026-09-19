import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AgroFedly.settings")
django.setup()

from django.test import Client

client = Client()
response = client.post('/i18n/setlang/', {'language': 'hi', 'next': '/'})
print(f"Status Code: {response.status_code}")
print(f"Redirect URL: {response.url if hasattr(response, 'url') else 'None'}")
print(f"Cookies: {response.cookies}")

# Now make a request to the dashboard to see if language is Hindi
response2 = client.get('/', HTTP_ACCEPT_LANGUAGE='hi')
print(f"Dashboard uses language (from cookie/session): {response2.context['LANGUAGE_CODE'] if getattr(response2, 'context', None) else 'Unknown'}")
