"""
AI Event Bus
A lightweight synchronous event bus for AgroFedly intelligence modules.
Allows decoupled components to publish and subscribe to business events.
"""
import logging

logger = logging.getLogger(__name__)

class AIEventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, handler):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        if handler not in self.subscribers[event_type]:
            self.subscribers[event_type].append(handler)

    def publish(self, event_type, organization=None, entity_id=None, description="", severity="INFO", **kwargs):
        """
        Synchronously dispatch an event to all registered subscribers.
        Persists the event to SystemEvent if an organization is provided.
        """
        logger.info(f"[AIEventBus] Published event: {event_type}")
        
        # Persist event
        if organization:
            try:
                from ..models import SystemEvent
                SystemEvent.objects.create(
                    organization=organization,
                    event_type=event_type,
                    entity_id=entity_id,
                    description=description,
                    severity=severity,
                    metadata=kwargs
                )
            except Exception as e:
                logger.error(f"[AIEventBus] Failed to persist SystemEvent {event_type}: {e}")

        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                try:
                    handler(organization=organization, entity_id=entity_id, **kwargs)
                except Exception as e:
                    logger.error(f"[AIEventBus] Error in handler {handler.__name__} for {event_type}: {e}")

# Global singleton event bus
event_bus = AIEventBus()

# Standard Events
EVENT_PRODUCE_CREATED = "ProduceCreated"
EVENT_HARVEST_RECORDED = "HarvestRecorded"
EVENT_DEMAND_UPDATED = "DemandForecastUpdated"
EVENT_PRODUCTION_COMPLETED = "ProductionCompleted"
EVENT_STORAGE_UPDATED = "StorageUpdated"
EVENT_TEMPERATURE_ANOMALY = "TemperatureAnomalyDetected"
EVENT_SURPLUS_DETECTED = "SurplusDetected"
EVENT_RECIPIENT_MATCHED = "RecipientMatched"
EVENT_DELIVERY_STARTED = "DeliveryStarted"
EVENT_DELIVERY_COMPLETED = "DeliveryCompleted"
EVENT_QUALITY_REVIEW_REQUIRED = "QualityReviewRequired"
