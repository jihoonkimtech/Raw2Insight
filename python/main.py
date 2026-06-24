import sqlite3
import time
from datetime import datetime
from arduino.app_utils import App, Bridge 

print("receive and store sensor data test start ...")

# sensor_data.db' creation
db_conn = sqlite3.connect('sensor_data.db', check_same_thread=False)
cursor = db_conn.cursor()

# table creation
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME,
        sensor_value INTEGER
    )
''')
db_conn.commit()
print("DB and TABLE ready! \n")

def loop():
    try:
        # read data
        sensor_val = Bridge.call("get_sensor_data")

        # make timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # row creation
        cursor.execute(
            "INSERT INTO sensor_logs (timestamp, sensor_value) VALUES (?, ?)", 
            (current_time, sensor_val)
        )
        db_conn.commit() # commit data
        
        print(f"[stored] time: {current_time} | value: {sensor_val}")
        
    except Exception as e:
        print(f"error occur : {e}")
        
    time.sleep(1)
    
# run in background
App.run(user_loop=loop)