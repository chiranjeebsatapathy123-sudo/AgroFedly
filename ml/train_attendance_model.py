import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def main():
    dataset_path = r"C:\Users\chira\Downloads\Nutrusafe_Dataset_2\02_attendance_calendar_events.csv"
    print(f"Loading data from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    
    # Extract month from date if available, otherwise just use day_of_week etc.
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.month
    else:
        df['month'] = 1
        
    features = [
        "day_of_week", "weekend", "holiday", 
        "exam_day", "event_flag", "event_size", "month"
    ]
    
    X = df[features]
    y = df["attendance"]
    
    print("Splitting data into train and test sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training RandomForestRegressor for Attendance...")
    model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
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
    
    bundle = {
        "model": model,
        "features": features,
        "model_name": "AgroFedly Attendance AI",
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "attendance_bundle.pkl")
    joblib.dump(bundle, output_path)
    
    print(f"Successfully saved ML bundle to {output_path}")

if __name__ == "__main__":
    main()
