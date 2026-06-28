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
import time

class AIManager:
    def __init__(self):
        print("[DEBUG] [AIManager] Initialize Isolation Forest Model...")
        # contamination: expected proportion of outliers (10%)
        self.models = {}
        self.sensitivities = {}
        # track last training time to prevent cpu blocking
        self.last_train_times = {}

    def detect(self, sensor_name, recent_data, protocol='analog', sensitivity=0.1):
        if not recent_data:
            return False, "NORMAL", 0.0
            
        if protocol == 'digital':
            # using rule-base decision
            latest_val = recent_data[0] 
            return bool(latest_val >= 1), "HIGH", -1.0 if latest_val >= 1 else 1.0

        # require minimum data points to train meaningfully
        if len(recent_data) < 15:
            return False, "NORMAL", 0.0

        current_time = time.time()
        # train interval set to 600 seconds (10 minutes)
        train_interval = 600
        needs_training = False

        # check if model needs init or retraining
        if sensor_name not in self.models or self.sensitivities.get(sensor_name) != sensitivity:
            print(f"[DEBUG] [AIManager] Re-building model for {sensor_name} with sensitivity {sensitivity}")
            self.models[sensor_name] = IsolationForest(contamination=sensitivity, random_state=42)
            self.sensitivities[sensor_name] = sensitivity
            needs_training = True
        elif current_time - self.last_train_times.get(sensor_name, 0) > train_interval:
            # periodic retraining triggered
            needs_training = True

        # reshape data for scikit-learn (e.g., [[val1], [val2], ...])
        X = np.array(recent_data).reshape(-1, 1)
        
        if needs_training:
            # fit model with recent time-series trend
            self.models[sensor_name].fit(X)
            self.last_train_times[sensor_name] = current_time

        # predict latest point (newest data is at index 0)
        latest_point = X[0].reshape(1, -1) 
        
        # extract anomaly score
        score = self.models[sensor_name].decision_function(latest_point)[0]
        is_anomaly = bool(score < 0)

        # decision anomaly direction using moving average
        direction = "NORMAL"
        if is_anomaly:
            # calculate moving average of recent window (max 10 points)
            window_size = min(10, len(recent_data))
            moving_avg = np.mean(recent_data[:window_size])
            
            if recent_data[0] > moving_avg:
                direction = "HIGH"  # anomaly cause data increase
            else:
                direction = "LOW"   # anomaly cause data decrease
                
        if is_anomaly:
            print(f"[DEBUG] [AIManager] ANOMALY! Sensor: {sensor_name}, Dir: {direction}, Score: {score:.3f}")

        return is_anomaly, direction, score