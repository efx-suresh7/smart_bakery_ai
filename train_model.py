import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
from sklearn.ensemble import RandomForestRegressor
from app import app
from models import db, Sale, Forecast, Item

def train_forecasting_model():
    print("Starting ML model training pipeline...")
    
    with app.app_context():
        # 1. Fetch sales data from database
        sales = Sale.query.all()
        if not sales:
            print("No sales data found in the database. Please run generate_data.py first.")
            return
        
        # Convert to DataFrame
        data = []
        for s in sales:
            data.append({
                'item_id': s.item_id,
                'date': pd.to_datetime(s.date),
                'quantity_sold': s.quantity_sold
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values(by=['item_id', 'date']).reset_index(drop=True)
        
        # 2. Engineer features
        # Calculate past 7 days rolling average (excluding current day's sales)
        df['past_7_day_avg'] = df.groupby('item_id')['quantity_sold'].transform(
            lambda x: x.shift(1).rolling(window=7, min_periods=1).mean()
        )
        
        # Fill missing values (for the first days where no shift/rolling average exists)
        # We fill with the mean of that item's sales
        item_means = df.groupby('item_id')['quantity_sold'].transform('mean')
        df['past_7_day_avg'] = df['past_7_day_avg'].fillna(item_means)
        
        # Extract calendar features
        df['day_of_week'] = df['date'].dt.weekday
        df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x in [5, 6] else 0)
        
        # One-hot encode item_id
        # To make it robust, we explicitly define columns for each bakery item
        items = Item.query.filter_by(category='Bakery Product').all()
        item_ids = [item.id for item in items]
        
        for item_id in item_ids:
            df[f'item_{item_id}'] = (df['item_id'] == item_id).astype(int)
            
        # Define feature columns
        feature_cols = ['day_of_week', 'is_weekend', 'past_7_day_avg'] + [f'item_{item_id}' for item_id in item_ids]
        
        X = df[feature_cols]
        y = df['quantity_sold']
        
        # 3. Train Random Forest Regressor
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        print("Model trained successfully.")
        
        # Calculate training metrics
        predictions = model.predict(X)
        mae = np.mean(np.abs(y - predictions))
        rmse = np.sqrt(np.mean((y - predictions) ** 2))
        r2 = model.score(X, y)
        print(f"Training Metrics -> MAE: {mae:.2f}, RMSE: {rmse:.2f}, R2: {r2:.2f}")
        
        # 4. Save the trained model and feature definitions
        model_data = {
            'model': model,
            'item_ids': item_ids,
            'feature_cols': feature_cols
        }
        joblib.dump(model_data, 'forecast_model.joblib')
        print("Model and metadata saved to 'forecast_model.joblib'.")
        
        # 5. Populate forecasts table for historical evaluation on dashboard
        print("Generating historical forecasts in database...")
        # Clear old forecasts first to avoid duplication
        db.session.query(Forecast).delete()
        
        # Predict on the entire training set
        df['predicted_qty'] = np.round(predictions).astype(int)
        
        # Save historical predictions into forecasts table
        forecasts_to_add = []
        for idx, row in df.iterrows():
            f = Forecast(
                item_id=int(row['item_id']),
                date=row['date'].date(),
                predicted_qty=max(0, int(row['predicted_qty']))
            )
            forecasts_to_add.append(f)
            
        db.session.bulk_save_objects(forecasts_to_add)
        db.session.commit()
        print(f"Generated and saved {len(forecasts_to_add)} historical forecasts.")

if __name__ == "__main__":
    train_forecasting_model()
