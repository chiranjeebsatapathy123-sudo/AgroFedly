class CropRecommendationModel:
    """
    Mock implementation of Crop Recommendation.
    In a real system, this would load a serialized ML model (e.g. Scikit-learn, TensorFlow)
    and perform inference based on soil NPK, pH, rainfall, and temperature.
    """
    def predict(self, input_data):
        # Validate required inputs
        required = ['nitrogen', 'phosphorus', 'potassium', 'ph', 'temperature', 'rainfall']
        missing = [req for req in required if req not in input_data]
        
        if missing:
            return {
                "success": False,
                "message": f"More information is required for a reliable recommendation. Missing: {', '.join(missing)}",
                "data": None,
                "confidence": "None"
            }
        
        # Simple mock logic based on pH and Nitrogen
        ph = float(input_data.get('ph', 7))
        nitrogen = float(input_data.get('nitrogen', 50))
        
        if ph < 5.5:
            crops = ["Potato", "Sweet Potato", "Cassava"]
            reason = "Acidic soil prefers root tubers."
        elif ph > 7.5:
            crops = ["Barley", "Sugarbeet", "Cotton"]
            reason = "Alkaline soil detected."
        else:
            if nitrogen > 80:
                crops = ["Maize", "Sugarcane", "Wheat"]
                reason = "High nitrogen soil prefers heavy-feeding cereals."
            else:
                crops = ["Soybean", "Lentils", "Peas"]
                reason = "Moderate nitrogen soil prefers legumes."
                
        return {
            "success": True,
            "data": {
                "recommended_crops": crops
            },
            "message": reason,
            "factors": [
                {"name": "Soil pH", "impact": "High", "value": ph},
                {"name": "Nitrogen", "impact": "High", "value": nitrogen},
                {"name": "Temperature", "impact": "Medium", "value": input_data.get('temperature')}
            ],
            "confidence": "Medium"
        }
