"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : main.py
Purpose      : Main orchestrator coordinating DB, Comm, and Web
===================================================================
"""
import time
from arduino.app_utils import App

# load custom modules
from db_manager import DBManager
from comm_manager import CommManager
from web_server import WebServer
from ai_manager import AIManager

print("Raw2Insight System Starting...")

# create instance of custom modules
db = DBManager()
comm = CommManager()
web = WebServer(db)
ai = AIManager()

# cycle count for debug
cycle_count = 0

def loop():
    global cycle_count
    cycle_count += 1
    print(f"\n--- [Main] Cycle #{cycle_count} Start ---")
    
    try:
        # read sensors list
        sensors = db.get_all_sensors()
        if not sensors:
            print("[DEBUG] [Main] 등록된 센서가 없습니다. 웹 대시보드에서 기기를 추가해주세요.")
            time.sleep(2)
            return
            
        payload = {}
        
        for sensor in sensors:
            s_name = sensor['name']
            s_protocol = sensor['protocol']
            s_pin = sensor['pin']

            # read sensor data
            sensor_val = comm.read_sensor_dynamic(s_protocol, s_pin)

            if sensor_val is not None:
                # store in DB
                db.insert_data(sensor_val, s_name)

            # load aggregated data
            formatted_rows, values_only = db.get_aggregated_data(sensor_name=s_name, limit=20)
    
            # check anomaly
            is_anomaly = ai.detect(s_name, values_only)
            
            # carrying in payload
            payload[s_name] = {
                'rows': formatted_rows,
                'alert': is_anomaly
            }
            
        web.broadcast_multi_data(payload)
        
        print(f"--- [Main] Cycle #{cycle_count} Completed ---")
        
    except Exception as e:
        print(f"[ERROR] [Main] Error occur in main loop : {e}")
        
    time.sleep(1)

# run application
print("[DEBUG] [Main] Handing over execution to App.run()...")
App.run(user_loop=loop)