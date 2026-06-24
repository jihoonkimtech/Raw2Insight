from arduino.app_utils import App, Bridge
import time

print("data communication test is start...")

while True:
    try:
        # call function
        sensor_value = Bridge.call("get_sensor_data")
        
        print(f"received : {sensor_value}")
        
    except Exception as e:
        print(f"error occur : {e}")
        
    time.sleep(0.5)