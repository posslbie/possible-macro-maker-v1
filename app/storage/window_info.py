import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

def list_windows():
    out=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd): return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length==0: return True
        buff = ctypes.create_unicode_buffer(length+1)
        user32.GetWindowTextW(hwnd, buff, length+1)
        title=buff.value.strip()
        if title and title != "Possible Macro Maker":
            out.append(title)
        return True
    user32.EnumWindows(cb, 0)
    # dedupe, keep order
    seen=set(); uniq=[]
    for t in out:
        if t not in seen:
            seen.add(t); uniq.append(t)
    return uniq[:50]

def get_foreground_window_title():
    hwnd=user32.GetForegroundWindow()
    if not hwnd: return ""
    length=user32.GetWindowTextLengthW(hwnd)
    buff=ctypes.create_unicode_buffer(length+1)
    user32.GetWindowTextW(hwnd, buff, length+1)
    return buff.value
