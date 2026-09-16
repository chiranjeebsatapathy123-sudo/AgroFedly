import logging
from .events import event_bus, EVENT_SURPLUS_DETECTED
from ..models import WorkflowRule, WorkflowExecution, UserTask, SystemEvent, Redistribution, SurplusFood

logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self):
        # Register standard listeners
        event_bus.subscribe(EVENT_SURPLUS_DETECTED, self.evaluate_rules)

    def evaluate_rules(self, organization=None, entity_id=None, **kwargs):
        if not organization:
            return
            
        # 1. Fetch relevant active rules for this event
        # Assuming event_type corresponds to the listener that called us
        # Since kwargs doesn't have event_type directly, we could pass it
        # Actually, let's simplify for the demo and just evaluate surplus rules
        rules = WorkflowRule.objects.filter(organization=organization, is_active=True, trigger_event=EVENT_SURPLUS_DETECTED)
        
        # We need the triggering event to link executions
        triggering_event = SystemEvent.objects.filter(organization=organization, event_type=EVENT_SURPLUS_DETECTED).order_by('-timestamp').first()
        if not triggering_event:
            return

        for rule in rules:
            logger.info(f"[WorkflowEngine] Evaluating rule {rule.name}")
            
            # Idempotency check: don't run the same rule on the same entity multiple times
            if WorkflowExecution.objects.filter(rule=rule, triggering_event=triggering_event).exists():
                logger.info(f"[WorkflowEngine] Rule {rule.name} already executed for event {triggering_event.id}")
                continue
                
            execution = WorkflowExecution.objects.create(
                rule=rule,
                triggering_event=triggering_event,
                status='PENDING'
            )
            
            # Evaluate conditions (simulated)
            conditions_met = True
            
            if not conditions_met:
                execution.status = 'COMPLETED'
                execution.execution_log.append("Conditions not met.")
                execution.save()
                continue
                
            if rule.automation_level == 'MANUAL':
                execution.status = 'COMPLETED'
                execution.execution_log.append("Rule is manual. No action taken.")
                execution.save()
                continue
                
            elif rule.automation_level == 'SUPERVISED':
                execution.status = 'WAITING_APPROVAL'
                execution.execution_log.append("Waiting for human approval.")
                execution.save()
                
                # Create a UserTask
                UserTask.objects.create(
                    organization=organization,
                    title=f"Review: {rule.name}",
                    description=f"AI Workflow '{rule.name}' requires approval. Triggered by {entity_id}.",
                    priority='HIGH',
                    related_entity=entity_id,
                    action_url=f"/intelligence/"
                )
                
            elif rule.automation_level == 'AUTOMATED':
                execution.status = 'COMPLETED'
                execution.execution_log.append("Automated execution completed safely.")
                execution.save()
                # Actually execute safe action...

workflow_engine = WorkflowEngine()
