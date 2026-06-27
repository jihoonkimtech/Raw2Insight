"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : main.py
Purpose      : Main orchestrator coordinating DB, Comm, and Web
===================================================================
"""
import time
import psutil
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
        actuators = db.get_all_actuators()
        
        if not sensors:
            print("[DEBUG] [Main] 등록된 센서가 없습니다. 웹 대시보드에서 기기를 추가해주세요.")
            time.sleep(2)
            return
            
        payload = {}
        
        for sensor in sensors:
            s_name = sensor['name']
            s_protocol = sensor['protocol']
            s_pin = sensor['pin']
            s_type = sensor.get('data_type', 'Data')
            s_unit = sensor.get('unit', '')
            s_sens = sensor.get('sensitivity', 0.1)

            # read sensor data
            sensor_val = comm.read_sensor_dynamic(s_protocol, s_pin)

            if sensor_val is not None:
                # store in DB
                db.insert_data(sensor_val, s_name)

            # load raw data
            raw_rows = db.get_raw_data(sensor_name=s_name, limit=20)

            # digital is not require MA
            if s_protocol == 'digital':
                formatted_rows = raw_rows
                values_only = [r[1] for r in raw_rows] if raw_rows else []
            else:
                # load aggregated data
                formatted_rows, values_only = db.get_aggregated_data(sensor_name=s_name, limit=20)
    
            
            is_anomaly, direction, score = ai.detect(s_name, values_only, s_protocol, s_sens)

            linked_acts_info = []
            for act in actuators:
                if act['linked_sensor_id'] == sensor['id']:
                    
                    target_val = 0 # default is off(0)

                    if is_anomaly:
                        # if anomaly case cause by data increase
                        #if direction == "HIGH":
                        if 1:
                            # actuator type is pwm
                            if act['control_type'] == 'pwm':
                                # change Score to PWM
                                max_severity = 0.5
                                intensity = min(1.0, abs(score) / max_severity)

                                target_val = int(act['trigger_logic'] * intensity)
                                
                                # lower bound of active actuator
                                if target_val < 100: 
                                    target_val = 100

                                print(f"[DEBUG] PWM Proportional: Score({score:.3f}) -> Intensity({intensity*100:.1f}%) -> Output({target_val})")                
                            # actuator type is digital
                            else:
                                target_val = act['trigger_logic'] 
                        
                    # target_val send to MCU
                    comm.set_actuator_dynamic(act['control_type'], act['pin'], target_val)
                    
                    linked_acts_info.append({
                        'name': act['name'],
                        'active': is_anomaly,
                        'pwm_val': target_val # for debug
                    })
            
            # carrying in payload
            payload[s_name] = {
                'rows': formatted_rows,
                'raw_rows': raw_rows,
                'alert': is_anomaly,
                'data_type': s_type,
                'unit': s_unit,
                'protocol': s_protocol,
                'actuators': linked_acts_info,
                'score': score
            }

        # for device monitoring
        try:
            payload['__sys_health__'] = {
                'cpu': psutil.cpu_percent(interval=None),
                'ram': psutil.virtual_memory().percent
            }
        except Exception as e:
            print(f"[ERROR] [Main] Failed to get system health: {e}")
            
        web.broadcast_multi_data(payload)
        
        print(f"--- [Main] Cycle #{cycle_count} Completed ---")
        
    except Exception as e:
        print(f"[ERROR] [Main] Error occur in main loop : {e}")
        
    time.sleep(1)

# run application
print("[DEBUG] [Main] Handing over execution to App.run()...")
App.run(user_loop=loop)