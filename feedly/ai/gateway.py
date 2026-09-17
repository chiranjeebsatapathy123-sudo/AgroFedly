import json
import logging
from django.utils import timezone
from feedly.models import AIModelRegistry, AIAuditLog
from .models.crop_recommendation import CropRecommendationModel
from .models.yield_prediction import YieldPredictionModel
from .models.disease_detection import DiseaseDetectionModel
from .models.market_intelligence import MarketIntelligenceModel

logger = logging.getLogger(__name__)

class AIGateway:
    """
    Centralized API for all AI/ML inference requests in AgroFedly.
    Ensures validation, logging, authorization, and graceful fallback.
    """
    
    # Map model names to their implementation classes
    MODEL_REGISTRY = {
        'crop_recommendation': CropRecommendationModel,
        'yield_prediction': YieldPredictionModel,
        'disease_detection': DiseaseDetectionModel,
        'market_intelligence': MarketIntelligenceModel,
    }

    @classmethod
    def run_inference(cls, model_name, user, input_data, organization=None):
        """
        Main entrypoint for AI inference.
        """
        # 1. Check Model Existence
        if model_name not in cls.MODEL_REGISTRY:
            return cls._error_response(f"Model '{model_name}' is not registered.")
        
        # 2. Check Database Registry Status
        try:
            registry_entry = AIModelRegistry.objects.get(model_name=model_name, status='ACTIVE')
        except AIModelRegistry.DoesNotExist:
            return cls._error_response(f"Model '{model_name}' is currently unavailable or offline.")

        # 3. Instantiate Model
        model_instance = cls.MODEL_REGISTRY[model_name]()
        
        # 4. Validate Input
        if not isinstance(input_data, dict):
            return cls._error_response("Input data must be a dictionary.")

        # 5. Run Inference
        try:
            start_time = timezone.now()
            result = model_instance.predict(input_data)
            end_time = timezone.now()
            latency = (end_time - start_time).total_seconds()
            
            # 6. Log Audit
            if organization:
                AIAuditLog.objects.create(
                    organization=organization,
                    user=user,
                    request_intent=f"Inference request for {model_name}",
                    ai_module=model_name,
                    model_version=registry_entry.version,
                    inputs_snapshot=json.dumps(input_data)[:2000],
                    recommendation=json.dumps(result.get('data', {}))[:2000],
                    confidence=result.get('confidence', 'Low'),
                    action_requested="Predict"
                )
            
            # 7. Structure Output
            return {
                "success": True,
                "data": result.get('data', {}),
                "confidence": result.get('confidence', 'Low'),
                "factors": result.get('factors', []),
                "message": result.get('message', 'Analysis complete.'),
                "model_version": registry_entry.version
            }

        except Exception as e:
            logger.error(f"AI Model Error ({model_name}): {str(e)}", exc_info=True)
            if organization:
                AIAuditLog.objects.create(
                    organization=organization,
                    user=user,
                    request_intent=f"Inference request for {model_name} FAILED",
                    ai_module=model_name,
                    model_version=registry_entry.version if 'registry_entry' in locals() else 'Unknown',
                    inputs_snapshot=json.dumps(input_data)[:2000],
                    recommendation=f"ERROR: {str(e)}"[:2000],
                    confidence="Error",
                    action_requested="Predict"
                )
            return cls._error_response("AI service temporarily unavailable. Your other AgroFedly features are still available.")

    @staticmethod
    def _error_response(message):
        return {
            "success": False,
            "message": message,
            "data": None
        }
