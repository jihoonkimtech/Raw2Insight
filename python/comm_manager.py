"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : comm_manager.py
Purpose      : Handle RPC communication with MCU via Bridge
===================================================================
"""
from arduino.app_utils import Bridge

class CommManager:
    def __init__(self):
        print("[DEBUG] [CommManager] Connecting to Arduino Router Bridge...")

    def read_sensor(self):
        # request sensor data from MCU
        print("[DEBUG] [CommManager] Calling MCU functions for read sensor data...")
        return Bridge.call("read_sensor")

    def send_control(self, param):
        # send control command to MCU
        Bridge.call("set_cooler", param)
from arduino.app_utils import Bridge

class CommManager:
    def __init__(self):
        pass # init process

    def read_sensor(self):
        # call procedure for read sensor data
        return Bridge.call("get_sensor_data")

    def send_control(self, param):
        # send control commands to the MCU 
        print(f"[DEBUG] [CommManager] Sending control command to MCU (param: {param})...")
        Bridge.call("set_cooler", param)