class AgriculturalWeatherEngine:
    @classmethod
    def get_insights(cls, current_weather, crop_type=None, crop_stage=None):
        insights = []
        alerts = []
        
        if not current_weather:
            return insights, alerts

        temp = current_weather.get('temperature', 0)
        humidity = current_weather.get('humidity', 0)
        rainfall = current_weather.get('precipitation', 0)
        wind_speed = current_weather.get('wind_speed') or 0

        # General Alerts
        if temp > 38.0:
            alerts.append({'severity': 'CRITICAL', 'message': 'Extreme heat alert. Heat stress likely.'})
        elif temp < 5.0:
            alerts.append({'severity': 'WARNING', 'message': 'Frost risk detected. Cover sensitive crops.'})
            
        if rainfall > 10.0:
            alerts.append({'severity': 'WARNING', 'message': 'Heavy rainfall expected. Risk of waterlogging.'})
            
        if wind_speed > 30.0:
            alerts.append({'severity': 'WARNING', 'message': 'High wind alert. Secure equipment and delay spraying.'})

        # Crop-specific Rules
        if crop_type and crop_type.lower() == 'rice':
            if rainfall > 5.0 and crop_stage == 'harvest':
                insights.append('Review harvesting window due to rain.')
        elif crop_type and crop_type.lower() == 'tomato':
            if humidity > 80.0 and temp > 20.0:
                insights.append('Risk indicator: High humidity increases fungal disease risk for tomatoes. Increase monitoring.')

        # General Rules
        if rainfall > 5.0:
            insights.append('Irrigation may be deferred due to recent rainfall.')
        elif temp > 35.0 and rainfall < 1.0:
            insights.append('Monitor crop water stress and review irrigation requirements.')
            
        if wind_speed > 20.0 or rainfall > 2.0:
            insights.append('Spraying Risk: HIGH. Delay application.')
        else:
            insights.append('Spraying Risk: LOW.')

        return insights, alerts
