import os
import pandas as pd
import numpy as np
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

def main():
    dataset_path = r"C:\Users\chira\Downloads\Nutrusafe_Dataset_4\04_nutrition.csv"
    print(f"Loading data from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    
    # We will train a model to predict calories based on macronutrients (Protein, Carbs, Fat)
    features = ["protein_g", "carbs_g", "fat_g"]
    target = "calories_kcal"
    
    X = df[features]
    y = df[target]
    
    print("Training Linear Regression for Nutrition Modeling...")
    # Using Linear Regression because Calories = 4*Protein + 4*Carbs + 9*Fat (Physics-based)
    model = LinearRegression()
    model.fit(X, y)
    
    # Evaluate model
    print("Evaluating model...")
    y_pred = model.predict(X)
    
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    print(f"Model Performance Metrics:")
    print(f" - MAE:  {mae:.2f} kcal")
    print(f" - R²:   {r2:.4f}")
    
    # Display learned coefficients (should be close to 4, 4, 9)
    print("\nLearned Macronutrient Caloric Multipliers:")
    print(f" - Protein: {model.coef_[0]:.2f} kcal/g (Expected ~4)")
    print(f" - Carbs:   {model.coef_[1]:.2f} kcal/g (Expected ~4)")
    print(f" - Fat:     {model.coef_[2]:.2f} kcal/g (Expected ~9)")
    
    bundle = {
        "model": model,
        "features": features,
        "target": target,
        "model_name": "AgroFedly Nutrition AI",
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "nutrition_bundle.pkl")
    joblib.dump(bundle, output_path)
    
    print(f"\nSuccessfully saved ML bundle to {output_path}")

if __name__ == "__main__":
    main()
