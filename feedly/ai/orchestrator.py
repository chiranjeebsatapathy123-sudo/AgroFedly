import logging
from datetime import date
from django.utils import timezone
from feedly.models import AIRecommendation, SurplusFood, Delivery, StorageRecord, IoTTemperatureReading, DemandForecast, MealRecord
from feedly.services.data_quality import DataQualityEngine

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    Central brain for coordinating specialized AI agents.
    Calculates deterministic metrics and generates structured operational briefings.
    """
    
    def __init__(self, organization):
        self.organization = organization
        self.today = timezone.now().date()
        
    def generate_daily_briefing(self):
        """
        Gathers operational signals and builds the Daily Briefing.
        """
        signals = []
        
        # 1. Storage / Temperature Anomalies
        critical_temps = IoTTemperatureReading.objects.filter(status='ALERT', recorded_at__date=self.today)
        if critical_temps.exists():
            signals.append({
                "type": "CRITICAL",
                "message": f"{critical_temps.count()} temperature anomalies detected today.",
                "action_url": "/intelligence/",
                "action_text": "Investigate"
            })
            
        # Data Quality Issues
        dq_engine = DataQualityEngine(self.organization)
        dq_result = dq_engine.run_audit()
        if dq_result['issue_count'] > 0:
            signals.append({
                "type": "CRITICAL" if dq_result['status'] == 'critical' else "WARNING",
                "message": f"Detected {dq_result['issue_count']} data quality anomalies.",
                "action_url": "/intelligence/",
                "action_text": "Review Data"
            })
            
        storage_alerts = StorageRecord.objects.filter(organization=self.organization, status__in=['ATTENTION', 'CRITICAL'])
        if storage_alerts.exists():
            signals.append({
                "type": "ATTENTION",
                "message": f"{storage_alerts.count()} storage locations require attention.",
                "action_url": "/dashboard/",
                "action_text": "View Storage"
            })
            
        # 2. Surplus & Waste Risk
        pending_surplus = SurplusFood.objects.filter(organization=self.organization, status='PENDING')
        if pending_surplus.exists():
            total_qty = sum([s.quantity for s in pending_surplus])
            signals.append({
                "type": "ATTENTION",
                "message": f"{total_qty} units of pending surplus require redistribution.",
                "action_url": "/surplus/",
                "action_text": "Redistribute"
            })
            
        # 3. Deliveries
        delayed_deliveries = Delivery.objects.filter(sender=self.organization, status='IN_TRANSIT')
        if delayed_deliveries.exists():
            signals.append({
                "type": "ATTENTION",
                "message": f"{delayed_deliveries.count()} deliveries currently in transit.",
                "action_url": "/delivery/",
                "action_text": "Track Deliveries"
            })
            
        # 4. Positive Signals
        completed_deliveries = Delivery.objects.filter(sender=self.organization, status='DELIVERED', updated_at__date=self.today)
        if completed_deliveries.exists():
            signals.append({
                "type": "POSITIVE",
                "message": f"{completed_deliveries.count()} successful deliveries today.",
                "action_url": "/impact/",
                "action_text": "View Impact"
            })
            
        # Forecast
        forecast = DemandForecast.objects.filter(date=self.today).first()
        if forecast:
            signals.append({
                "type": "POSITIVE",
                "message": f"Demand predicted at {forecast.predicted_demand} units. Confidence: {int(forecast.confidence * 100)}%.",
                "action_url": "/forecast/",
                "action_text": "View Forecast"
            })

        critical_count = len([s for s in signals if s['type'] == 'CRITICAL'])
        attention_count = len([s for s in signals if s['type'] == 'ATTENTION'])
        positive_count = len([s for s in signals if s['type'] == 'POSITIVE'])
        total_signals = len(signals)

        return {
            "total_signals": total_signals,
            "critical_count": critical_count,
            "attention_count": attention_count,
            "positive_count": positive_count,
            "signals": signals,
            "generated_at": timezone.now()
        }

    def get_attention_items(self):
        """
        Universal operational priority engine.
        Deterministically calculates severity of actionable items.
        """
        attention_items = []
        
        # Produce requiring quality check
        pending_quality = SurplusFood.objects.filter(organization=self.organization, status='PENDING', is_safe=False)
        for p in pending_quality:
            attention_items.append({
                "title": f"Produce Batch {p.food_name}",
                "description": "Quality review pending",
                "severity": "HIGH",
                "action_url": f"/surplus/",
                "action_text": "Review Quality"
            })
            
        dq_engine = DataQualityEngine(self.organization)
        dq_result = dq_engine.run_audit()
        for issue in dq_result['issues']:
            attention_items.append({
                "title": f"Data Quality: {issue['category']}",
                "description": issue['message'],
                "severity": issue['severity'],
                "action_url": "/intelligence/",
                "action_text": "Resolve"
            })

        # Storage capacity nearing limits or temp alerts
        storage_alerts = StorageRecord.objects.filter(organization=self.organization, status__in=['ATTENTION', 'CRITICAL'])
        for s in storage_alerts:
            attention_items.append({
                "title": f"Storage: {s.location}",
                "description": f"Condition: {s.status}",
                "severity": "CRITICAL" if s.status == 'CRITICAL' else "MEDIUM",
                "action_url": f"/dashboard/",
                "action_text": "Investigate"
            })

        # Pending AI Recommendations
        ai_recs = AIRecommendation.objects.filter(organization=self.organization, status='NEW')
        for rec in ai_recs:
            attention_items.append({
                "title": f"AI: {rec.title}",
                "description": rec.reason,
                "severity": rec.priority,
                "action_url": f"/intelligence/",
                "action_text": "View Insight"
            })

        # Sort by severity
        severity_map = {"CRITICAL": 4, "URGENT": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        attention_items.sort(key=lambda x: severity_map.get(x['severity'], 0), reverse=True)
        
        return attention_items
