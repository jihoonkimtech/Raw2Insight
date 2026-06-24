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
        self.ui = WebUI()

    def broadcast_table(self, rows):
        # data transit to frontend
        self.ui.send_message('update_table', rows)