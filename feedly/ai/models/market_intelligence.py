class MarketIntelligenceModel:
    """
    Mock implementation of Market Price Intelligence.
    """
    def predict(self, input_data):
        required = ['crop_type', 'market_location']
        missing = [req for req in required if req not in input_data]
        
        if missing:
            return {
                "success": False,
                "message": f"More information is required for market analysis. Missing: {', '.join(missing)}",
                "data": None,
                "confidence": "None"
            }
            
        crop_type = input_data.get('crop_type', 'Wheat').lower()
        
        # Simple mock trend
        if crop_type in ['wheat', 'rice']:
            trend = "Stable"
            volatility = "Low"
            insight = "Staple crop prices are currently stable due to government reserves."
        elif crop_type in ['tomato', 'onion', 'potato']:
            trend = "Upward"
            volatility = "High"
            insight = "High volatility expected due to recent unseasonal rains affecting supply chains."
        else:
            trend = "Fluctuating"
            volatility = "Medium"
            insight = "Market prices showing seasonal fluctuations."
            
        return {
            "success": True,
            "data": {
                "price_trend": trend,
                "volatility": volatility
            },
            "message": insight,
            "factors": [
                {"name": "Historical Seasonality", "impact": "High", "value": "Based on 5-year average"},
                {"name": "Recent Supply Shocks", "impact": "Medium", "value": "None detected" if volatility == "Low" else "Detected"}
            ],
            "confidence": "Medium"
        }
