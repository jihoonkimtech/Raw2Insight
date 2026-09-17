"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : config_preset.py
Purpose      : Export, import and auto-seed device configuration presets
===================================================================
"""
import os
import json
import time
from logutil import dbg

PRESET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets")
DEFAULT_PRESET = "default.json"
PRESET_VERSION = 1

SENSOR_PROTOCOLS = ("analog", "digital", "i2c", "dht")
ACTUATOR_TYPES = ("digital_out", "pwm", "virtual_counter", "virtual_timer", "virtual_latch", "virtual_webhook")
TRIGGER_DIRS = ("BOTH", "HIGH", "LOW")


class PresetError(ValueError):
    pass


def _num(value, default=None):
    # Numbers may arrive as strings or be missing
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        raise PresetError(f"숫자가 아닌 값: {value!r}")


def export_config(db):
    # Actuators reference sensors by name because row ids change between databases
    sensors = db.get_all_sensors() or []
    actuators = db.get_all_actuators() or []
    names = {s["id"]: s["name"] for s in sensors}
    out_sensors = []
    for s in sensors:
        out_sensors.append({
            "name": s["name"], "protocol": s["protocol"], "pin": s["pin"],
            "data_type": s.get("data_type") or "", "unit": s.get("unit") or "",
            "threshold_low": s.get("threshold_low"), "threshold_high": s.get("threshold_high"),
            "multiplier": s.get("multiplier") if s.get("multiplier") is not None else 1.0,
            "offset": s.get("offset") if s.get("offset") is not None else 0.0,
            "sensitivity": s.get("sensitivity") if s.get("sensitivity") is not None else 0.1,
            "profile_name": s.get("profile_name"), "data_key": s.get("data_key"),
        })
    out_acts = []
    for a in actuators:
        try:
            extra = json.loads(a.get("extra_params") or "{}")
        except ValueError:
            extra = {}
        out_acts.append({
            "name": a["name"], "control_type": a["control_type"], "pin": a["pin"],
            "linked_sensor": names.get(a.get("linked_sensor_id")),
            "trigger_dir": a.get("trigger_dir") or "BOTH",
            "normal_val": a.get("normal_val") or 0, "low_val": a.get("low_val") or 0, "high_val": a.get("high_val") or 0,
            "extra": extra,
        })
    return {
        "format": "raw2insight-preset", "version": PRESET_VERSION,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sensors": out_sensors, "actuators": out_acts,
    }


def validate_preset(preset):
    # Check the whole preset before touching the database
    if not isinstance(preset, dict):
        raise PresetError("프리셋 형식이 올바르지 않아요.")
    sensors = preset.get("sensors")
    actuators = preset.get("actuators", [])
    if not isinstance(sensors, list) or not isinstance(actuators, list):
        raise PresetError("sensors / actuators 목록이 필요해요.")

    seen = set()
    for i, s in enumerate(sensors):
        where = f"센서 #{i + 1}"
        if not s.get("name"):
            raise PresetError(f"{where}: 이름이 없어요.")
        if s["name"] in seen:
            raise PresetError(f"{where}: 이름 '{s['name']}'이 중복돼요.")
        seen.add(s["name"])
        if s.get("protocol") not in SENSOR_PROTOCOLS:
            raise PresetError(f"{where}: 알 수 없는 프로토콜 {s.get('protocol')!r}")
        if s.get("pin") in (None, ""):
            raise PresetError(f"{where}: 핀/주소가 없어요.")
        if s["protocol"] in ("i2c", "dht") and not (s.get("profile_name") and s.get("data_key")):
            raise PresetError(f"{where}: {s['protocol']} 센서는 profile_name과 data_key가 필요해요.")
        low, high = _num(s.get("threshold_low")), _num(s.get("threshold_high"))
        if s["protocol"] != "digital" and low is not None and high is not None and low > high:
            raise PresetError(f"{where}: 하한이 상한보다 커요.")

    for i, a in enumerate(actuators):
        where = f"출력 #{i + 1}"
        if not a.get("name"):
            raise PresetError(f"{where}: 이름이 없어요.")
        if a.get("control_type") not in ACTUATOR_TYPES:
            raise PresetError(f"{where}: 알 수 없는 종류 {a.get('control_type')!r}")
        if a.get("linked_sensor") not in seen:
            raise PresetError(f"{where}: 연동 센서 '{a.get('linked_sensor')}'를 찾을 수 없어요.")
        if a.get("trigger_dir", "BOTH") not in TRIGGER_DIRS:
            raise PresetError(f"{where}: 동작 조건은 BOTH/HIGH/LOW 중 하나예요.")
        for key in ("normal_val", "low_val", "high_val"):
            v = _num(a.get(key), 0)
            if not 0 <= v <= 255:
                raise PresetError(f"{where}: {key}는 0~255 사이여야 해요.")
    return sensors, actuators


def apply_preset(db, preset):
    # Replace the whole device configuration with the preset
    sensors, actuators = validate_preset(preset)
    db.clear_config()

    for s in sensors:
        db.add_sensor(
            s["name"], s["protocol"], str(s["pin"]),
            s.get("data_type") or "", s.get("unit") or "",
            _num(s.get("threshold_low")), _num(s.get("threshold_high")),
            _num(s.get("multiplier"), 1.0), _num(s.get("offset"), 0.0),
            s.get("profile_name"), s.get("data_key"),
        )
    ids = {row["name"]: row["id"] for row in db.get_all_sensors()}
    for s in sensors:
        if s.get("sensitivity") is not None:
            db.update_sensor_sensitivity(ids[s["name"]], _num(s["sensitivity"], 0.1))

    for a in actuators:
        is_virtual = a["control_type"].startswith("virtual_")
        db.add_actuator(
            a["name"], a["control_type"], "VIRTUAL" if is_virtual else str(a["pin"]),
            int(_num(a.get("normal_val"), 0)), int(_num(a.get("low_val"), 0)), int(_num(a.get("high_val"), 0)),
            a.get("trigger_dir", "BOTH"), ids[a["linked_sensor"]],
            json.dumps(a.get("extra") or {}, ensure_ascii=False),
        )
    db.mark_config_changed()
    print(f"[INFO] [Preset] Applied {len(sensors)} sensors, {len(actuators)} actuators")
    return len(sensors), len(actuators)


def list_presets():
    try:
        return sorted(f for f in os.listdir(PRESET_DIR) if f.endswith(".json"))
    except OSError:
        return []


def load_preset_file(name):
    # Only plain file names inside the preset folder are allowed
    if os.path.basename(name) != name or not name.endswith(".json"):
        raise PresetError("잘못된 프리셋 이름이에요.")
    path = os.path.join(PRESET_DIR, name)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise PresetError(f"프리셋 파일 {name}이 없어요.")
    except ValueError as e:
        raise PresetError(f"프리셋 JSON을 읽을 수 없어요: {e}")


def seed_if_empty(db):
    # First run on a fresh /app/data: load presets/default.json automatically
    if os.environ.get("RAW2INSIGHT_NO_SEED") == "1":
        return False
    if db.get_all_sensors() or db.get_all_actuators():
        return False
    try:
        preset = load_preset_file(DEFAULT_PRESET)
    except PresetError as e:
        dbg(f"[DEBUG] [Preset] No default preset: {e}")
        return False
    try:
        apply_preset(db, preset)
        return True
    except PresetError as e:
        print(f"[ERROR] [Preset] default.json is invalid: {e}")
        return False
