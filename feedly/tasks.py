from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Delivery, Notification

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
