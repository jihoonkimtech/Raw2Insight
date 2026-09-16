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
        
    def read_sensor_dynamic(self, protocol, pin_or_addr, read_bytes=0, register=None):
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
                if read_bytes > 0 and register is not None:
                    # Register-mapped read (pointer write + read)
                    print(f"[DEBUG] [CommManager] Call function via Bridge : read_i2c_reg({pin_or_addr}, {hex(register)}, {read_bytes})")
                    byte_str = Bridge.call("read_i2c_reg", pin_or_addr, int(register), read_bytes)
                    if byte_str:
                        return [int(x) for x in str(byte_str).split(",") if x.strip()]
                    return []
                elif read_bytes > 0:
                    print(f"[DEBUG] [CommManager] Call function via Bridge : read_i2c_bytes({pin_or_addr}, {read_bytes})")
                    byte_str = Bridge.call("read_i2c_bytes", pin_or_addr, read_bytes)
                    if byte_str:
                        return [int(x) for x in str(byte_str).split(",") if x.strip()]
                    return []
                # for debug
                else:
                    print(f"[DEBUG] [CommManager] Call function via Bridge : read_i2c({pin_or_addr})")
                    return Bridge.call("read_i2c", pin_or_addr)
                
            elif protocol == 'dht':
                # register carries the start signal length (ms) for the DHT family
                pin_num = int(pin_or_addr)
                start_low_ms = int(register) if register is not None else 20
                print(f"[DEBUG] [CommManager] Call function via Bridge : read_dht_bytes({pin_num}, {start_low_ms})")
                byte_str = Bridge.call("read_dht_bytes", pin_num, start_low_ms)
                if byte_str:
                    return [int(x) for x in str(byte_str).split(",") if x.strip()]
                return []

            else:
                print(f"[ERROR] [CommManager] Unknown Protocol: {protocol}")
                return 0
                
        except Exception as e:
            print(f"[ERROR] [CommManager] Communication Fail ({protocol} - {pin_or_addr}): {e}")
            return [] if protocol == 'dht' or (protocol == 'i2c' and read_bytes > 0) else 0
    
    def write_i2c_bytes(self, addr, data_bytes):
        # Send raw bytes to an I2C device, returns True on ACK
        try:
            csv_bytes = ",".join(str(int(b) & 0xFF) for b in data_bytes)
            print(f"[DEBUG] [CommManager] Call function via Bridge : write_i2c_bytes({addr}, {csv_bytes})")
            return bool(Bridge.call("write_i2c_bytes", addr, csv_bytes))
        except Exception as e:
            print(f"[ERROR] [CommManager] I2C write Fail ({addr}): {e}")
            return False

    def set_actuator_dynamic(self, control_type, pin, value):
        try:
            pin_num = int(pin)
            value = int(value)
            print(f"[DEBUG] [CommManager] Actuator control ({control_type} - {pin}) [{value}]")
            if control_type == 'digital_out':
                result = Bridge.call("write_digital", pin_num, value)
            elif control_type == 'pwm':
                result = Bridge.call("write_pwm", pin_num, value)
            else:
                print(f"[ERROR] [CommManager] Unknown actuator type: {control_type}")
                return 0
            # MCU returns 0 when the pin is not valid for the requested type
            if not result:
                print(f"[WARN] [CommManager] MCU rejected actuator write ({control_type} - {pin})")
            return result
        except Exception as e:
            print(f"[ERROR] [CommManager] Actuator control Fail ({control_type} - {pin}): {e}")
            return 0
