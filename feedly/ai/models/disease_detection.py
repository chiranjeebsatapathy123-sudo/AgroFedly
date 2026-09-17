class DiseaseDetectionModel:
    """
    Mock implementation of Image-based Disease Detection.
    """
    def predict(self, input_data):
        required = ['image_file_path', 'image_mime_type', 'image_size_bytes']
        missing = [req for req in required if req not in input_data]
        
        if missing:
            return {
                "success": False,
                "message": f"Invalid image upload. Missing: {', '.join(missing)}",
                "data": None,
                "confidence": "None"
            }
            
        mime_type = input_data.get('image_mime_type', '')
        size = int(input_data.get('image_size_bytes', 0))
        
        if mime_type not in ['image/jpeg', 'image/png']:
            return {
                "success": False,
                "message": "Unsupported image format. Please upload JPEG or PNG.",
                "data": None,
                "confidence": "None"
            }
            
        if size > 5 * 1024 * 1024:
            return {
                "success": False,
                "message": "Image size too large. Maximum allowed size is 5MB.",
                "data": None,
                "confidence": "None"
            }
        
        # In a real model, we would pass the image buffer through a ResNet or EfficientNet
        # Mocking detection based on filename hashing for stable demo
        filename = input_data.get('image_file_path', 'unknown').lower()
        
        if 'healthy' in filename:
            disease = 'Healthy'
            confidence = 'High'
            action = 'Continue normal monitoring.'
        elif 'rust' in filename:
            disease = 'Leaf Rust'
            confidence = 'High'
            action = 'Apply approved fungicide. Isolate affected plants if possible.'
        elif 'blight' in filename:
            disease = 'Early Blight'
            confidence = 'Medium'
            action = 'Ensure proper spacing for airflow. Avoid overhead watering.'
        else:
            return {
                "success": False,
                "message": "Unable to determine the issue reliably. Please upload a clearer image or seek appropriate expert verification.",
                "data": None,
                "confidence": "Low"
            }
            
        return {
            "success": True,
            "data": {
                "detection": disease,
                "suggested_action": action
            },
            "message": "Analysis complete.",
            "factors": [
                {"name": "Visual signatures", "impact": "High", "value": "Fungal pattern detected" if disease != "Healthy" else "Uniform green coloration"}
            ],
            "confidence": confidence
        }
