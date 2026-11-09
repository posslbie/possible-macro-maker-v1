import ctypes, os, json, glob, sys

_dll=None
def _get():
    global _dll
    if _dll: return _dll
    candidates=[]
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        candidates.append(os.path.join(base, 'app', 'native', 'pmm_runtime.dll'))
        candidates.append(os.path.join(os.path.dirname(sys.executable), 'app', 'native', 'pmm_runtime.dll'))
    candidates.append(os.path.join(os.path.dirname(__file__), 'pmm_runtime.dll'))
    candidates.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'native', 'pmm_runtime.dll'))
    for path in candidates:
        if path and os.path.exists(path):
            _dll = ctypes.WinDLL(path)
            break
    if not _dll:
        return None
    _dll.rt_init()
    _dll.rt_start()
    _dll.rt_clear_macros.argtypes=[]
    _dll.rt_add_macro_json.argtypes=[ctypes.c_char_p]
    _dll.rt_add_macro_json.restype=ctypes.c_bool
    _dll.rt_set_enabled.argtypes=[ctypes.c_char_p, ctypes.c_bool]
    _dll.rt_set_enabled.restype=ctypes.c_bool
    _dll.rt_get_enabled_count.restype=ctypes.c_int
    _dll.rt_get_loop_ms.restype=ctypes.c_double
    return _dll

def sync_all():
    dll=_get()
    if not dll: return
    dll.rt_clear_macros()
    # push filtered? push all, enabled state controlled separately
    from ..storage.macro_store import load_all
    for m in load_all():
        j=json.dumps(m.to_dict())
        dll.rt_add_macro_json(j.encode("utf-8"))
        # set enabled (starts disabled per startup)
        dll.rt_set_enabled(m.name.encode("utf-8"), bool(m.enabled))

def set_enabled(name, enabled):
    dll=_get()
    if dll:
        dll.rt_set_enabled(name.encode("utf-8"), bool(enabled))

def get_loop_ms():
    dll=_get()
    return dll.rt_get_loop_ms() if dll else 0.0

def set_tick_ms(ms):
    dll=_get()
    if dll:
        dll.rt_set_tick_ms.argtypes=[ctypes.c_int]
        dll.rt_set_tick_ms(ms)

def get_tick_ms():
    dll=_get()
    if dll:
        dll.rt_get_tick_ms.restype=ctypes.c_int
        return int(dll.rt_get_tick_ms())
    return 1

def set_window_lock_enabled(v):
    dll=_get()
    if dll:
        dll.rt_set_window_lock_enabled.argtypes=[ctypes.c_bool]
        dll.rt_set_window_lock_enabled(bool(v))
        try:
            from ..storage.settings_store import set as sset
            sset("window_lock_enabled", bool(v))
        except: pass

def get_window_lock_enabled():
    dll=_get()
    if dll:
        dll.rt_get_window_lock_enabled.restype=ctypes.c_bool
        try:
            return bool(dll.rt_get_window_lock_enabled())
        except: pass
    try:
        from ..storage.settings_store import get as sget
        return bool(sget("window_lock_enabled"))
    except: return False


def set_window_blacklist(windows):
    vals = []
    for w in windows or []:
        s = str(w).strip()
        if s:
            vals.append(s)
    try:
        from ..storage.settings_store import set as sset
        sset("window_blacklist", vals)
    except: pass
    dll = _get()
    if dll and hasattr(dll, "rt_set_window_blacklist"):
        try:
            import json
            payload = json.dumps(vals).encode("utf-8")
            dll.rt_set_window_blacklist.argtypes = [ctypes.c_char_p]
            dll.rt_set_window_blacklist(payload)
        except: pass


def set_window_blacklist_enabled(v):
    value = bool(v)
    try:
        from ..storage.settings_store import set as sset
        sset("window_blacklist_enabled", value)
    except: pass
    dll = _get()
    if dll and hasattr(dll, "rt_set_window_blacklist_enabled"):
        try:
            dll.rt_set_window_blacklist_enabled.argtypes = [ctypes.c_bool]
            dll.rt_set_window_blacklist_enabled(value)
        except: pass


def get_window_blacklist_enabled():
    try:
        from ..storage.settings_store import get as sget
        value = bool(sget("window_blacklist_enabled"))
        dll = _get()
        if dll and hasattr(dll, "rt_get_window_blacklist_enabled"):
            try:
                dll.rt_get_window_blacklist_enabled.restype = ctypes.c_bool
                return bool(dll.rt_get_window_blacklist_enabled())
            except: pass
        return value
    except: return True


def get_window_blacklist():
    try:
        from ..storage.settings_store import get as sget
        vals = list(sget("window_blacklist") or [])
        return [str(v).strip() for v in vals if str(v).strip()]
    except: return []
