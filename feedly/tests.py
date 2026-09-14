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
            'copilot_chat' # API endpoint
        ]
        
        passed = 0
        failed = 0
        
        for pattern in urlpatterns:
            if not hasattr(pattern, 'name') or not pattern.name:
                continue
                
            if pattern.name in skip_list:
                continue
                
            try:
                # Some views might need kwargs, but most in our app don't
                url = reverse(pattern.name)
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
