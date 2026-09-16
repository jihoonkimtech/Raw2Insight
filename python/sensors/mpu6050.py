"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sensors/mpu6050.py
Purpose      : driver for MPU6050 (6-axis accel + gyro)
===================================================================
"""
import math
from sensors import BaseI2CSensor

# Register map
REG_SMPLRT_DIV   = 0x19
REG_CONFIG       = 0x1A
REG_GYRO_CONFIG  = 0x1B
REG_ACCEL_CONFIG = 0x1C
REG_ACCEL_XOUT_H = 0x3B
REG_PWR_MGMT_1   = 0x6B

# Scale factors for the default full-scale ranges (+-2g, +-250dps)
ACCEL_LSB_PER_G   = 16384.0
GYRO_LSB_PER_DPS  = 131.0


def _to_int16(high, low):
    # Combine two bytes into a signed 16-bit integer (big endian)
    value = (high << 8) | low
    return value - 0x10000 if value & 0x8000 else value


class MPU6050Sensor(BaseI2CSensor):
    profile_name = "MPU6050"
    default_addr = "0x68"   # 0x69 when AD0 is pulled high
    read_bytes = 14         # ACCEL(6) + TEMP(2) + GYRO(6)
    read_register = REG_ACCEL_XOUT_H
    outputs = [
        "Accel_X", "Accel_Y", "Accel_Z", "Accel_Mag",
        "Gyro_X", "Gyro_Y", "Gyro_Z",
        "Roll", "Pitch", "Temperature",
    ]

    # Wake up with PLL clock, 1kHz/(1+9)=100Hz, DLPF ~44Hz, +-250dps, +-2g
    init_sequence = [
        [REG_PWR_MGMT_1, 0x01],
        [REG_SMPLRT_DIV, 0x09],
        [REG_CONFIG, 0x03],
        [REG_GYRO_CONFIG, 0x00],
        [REG_ACCEL_CONFIG, 0x00],
    ]
    init_delay = 0.05

    def parse(self, data_bytes):
        if not data_bytes or len(data_bytes) < 14: return None

        # All zeros means the MCU padded a failed read
        if not any(data_bytes[:14]): return None

        ax = _to_int16(data_bytes[0], data_bytes[1]) / ACCEL_LSB_PER_G
        ay = _to_int16(data_bytes[2], data_bytes[3]) / ACCEL_LSB_PER_G
        az = _to_int16(data_bytes[4], data_bytes[5]) / ACCEL_LSB_PER_G
        temp_raw = _to_int16(data_bytes[6], data_bytes[7])
        gx = _to_int16(data_bytes[8], data_bytes[9]) / GYRO_LSB_PER_DPS
        gy = _to_int16(data_bytes[10], data_bytes[11]) / GYRO_LSB_PER_DPS
        gz = _to_int16(data_bytes[12], data_bytes[13]) / GYRO_LSB_PER_DPS

        # Vector magnitude is ~1g at rest, useful for vibration/shock detection
        mag = math.sqrt(ax * ax + ay * ay + az * az)

        # Tilt from gravity vector (valid when not accelerating)
        roll = math.degrees(math.atan2(ay, az))
        pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
        print(f"[DEBUG] [MPU6050 Driver] bit parsing done!")

        return {
            "Accel_X": round(ax, 3),
            "Accel_Y": round(ay, 3),
            "Accel_Z": round(az, 3),
            "Accel_Mag": round(mag, 3),
            "Gyro_X": round(gx, 2),
            "Gyro_Y": round(gy, 2),
            "Gyro_Z": round(gz, 2),
            "Roll": round(roll, 2) + 0.0,
            "Pitch": round(pitch, 2) + 0.0,  # avoid -0.0 in UI
            # Datasheet formula: T = raw / 340 + 36.53
            "Temperature": round(temp_raw / 340.0 + 36.53, 2),
        }
