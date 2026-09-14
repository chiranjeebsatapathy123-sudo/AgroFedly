from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from feedly.urls import urlpatterns

User = get_user_model()

class FeedlySmokeTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')

    def test_all_get_endpoints(self):
        """
        Dynamically loops through all URL patterns in feedly/urls.py
        and ensures they return either a 200 (OK) or 302 (Redirect) status.
        """
        print("\n--- Running Smoke Tests on All Endpoints ---")
        
        # Skip URLs that require specific arguments (like <int:id>)
        # or endpoints that are meant for POST only.
        skip_list = [
            'generate_donation_receipt', # Requires <int:delivery_id>
            'copilot_chat', # API endpoint
            'api_erp_attendance', # Requires API Key
            'api_iot_temperature' # Requires API Key
        ]
        
        passed = 0
        failed = 0
        
        for pattern in urlpatterns:
            if not hasattr(pattern, 'name') or not pattern.name:
                continue
                
            if pattern.name in skip_list:
                continue
                
            try:
                from django.urls.exceptions import NoReverseMatch
                try:
                    url = reverse(pattern.name)
                except NoReverseMatch:
                    print(f"Skipping {pattern.name} (requires arguments)")
                    continue
                response = self.client.get(url)
                
                # We expect 200 OK or 302 Redirect (e.g. login required or successful post redirect)
                if response.status_code in [200, 302]:
                    passed += 1
                else:
                    print(f"FAILED: {pattern.name} returned {response.status_code}")
                    failed += 1
            except Exception as e:
                print(f"ERROR on {pattern.name}: {str(e)}")
                failed += 1
                
        print(f"--- Smoke Test Results: {passed} Passed, {failed} Failed ---\n")
        
        self.assertEqual(failed, 0, f"{failed} endpoints failed the smoke test.")

class TemplateSyntaxTests(TestCase):
    def test_all_templates_compile(self):
        """
        Discovers all HTML templates in the project and attempts to compile them
        using the Django template engine to catch syntax errors.
        """
        import os
        from django.conf import settings
        from django.template.loader import get_template
        from django.template import TemplateSyntaxError, TemplateDoesNotExist
        from pathlib import Path
        
        app_template_dirs = [Path(settings.BASE_DIR) / 'feedly' / 'templates', Path(settings.BASE_DIR) / 'templates']
        html_files = []
        for d in app_template_dirs:
            if not d.exists():
                continue
            for root, dirs, files in os.walk(d):
                for file in files:
                    if file.endswith('.html'):
                        html_files.append(os.path.relpath(os.path.join(root, file), d))

        html_files = list(set(html_files))
        errors = []
        
        for template_name in html_files:
            template_name = template_name.replace('\\', '/')
            try:
                get_template(template_name)
            except (TemplateSyntaxError, TemplateDoesNotExist) as e:
                errors.append(f"{template_name}: {e}")
            except Exception as e:
                errors.append(f"{template_name}: {e}")
                
        self.assertEqual(len(errors), 0, f"Template syntax errors found in {len(errors)} templates: {errors}")

