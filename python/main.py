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

print("Raw2Insight System Starting...")

# create instance of custom modules
db = DBManager()
comm = CommManager()
web = WebServer()

def loop():
    try:
        # receive sensor data using communication manager
        sensor_val = comm.read_sensor()
        
        # store data using DB manager
        db.insert_data(sensor_val)
        
        # load 5 latest datas from DB
        latest_rows = db.get_latest_data()
        
        # refresh dashboard using latest rows with Web Server Manager
        web.broadcast_table(latest_rows)
        
        print(f"[Main] Processing Complete | Sensor: {sensor_val}")
        
    except Exception as e:
        print(f"Error occur in main loop : {e}")
        
    time.sleep(1)

# run application
App.run(user_loop=loop)