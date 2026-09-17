class YieldPredictionModel:
    """
    Mock implementation of Yield Prediction.
    """
    def predict(self, input_data):
        required = ['crop_type', 'area_hectares', 'crop_stage']
        missing = [req for req in required if req not in input_data]
        
        if missing:
            return {
                "success": False,
                "message": f"More information is required for a reliable recommendation. Missing: {', '.join(missing)}",
                "data": None,
                "confidence": "None"
            }
            
        area = float(input_data.get('area_hectares', 1.0))
        crop_type = input_data.get('crop_type', 'Wheat').lower()
        
        # Base yield in tons per hectare
        base_yield_map = {
            'wheat': 3.5,
            'rice': 4.0,
            'maize': 5.5,
            'soybean': 2.8,
            'cotton': 1.5,
            'sugarcane': 70.0
        }
        
        base_yield = base_yield_map.get(crop_type, 3.0)
        estimated_yield = base_yield * area
        
        # Uncertainty bound of +/- 15%
        lower_bound = round(estimated_yield * 0.85, 1)
        upper_bound = round(estimated_yield * 1.15, 1)
        
        return {
            "success": True,
            "data": {
                "estimated_yield_tons": round(estimated_yield, 1),
                "range": f"{lower_bound} - {upper_bound} tons"
            },
            "message": f"Estimated yield for {area} hectares of {crop_type.title()}.",
            "factors": [
                {"name": "Farm Area", "impact": "High", "value": f"{area} ha"},
                {"name": "Crop Base Yield", "impact": "High", "value": f"{base_yield} t/ha"},
                {"name": "Crop Stage", "impact": "Medium", "value": input_data.get('crop_stage')}
            ],
            "confidence": "Medium"
        }
