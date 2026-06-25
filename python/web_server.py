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
        print("[DEBUG] [WebServer] WebUI successfully started. Listening on port 7000.")

    def on_add_sensor(self, sid, data):
        print(f"[DEBUG] [WebServer] Received Sensor Config: {data}")
        self.db.add_sensor(data['name'], data['protocol'], data['pin'])
        # refresh frontend
        self.ui.send_message('device_list_updated', {'type': 'sensor'})

    def on_add_actuator(self, sid, data):
        print(f"[DEBUG] [WebServer] Received Actuator Config: {data}")
        self.db.add_actuator(
            data['name'], data['control_type'], data['pin'], 
            data['trigger_logic'], data['linked_sensor_id']
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