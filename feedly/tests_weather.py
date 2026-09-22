from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Organization, OrganizationMember, Farm, WeatherObservation
from .services.weather.cache import WeatherCacheManager
from .services.weather.agricultural import AgriculturalWeatherEngine
from unittest.mock import patch
from django.utils import timezone

class WeatherTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test_farmer', password='password')
        self.org = Organization.objects.create(name='Test Farm Org', org_type='FARM')
        OrganizationMember.objects.create(user=self.user, organization=self.org, role='FARMER', status='ACTIVE')
        self.farm = Farm.objects.create(
            organization=self.org,
            name='Main Farm',
            latitude=28.7041,
            longitude=77.1025,
            location='Delhi'
        )

    def test_weather_requires_authentication(self):
        response = self.client.get(reverse('weather_data'))
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_weather_is_organization_scoped(self):
        self.client.login(username='test_farmer', password='password')
        
        # Another org's farm
        other_org = Organization.objects.create(name='Other Org')
        other_farm = Farm.objects.create(organization=other_org, name='Other', latitude=12.0, longitude=77.0)
        
        response = self.client.get(reverse('weather_data'), {'farm_id': other_farm.id})
        self.assertEqual(response.status_code, 400) # Should fail or fallback if farm doesn't belong to org

    @patch('feedly.services.weather.client.OpenWeatherClient.fetch_current')
    def test_weather_uses_farm_coordinates(self, mock_fetch):
        mock_fetch.return_value = {
            'main': {'temp': 30.0, 'humidity': 60, 'pressure': 1012},
            'weather': [{'description': 'clear sky'}],
            'coord': {'lat': 28.7041, 'lon': 77.1025}
        }
        
        self.client.login(username='test_farmer', password='password')
        response = self.client.get(reverse('weather_data'), {'farm_id': self.farm.id})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['temperature'], 30.0)
        
        # Verify it used the coordinates
        mock_fetch.assert_called_with(lat=28.7041, lon=77.1025, city='Delhi')
        
        # Verify cache was created
        self.assertTrue(WeatherObservation.objects.filter(farm=self.farm).exists())

    @patch('feedly.services.weather.client.OpenWeatherClient.fetch_current')
    def test_weather_provider_failure_does_not_create_fake_data(self, mock_fetch):
        mock_fetch.return_value = None # Simulate failure
        
        self.client.login(username='test_farmer', password='password')
        response = self.client.get(reverse('weather_data'), {'farm_id': self.farm.id})
        
        self.assertEqual(response.status_code, 503) # Service Unavailable
        self.assertFalse(WeatherObservation.objects.exists())

    def test_heavy_rain_generates_alert(self):
        weather = {'temperature': 25.0, 'precipitation': 15.0} # > 10.0
        insights, alerts = AgriculturalWeatherEngine.get_insights(weather)
        
        self.assertTrue(any(a['message'] == 'Heavy rainfall expected. Risk of waterlogging.' for a in alerts))
        self.assertTrue(any(a['severity'] == 'WARNING' for a in alerts))
