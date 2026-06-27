"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sensors/aht20.py
Purpose      : driver for AHT20
===================================================================
"""
from sensors import BaseI2CSensor

class AHT20Sensor(BaseI2CSensor):
    profile_name = "AHT20"
    default_addr = "0x38"
    read_bytes = 6
    outputs = ["Temperature", "Humidity"]

    def parse(self, data_bytes):
        if len(data_bytes) < 6: return None
        
        # bit parsing
        humidity_raw = ((data_bytes[1] << 12) | (data_bytes[2] << 4) | (data_bytes[3] >> 4))
        temp_raw = (((data_bytes[3] & 0x0F) << 16) | (data_bytes[4] << 8) | data_bytes[5])
        print(f"[DEBUG] [AHT20 Driver] bit parsing done!")
        
        return {
            "Temperature": round((temp_raw / 1048576.0) * 200.0 - 50.0, 2),
            "Humidity": round((humidity_raw / 1048576.0) * 100.0, 2)
        }