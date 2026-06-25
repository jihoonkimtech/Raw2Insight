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
        
    def read_sensor_dynamic(self, protocol, pin_or_addr):
        try:
            if protocol == 'analog':
                pin_num = int(pin_or_addr.upper().replace('A', ''))
                print(f"[DEBUG] [CommManager] Call function via Bridge : read_analog({pin_num})")
                return Bridge.call("read_analog", pin_num)
                
            elif protocol == 'digital':
                pin_num = int(pin_or_addr)
                print(f"[DEBUG] [CommManager] Call function via Bridge : read_digital({pin_num})")
                return Bridge.call("read_digital", pin_num)
                
            elif protocol == 'i2c':
                # I2C addr is string
                print(f"[DEBUG] [CommManager] Call function via Bridge : read_i2c({pin_or_addr})")
                return Bridge.call("read_i2c", pin_or_addr)
                
            else:
                print(f"[ERROR] [CommManager] 알 수 없는 프로토콜: {protocol}")
                return 0
                
        except Exception as e:
            print(f"[ERROR] [CommManager] 통신 실패 ({protocol} - {pin_or_addr}): {e}")
            return 0

    def send_control(self, param):
        # send control commands to the MCU 
        print(f"[DEBUG] [CommManager] Sending control command to MCU (param: {param})...")
        Bridge.call("set_cooler", param)