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
    def __init__(self):
        # init web server instance
        print("[DEBUG] [WebServer] Initializing WebUI module...")
        self.ui = WebUI()

        # register event handlers for incoming messages from frontend
        self.ui.on_message('client_ready', self.on_client_ready)
        self.ui.on_message('request_update', self.on_request_update)
        print("[DEBUG] [WebServer] WebUI successfully started. Listening on port 7000.")

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