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
        self.sensitivities = {}

    def detect(self, sensor_name, recent_data, protocol='analog', sensitivity=0.1):
        if not recent_data:
            return False, "NORMAL", 0.0
            
        if protocol == 'digital':
            # using rule-base decision
            latest_val = recent_data[0] 
            return bool(latest_val >= 1), "HIGH", -1.0 if latest_val >= 1 else 1.0

        # create sensor's IsolationForest model
        if sensor_name not in self.models or self.sensitivities.get(sensor_name) != sensitivity:
            print(f"[DEBUG] [AIManager] Re-building model for {sensor_name} with sensitivity {sensitivity}")
            # contamination is sensitivity
            self.models[sensor_name] = IsolationForest(contamination=sensitivity, random_state=42)
            self.sensitivities[sensor_name] = sensitivity

        # require minimum data points to train meaningfully
        if len(recent_data) < 15:
            return False, "NORMAL", 0.0

        # reshape data for scikit-learn (e.g., [[val1], [val2], ...])
        X = np.array(recent_data).reshape(-1, 1)
        # fit model with recent time-series trend
        self.models[sensor_name].fit(X)

        # predict latest point (1: normal, -1: anomaly)
        latest_point = X[0].reshape(1, -1) # newest data is at index 0 (descending)
        
        # extract anomaly score
        #score = self.models[sensor_name].score_samples(latest_point)[0]
        #prediction = self.models[sensor_name].predict(latest_point)
        score = self.models[sensor_name].decision_function(latest_point)[0]
        #is_anomaly = bool(prediction[0] == -1)
        is_anomaly = bool(score < 0)

        # decision anomaly direction using 10 means data
        direction = "NORMAL"
        if is_anomaly:
            recent_mean = np.mean(recent_data[1:11]) if len(recent_data) > 1 else recent_data[0]
            if recent_data[0] > recent_mean:
                direction = "HIGH"  # anomaly cause data increase
            else:
                direction = "LOW"   # anomaly cause data decrease
                
        if is_anomaly:
            print(f"[DEBUG] [AIManager] ANOMALY! Sensor: {sensor_name}, Dir: {direction}, Score: {score:.3f}")

        return is_anomaly, direction, score