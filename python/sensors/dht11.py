"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sensors/dht11.py
Purpose      : driver for DHT11 (single-wire temperature/humidity)
===================================================================
"""
from sensors import BaseDHTSensor


class DHT11Sensor(BaseDHTSensor):
    profile_name = "DHT11"
    default_addr = "2"      # DIN01 (D2), DIN02 is D4
    read_bytes = 5          # RH int, RH dec, T int, T dec, checksum
    outputs = ["Temperature", "Humidity"]
    # Sensor needs at least 1s between conversions
    min_interval = 1.0
    # Host start signal length in ms (datasheet: at least 18ms)
    start_low_ms = 20

    def parse(self, data_bytes):
        if not data_bytes or len(data_bytes) < 5: return None

        # All zeros means timeout or no sensor on the line
        if not any(data_bytes[:5]): return None

        if ((data_bytes[0] + data_bytes[1] + data_bytes[2] + data_bytes[3]) & 0xFF) != data_bytes[4]:
            print(f"[WARN] [DHT11 Driver] checksum mismatch")
            return None

        humidity = data_bytes[0] + data_bytes[1] * 0.1
        # Newer DHT11 revisions use bit7 of the decimal byte as the sign
        temperature = data_bytes[2] + (data_bytes[3] & 0x7F) * 0.1
        if data_bytes[3] & 0x80:
            temperature = -temperature

        # Reject values outside the physical range of the part
        if humidity > 100 or not (-20 <= temperature <= 60):
            print(f"[WARN] [DHT11 Driver] out of range value")
            return None
        print(f"[DEBUG] [DHT11 Driver] bit parsing done!")

        return {
            "Temperature": round(temperature, 1),
            "Humidity": round(humidity, 1)
        }
