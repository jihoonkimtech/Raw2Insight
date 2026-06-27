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
            s_multiplier = sensor.get('multiplier', 1.0)
            s_offset = sensor.get('offset', 0.0)

            # read sensor data
            sensor_val = comm.read_sensor_dynamic(s_protocol, s_pin)

            if sensor_val is not None:
                if s_protocol == 'analog':
                    sensor_val = int((sensor_val * s_multiplier) + s_offset)
                
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

            s_thresh_low = sensor.get('threshold_low')
            s_thresh_high = sensor.get('threshold_high')
            latest_val = values_only[0] if values_only else (raw_rows[0][1] if raw_rows else None)

            manual_intensity = 0.0
            is_manual_anomaly = False
            

            if s_protocol == 'digital':
                trigger_val = s_thresh_high if s_thresh_high is not None else 1
                if latest_val is not None:
                    is_anomaly = (latest_val == trigger_val)
                else:
                    is_anomaly = False
                
                direction = "HIGH" if trigger_val == 1 else "LOW" 
                score = -1.0 if is_anomaly else 1.0
            else:
                is_anomaly, direction, score = ai.detect(s_name, values_only, s_protocol, s_sens)

                if latest_val is not None:
                    if s_thresh_high is not None and latest_val > s_thresh_high:
                        is_anomaly, is_manual_anomaly, direction = True, True, "HIGH"
                        gap = latest_val - s_thresh_high
                        max_gap = s_thresh_high * 0.2 if s_thresh_high != 0 else 10.0
                        manual_intensity = min(1.0, gap / max_gap) if max_gap > 0 else 1.0
                        
                    elif s_thresh_low is not None and latest_val < s_thresh_low:
                        is_anomaly, is_manual_anomaly, direction = True, True, "LOW"
                        gap = s_thresh_low - latest_val
                        max_gap = s_thresh_low * 0.2 if s_thresh_low != 0 else 10.0
                        manual_intensity = min(1.0, gap / max_gap) if max_gap > 0 else 1.0

            linked_acts_info = []
            for act in actuators:
                if act['linked_sensor_id'] == sensor['id']:
                    target_val = act.get('normal_val', 0)
                    act_dir = act.get('trigger_dir', 'BOTH')
                    is_active = False

                    if is_anomaly:
                        # check direction of anomaly
                        if (direction == "HIGH" and act_dir in ["HIGH", "BOTH"]) or \
                           (direction == "LOW" and act_dir in ["LOW", "BOTH"]):
                            
                            is_active = True
                            base_target = act['high_val'] if direction == "HIGH" else act['low_val']

                            # calc output value
                            if act['control_type'] == 'pwm':
                                max_severity = 0.5
                                intensity = manual_intensity if is_manual_anomaly else min(1.0, abs(score) / 0.5)

                                # normal to base_target
                                val_diff = base_target - act['normal_val']
                                target_val = act['normal_val'] + int(val_diff * intensity)

                                print(f"[DEBUG] PWM Proportional: Intensity({intensity*100:.1f}%) -> Output({target_val})")
                            else:
                                # case of digital device
                                target_val = base_target
                        
                    # target_val send to MCU
                    comm.set_actuator_dynamic(act['control_type'], act['pin'], target_val)
                    
                    linked_acts_info.append({
                        'name': act['name'],
                        'active': is_active,
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
                'score': score,
                'threshold_low': s_thresh_low,
                'threshold_high': s_thresh_high
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