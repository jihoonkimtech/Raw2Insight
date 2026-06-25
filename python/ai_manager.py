"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : ai_manager.py
Purpose      : Machine Learning Anomaly Detection (Isolation Forest)
===================================================================
"""
import numpy as np
from sklearn.ensemble import IsolationForest

class AIManager:
    def __init__(self):
        print("[DEBUG] [AIManager] Initialize Isolation Forest Model...")
        # contamination: expected proportion of outliers (10%)
        self.models = {}

    def detect(self, sensor_name, recent_data):
        # create sensor's IsolationForest model
        if sensor_name not in self.models:
            self.models[sensor_name] = IsolationForest(contamination=0.1, random_state=42)
            
        # require minimum data points to train meaningfully
        if len(recent_data) < 15:
            return False

        # reshape data for scikit-learn (e.g., [[val1], [val2], ...])
        X = np.array(recent_data).reshape(-1, 1)

        # fit model with recent time-series trend
        self.models[sensor_name].fit(X)

        # predict latest point (1: normal, -1: anomaly)
        latest_point = X[0].reshape(1, -1) # newest data is at index 0 (descending)
        prediction = self.models[sensor_name].predict(latest_point)

        is_anomaly = bool(prediction[0] == -1)
        if is_anomaly:
            print(f"[DEBUG] [AIManager] ANOMALY DETECTED in [{sensor_name}]!")
            
        return is_anomaly