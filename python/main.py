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
from sensors import load_sensor_profiles

print("Raw2Insight System Starting...")

# create instance of custom modules
db = DBManager()
comm = CommManager()
web = WebServer(db)
ai = AIManager()
I2C_PROFILES = load_sensor_profiles() 
print(f"[DEBUG] [Main] Loaded I2C profiles: {list(I2C_PROFILES.keys())}")

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
        i2c_cache = {}
        
        for sensor in sensors:
            s_name = sensor['name']
            s_protocol = sensor['protocol']
            s_pin = sensor['pin']
            s_type = sensor.get('data_type', 'Data')
            s_unit = sensor.get('unit', '')
            s_sens = sensor.get('sensitivity', 0.1)
            s_multiplier = sensor.get('multiplier', 1.0)
            s_offset = sensor.get('offset', 0.0)
            s_thresh_low = sensor.get('threshold_low')
            s_thresh_high = sensor.get('threshold_high')
            s_profile = sensor.get('profile_name')
            s_data_key = sensor.get('data_key')

            calibrated_value = None

            # read sensor data
            print(f"[DEBUG] [Main] Sensing start ({s_protocol}, {s_pin})")
            if s_protocol == 'analog':
                raw_value = comm.read_sensor_dynamic(s_protocol, s_pin)
                if raw_value is not None:
                    calibrated_value = (raw_value * s_multiplier) + s_offset
            elif s_protocol == 'digital':
                raw_value = comm.read_sensor_dynamic(s_protocol, s_pin)
                calibrated_value = raw_value
            elif s_protocol == 'i2c': 
                # check drive
                profile_instance = I2C_PROFILES.get(s_profile)
                if profile_info := profile_instance:
                    # if there is not cache? req read_bytes
                    if s_pin not in i2c_cache:
                        print(f"[DEBUG] [Main] Can't find cache of {s_pin} sensor. Read start")
                        raw_bytes = comm.read_sensor_dynamic('i2c', s_pin, read_bytes=profile_info.read_bytes)
                        i2c_cache[s_pin] = profile_info.parse(raw_bytes)
                    
                    # extract 'data_key' value
                    parsed_dict = i2c_cache[s_pin]
                    if parsed_dict and s_data_key in parsed_dict:
                        calibrated_value = parsed_dict[s_data_key]
                    else:
                        print(f"[ERROR] [Main] Can't find {s_data_key} KEY!")
                           
                else:
                    # for debug
                    print(f"[DEBUG] [Main] Call debug i2c functionY!")
                    calibrated_value = comm.read_sensor_dynamic('i2c', s_pin)

                
            # store in DB
            db.insert_data(calibrated_value, s_name)

            # load data
            formatted_rows, values_only = db.get_aggregated_data(s_name)
            raw_rows = db.get_raw_data(s_name)

            # anomaly decision
            manual_intensity = 0.0
            is_manual_anomaly = False
            is_anomaly = False
            direction = "NORMAL"
            score = 0.0

            if s_protocol == 'digital':
                # digital sensor is not require anomaly check
                trigger_val = s_thresh_high if s_thresh_high is not None else 1
                is_anomaly = (calibrated_value == trigger_val)
                direction = "HIGH" if trigger_val == 1 else "LOW"
                score = -1.0 if is_anomaly else 1.0
            else:
                # analog, i2c : do Isolation Forest
                is_anomaly, direction, score = ai.detect(s_name, values_only, s_protocol, s_sens)

                if s_thresh_high is not None and calibrated_value > s_thresh_high:
                    is_anomaly, is_manual_anomaly, direction = True, True, "HIGH"
                    gap = calibrated_value - s_thresh_high
                    max_gap = s_thresh_high * 0.2 if s_thresh_high != 0 else 10.0
                    manual_intensity = min(1.0, gap / max_gap) if max_gap > 0 else 1.0
                    
                elif s_thresh_low is not None and calibrated_value < s_thresh_low:
                    is_anomaly, is_manual_anomaly, direction = True, True, "LOW"
                    gap = s_thresh_low - calibrated_value
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