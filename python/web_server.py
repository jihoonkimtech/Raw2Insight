"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : web_server.py
Purpose      : Manage WebUI and broadcast data to frontend
===================================================================
"""
import json
from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI
from sensors import load_sensor_profiles
import config_preset
from logutil import dbg

I2C_PROFILES = load_sensor_profiles()

class WebServer:
    def __init__(self, db_manager):
        # init web server instance
        dbg("[DEBUG] [WebServer] Initializing WebUI module...")
        self.ui = WebUI()
        self.db = db_manager
        self.actuator_mem = None
        # set by main: in-memory history and the latest per-sensor status
        self.history = None
        self.latest_meta = {}

        # register event handlers for incoming messages from frontend
        self.ui.on_message('client_ready', self.on_client_ready)
        self.ui.on_message('request_update', self.on_request_update)
        self.ui.on_message('request_snapshot', self.on_request_snapshot)
        self.ui.on_message('request_device_list', self.on_request_device_list)
        self.ui.on_message('add_sensor_request', self.on_add_sensor)
        self.ui.on_message('add_actuator_request', self.on_add_actuator)
        self.ui.on_message('update_sensor_request', self.on_update_sensor)
        self.ui.on_message('update_actuator_request', self.on_update_actuator)
        self.ui.on_message('export_config_request', self.on_export_config)
        self.ui.on_message('list_presets_request', self.on_list_presets)
        self.ui.on_message('apply_preset_request', self.on_apply_preset)
        self.ui.on_message('delete_device_request', self.on_delete_device)
        self.ui.on_message('change_sensitivity', self.on_change_sensitivity)
        self.ui.on_message('request_i2c_profiles', self.on_request_i2c_profiles)
        self.ui.on_message('reset_virtual', self.on_reset_virtual)
        dbg("[DEBUG] [WebServer] WebUI successfully started. Listening on port 7000.")

    def on_request_i2c_profiles(self, sid, data):
        profiles_data = {}
        for name, inst in I2C_PROFILES.items():
            profiles_data[name] = {
                "bus": inst.bus,
                "default_addr": inst.default_addr,
                "outputs": inst.outputs
            }
        self.ui.send_message('update_i2c_profiles', profiles_data)

    def on_add_sensor(self, sid, data):
        dbg(f"[DEBUG] [WebServer] Received Sensor Config: {data}")
        self.db.add_sensor(
            data['name'], 
            data['protocol'], 
            data['pin'], 
            data.get('data_type', ''), 
            data.get('unit', ''),
            data.get('threshold_low'),
            data.get('threshold_high'),
            data.get('multiplier', 1.0),
            data.get('offset', 0.0),
            data.get('profile_name'), 
            data.get('data_key')
        )
        # refresh frontend
        self.ui.send_message('device_list_updated', {'type': 'sensor'})

    def on_add_actuator(self, sid, data):
        dbg(f"[DEBUG] [WebServer] Received Actuator Config: {data}")
        self.db.add_actuator(
            data['name'], data['control_type'], data['pin'], 
            data['normal_val'], data['low_val'], data['high_val'], 
            data['trigger_dir'], data['linked_sensor_id'],
            data['extra_params']
        )
        # refresh frontend
        self.ui.send_message('device_list_updated', {'type': 'actuator'})

    @staticmethod
    def _num(value, cast=float):
        # Empty or invalid input becomes None (NULL in SQL)
        if value is None or value == '':
            return None
        try:
            return cast(value)
        except (TypeError, ValueError):
            return None

    def on_update_sensor(self, sid, data):
        dbg(f"[DEBUG] [WebServer] Update Sensor: {data}")
        try:
            sensor_id = int(data.get('id'))
        except (TypeError, ValueError):
            return
        fields = {}
        for key in ('data_type', 'unit'):
            if key in data:
                fields[key] = str(data[key] or '')
        for key in ('threshold_low', 'threshold_high'):
            if key in data:
                fields[key] = self._num(data[key])
        for key, default in (('multiplier', 1.0), ('offset', 0.0)):
            if key in data:
                val = self._num(data[key])
                fields[key] = default if val is None else val
        low, high = fields.get('threshold_low'), fields.get('threshold_high')
        if low is not None and high is not None and low > high:
            self.ui.send_message('device_update_error', {'type': 'sensor', 'id': sensor_id, 'message': '하한이 상한보다 클 수 없어요.'})
            return
        self.db.update_sensor(sensor_id, fields)
        self.ui.send_message('device_list_updated', {'type': 'sensor'})

    def on_update_actuator(self, sid, data):
        dbg(f"[DEBUG] [WebServer] Update Actuator: {data}")
        try:
            act_id = int(data.get('id'))
        except (TypeError, ValueError):
            return
        fields = {}
        if data.get('name'):
            fields['name'] = str(data['name'])
        for key in ('normal_val', 'low_val', 'high_val'):
            if key in data:
                val = self._num(data[key], lambda v: int(float(v)))
                fields[key] = max(0, min(255, val)) if val is not None else 0
        if data.get('trigger_dir') in ('BOTH', 'HIGH', 'LOW'):
            fields['trigger_dir'] = data['trigger_dir']
        if 'linked_sensor_id' in data:
            linked = self._num(data['linked_sensor_id'], int)
            if linked is not None:
                fields['linked_sensor_id'] = linked
        if 'extra_params' in data:
            fields['extra_params'] = data['extra_params'] if isinstance(data['extra_params'], str) else json.dumps(data['extra_params'])
        self.db.update_actuator(act_id, fields)
        # restart timers, latches and counters with the new rules
        mem = self.actuator_mem.get(str(act_id)) if self.actuator_mem is not None else None
        if mem is not None:
            # reset in place so the main loop never sees a missing key
            mem.update({'timer_start': 0, 'latched': False, 'count': 0, 'status_text': '', 'prev_active': False})
        self.ui.send_message('device_list_updated', {'type': 'actuator'})

    def on_export_config(self, sid, data):
        self.ui.send_message('config_export', config_preset.export_config(self.db))

    def on_list_presets(self, sid, data):
        self.ui.send_message('preset_list', {'presets': config_preset.list_presets()})

    def on_apply_preset(self, sid, data):
        # data: {'name': 'default.json'} for a bundled preset or {'preset': {...}} for an uploaded file
        try:
            if data.get('preset') is not None:
                preset = data['preset']
                if isinstance(preset, str):
                    preset = json.loads(preset)
            else:
                preset = config_preset.load_preset_file(str(data.get('name', '')))
            n_sen, n_act = config_preset.apply_preset(self.db, preset)
        except (config_preset.PresetError, ValueError) as e:
            self.ui.send_message('preset_result', {'ok': False, 'message': str(e)})
            return
        except Exception as e:
            print(f"[ERROR] [WebServer] Preset apply failed: {e}")
            self.ui.send_message('preset_result', {'ok': False, 'message': f'적용 중 오류: {e}'})
            return
        # outputs, latches and counters start fresh with the new configuration
        if self.actuator_mem is not None:
            for mem in self.actuator_mem.values():
                mem.update({'timer_start': 0, 'latched': False, 'count': 0, 'status_text': '', 'prev_active': False})
        self.ui.send_message('preset_result', {'ok': True, 'message': f'센서 {n_sen}개, 출력 {n_act}개를 불러왔어요.'})
        self.ui.send_message('device_list_updated', {'type': 'preset'})

    def broadcast_data(self, rows, is_anomaly):
        # send aggregated DB data and AI detection status
        payload = {
            'rows': rows,
            'alert': is_anomaly
        }
        self.ui.send_message('update_dashboard', payload)

    def broadcast_table(self, rows):
        # data transit to frontend
        dbg(f"[DEBUG] [WebServer] Broadcasting {len(rows)} rows to frontend UI...")
        self.ui.send_message('update_table', rows)
        
    def broadcast_multi_data(self, payload_dict):
        # payload_dict form: { "Main_Temp": {"rows": [...], "alert": False}, "Humidity": {...} }
        self.ui.send_message('update_dashboard_multi', payload_dict)

    def on_client_ready(self, sid, data):
        # sid(Session ID) for indicate
        dbg(f"[DEBUG] [WebServer] EVENT: New web client connected! (SID: {sid})")
        self.on_request_snapshot(sid, data)
        
    def build_snapshot(self):
        # Full chart history so a new or reconnected client can draw immediately
        sensors = {}
        if self.history is not None:
            for name, meta in dict(self.latest_meta).items():
                entry = dict(meta)
                entry['points'] = self.history.points(name)
                sensors[name] = entry
        return {'sensors': sensors}

    def on_request_snapshot(self, sid, data):
        self.ui.send_message('dashboard_snapshot', self.build_snapshot())

    def on_request_update(self, sid, data):
        dbg(f"[DEBUG] [WebServer] EVENT: Client manually requested an update. (SID: {sid})")

    def on_request_device_list(self, sid, data):
        # request from DB, then send to frontend
        sensors = self.db.get_all_sensors()
        actuators = self.db.get_all_actuators()
        
        # send origin form
        payload = {
            'sensors': sensors,
            'actuators': actuators
        }
        self.ui.send_message('update_device_list', payload)
        
    def on_delete_device(self, sid, data):
        device_type = data.get('type')
        device_id = data.get('id')
        
        dbg(f"[DEBUG] [WebServer] EVENT: Delete Request -> Type: {device_type}, ID: {device_id}")
        
        if device_type == 'sensor':
            self.db.delete_sensor(device_id)
        elif device_type == 'actuator':
            self.db.delete_actuator(device_id)
            
        # send refresh cmd after delete
        self.ui.send_message('device_list_updated', {'type': f'deleted_{device_type}'})
        
    def on_change_sensitivity(self, sid, data):
        sensor_id = data.get('id')
        sensitivity = data.get('sensitivity', 0.1)
        
        dbg(f"[DEBUG] [WebServer] EVENT: Change Sensitivity -> ID: {sensor_id}, Val: {sensitivity}")
        self.db.update_sensor_sensitivity(sensor_id, sensitivity)
        
        # update
        self.on_request_device_list(sid, {})
        
    def on_reset_virtual(self, sid, data):
        act_id = str(data.get('id'))
        if self.actuator_mem is not None and act_id in self.actuator_mem:
            self.actuator_mem[act_id]['latched'] = False
            self.actuator_mem[act_id]['count'] = 0
            self.actuator_mem[act_id]['status_text'] = "✔️ 안전 (수동 초기화됨)"
            self.actuator_mem[act_id]['prev_active'] = False
            dbg(f"[DEBUG] 장치(ID: {act_id}) 수동 초기화 완료.")