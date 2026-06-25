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
from arduino.app_bricks.dbstorage_sqlstore import SQLStore

class DBManager:
    def __init__(self, db_name='sensor_data.db'):
        # init db connection for sensor value
        print("[DEBUG] [DBManager] Connecting to InfluxDB TimeSeriesStore...")
        self.ts_store = TimeSeriesStore(host="dbstorage-influx", port=8086, retention_days=7)
        # setting data grouping name
        self.measurement_name = "arduino"
        self.field_name = "sensor_value"

        # init db connection for device config
        print("[DEBUG] [DBManager] Connecting to SQLStore for Device Config...")
        self.config_db = SQLStore("device_config.db")
        self.init_config_db()

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

    def init_config_db(self):
        # sensor table
        sensor_cols = {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
            "protocol": "TEXT", # 'analog', 'i2c', 'digital_in'
            "pin": "TEXT"       # 'A0', '0x68', '2'
        }
        self.config_db.create_table("sensors", sensor_cols)

        # output device table
        actuator_cols = {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
            "control_type": "TEXT", # 'digital_out', 'pwm'
            "pin": "TEXT",          # '9', '7'
            "trigger_logic": "INTEGER", # 0 (Active-Low) or 1/255 (Active-High/PWM)
            "linked_sensor_id": "INTEGER" # sensor mapping
        }
        self.config_db.create_table("actuators", actuator_cols)
        print("[DEBUG] [DBManager] Device Config Tables Checked/Initialized.")

    # sensor management
    def add_sensor(self, name, protocol, pin):
        data = {"name": name, "protocol": protocol, "pin": pin}
        self.config_db.store("sensors", data)
        print(f"[DEBUG] [DBManager] 🟢 Sensor Added: {name} ({protocol} on {pin})")

    # output device management
    def add_actuator(self, name, control_type, pin, trigger_logic, linked_sensor_id):
        data = {
            "name": name, "control_type": control_type, 
            "pin": pin, "trigger_logic": trigger_logic, 
            "linked_sensor_id": linked_sensor_id
        }
        self.config_db.store("actuators", data)
        print(f"[DEBUG] [DBManager] 🔴 Actuator Added: {name} (Pin {pin})")

    def get_all_sensors(self):
        return self.config_db.read("sensors")

    def get_all_actuators(self):
        return self.config_db.read("actuators")

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

    def get_aggregated_data(self, limit=20):
        # fetch aggregated data (2-second moving average)
        try:
            samples = self.ts_store.read_samples(
                measure=self.field_name,
                measurement_name=self.measurement_name,
                start_from="-10m",
                aggr_window="2s",  # aggregate every 2 seconds
                aggr_func="mean",  # calculate mean
                limit=limit,
                order="desc" 
            )
            
            formatted_rows = []
            values_only = []
            
            for sample in samples:
                field_name, ts_iso, val = sample
                if val is not None:
                    # extract HH:MM:SS
                    time_only = ts_iso.split('T')[1][:8] if 'T' in ts_iso else ts_iso
                    formatted_rows.append([time_only, round(val, 1)])
                    values_only.append(val)
            
            return formatted_rows, values_only

        except Exception as e:
            print(f"[ERROR] [DBManager] Error reading aggregated samples: {e}")
            return [], []
            
    def delete_sensor(self, sensor_id):
        self.config_db.delete("sensors", f"id = {sensor_id}")
        print(f"[DEBUG] [DBManager] Sensor ID {sensor_id} Deleted.")

    def delete_actuator(self, actuator_id):
        self.config_db.delete("actuators", f"id = {actuator_id}")
        print(f"[DEBUG] [DBManager] Actuator ID {actuator_id} Deleted.")