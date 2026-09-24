import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def main():
    dataset_path = r"C:\Users\chira\Downloads\Nutrusafe_Dataset_3\03_weather.csv"
    print(f"Loading data from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    
    # Feature engineering for time series
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    df['day_of_year'] = df['date'].dt.dayofyear
    
    # We will train a Multi-output Random Forest to predict temperature, humidity, and rainfall
    features = ["month", "day_of_year"]
    targets = ["temperature_c", "humidity_percent", "rainfall_mm"]
    
    X = df[features]
    y = df[targets]
    
    print("Splitting data into train and test sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Multi-output RandomForestRegressor for Weather...")
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    # Evaluate model
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred, multioutput='raw_values')
    rmse = np.sqrt(mean_squared_error(y_test, y_pred, multioutput='raw_values'))
    r2 = r2_score(y_test, y_pred, multioutput='raw_values')
    
    print(f"Model Performance Metrics (Temp, Humidity, Rainfall):")
    print(f" - MAE:  {mae}")
    print(f" - RMSE: {rmse}")
    print(f" - R²:   {r2}")
    
    bundle = {
        "model": model,
        "features": features,
        "targets": targets,
        "model_name": "AgroFedly Weather Forecast AI",
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "weather_bundle.pkl")
    joblib.dump(bundle, output_path)
    
    print(f"Successfully saved ML bundle to {output_path}")

if __name__ == "__main__":
    main()
