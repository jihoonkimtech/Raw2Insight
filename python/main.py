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
from logutil import dbg

# load custom modules
from db_manager import DBManager
from comm_manager import CommManager
from web_server import WebServer
from ai_manager import AIManager
from sensors import load_sensor_profiles
from history import SensorHistory
from config_preset import seed_if_empty

print("Raw2Insight System Starting...")

# create instance of custom modules
db = DBManager()
# a fresh /app/data starts from python/presets/default.json
if seed_if_empty(db):
    print("[INFO] [Main] Device configuration loaded from presets/default.json")
comm = CommManager()
web = WebServer(db)
ai = AIManager()
I2C_PROFILES = load_sensor_profiles() 
dbg(f"[DEBUG] [Main] Loaded I2C profiles: {list(I2C_PROFILES.keys())}")

sensor_prev_states = {}
sensor_prev_manual = {} # added for hysteresis tracking
actuator_mem = {}
web.actuator_mem = actuator_mem

# persistent variable for last known fine bus (i2c, dht) data, keyed by "protocol:pin"
bus_last_known_good = {}

# last physical read time per bus sensor, used for min_interval
bus_last_read_time = {}

# i2c addresses whose init sequence has been applied (addr -> profile name)
i2c_initialized = {}

# physical outputs written in the previous cycle: pin -> {'type', 'safe_val'}
driven_outputs = {}

# cycle count for debug
cycle_count = 0

# Target loop period in seconds (5Hz)
LOOP_PERIOD = 0.2
# Isolation Forest is re-evaluated at most this often per sensor
AI_EVAL_INTERVAL = 0.5

# in-memory history shared with the web server
history = SensorHistory()
web.history = history

# cached AI result per sensor: name -> (time, (is_anomaly, direction, score))
ai_cache = {}

# pending non-blocking I2C conversions: cache_key -> trigger time
bus_trigger_time = {}

# measured loop timing for the dashboard
loop_stats = {'hz': 0.0, 'cycle_ms': 0.0, 'last': None}

# rate-limited warnings: key -> last print time
_warn_times = {}

def warn_throttled(key, message, interval=10.0):
    # Print a repeating warning at most once per interval
    now = time.time()
    if now - _warn_times.get(key, 0) >= interval:
        _warn_times[key] = now
        print(message)

def to_int(value, default=0):
    # DB rows may carry numbers as strings or None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default

def overshoot_intensity(gap, threshold, other_threshold=None):
    # Map how far a value passed its threshold to 0..1 (full at 20% of the threshold magnitude)
    scale = abs(threshold) * 0.2
    if scale == 0 and other_threshold is not None:
        # threshold 0: fall back to 20% of the band width
        scale = abs(other_threshold - threshold) * 0.2
    if scale == 0:
        scale = 10.0
    return max(0.0, min(1.0, gap / scale))

def release_stale_outputs(current_outputs, actuators):
    # Drive outputs that no actuator controls anymore (deleted or orphaned) back to their normal value
    for pin, info in list(driven_outputs.items()):
        if pin in current_outputs:
            continue
        dbg(f"[DEBUG] [Main] Releasing stale output pin {pin} -> {info['safe_val']}")
        comm.set_actuator_dynamic(info['type'], pin, info['safe_val'])
        driven_outputs.pop(pin, None)
    driven_outputs.update(current_outputs)

    # Drop runtime memory of deleted actuators
    live_ids = {str(a['id']) for a in actuators}
    for act_id in list(actuator_mem.keys()):
        if act_id not in live_ids:
            actuator_mem.pop(act_id, None)

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

def ensure_i2c_init(addr, profile):
    # Run the driver init sequence once per address, returns False if the device did not ACK
    if not profile.init_sequence:
        return True
    if i2c_initialized.get(addr) == profile.profile_name:
        return True
    for cmd in profile.init_sequence:
        if not comm.write_i2c_bytes(addr, cmd):
            print(f"[WARN] [Main] I2C init failed for {addr} ({profile.profile_name})")
            return False
        if profile.init_delay > 0:
            time.sleep(profile.init_delay)
    i2c_initialized[addr] = profile.profile_name
    dbg(f"[DEBUG] [Main] I2C init done for {addr} ({profile.profile_name})")
    return True

def trigger_i2c_measurement(addr, profile):
    # Send the per-read trigger command, the caller reads after trigger_delay (non-blocking)
    for cmd in profile.trigger_sequence:
        if not comm.write_i2c_bytes(addr, cmd):
            warn_throttled(f"trig:{addr}", f"[WARN] [Main] I2C trigger failed for {addr} ({profile.profile_name})")
            return False
    return True

def read_bus_sensor(protocol, pin, profile, cache_key):
    # Read and parse one bus sensor, falling back to the last good data on failure
    last_good = bus_last_known_good.get(cache_key, {})
    now = time.time()

    # Conversion in progress: come back on a later cycle instead of sleeping
    pending = bus_trigger_time.get(cache_key)
    if pending is not None and now - pending < profile.trigger_delay:
        return last_good

    # Respect the minimum conversion interval of slow sensors
    if pending is None and last_good and (now - bus_last_read_time.get(cache_key, 0)) < profile.min_interval:
        return last_good

    parsed_data = None

    if protocol == 'i2c':
        if pending is None:
            if not ensure_i2c_init(pin, profile):
                bus_last_read_time[cache_key] = now
                return last_good
            if profile.trigger_sequence:
                if trigger_i2c_measurement(pin, profile):
                    bus_trigger_time[cache_key] = now
                else:
                    bus_last_read_time[cache_key] = now
                return last_good
        bus_trigger_time.pop(cache_key, None)
        bus_last_read_time[cache_key] = now
        dbg(f"[DEBUG] [Main] Reading {cache_key}")
        raw_bytes = comm.read_sensor_dynamic('i2c', pin, read_bytes=profile.read_bytes, register=profile.read_register)
        parsed_data = profile.parse(raw_bytes)
        if not parsed_data:
            # Force re-init next cycle in case the device was reset or re-plugged
            i2c_initialized.pop(pin, None)
    elif protocol == 'dht':
        bus_last_read_time[cache_key] = now
        raw_bytes = comm.read_sensor_dynamic('dht', pin, read_bytes=profile.read_bytes, register=getattr(profile, 'start_low_ms', 20))
        parsed_data = profile.parse(raw_bytes)

    if parsed_data:
        # physical read success: update persistent fallback
        bus_last_known_good[cache_key] = parsed_data
        return parsed_data

    # physical read failed: use last known good value (fallback)
    warn_throttled(f"read:{cache_key}", f"[WARN] [Main] {protocol.upper()} read failed for {pin}. Using fallback data.")
    return last_good

def loop():
    global cycle_count
    cycle_count += 1
    dbg(f"\n--- [Main] Cycle #{cycle_count} Start ---")
    
    cycle_start = time.time()
    try:
        # read sensors list (cached until a device changes)
        sensors, actuators = db.get_config_cached()
        
        if not sensors:
            dbg("[DEBUG] [Main] 등록된 센서가 없습니다. 웹 대시보드에서 기기를 추가해주세요.")
            # No sensor means no actuator is driven, release everything
            release_stale_outputs({}, actuators)
            history.prune(set())
            time.sleep(1)
            return
            
        payload = {}
        current_outputs = {}
        bus_cache = {}
        
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
            dbg(f"[DEBUG] [Main] Sensing start ({s_protocol}, {s_pin})")
            if s_protocol == 'analog':
                raw_value = comm.read_sensor_dynamic(s_protocol, s_pin)
                if raw_value is not None:
                    calibrated_value = (raw_value * s_multiplier) + s_offset
            elif s_protocol == 'digital':
                raw_value = comm.read_sensor_dynamic(s_protocol, s_pin)
                calibrated_value = raw_value
            elif s_protocol in ('i2c', 'dht'):
                # check driver (bus must match the protocol)
                profile_info = I2C_PROFILES.get(s_profile)
                if profile_info and profile_info.bus == s_protocol:
                    cache_key = f"{s_protocol}:{s_pin}"
                    if cache_key not in bus_cache:
                        bus_cache[cache_key] = read_bus_sensor(s_protocol, s_pin, profile_info, cache_key)

                    # extract 'data_key' value from cache (which now has fresh or fallback data)
                    parsed_dict = bus_cache[cache_key]
                    if parsed_dict and s_data_key in parsed_dict:
                        calibrated_value = parsed_dict[s_data_key]
                    elif parsed_dict:
                        warn_throttled(f"key:{s_name}", f"[ERROR] [Main] Can't find {s_data_key} KEY!")

                elif s_protocol == 'i2c':
                    dbg(f"[DEBUG] [Main] Call debug i2c function!")
                    calibrated_value = comm.read_sensor_dynamic('i2c', s_pin)
                else:
                    warn_throttled(f"drv:{s_name}", f"[ERROR] [Main] No {s_protocol} driver named {s_profile}")

            # seed AI history from DB once, so a restart keeps the learned baseline
            if not history.is_seeded(s_name):
                _, seed_values = db.get_aggregated_data(s_name, limit=300)
                history.seed(s_name, seed_values)

            # keep samples in memory, DB gets 1s averages after the loop
            now = time.time()
            smoothed = None
            if calibrated_value is not None:
                smoothed = history.add(s_name, calibrated_value, now)
            values_only = history.ai_values(s_name)

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
                # analog, i2c : do Isolation Forest (throttled, the model input moves in 2s steps)
                cached = ai_cache.get(s_name)
                if cached and now - cached[0] < AI_EVAL_INTERVAL:
                    is_anomaly, direction, score = cached[1]
                else:
                    is_anomaly, direction, score = ai.detect(s_name, values_only, s_protocol, s_sens)
                    ai_cache[s_name] = (now, (is_anomaly, direction, score))

                # rule-base decision with hysteresis logic applied
                margin = 1.5 
                
                if s_name not in sensor_prev_manual:
                    sensor_prev_manual[s_name] = {"HIGH": False, "LOW": False}

                # Skip threshold checks when no value is available yet (e.g. first bus read failed)
                if calibrated_value is None:
                    dbg(f"[DEBUG] [Main] No value for {s_name}, threshold check skipped")
                elif s_thresh_high is not None:
                    if calibrated_value > s_thresh_high:
                        sensor_prev_manual[s_name]["HIGH"] = True
                        is_anomaly, is_manual_anomaly, direction = True, True, "HIGH"
                    elif sensor_prev_manual[s_name]["HIGH"] and calibrated_value > (s_thresh_high - margin):
                        is_anomaly, is_manual_anomaly, direction = True, True, "HIGH"
                    else:
                        sensor_prev_manual[s_name]["HIGH"] = False

                if not is_manual_anomaly and calibrated_value is not None and s_thresh_low is not None:
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
                        manual_intensity = overshoot_intensity(gap, s_thresh_high, s_thresh_low)
                    elif direction == "LOW":
                        gap = s_thresh_low - calibrated_value
                        manual_intensity = overshoot_intensity(gap, s_thresh_low, s_thresh_high)

            just_triggered = False
            if s_name not in sensor_prev_states:
                sensor_prev_states[s_name] = False
                
            if is_anomaly and not sensor_prev_states[s_name]:
                just_triggered = True
                
            sensor_prev_states[s_name] = is_anomaly

            linked_acts_info = []
            for act in actuators:
                if str(act['linked_sensor_id']) == str(sensor['id']):
                    act_type = act.get('control_type', '')
                    act_id = str(act['id'])
                    
                    # parse extra params
                    extra = json.loads(act.get('extra_params', '{}'))
                    
                    # init actuator memory
                    if act_id not in actuator_mem:
                        actuator_mem[act_id] = {'timer_start': 0, 'latched': False, 'count': 0, 'status_text': '', 'prev_active': False, 'last_dir': 'HIGH'}
                        
                    mem = actuator_mem[act_id]

                    # check delay and latch condition
                    delay_sec = to_int(extra.get('delay', 0), 0)
                    # the timer's own duration field is its delay when no delay is given
                    if act_type == 'virtual_timer' and delay_sec <= 0:
                        delay_sec = to_int(extra.get('duration', 0), 0)
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

                    normal_val = to_int(act.get('normal_val'), 0)
                    high_val = to_int(act.get('high_val'), 0)
                    low_val = to_int(act.get('low_val'), 0)
                    target_val = normal_val

                    # Remember the direction that activated the output (latched/delayed states report NORMAL)
                    if is_anomaly and direction in ("HIGH", "LOW"):
                        mem['last_dir'] = direction
                    active_dir = direction if direction in ("HIGH", "LOW") else mem.get('last_dir', 'HIGH')
                    
                    if final_active:
                        base_target = high_val if active_dir == "HIGH" else low_val
                        
                        # calc output value
                        if act_type == 'pwm' and is_anomaly:
                            max_severity = 0.5
                            intensity = manual_intensity if is_manual_anomaly else min(1.0, abs(score) / max_severity)
                            
                            # normal to base_target
                            val_diff = base_target - normal_val
                            target_val = normal_val + int(val_diff * intensity)
                            
                            # clamping to protect hardware limits
                            target_val = max(0, min(255, target_val))
                        else:
                            # case of digital device
                            target_val = base_target
                            
                    # target_val send to MCU
                    target_val = int(target_val)
                    comm.set_actuator_dynamic(act_type, act['pin'], target_val)
                    current_outputs[str(act['pin'])] = {'type': act_type, 'safe_val': normal_val}
                    
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
                # only the newest point, the client keeps its own history (see dashboard_snapshot)
                'point': [int(now * 1000), round(float(calibrated_value), 3), round(float(smoothed), 3)] if calibrated_value is not None else None,
                'value': round(float(calibrated_value), 3) if calibrated_value is not None else None,
                'alert': is_anomaly,
                'direction': direction,
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
                'ram': psutil.virtual_memory().percent,
                'hz': round(loop_stats['hz'], 1),
                'cycle_ms': round(loop_stats['cycle_ms'], 1),
                'ts': int(time.time() * 1000)
            }
        except Exception as e:
            print(f"[ERROR] [Main] Failed to get system health: {e}")
            
        # turn off outputs of deleted or unlinked actuators
        release_stale_outputs(current_outputs, actuators)

        # write 1s averages to InfluxDB and drop history of deleted sensors
        for name, mean_val in history.pop_db_writes().items():
            try:
                db.insert_data(mean_val, name)
            except Exception as e:
                warn_throttled(f"db:{name}", f"[ERROR] [Main] DB write failed for {name}: {e}")
        history.prune({s['name'] for s in sensors})
        web.latest_meta = {k: {kk: vv for kk, vv in v.items() if kk not in ('point', 'value')} for k, v in payload.items() if k != '__sys_health__'}

        web.broadcast_multi_data(payload)
        
        dbg(f"--- [Main] Cycle #{cycle_count} Completed ---")
        
    except Exception as e:
        print(f"[ERROR] [Main] Error occur in main loop : {e}")

    # pace the loop to LOOP_PERIOD and track the real rate
    elapsed = time.time() - cycle_start
    if elapsed < LOOP_PERIOD:
        time.sleep(LOOP_PERIOD - elapsed)
    end = time.time()
    if loop_stats['last'] is not None:
        period = end - loop_stats['last']
        rate = 1.0 / period if period > 0 else 0.0
        loop_stats['hz'] = rate if loop_stats['hz'] == 0 else 0.8 * loop_stats['hz'] + 0.2 * rate
    loop_stats['last'] = end
    loop_stats['cycle_ms'] = 0.8 * loop_stats['cycle_ms'] + 0.2 * (elapsed * 1000.0)

# run application
dbg("[DEBUG] [Main] Handing over execution to App.run()...")
App.run(user_loop=loop)