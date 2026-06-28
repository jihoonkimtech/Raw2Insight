"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : web_server.py
Purpose      : Manage WebUI and broadcast data to frontend
===================================================================
"""
from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI
from sensors import load_sensor_profiles

I2C_PROFILES = load_sensor_profiles()

class WebServer:
    def __init__(self, db_manager):
        # init web server instance
        print("[DEBUG] [WebServer] Initializing WebUI module...")
        self.ui = WebUI()
        self.db = db_manager

        # register event handlers for incoming messages from frontend
        self.ui.on_message('client_ready', self.on_client_ready)
        self.ui.on_message('request_update', self.on_request_update)
        self.ui.on_message('request_device_list', self.on_request_device_list)
        self.ui.on_message('add_sensor_request', self.on_add_sensor)
        self.ui.on_message('add_actuator_request', self.on_add_actuator)
        self.ui.on_message('delete_device_request', self.on_delete_device)
        self.ui.on_message('change_sensitivity', self.on_change_sensitivity)
        self.ui.on_message('request_i2c_profiles', self.on_request_i2c_profiles)
        self.ui.on_message('reset_virtual', self.on_reset_virtual)
        print("[DEBUG] [WebServer] WebUI successfully started. Listening on port 7000.")

    def on_request_i2c_profiles(self, sid, data):
        profiles_data = {}
        for name, inst in I2C_PROFILES.items():
            profiles_data[name] = {
                "default_addr": inst.default_addr,
                "outputs": inst.outputs
            }
        self.ui.send_message('update_i2c_profiles', profiles_data)

    def on_add_sensor(self, sid, data):
        print(f"[DEBUG] [WebServer] Received Sensor Config: {data}")
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
        print(f"[DEBUG] [WebServer] Received Actuator Config: {data}")
        self.db.add_actuator(
            data['name'], data['control_type'], data['pin'], 
            data['normal_val'], data['low_val'], data['high_val'], 
            data['trigger_dir'], data['linked_sensor_id'],
            data['extra_params']
        )
        # refresh frontend
        self.ui.send_message('device_list_updated', {'type': 'actuator'})

    def broadcast_data(self, rows, is_anomaly):
        # send aggregated DB data and AI detection status
        payload = {
            'rows': rows,
            'alert': is_anomaly
        }
        self.ui.send_message('update_dashboard', payload)

    def broadcast_table(self, rows):
        # data transit to frontend
        print(f"[DEBUG] [WebServer] Broadcasting {len(rows)} rows to frontend UI...")
        self.ui.send_message('update_table', rows)
        
    def broadcast_multi_data(self, payload_dict):
        # payload_dict form: { "Main_Temp": {"rows": [...], "alert": False}, "Humidity": {...} }
        self.ui.send_message('update_dashboard_multi', payload_dict)

    def on_client_ready(self, sid, data):
        # sid(Session ID) for indicate
        print(f"[DEBUG] [WebServer] EVENT: New web client connected! (SID: {sid})")
        
    def on_request_update(self, sid, data):
        print(f"[DEBUG] [WebServer] EVENT: Client manually requested an update. (SID: {sid})")

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
        
        print(f"[DEBUG] [WebServer] EVENT: Delete Request -> Type: {device_type}, ID: {device_id}")
        
        if device_type == 'sensor':
            self.db.delete_sensor(device_id)
        elif device_type == 'actuator':
            self.db.delete_actuator(device_id)
            
        # send refresh cmd after delete
        self.ui.send_message('device_list_updated', {'type': f'deleted_{device_type}'})
        
    def on_change_sensitivity(self, sid, data):
        sensor_id = data.get('id')
        sensitivity = data.get('sensitivity', 0.1)
        
        print(f"[DEBUG] [WebServer] EVENT: Change Sensitivity -> ID: {sensor_id}, Val: {sensitivity}")
        self.db.update_sensor_sensitivity(sensor_id, sensitivity)
        
        # update
        self.on_request_device_list(sid, {})
        
    def on_reset_virtual(self, sid, data):
        act_id = str(data.get('id'))
        if hasattr(self, 'virtual_device_mem') and act_id in self.virtual_device_mem:
            # force reset
            self.virtual_device_mem[act_id]['latched'] = False
            self.virtual_device_mem[act_id]['count'] = 0
            self.virtual_device_mem[act_id]['status_text'] = "✔️ 안전 (수동 초기화됨)"
            print(f"[DEBUG] [WebServer] 가상 장치(ID: {act_id}) 수동 초기화 완료.")