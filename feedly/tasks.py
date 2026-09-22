from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from .models import Delivery, Notification, Organization, Farm
from .services.data_quality import DataQualityEngine
from .services.forecasting import DemandForecastingPipeline
from .services.weather.cache import WeatherCacheManager
from .signals import broadcast_event_to_org
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 5})
def send_websocket_notification_task(self, delivery_id):
    """
    Asynchronously sends WebSocket push notifications to members of the receiving organization
    when a delivery status updates. Persists notifications in the database.
    """
    try:
        delivery = Delivery.objects.select_related('receiver').get(id=delivery_id)
    except Delivery.DoesNotExist:
        return

    channel_layer = get_channel_layer()
    message = f"Delivery {delivery.tracking_code} is now {delivery.get_status_display()}."
    
    # Notify receiver organization members
    for member in delivery.receiver.members.all():
        # Persist to DB
        Notification.objects.create(
            user=member.user,
            organization=delivery.receiver,
            notification_type="DELIVERY_UPDATE",
            message=message
        )
        
        if channel_layer:
            try:
                async_to_sync(channel_layer.group_send)(
                    f"user_{member.user.id}",
                    {
                        "type": "notification",
                        "message": message
                    }
                )
            except Exception as e:
                print(f"Failed to send websocket notification in task: {e}")

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def refresh_organization_forecasts(self):
    """Daily job to refresh forecasts for all active organizations."""
    orgs = Organization.objects.filter(is_active=True)
    count = 0
    for org in orgs:
        try:
            pipeline = DemandForecastingPipeline(org)
            # Example using a default heuristic base
            pipeline.predict_demand(attendance=100, target_date=timezone.localdate())
            count += 1
        except Exception as e:
            logger.error(f"Failed to refresh forecast for org {org.name}: {e}")
            
    return f"Refreshed forecasts for {count} organizations."

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def run_data_quality_audit(self):
    """Nightly job to run data quality audits and generate alerts."""
    orgs = Organization.objects.filter(is_active=True)
    for org in orgs:
        try:
            engine = DataQualityEngine(org)
            result = engine.run_audit()
            if result['issue_count'] > 0:
                from .models import SystemEvent
                SystemEvent.objects.create(
                    organization=org,
                    event_type='DataQualityAudit',
                    description=f"Found {result['issue_count']} data quality issues.",
                    severity='WARNING' if result['status'] == 'warning' else 'CRITICAL',
                    metadata=result
                )
        except Exception as e:
            logger.error(f"Data quality audit failed for org {org.name}: {e}")

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def refresh_active_weather(self):
    """
    Periodic task (e.g. every 30 mins) to refresh weather for active farms.
    Broadcasts the new weather data via WebSockets to the agriculture dashboard.
    """
    farms = Farm.objects.filter(organization__is_active=True)
    updated = 0
    for farm in farms:
        if farm.latitude and farm.longitude:
            try:
                # Force fetch (cache manager internally saves new observation)
                weather = WeatherCacheManager.get_current_weather(
                    organization=farm.organization,
                    farm=farm,
                    lat=farm.latitude,
                    lon=farm.longitude,
                    city=farm.location
                )
                if weather:
                    updated += 1
                    # Broadcast to org members
                    broadcast_event_to_org(
                        farm.organization,
                        'agri_user',
                        {
                            'type': 'weather_update',
                            'farm_id': farm.id,
                            'data': weather
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to refresh weather for farm {farm.id}: {e}")
                
    return f"Refreshed weather for {updated} farms."
