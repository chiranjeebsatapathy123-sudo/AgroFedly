from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from feedly.models import Organization, UserProfile

User = get_user_model()

class Phase48JourneyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org1 = Organization.objects.create(name="Org1", organization_type="NGO", onboarding_completed=True)
        self.org2 = Organization.objects.create(name="Org2", organization_type="COMPANY", onboarding_completed=True)
        
        # Setup Users
        self.farmer = self.create_user("farmer", "FARMER", self.org1, "STAFF")
        self.kitchen = self.create_user("kitchen", "KITCHEN", self.org2, "STAFF")
        self.ngo = self.create_user("ngo", "NGO", self.org1, "STAFF")
        self.logistics = self.create_user("logistics", "LOGISTICS", self.org1, "STAFF")
        self.admin = self.create_user("admin", "ADMIN", self.org1, "ADMIN")
        self.superadmin = self.create_user("superadmin", "SUPER_ADMIN", self.org1, "OWNER")

    def create_user(self, username, role, org, org_role="STAFF"):
        user = User.objects.create_user(username=username, password="password123")
        UserProfile.objects.create(user=user, role=role, onboarding_completed=True)
        from feedly.models import OrganizationMember
        OrganizationMember.objects.create(user=user, organization=org, role=org_role, status="ACTIVE", is_active=True)
        return user

    def test_login_success(self):
        # Valid login
        response = self.client.post(reverse('login'), {'username': 'farmer', 'password': 'password123'})
        self.assertEqual(response.status_code, 302, "Login should redirect on success")
        
        # We know it redirects to /dashboard/, so let's hit /dashboard/ to set session
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302, "Dashboard should redirect to workspace")
        self.assertEqual(self.client.session.get('active_workspace'), 'AGRICULTURE')

    def test_login_invalid(self):
        response = self.client.post(reverse('login'), {'username': 'farmer', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200, "Invalid login should reload the form")
        self.assertContains(response, "We couldn&#x27;t sign you in", status_code=200)

    def test_role_workspace_routing(self):
        role_mappings = {
            'farmer': 'AGRICULTURE',
            'kitchen': 'KITCHEN',
            'ngo': 'REDISTRIBUTION',
            'admin': 'ADMIN'
        }
        
        for username, expected_workspace in role_mappings.items():
            self.client.login(username=username, password='password123')
            # Trigger dashboard redirect to set session
            resp = self.client.get(reverse('dashboard'))
            self.assertEqual(
                self.client.session.get('active_workspace'), 
                expected_workspace, 
                f"{username} should default to {expected_workspace}"
            )
            self.client.logout()

    def test_workspace_security_boundary(self):
        # Farmer should not access logistics dashboard
        self.client.login(username='farmer', password='password123')
        # Attempt to access logistics
        response = self.client.get(reverse('workspace_logistics_dashboard'))
        # Usually Django auth throws 403 or redirects to login if permission denied
        self.assertIn(response.status_code, [403, 302, 404], "Farmer should be forbidden or redirected from logistics")

        # Admin should be able to access Admin dashboard
        self.client.login(username='admin', password='password123')
        # Simulate active org middleware resolving
        session = self.client.session
        session['active_organization_id'] = self.org1.id
        session['active_workspace'] = 'ADMIN'
        session.save()
        
        response = self.client.get(reverse('workspace_admin_dashboard'))
        self.assertEqual(response.status_code, 200, "Admin should access Admin dashboard")
