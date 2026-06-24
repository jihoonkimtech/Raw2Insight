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
        pass

    def read_sensor(self):
        # request sensor data from MCU
        return Bridge.call("read_sensor")

    def send_control(self, speed):
        # send control command to MCU
        Bridge.call("set_cooler", speed)
from arduino.app_utils import Bridge

class CommManager:
    def __init__(self):
        pass # init process

    def read_sensor(self):
        # call procedure for read sensor data
        return Bridge.call("get_sensor_data")

    def send_control(self, speed):
        # send control commands to the MCU 
        Bridge.call("set_cooler", speed)