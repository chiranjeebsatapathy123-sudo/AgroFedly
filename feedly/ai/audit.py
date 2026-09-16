import json
from feedly.models import AIAuditLog, Organization

def log_ai_action(
    organization,
    user,
    request_intent,
    ai_module,
    recommendation,
    inputs_snapshot=None,
    model_version="AgroFedly AI 1.0",
    confidence="",
    action_requested="",
    user_decision="",
    execution_result="",
    failure_reason="",
):
    """
    Records an AI operation into the AIAuditLog.
    """
    if isinstance(inputs_snapshot, dict) or isinstance(inputs_snapshot, list):
        try:
            inputs_snapshot = json.dumps(inputs_snapshot)
        except Exception:
            inputs_snapshot = str(inputs_snapshot)
    
    AIAuditLog.objects.create(
        organization=organization,
        user=user,
        request_intent=request_intent,
        ai_module=ai_module,
        model_version=model_version,
        inputs_snapshot=inputs_snapshot or "",
        recommendation=recommendation,
        confidence=confidence,
        action_requested=action_requested,
        user_decision=user_decision,
        execution_result=execution_result,
        failure_reason=failure_reason,
    )
