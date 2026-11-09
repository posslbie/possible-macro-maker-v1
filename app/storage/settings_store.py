import os, json

from .local_data import settings_path

SETTINGS_PATH = str(settings_path())

DEFAULTS = {
    "last_active_profile": "Default",
    "engine_tick_ms": 1,  # 1ms default, 1-50
    "engine_adaptive": True,
    "minimize_to_tray": True,
    "window_lock_enabled": False,
    "window_lock_windows": [],
    "window_blacklist_enabled": True,
    "window_blacklist": [],
}


def _ensure_parent():
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)


def _load():
    _ensure_parent()
    if not os.path.exists(SETTINGS_PATH):
        return dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data=json.load(f)
        for k,v in DEFAULTS.items():
            if k not in data: data[k]=v
        return data
    except Exception:
        return dict(DEFAULTS)


def _save(d):
    _ensure_parent()
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def get(key):
    return _load().get(key, DEFAULTS.get(key))


def set(key, value):
    d=_load(); d[key]=value; _save(d)


def get_all(): return _load()
