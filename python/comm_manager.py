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
        
    def read_sensor_dynamic(self, protocol, pin_or_addr, read_bytes=0):
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
                if read_bytes > 0:
                    print(f"[DEBUG] [CommManager] Call function via Bridge : read_i2c_bytes({pin_or_addr}, {read_bytes})")
                    byte_str = Bridge.call("read_i2c_bytes", pin_or_addr, read_bytes)
                    if byte_str:
                        return [int(x) for x in str(byte_str).split(",") if x.strip()]
                    return []
                # for debug
                else:
                    print(f"[DEBUG] [CommManager] Call function via Bridge : read_i2c({pin_or_addr})")
                    return Bridge.call("read_i2c", pin_or_addr)
                
            else:
                print(f"[ERROR] [CommManager] Unknown Protocol: {protocol}")
                return 0
                
        except Exception as e:
            print(f"[ERROR] [CommManager] Communication Fail ({protocol} - {pin_or_addr}): {e}")
            return [] if protocol == 'i2c' and read_bytes > 0 else 0
    
    def set_actuator_dynamic(self, control_type, pin, value):
        try:
            pin_num = int(pin)
            print(f"[ERROR] [CommManager] Actuator control ({control_type} - {pin}) [{value}]")
            if control_type == 'digital_out':
                return Bridge.call("write_digital", pin_num, value)
            elif control_type == 'pwm':
                return Bridge.call("write_pwm", pin_num, value)
        except Exception as e:
            print(f"[ERROR] [CommManager] Actuator control Fail ({control_type} - {pin}): {e}")