"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sensors/aht20.py
Purpose      : driver for AHT20
===================================================================
"""
from sensors import BaseI2CSensor

# Commands from the AHT20 datasheet
CMD_SOFT_RESET = [0xBA]
CMD_INITIALIZE = [0xBE, 0x08, 0x00]
CMD_TRIGGER    = [0xAC, 0x33, 0x00]

# Status byte bits
STATUS_BUSY       = 0x80
STATUS_CALIBRATED = 0x08


def _crc8(data):
    # CRC-8, poly 0x31, init 0xFF (datasheet)
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


class AHT20Sensor(BaseI2CSensor):
    profile_name = "AHT20"
    default_addr = "0x38"
    read_bytes = 7          # status + 5 data bytes + CRC
    outputs = ["Temperature", "Humidity"]

    # Soft reset then load calibration, applied once (and again after a failed read)
    init_sequence = [CMD_SOFT_RESET, CMD_INITIALIZE]
    init_delay = 0.05

    # A measurement must be triggered before every read, conversion takes ~80ms
    trigger_sequence = [CMD_TRIGGER]
    trigger_delay = 0.1

    def parse(self, data_bytes):
        if not data_bytes or len(data_bytes) < 7: return None

        # All zeros means the MCU padded a failed read
        if not any(data_bytes[:7]): return None

        status = data_bytes[0]
        if status & STATUS_BUSY:
            print(f"[WARN] [AHT20 Driver] sensor busy, measurement not ready")
            return None
        if not status & STATUS_CALIBRATED:
            print(f"[WARN] [AHT20 Driver] calibration bit not set")
            return None
        if _crc8(data_bytes[:6]) != data_bytes[6]:
            print(f"[WARN] [AHT20 Driver] CRC mismatch")
            return None

        # bit parsing
        humidity_raw = ((data_bytes[1] << 12) | (data_bytes[2] << 4) | (data_bytes[3] >> 4))
        temp_raw = (((data_bytes[3] & 0x0F) << 16) | (data_bytes[4] << 8) | data_bytes[5])
        print(f"[DEBUG] [AHT20 Driver] bit parsing done!")

        return {
            "Temperature": round((temp_raw / 1048576.0) * 200.0 - 50.0, 2),
            "Humidity": round((humidity_raw / 1048576.0) * 100.0, 2)
        }
