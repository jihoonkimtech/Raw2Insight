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
        print(f"[DEBUG] [DBManager] Connecting to database: {db_name}...")
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # table creation
        print("[DEBUG] [DBManager] Checking and initializing 'sensor_logs' table...")
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
        print(f"[DEBUG] [DBManager] Inserted Row -> Time: {current_time}, Value: {value}")
        return current_time

    def get_latest_data(self, limit=5):
        # load N latest data from DB
        print(f"[DEBUG] [DBManager] Fetching latest {limit} records from DB...")
        self.cursor.execute("SELECT timestamp, sensor_value FROM sensor_logs ORDER BY id DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()