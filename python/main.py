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
import json
import urllib.request
import threading # added for non-blocking webhook operations
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

sensor_prev_states = {}
sensor_prev_manual = {} # added for hysteresis tracking
actuator_mem = {}
web.actuator_mem = actuator_mem

# persistent variable for last known fine i2c data
i2c_last_known_good = {}

# cycle count for debug
cycle_count = 0

# added background thread helper for webhook to prevent main loop blocking
def fire_webhook_async(url, payload_json, mem, messenger):
    def task():
        try:
            req = urllib.request.Request(
                url, data=payload_json, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
            )
            urllib.request.urlopen(req, timeout=2.0)
            mem['status_text'] = f"✅ {messenger.upper()} 전송 완료"
        except Exception as e:
            mem['status_text'] = f"❌ 전송 실패"
            print(f"[ERROR] [Webhook] failed: {e}")
            
    t = threading.Thread(target=task)
    t.daemon = True
    t.start()

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
                # check driver
                profile_instance = I2C_PROFILES.get(s_profile)
                if profile_info := profile_instance:
                    if s_pin not in i2c_cache:
                        print(f"[DEBUG] [Main] Can't find cache of {s_pin} sensor. Read start")
                        raw_bytes = comm.read_sensor_dynamic('i2c', s_pin, read_bytes=profile_info.read_bytes)
                        parsed_data = profile_info.parse(raw_bytes)
                        
                        if parsed_data:
                            # physical read success: update current cache and persistent fallback
                            i2c_cache[s_pin] = parsed_data
                            i2c_last_known_good[s_pin] = parsed_data
                        else:
                            # physical read failed: use last known good value (fallback)
                            print(f"[WARN] [Main] I2C read failed for {s_pin}. Using fallback data.")
                            i2c_cache[s_pin] = i2c_last_known_good.get(s_pin, {})
                    
                    # extract 'data_key' value from cache (which now has fresh or fallback data)
                    parsed_dict = i2c_cache[s_pin]
                    if parsed_dict and s_data_key in parsed_dict:
                        calibrated_value = parsed_dict[s_data_key]
                    else:
                        print(f"[ERROR] [Main] Can't find {s_data_key} KEY!")
                           
                else:
                    print(f"[DEBUG] [Main] Call debug i2c function!")
                    calibrated_value = comm.read_sensor_dynamic('i2c', s_pin)

                
            # store in DB
            db.insert_data(calibrated_value, s_name)

            # load data (improved: fetch more for AI context, UI gets sliced later)
            formatted_rows, values_only = db.get_aggregated_data(s_name, limit=300)
            raw_rows = db.get_raw_data(s_name, limit=60)

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

                # rule-base decision with hysteresis logic applied
                margin = 1.5 
                
                if s_name not in sensor_prev_manual:
                    sensor_prev_manual[s_name] = {"HIGH": False, "LOW": False}

                if s_thresh_high is not None:
                    if calibrated_value > s_thresh_high:
                        sensor_prev_manual[s_name]["HIGH"] = True
                        is_anomaly, is_manual_anomaly, direction = True, True, "HIGH"
                    elif sensor_prev_manual[s_name]["HIGH"] and calibrated_value > (s_thresh_high - margin):
                        is_anomaly, is_manual_anomaly, direction = True, True, "HIGH"
                    else:
                        sensor_prev_manual[s_name]["HIGH"] = False

                if not is_manual_anomaly and s_thresh_low is not None:
                    if calibrated_value < s_thresh_low:
                        sensor_prev_manual[s_name]["LOW"] = True
                        is_anomaly, is_manual_anomaly, direction = True, True, "LOW"
                    elif sensor_prev_manual[s_name]["LOW"] and calibrated_value < (s_thresh_low + margin):
                        is_anomaly, is_manual_anomaly, direction = True, True, "LOW"
                    else:
                        sensor_prev_manual[s_name]["LOW"] = False

                # recalculate manual intensity based on active direction
                if is_manual_anomaly:
                    if direction == "HIGH":
                        gap = calibrated_value - s_thresh_high
                        max_gap = s_thresh_high * 0.2 if s_thresh_high != 0 else 10.0
                        manual_intensity = min(1.0, gap / max_gap) if max_gap > 0 else 1.0
                    elif direction == "LOW":
                        gap = s_thresh_low - calibrated_value
                        max_gap = s_thresh_low * 0.2 if s_thresh_low != 0 else 10.0
                        manual_intensity = min(1.0, gap / max_gap) if max_gap > 0 else 1.0

            just_triggered = False
            if s_name not in sensor_prev_states:
                sensor_prev_states[s_name] = False
                
            if is_anomaly and not sensor_prev_states[s_name]:
                just_triggered = True
                
            sensor_prev_states[s_name] = is_anomaly

            linked_acts_info = []
            for act in actuators:
                if act['linked_sensor_id'] == sensor['id']:
                    act_type = act.get('control_type', '')
                    act_id = str(act['id'])
                    
                    # parse extra params
                    extra = json.loads(act.get('extra_params', '{}'))
                    
                    # init actuator memory
                    if act_id not in actuator_mem:
                        actuator_mem[act_id] = {'timer_start': 0, 'latched': False, 'count': 0, 'status_text': '', 'prev_active': False}
                        
                    mem = actuator_mem[act_id]

                    # check delay and latch condition
                    delay_sec = extra.get('delay', 0)
                    use_latch = extra.get('latch', False)
                    condition_met = False
                    
                    if is_anomaly:
                        # check direction of anomaly
                        act_dir = act.get('trigger_dir', 'BOTH')
                        if (direction == "HIGH" and act_dir in ["HIGH", "BOTH"]) or \
                           (direction == "LOW" and act_dir in ["LOW", "BOTH"]):
                            
                            # check timer
                            if delay_sec > 0:
                                if mem['timer_start'] == 0:
                                    mem['timer_start'] = time.time()
                                if (time.time() - mem['timer_start']) >= delay_sec:
                                    condition_met = True
                            else:
                                condition_met = True
                    else:
                        # reset timer
                        mem['timer_start'] = 0
                        
                    if condition_met and use_latch:
                        mem['latched'] = True
                        
                    # final active state
                    final_active = condition_met or mem['latched']
                    
                    # check edge trigger
                    act_just_triggered = (final_active and not mem['prev_active'])
                    mem['prev_active'] = final_active

                    if act_type.startswith('virtual_'):
                        # counter
                        if act_type == 'virtual_counter':
                            if act_just_triggered:
                                mem['count'] += 1
                            mem['status_text'] = f"누적 {mem['count']}회 감지"
                            
                        # webhook
                        elif act_type == 'virtual_webhook':
                            if act_just_triggered:
                                url = extra.get('url', '')
                                messenger = extra.get('messenger', 'discord')
                                if url:
                                    msg = f"🚨 **[Raw2Insight 엣지 알림]**\n`{s_name}` 센서 이상 패턴 감지!"
                                    
                                    if messenger == 'discord':
                                        payload_json = json.dumps({"content": msg}).encode('utf-8')
                                    elif messenger == 'slack':
                                        payload_json = json.dumps({"text": msg}).encode('utf-8')
                                    else:
                                        payload_json = json.dumps({"message": msg}).encode('utf-8')
                                        
                                    # send via background thread
                                    mem['status_text'] = f"⏳ {messenger.upper()} 전송 중..."
                                    fire_webhook_async(url, payload_json, mem, messenger)
                                        
                            if not final_active and '전송 완료' not in mem['status_text']:
                                mem['status_text'] = "✔️ 대기중"

                        # timer or latch status
                        elif act_type == 'virtual_timer' or act_type == 'virtual_latch':
                            if final_active:
                                mem['status_text'] = "🚨 위험 상태 감지됨!"
                            else:
                                elapsed = int(time.time() - mem['timer_start']) if mem['timer_start'] > 0 else 0
                                mem['status_text'] = f"⏳ {elapsed}초 경과... (대기)" if mem['timer_start'] > 0 else "✔️ 정상 대기중"

                        disp_text = mem['status_text'] if not mem['latched'] else f"🧲 래치됨! ({mem['status_text']})"

                        # virtual device payload
                        linked_acts_info.append({
                            'id': act['id'],
                            'name': act['name'],
                            'active': final_active,
                            'control_type': act_type,
                            'val': disp_text,
                            'is_virtual': True
                        })
                        continue

                    target_val = act.get('normal_val', 0)
                    
                    if final_active:
                        base_target = act['high_val'] if direction == "HIGH" else act['low_val']
                        
                        # calc output value
                        if act_type == 'pwm' and is_anomaly:
                            max_severity = 0.5
                            intensity = manual_intensity if is_manual_anomaly else min(1.0, abs(score) / max_severity)
                            
                            # normal to base_target
                            val_diff = base_target - act['normal_val']
                            target_val = act['normal_val'] + int(val_diff * intensity)
                            
                            # clamping to protect hardware limits
                            target_val = max(0, min(255, target_val))
                        else:
                            # case of digital device
                            target_val = base_target
                            
                    # target_val send to MCU
                    comm.set_actuator_dynamic(act['control_type'], act['pin'], target_val)
                    
                    linked_acts_info.append({
                        'id': act['id'],
                        'name': act['name'],
                        'active': final_active,
                        'control_type': act_type,
                        'pwm_val': target_val,
                        'latched': mem['latched']
                    })
            
            # carrying in payload
            payload[s_name] = {
                'rows': formatted_rows[:60],  # sliced to 60 for frontend performance
                'raw_rows': raw_rows,         
                'alert': is_anomaly,
                'data_type': s_type,
                'unit': s_unit,
                'protocol': s_protocol,
                'actuators': linked_acts_info,
                'score': float(score),        # serialized as float for JSON
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