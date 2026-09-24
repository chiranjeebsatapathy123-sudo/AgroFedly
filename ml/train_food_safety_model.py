import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder

def main():
    dataset_path = r"C:\Users\chira\Downloads\Nutrusafe_Dataset_5\05_food_safety_temperature.csv"
    print(f"Loading data from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    
    features_continuous = ["storage_temperature_c", "storage_duration_hours", "quantity_kg"]
    features_categorical = ["food_type", "storage_method"]
    target = "safety_label_demo"
    
    # Preprocessing
    encoders = {}
    for cat_col in features_categorical:
        le = LabelEncoder()
        df[cat_col + "_encoded"] = le.fit_transform(df[cat_col])
        encoders[cat_col] = le
        
    encoded_categorical_features = [col + "_encoded" for col in features_categorical]
    X = df[features_continuous + encoded_categorical_features]
    
    # Target encoding
    target_le = LabelEncoder()
    y = target_le.fit_transform(df[target])
    
    print("Splitting data into train and test sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training RandomForestClassifier for Food Safety Risk...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    # Evaluate model
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=target_le.classes_)
    
    print(f"Model Performance Metrics:")
    print(f" - Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(report)
    
    bundle = {
        "model": model,
        "features_continuous": features_continuous,
        "features_categorical": features_categorical,
        "encoders": encoders,
        "target_encoder": target_le,
        "model_name": "AgroFedly Food Safety AI",
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "food_safety_bundle.pkl")
    joblib.dump(bundle, output_path)
    
    print(f"\nSuccessfully saved ML bundle to {output_path}")

if __name__ == "__main__":
    main()
