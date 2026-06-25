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
web = WebServer()
ai = AIManager()

# cycle count for debug
cycle_count = 0

def loop():
    global cycle_count
    cycle_count += 1
    print(f"\n--- [Main] Cycle #{cycle_count} Start ---")
    
    try:
        # receive sensor data using communication manager
        sensor_val = comm.read_sensor()

        # store data using DB manager
        db.insert_data(sensor_val)

        # fetch aggregated data (2s mean) for AI
        formatted_rows, values_only = db.get_aggregated_data(limit=20)
        
        # load 5 latest datas from DB
        #latest_rows = db.get_latest_data()
        
        # refresh dashboard using latest rows with Web Server Manager
        #web.broadcast_table(latest_rows)

        # run anomaly detection
        is_anomaly = False
        if len(values_only) >= 15:
            is_anomaly = ai.detect(values_only)
            
        # broadcast to frontend
        web.broadcast_data(formatted_rows, is_anomaly)
        
        print(f"--- [Main] Cycle #{cycle_count} Completed ---")
        
    except Exception as e:
        print(f"[ERROR] [Main] Error occur in main loop : {e}")
        
    time.sleep(1)

# run application
print("[DEBUG] [Main] Handing over execution to App.run()...")
App.run(user_loop=loop)