"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : db_manager.py
Purpose      : Manage SQLite database connection and queries
===================================================================
"""
import sqlite3
from datetime import datetime

class DBManager:
    def __init__(self, db_name='sensor_data.db'):
        # init db connection
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # table creation
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                sensor_value INTEGER
            )
        ''')
        self.conn.commit()

    def insert_data(self, value):
        # store date with timestamp
        current_time = datetime.now().strftime('%H:%M:%S')
        self.cursor.execute(
            "INSERT INTO sensor_logs (timestamp, sensor_value) VALUES (?, ?)", 
            (current_time, value)
        )
        self.conn.commit()
        return current_time

    def get_latest_data(self, limit=5):
        # load N latest data from DB
        self.cursor.execute("SELECT timestamp, sensor_value FROM sensor_logs ORDER BY id DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()