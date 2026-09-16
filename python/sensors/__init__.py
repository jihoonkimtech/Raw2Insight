"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sensors/__init__.py
Purpose      : sensor driver interface interceptor (I2C, DHT)
===================================================================
"""
import os
import importlib

class BaseSensor:
    # Common driver interface, "bus" decides which UI protocol and MCU RPC are used
    bus = "none"
    profile_name = "BASE"
    default_addr = ""
    read_bytes = 0
    outputs = [] # ["Temperature", "Humidity", ...]
    # Minimum seconds between physical reads, cached data is reused in between
    min_interval = 0.0

    def parse(self, data_bytes):
        #take byte array and return {data type: value} to dictionary
        raise NotImplementedError


class BaseI2CSensor(BaseSensor):
    # Standard sensor-based classes that open-source contributors must inherit
    bus = "i2c"
    default_addr = "0x00"
    # Optional: register pointer to set before reading (None = plain read)
    read_register = None
    # Optional: byte sequences written once before the first read, e.g. [[0x6B, 0x00]]
    init_sequence = []
    # Delay in seconds after each init write
    init_delay = 0.0
    # Optional: byte sequences written before every read (e.g. measurement trigger)
    trigger_sequence = []
    # Delay in seconds between trigger and read (measurement time)
    trigger_delay = 0.0


class BaseDHTSensor(BaseSensor):
    # Single-wire DHT family, decoded on the MCU and returned as 5 raw bytes
    bus = "dht"
    default_addr = "2"   # DIN01
    read_bytes = 5
    min_interval = 1.0


BASE_CLASSES = (BaseSensor, BaseI2CSensor, BaseDHTSensor)


def load_sensor_profiles():
    profiles = {}
    current_dir = os.path.dirname(__file__)
    
    for filename in sorted(os.listdir(current_dir)):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = f"sensors.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                # register functions
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseSensor) and attr not in BASE_CLASSES:
                        instance = attr()
                        profiles[instance.profile_name] = instance
            except Exception as e:
                print(f"[ERROR] [SensorLoader] Failed to load plugin {module_name}: {e}")
                
    return profiles