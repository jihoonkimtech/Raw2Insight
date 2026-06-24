"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : db_manager.py
Purpose      : Manage InfluxDB database connection and queries
===================================================================
"""
import time
from arduino.app_bricks.dbstorage_tsstore import TimeSeriesStore

class DBManager:
    def __init__(self, db_name='sensor_data.db'):
        # init db connection
        print("[DEBUG] [DBManager] Connecting to InfluxDB TimeSeriesStore...")
        self.ts_store = TimeSeriesStore(host="dbstorage-influx", port=8086, retention_days=7)
        
        # setting data grouping name
        self.measurement_name = "arduino"
        self.field_name = "sensor_value"

    def init_db(self):
        # table creation
        print("[DEBUG] [DBManager] Checking and initializing 'sensor_logs' table...")
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                sensor_value INTEGER
            )
        ''')
        self.conn.commit()

    def insert_data(self, value):
        # store date with timestamp
        self.ts_store.write_sample(
            measure=self.field_name, 
            value=value, 
            measurement_name=self.measurement_name
        )
        print(f"[DEBUG] [DBManager] Inserted TimeSeries Row -> Value: {value}")
        return value

    def get_latest_data(self, limit=15):
        
        print(f"[DEBUG] [DBManager] Fetching latest {limit} records from InfluxDB...")
        try:
            # load N latest data from DB (in 1 hour)
            samples = self.ts_store.read_samples(
                measure=self.field_name,
                measurement_name=self.measurement_name,
                start_from="-1h",
                limit=limit,
                order="desc" 
            )
            
            # transform to [time, value] for web display
            formatted_rows = []
            for sample in samples:
                field_name, ts_iso, val = sample
                # transform 2026-06-24T11:35:12Z to 11:35:12
                time_only = ts_iso.split('T')[1][:8] if 'T' in ts_iso else ts_iso
                formatted_rows.append([time_only, val])
            
            return formatted_rows
            
        except Exception as e:
            print(f"[DEBUG] [DBManager] Error reading timeseries samples: {e}")
            return []