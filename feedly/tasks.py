from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from .models import Delivery, Notification, Organization
from .services.data_quality import DataQualityEngine
from .services.forecasting import DemandForecastingPipeline
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_websocket_notification_task(delivery_id):
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

@shared_task
def refresh_organization_forecasts():
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

@shared_task
def run_data_quality_audit():
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
