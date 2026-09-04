import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Features expected by views.py:
# "attendance", "temperature", "rainfall", "holiday", "day_of_week",
# "humidity", "month", "weekend", "exam_day", "event_flag", "recent_avg_demand"

def generate_synthetic_data(num_records=500):
    np.random.seed(42)
    data = []
    
    for _ in range(num_records):
        month = np.random.randint(1, 13)
        day_of_week = np.random.randint(0, 7)
        weekend = 1 if day_of_week >= 5 else 0
        holiday = 1 if np.random.rand() > 0.95 else 0
        exam_day = 1 if np.random.rand() > 0.90 else 0
        event_flag = 1 if np.random.rand() > 0.90 else 0
        
        # Base attendance between 300 and 500
        attendance = np.random.randint(300, 500)
        
        temperature = round(np.random.normal(25, 5), 1)
        humidity = round(np.random.normal(65, 10), 1)
        rainfall = round(np.random.exponential(2), 1) if np.random.rand() > 0.8 else 0
        
        # Calculate recent avg demand (just close to attendance for synthetic)
        recent_avg_demand = attendance * 0.85 + np.random.normal(0, 5)
        
        # True demand logic
        # ~85% of attendance eat, but less on holidays or weekends
        ratio = 0.86
        if holiday: ratio -= 0.15
        if weekend: ratio -= 0.05
        if rainfall > 10: ratio -= 0.03
        if event_flag: ratio += 0.05
        
        demand = max(0, int(attendance * ratio + np.random.normal(0, 8)))
        
        data.append({
            "attendance": attendance,
            "temperature": temperature,
            "rainfall": rainfall,
            "holiday": holiday,
            "day_of_week": day_of_week,
            "humidity": humidity,
            "month": month,
            "weekend": weekend,
            "exam_day": exam_day,
            "event_flag": event_flag,
            "recent_avg_demand": recent_avg_demand,
            "demand": demand
        })
        
    return pd.DataFrame(data)

def main():
    print("Generating synthetic data for ML training...")
    df = generate_synthetic_data()
    
    features = [
        "attendance", "temperature", "rainfall", "holiday", 
        "day_of_week", "humidity", "month", "weekend", 
        "exam_day", "event_flag", "recent_avg_demand"
    ]
    
    X = df[features]
    y = df["demand"]
    
    print("Splitting data into train and test sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training RandomForestRegressor...")
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate model
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    print(f"Model Performance Metrics:")
    print(f" - MAE:  {mae:.2f}")
    print(f" - RMSE: {rmse:.2f}")
    print(f" - R²:   {r2:.2f}")
    
    # Calculate residuals on the entire dataset for confidence bounds (90th percentile)
    preds = model.predict(X)
    residuals = np.abs(y - preds)
    residual_p90 = np.percentile(residuals, 90)
    print(f"\nCalculated 90th percentile residual for confidence bounds: {residual_p90:.2f}")
    
    bundle = {
        "model": model,
        "features": features,
        "model_name": "Fedly Advanced AI",
        "residual_p90": residual_p90
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "demand_bundle.pkl")
    joblib.dump(bundle, output_path)
    
    print(f"Successfully saved ML bundle to {output_path}")

if __name__ == "__main__":
    main()
