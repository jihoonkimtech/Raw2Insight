"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : sensors/__init__.py
Purpose      : sensor driver interface interceptor
===================================================================
"""
import os
import importlib

class BaseI2CSensor:
    # Standard sensor-based classes that open-source contributors must inherit
    profile_name = "BASE"
    default_addr = "0x00"
    read_bytes = 0
    outputs = [] # ["Temperature", "Humidity", ...]

    def parse(self, data_bytes):
        #take byte array and return {data type: value} to dictionary
        raise NotImplementedError


def load_sensor_profiles():
    profiles = {}
    current_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = f"sensors.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                # register functions
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseI2CSensor) and attr != BaseI2CSensor:
                        instance = attr()
                        profiles[instance.profile_name] = instance
            except Exception as e:
                print(f"[ERROR] [SensorLoader] Failed to load plugin {module_name}: {e}")
                
    return profiles