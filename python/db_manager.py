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
                sensor_value REAL
            )
        ''')
        self.conn.commit()

    def init_config_db(self):
        # sensor table
        sensor_cols = {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
            "protocol": "TEXT", # 'analog', 'i2c', 'digital_in'
            "pin": "TEXT",       # 'A0', '0x68', '2'
            "data_type": "TEXT", # 'Temperature' ...
            "unit": "TEXT",       # '°C', 'lux' ...
            "sensitivity": "REAL", # 0.1, 0.2 ...
            "threshold_low": "REAL",    # lower threshold
            "threshold_high": "REAL",    # higher threshold
            "multiplier": "REAL",
            "offset": "REAL",
            "profile_name": "TEXT", # sensor driver name
            "data_key": "TEXT" # extract data lables
        }
        self.config_db.create_table("sensors", sensor_cols)

        # output device table
        actuator_cols = {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
            "control_type": "TEXT", # 'digital_out', 'pwm'
            "pin": "TEXT",          # '9', '7'
            "trigger_logic": "INTEGER", # 0 (Active-Low) or 1/255 (Active-High/PWM)
            "linked_sensor_id": "INTEGER", # sensor mapping
            "normal_val": "INTEGER",   # normal state output
            "low_val": "INTEGER",      # lower threshold output
            "high_val": "INTEGER",     # higher threshold output
            "trigger_dir": "TEXT",     # 'BOTH', 'HIGH', 'LOW'
            "extra_params": "TEXT"     # for virtual
        }
        self.config_db.create_table("actuators", actuator_cols)
        print("[DEBUG] [DBManager] Device Config Tables Checked/Initialized.")

    # sensor management
    def add_sensor(self, name, protocol, pin, data_type="", unit="", 
                   threshold_low=None, threshold_high=None, 
                   multiplier=1.0, offset=0.0, 
                   profile_name=None, data_key=None):
        data = {
            "name": name, "protocol": protocol, "pin": pin, 
            "data_type": data_type, "unit": unit, "sensitivity": 0.1,
            "multiplier": multiplier, "offset": offset
        }

        if threshold_low is not None:
            data["threshold_low"] = threshold_low
        if threshold_high is not None:
            data["threshold_high"] = threshold_high
        if profile_name is not None:
            data["profile_name"] = profile_name
        if data_key is not None:
            data["data_key"] = data_key
            
        self.config_db.store("sensors", data)
        print(f"[DEBUG] [DBManager] Sensor Added: {name} (Low: {threshold_low}, High: {threshold_high})(Mult: {multiplier}, Offset: {offset})")

    # output device management
    def add_actuator(self, name, control_type, pin, normal_val, low_val, high_val, trigger_dir, linked_sensor_id, extra_params="{}"):
        data = {
            "name": name, "control_type": control_type, 
            "pin": pin, "normal_val": normal_val, 
            "low_val": low_val, "high_val": high_val,
            "trigger_dir": trigger_dir, "linked_sensor_id": linked_sensor_id,
            "extra_params": extra_params
        }
        self.config_db.store("actuators", data)
        print(f"[DEBUG] [DBManager] Actuator Added: {name} (Pin {pin})")

    def get_all_sensors(self):
        return self.config_db.read("sensors")

    def get_all_actuators(self):
        return self.config_db.read("actuators")

    def insert_data(self, value, sensor_name):
        # store date with timestamp
        self.ts_store.write_sample(
            measure=sensor_name,
            value=float(value), 
            measurement_name=self.measurement_name
        )
        print(f"[DEBUG] [DBManager] Inserted [{sensor_name}] -> Value: {value}")
        return value

    def get_latest_data(self, limit=20):
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

    def get_aggregated_data(self, sensor_name, limit=20):
        # fetch aggregated data (2-second moving average)
        try:
            samples = self.ts_store.read_samples(
                measure=sensor_name, # only specific sensor
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

    def get_raw_data(self, sensor_name, limit=20):
        try:
            samples = self.ts_store.read_samples(
                measure=sensor_name,
                measurement_name=self.measurement_name,
                start_from="-10m",
                limit=limit,
                order="desc" 
            )
            
            formatted_rows = []
            for sample in samples:
                field_name, ts_iso, val = sample
                if val is not None:
                    # extract time
                    time_only = ts_iso.split('T')[1][:8] if 'T' in ts_iso else ts_iso
                    formatted_rows.append([time_only, round(val, 2)])
            
            return formatted_rows

        except Exception as e:
            print(f"[ERROR] [DBManager] Error reading raw samples: {e}")
            return []
            
    def update_sensor_sensitivity(self, sensor_id, sensitivity):
        try:
            # if not exist sensitivity column? create
            try:
                self.config_db.execute_sql("ALTER TABLE sensors ADD COLUMN sensitivity REAL DEFAULT 0.1", None)
            except:
                pass
                
            # update sensitivity
            self.config_db.update("sensors", {"sensitivity": sensitivity}, f"id = {sensor_id}")
            
            print(f"[DEBUG] [DBManager] Sensor ID {sensor_id} sensitivity updated to {sensitivity}")
            
        except Exception as e:
            print(f"[ERROR] [DBManager] Error updating sensitivity using SQLStore: {e}")