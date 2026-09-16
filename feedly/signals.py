import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import SurplusFood, Delivery, StorageRecord, IoTTemperatureReading, OrganizationImpact, Notification

def send_realtime_event(organization, event_type, message, related_id=None):
    if not organization:
        return
        
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    # Create DB notification
    Notification.objects.create(
        organization=organization,
        notification_type=event_type,
        message=message
    )

    # Broadcast to all users in the organization
    payload = {
        'type': 'notification',
        'message': {
            'type': event_type,
            'title': event_type.replace('_', ' ').title(),
            'message': message,
            'related_id': related_id
        }
    }
    
    for member in organization.members.all():
        async_to_sync(channel_layer.group_send)(
            f"user_{member.user.id}",
            payload
        )

@receiver(post_save, sender=SurplusFood)
def surplus_food_saved(sender, instance, created, **kwargs):
    if created:
        send_realtime_event(
            instance.organization,
            'SURPLUS_CREATED',
            f"New surplus detected: {instance.quantity} units of {instance.food_name}",
            instance.id
        )
    elif instance.status == 'SAFE':
        send_realtime_event(
            instance.organization,
            'SURPLUS_UPDATED',
            f"Surplus {instance.food_name} marked as SAFE and ready for redistribution.",
            instance.id
        )

@receiver(post_save, sender=Delivery)
def delivery_saved(sender, instance, created, **kwargs):
    if created:
        send_realtime_event(
            instance.sender,
            'DELIVERY_CREATED',
            f"Delivery #{instance.tracking_code} planned to {instance.receiver.name}.",
            instance.id
        )
    else:
        send_realtime_event(
            instance.sender,
            'DELIVERY_STATUS_CHANGED',
            f"Delivery #{instance.tracking_code} status updated to {instance.get_status_display()}.",
            instance.id
        )
        
    # Update Impact when delivered
    if instance.status == 'DELIVERED':
        impact, _ = OrganizationImpact.objects.get_or_create(organization=instance.sender)
        impact.total_meals_saved += instance.quantity
        impact.total_co2_reduced_kg += (instance.quantity * 0.65) # Approx 0.65kg per meal
        impact.save()

@receiver(post_save, sender=IoTTemperatureReading)
def iot_reading_saved(sender, instance, created, **kwargs):
    if instance.status == 'ALERT':
        # Need to find the org. Let's broadcast this globally for simplicity in the demo, or skip if no org attached directly.
        # Currently IoT readings don't have an organization foreign key in the model.
        pass
