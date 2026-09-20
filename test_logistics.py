import os
import sys
import django

sys.path.append(r"c:\Users\chira\Downloads\Nutrusafe\Annadata")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AgroFedly.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
c = Client()
u = User.objects.get(username="Chiranjeebsatapathy")
c.force_login(u)
try:
    res = c.get("/workspace/logistics/dashboard/")
    if res.status_code >= 400:
        print("ERROR CODE:", res.status_code)
        import re
        content = res.content.decode('utf-8')
        match = re.search(r'<title>(.*?)</title>', content)
        if match:
            print("TITLE:", match.group(1))
        # Print first 2000 chars of traceback if it exists
        match = re.search(r'<div id="traceback_area".*?>(.*?)</div>', content, re.DOTALL)
        if match:
            print("TRACEBACK:", match.group(1)[:2000])
        else:
            print(content[:2000])
    else:
        print("SUCCESS:", res.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
