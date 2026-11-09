import ctypes

from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QGridLayout, QScrollArea, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QAbstractAnimation
from PySide6.QtGui import QKeySequence

from .theme import (
    C, Button, QSS_PRIMARY, QSS_SECONDARY, style_panel, panel_title,
)

_XINPUT_GAMEPAD_A = 0x1000
_XINPUT_GAMEPAD_B = 0x2000
_XINPUT_GAMEPAD_X = 0x4000
_XINPUT_GAMEPAD_Y = 0x8000
_XINPUT_GAMEPAD_LEFT_SHOULDER = 0x0100
_XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200
_XINPUT_GAMEPAD_BACK = 0x0020
_XINPUT_GAMEPAD_START = 0x0010
_XINPUT_GAMEPAD_LEFT_THUMB = 0x0040
_XINPUT_GAMEPAD_RIGHT_THUMB = 0x0080
_XINPUT_GAMEPAD_DPAD_UP = 0x0001
_XINPUT_GAMEPAD_DPAD_DOWN = 0x0002
_XINPUT_GAMEPAD_DPAD_LEFT = 0x0004
_XINPUT_GAMEPAD_DPAD_RIGHT = 0x0008


class _XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_ulong),
        ("Gamepad", _XINPUT_GAMEPAD),
    ]


def _decode_xinput_buttons(mask):
    names = []
    if mask & _XINPUT_GAMEPAD_A:
        names.append("A")
    if mask & _XINPUT_GAMEPAD_B:
        names.append("B")
    if mask & _XINPUT_GAMEPAD_X:
        names.append("X")
    if mask & _XINPUT_GAMEPAD_Y:
        names.append("Y")
    if mask & _XINPUT_GAMEPAD_LEFT_SHOULDER:
        names.append("LB")
    if mask & _XINPUT_GAMEPAD_RIGHT_SHOULDER:
        names.append("RB")
    if mask & _XINPUT_GAMEPAD_BACK:
        names.append("Back")
    if mask & _XINPUT_GAMEPAD_START:
        names.append("Start")
    if mask & _XINPUT_GAMEPAD_LEFT_THUMB:
        names.append("L3")
    if mask & _XINPUT_GAMEPAD_RIGHT_THUMB:
        names.append("R3")
    if mask & _XINPUT_GAMEPAD_DPAD_UP:
        names.append("DPad Up")
    if mask & _XINPUT_GAMEPAD_DPAD_DOWN:
        names.append("DPad Down")
    if mask & _XINPUT_GAMEPAD_DPAD_LEFT:
        names.append("DPad Left")
    if mask & _XINPUT_GAMEPAD_DPAD_RIGHT:
        names.append("DPad Right")
    return names


def _decode_joystick_buttons(mask, pov=None):
    names = []
    bit_names = {
        0: "A", 1: "B", 2: "X", 3: "Y",
        4: "LB", 5: "RB", 6: "LT", 7: "RT",
        8: "Back", 9: "Start", 10: "L3", 11: "R3",
        12: "PS", 13: "Home",
    }
    for bit, name in bit_names.items():
        if mask & (1 << bit):
            names.append(name)
    if pov is not None and pov != 0xFFFFFFFF:
        if pov in (0, 36000): names.append("DPad Up")
        elif pov == 9000: names.append("DPad Right")
        elif pov == 18000: names.append("DPad Down")
        elif pov == 27000: names.append("DPad Left")
    return names


def _normalize_mouse_button_name(value):
    if value is None:
        return ""
    value = str(value).strip()
    if not value:
        return ""
    aliases = {
        "MBL": "Left",
        "MBR": "Right",
        "MBM": "Middle",
        "M1": "Left",
        "M2": "Right",
        "M3": "Middle",
        "Left Mouse Button": "Left",
        "Right Mouse Button": "Right",
        "Middle Mouse Button": "Middle",
        "Left": "Left",
        "Right": "Right",
        "Middle": "Middle",
        "Mouse 4": "Mouse 4",
        "Mouse 5": "Mouse 5",
        "XButton1 (Side)": "XButton1 (Side)",
        "XButton2 (Side)": "XButton2 (Side)",
        "Wheel Up": "Wheel Up",
        "Wheel Down": "Wheel Down",
        "Wheel Left": "Wheel Left",
        "Wheel Right": "Wheel Right",
    }
    lowered = value.lower()
    for key, normalized in aliases.items():
        if key.lower() == lowered:
            return normalized
    if lowered in {"leftbutton", "left_btn", "left-button"}:
        return "Left"
    if lowered in {"rightbutton", "right_btn", "right-button"}:
        return "Right"
    if lowered in {"middlebutton", "middle_btn", "middle-button"}:
        return "Middle"
    if "left" in lowered:
        return "Left"
    if "right" in lowered:
        return "Right"
    if "middle" in lowered:
        return "Middle"
    return value


def _read_xinput_state(index=0):
    try:
        module = getattr(ctypes.windll, "xinput1_4", None)
        if module is None:
            module = getattr(ctypes.windll, "xinput9_1_0", None)
        if module is None:
            return None
        state = _XINPUT_STATE()
        result = module.XInputGetState(index, ctypes.byref(state))
        if result != 0:
            return None
        return state
    except Exception:
        return None


def _read_directinput_state(index=0):
    try:
        winmm = getattr(ctypes.windll, "winmm", None)
        if winmm is None:
            return None
        if not hasattr(winmm, "joyGetNumDevs"):
            return None
        if winmm.joyGetNumDevs() <= index:
            return None
        class JOYINFOEX(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("dwXpos", ctypes.c_ulong),
                ("dwYpos", ctypes.c_ulong),
                ("dwZpos", ctypes.c_ulong),
                ("dwRpos", ctypes.c_ulong),
                ("dwUpos", ctypes.c_ulong),
                ("dwVpos", ctypes.c_ulong),
                ("dwButtons", ctypes.c_ulong),
                ("dwButtonNumber", ctypes.c_ulong),
                ("dwPOV", ctypes.c_ulong),
                ("dwReserved1", ctypes.c_ulong),
                ("dwReserved2", ctypes.c_ulong),
            ]
        joy = JOYINFOEX()
        joy.dwSize = ctypes.sizeof(joy)
        joy.dwFlags = 0x80 | 0x40 | 0x01 | 0x02
        result = winmm.joyGetPosEx(index, ctypes.byref(joy))
        if result != 0:
            return None
        return {"buttons": int(joy.dwButtons), "pov": int(joy.dwPOV)}
    except Exception:
        return None


def _read_controller_state(index=0):
    state = _read_xinput_state(index)
    if state is not None:
        return set(_decode_xinput_buttons(state.Gamepad.wButtons))
    raw = _read_directinput_state(index)
    if raw is None:
        return set()
    return set(_decode_joystick_buttons(raw.get("buttons", 0), raw.get("pov")))

class BaseOverlay(QWidget):
    """Dimmed full-page layer. Fades in; any child QFrame#panel pops up from below."""
    closed = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("overlayRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("#overlayRoot{background:rgba(5,7,11,205);}")
        self.hide()
        parent.installEventFilter(self)

    def showOverlay(self):
        self.setGeometry(self.parent().rect())
        self.raise_()
        try:
            fx = QGraphicsOpacityEffect(self)
            fx.setOpacity(0.0)
            self.setGraphicsEffect(fx)
            anim = QPropertyAnimation(fx, b"opacity", self)
            anim.setDuration(170)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(self._drop_effect)
            anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        except RuntimeError:
            pass
        self.show()
        self.setFocus()
        QTimer.singleShot(0, self._pop_panels)

    def _drop_effect(self):
        try:
            self.setGraphicsEffect(None)
        except RuntimeError:
            pass

    def _pop_panels(self):
        try:
            for child in self.children():
                if isinstance(child, QFrame) and child.objectName() == "panel":
                    end = child.pos()
                    start = QPoint(end.x(), end.y() + 18)
                    child.move(start)
                    a = QPropertyAnimation(child, b"pos", child)
                    a.setDuration(260)
                    a.setStartValue(start)
                    a.setEndValue(end)
                    a.setEasingCurve(QEasingCurve.Type.OutCubic)
                    a.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        except RuntimeError:
            pass

    def hideOverlay(self):
        self.hide()
        self.closed.emit()

    def resizeEvent(self, e):
        super().resizeEvent(e)

    def eventFilter(self, obj, e):
        if obj is self.parent() and e.type() == e.Type.Resize:
            if self.isVisible():
                self.setGeometry(self.parent().rect())
        return False

    def mousePressEvent(self, e):
        pass


def _center_panel(parent, panel):
    panel.setParent(parent)
    panel.move((parent.width() - panel.width()) // 2, (parent.height() - panel.height()) // 2)


def build_dialog(host, w, h, margins=(22, 20, 22, 18), spacing=12):
    """Create (overlay, panel, layout) for a simple centred dialog."""
    ov = BaseOverlay(host)
    ov.setGeometry(host.rect())
    panel = QFrame(ov)
    panel.setFixedSize(w, h)
    style_panel(panel)
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return ov, panel, lay


def present_dialog(host, overlay, panel):
    panel.move((host.width() - panel.width()) // 2, (host.height() - panel.height()) // 2)
    overlay.showOverlay()


class RenameOverlay(BaseOverlay):
    renamed = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.panel = QFrame(self)
        self.panel.setFixedSize(380, 176)
        style_panel(self.panel)
        lay = QVBoxLayout(self.panel)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)
        self.title_lbl = panel_title("Rename Macro")
        lay.addWidget(self.title_lbl)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("New name")
        self.edit.setStyleSheet(
            "QLineEdit{background:%s; color:%s; border:1px solid %s; border-radius:9px; padding:9px 10px;}"
            "QLineEdit:focus{border:1px solid %s;}" % (C.field, C.text, C.border, C.accent)
        )
        self.edit.returnPressed.connect(self._save)
        lay.addWidget(self.edit)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(8)
        cancel = Button("Cancel")
        cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(self.hideOverlay)
        save = Button("Save")
        save.setStyleSheet(QSS_PRIMARY)
        save.clicked.connect(self._save)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(save)
        lay.addLayout(row)

    def set_title(self, text):
        self.title_lbl.setText(text)

    def showOverlay(self):
        super().showOverlay()
        _center_panel(self, self.panel)
        self.edit.setFocus()
        self.edit.selectAll()

    def _save(self):
        t = self.edit.text().strip()
        if t:
            self.renamed.emit(t)
        self.hideOverlay()

    def open(self, current):
        self.edit.setText(current)
        self.showOverlay()


class BindCaptureOverlay(BaseOverlay):
    captured = Signal(dict)
    def __init__(self, parent):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self._timer=None
        self._input_type="keyboard"
        self._listening_active=False
        self._controller_state=set()
        self._controller_poll_timer = QTimer(self)
        self._controller_poll_timer.timeout.connect(self._poll_controller)
        self._controller_poll_timer.start(50)
        self._init_ui()

    def _device_options(self):
        return {
            "keyboard": [
                "Shift", "Ctrl", "Alt", "CapsLock", "Tab", "Esc", "Enter", "Space", "Backspace",
                "Slash", "Backslash", "A", "W", "S", "D", "Q", "E", "F", "Z", "X", "C",
                "V", "1", "2", "3", "4", "5", "Up", "Down", "Left", "Right"
            ],
            "mouse": [
                "Left", "Right", "Middle", "XButton1 (Side)", "XButton2 (Side)",
                "Wheel Up", "Wheel Down", "Wheel Left", "Wheel Right", "Mouse 4", "Mouse 5"
            ],
            "controller": [
                "A", "B", "X", "Y", "LB", "RB", "LT", "RT", "Back", "Start",
                "L3", "R3", "Left Stick", "Right Stick", "DPad Up", "DPad Down", "DPad Left",
                "DPad Right", "Home", "Share", "PS", "Xbox Guide"
            ],
        }

    def _init_ui(self):
        self.panel = QFrame(self); self.panel.setFixedSize(540, 460)
        style_panel(self.panel)
        lay=QVBoxLayout(self.panel); lay.setContentsMargins(22,20,22,18); lay.setSpacing(12)

        title=QLabel("Set Input"); title.setStyleSheet("color:#ffffff; font-size:16px; font-weight:700; background:transparent;")
        title.setWordWrap(True); lay.addWidget(title)

        self.type_row = QHBoxLayout(); self.type_row.setSpacing(8)
        self.keyboard_btn = Button("Keyboard"); self.keyboard_btn.setCursor(Qt.PointingHandCursor)
        self.mouse_btn = Button("Mouse"); self.mouse_btn.setCursor(Qt.PointingHandCursor)
        self.controller_btn = Button("Controller"); self.controller_btn.setCursor(Qt.PointingHandCursor)
        for btn in (self.keyboard_btn, self.mouse_btn, self.controller_btn):
            btn.setFixedHeight(34)
            btn.setStyleSheet("QPushButton{background:%s; color:%s; border:none; border-radius:9px; padding:0 14px;} QPushButton:hover{background:%s; color:#ffffff;}" % (C.control, C.text2, C.control_hi))
        self.keyboard_btn.clicked.connect(lambda: self._select_input_type("keyboard"))
        self.mouse_btn.clicked.connect(lambda: self._select_input_type("mouse"))
        self.controller_btn.clicked.connect(lambda: self._select_input_type("controller"))
        self.type_row.addWidget(self.keyboard_btn); self.type_row.addWidget(self.mouse_btn); self.type_row.addWidget(self.controller_btn)
        lay.addLayout(self.type_row)

        self.info=QLabel("Click the waiting area to start keyboard listening."); self.info.setWordWrap(True)
        self.info.setStyleSheet("color:%s; font-size:12px; background:transparent;" % C.muted); lay.addWidget(self.info)

        self.display=QLabel("Click here to turn on listening mode"); self.display.setAlignment(Qt.AlignCenter)
        self.display.setCursor(Qt.PointingHandCursor)
        self.display.setStyleSheet("color:%s; font-size:14px; font-weight:700; background:%s; border:1px dashed %s; border-radius:10px; padding:14px 16px;" % (C.text2, C.field, C.border_hi)); lay.addWidget(self.display)
        self.display.mousePressEvent = self._display_press_event

        self.button_scroll = QScrollArea(); self.button_scroll.setWidgetResizable(True); self.button_scroll.setFrameShape(QFrame.NoFrame)
        self.button_scroll.setStyleSheet("QScrollArea{background:transparent; border:none;} QScrollBar:vertical{background:transparent; width:10px; margin:2px;} QScrollBar::handle:vertical{background:%s; border-radius:3px; min-height:24px;} QScrollBar::add-line, QScrollBar::sub-line{height:0;}" % C.control_hi)
        self.button_panel = QWidget(); self.button_panel.setStyleSheet("background:%s; border-radius:10px;" % C.field)
        self.button_grid = QGridLayout(self.button_panel); self.button_grid.setContentsMargins(12,12,12,12); self.button_grid.setSpacing(8)
        self.button_scroll.setWidget(self.button_panel); lay.addWidget(self.button_scroll, 1)

        self._populate_device_buttons(); self._select_input_type("keyboard")

        row=QHBoxLayout()
        cancel=Button("Cancel"); cancel.setStyleSheet(QSS_SECONDARY); cancel.clicked.connect(self.hideOverlay)
        row.addStretch(1); row.addWidget(cancel); lay.addLayout(row)

    def _select_input_type(self, input_type):
        self._input_type = input_type
        self._listening_active = False
        self._update_device_styles()
        self._populate_device_buttons()
        labels = {"keyboard": "Click below to turn on listening mode.",
                  "mouse": "Click below to turn on mouse listening mode.",
                  "controller": "Click below to turn on controller listening mode."}
        self.info.setText(labels.get(input_type, "Listening for input."))
        if input_type in {"keyboard", "mouse", "controller"}:
            self.display.setText("Click here to turn on listening mode")
            self.display.setStyleSheet("color:%s; font-size:14px; font-weight:700; background:%s; border:1px dashed %s; border-radius:10px; padding:14px 16px;" % (C.text2, C.field, C.border_hi))

    def _display_press_event(self, event):
        self._listening_active = True
        if self._input_type == "keyboard":
            self.display.setText("● listening")
            self.display.setStyleSheet("color:%s; font-size:18px; font-weight:700; background:%s; border:1px solid %s; border-radius:10px; padding:14px 16px;" % (C.accent_hi, C.field, C.accent))
            self.info.setText("Listening for keyboard input. Press any key to capture it.")
            self.setFocus(); self.grabKeyboard()
            event.accept()
            return
        if self._input_type == "mouse":
            self.display.setText("● listening")
            self.display.setStyleSheet("color:%s; font-size:18px; font-weight:700; background:%s; border:1px solid %s; border-radius:10px; padding:14px 16px;" % (C.accent_hi, C.field, C.accent))
            self.info.setText("Listening for mouse input. Click a mouse button or use the wheel.")
            self.setFocus(); self.grabMouse();
            event.accept()
            return
        if self._input_type == "controller":
            self.display.setText("● listening")
            self.display.setStyleSheet("color:%s; font-size:18px; font-weight:700; background:%s; border:1px solid %s; border-radius:10px; padding:14px 16px;" % (C.accent_hi, C.field, C.accent))
            self.info.setText("Listening for controller input. Use mapped keys or pick a button below.")
            self.setFocus(); self.grabKeyboard()
            event.accept()
            return

    def _update_device_styles(self):
        for name, btn in {"keyboard": self.keyboard_btn, "mouse": self.mouse_btn, "controller": self.controller_btn}.items():
            selected = name == self._input_type
            btn.setStyleSheet(
                "QPushButton{background:%s; color:%s; border:none; border-radius:9px; padding:0 14px; font-weight:%s;} QPushButton:hover{background:%s; color:#ffffff;}" % (
                    C.accent if selected else C.control,
                    "#ffffff" if selected else C.text2,
                    "700" if selected else "400",
                    C.accent_hi if selected else C.control_hi,
                )
            )

    def _populate_device_buttons(self):
        while self.button_grid.count():
            item = self.button_grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        options = self._device_options().get(self._input_type, [])
        for index, name in enumerate(options):
            btn = Button(name)
            btn.setFixedHeight(34)
            btn.setStyleSheet("QPushButton{background:%s; color:%s; border:none; border-radius:8px; text-align:left; padding-left:10px; font-size:12px;} QPushButton:hover{background:%s; color:#ffffff;}" % (C.control, C.text2, C.control_hi))
            btn.clicked.connect(lambda _, value=name: self._capture_manual(value))
            self.button_grid.addWidget(btn, index // 4, index % 4)
        self.button_grid.setColumnStretch(0, 1); self.button_grid.setColumnStretch(1, 1); self.button_grid.setColumnStretch(2, 1); self.button_grid.setColumnStretch(3, 1)

    def _capture_manual(self, value):
        kind = self._input_type
        self._listening_active = False
        self._controller_state = set()
        payload = {"type": kind, "value": value}
        if kind == "keyboard":
            payload["vk"] = self._keyboard_vkey(value)
            payload["mods"] = []
        elif kind == "mouse":
            payload["button"] = self._mouse_button(value)
        self.captured.emit(payload)
        self.hideOverlay()

    def showOverlay(self):
        super().showOverlay()
        _center_panel(self, self.panel)
        self._listening_active = False
        self._controller_state = set()
        self._controller_poll_timer.start(50)
        self.releaseKeyboard()
        self._select_input_type(self._input_type)

    def hideOverlay(self):
        if self._timer: self._timer.stop(); self._timer=None
        self._listening_active = False
        self._controller_state = set()
        self._controller_poll_timer.stop()
        try:
            self.releaseMouse()
        except Exception:
            pass
        self.releaseKeyboard()
        super().hideOverlay()

    def keyPressEvent(self, e):
        if not self._listening_active:
            e.ignore(); return
        if self._input_type == "keyboard":
            key = e.key()
            name = QKeySequence(key).toString(QKeySequence.NativeText)
            if not name:
                mapping={Qt.Key_Shift:"Shift", Qt.Key_Control:"Ctrl", Qt.Key_Alt:"Alt", Qt.Key_CapsLock:"CapsLock", Qt.Key_Slash:"Slash", Qt.Key_Backslash:"Backslash", Qt.Key_QuoteDbl:"Quote", Qt.Key_Space:"Space", Qt.Key_Enter:"Enter", Qt.Key_Tab:"Tab", Qt.Key_Escape:"Esc", Qt.Key_Backspace:"Backspace"}
                name=mapping.get(key, f"Key_{key}")
            mods=[]
            if e.modifiers() & Qt.ShiftModifier and name!="Shift": mods.append("Shift")
            if e.modifiers() & Qt.ControlModifier: mods.append("Ctrl")
            if e.modifiers() & Qt.AltModifier: mods.append("Alt")
            full="+".join(mods+[name]) if mods else name
            self.captured.emit({"type":"keyboard", "value":full, "vk":key, "mods":mods})
            self.hideOverlay()
            return
        if self._input_type == "controller":
            mapping = {
                Qt.Key_Z: "A", Qt.Key_X: "B", Qt.Key_C: "X", Qt.Key_V: "Y",
                Qt.Key_Q: "LB", Qt.Key_E: "RB", Qt.Key_Up: "DPad Up", Qt.Key_Down: "DPad Down",
                Qt.Key_Left: "DPad Left", Qt.Key_Right: "DPad Right", Qt.Key_Backspace: "Back",
                Qt.Key_Return: "Start", Qt.Key_Space: "Home", Qt.Key_W: "DPad Up", Qt.Key_S: "DPad Down",
                Qt.Key_A: "DPad Left", Qt.Key_D: "DPad Right",
            }
            name = mapping.get(e.key(), None)
            if name:
                self.captured.emit({"type":"controller", "value":name, "key":e.key()})
                self.hideOverlay()
                return
        e.ignore()
        name = QKeySequence(key).toString(QKeySequence.NativeText)
        if not name:
            mapping={Qt.Key_Shift:"Shift", Qt.Key_Control:"Ctrl", Qt.Key_Alt:"Alt", Qt.Key_CapsLock:"CapsLock", Qt.Key_Slash:"Slash", Qt.Key_Backslash:"Backslash", Qt.Key_QuoteDbl:"Quote", Qt.Key_Space:"Space", Qt.Key_Enter:"Enter", Qt.Key_Tab:"Tab", Qt.Key_Escape:"Esc", Qt.Key_Backspace:"Backspace"}
            name=mapping.get(key, f"Key_{key}")
        mods=[]
        if e.modifiers() & Qt.ShiftModifier and name!="Shift": mods.append("Shift")
        if e.modifiers() & Qt.ControlModifier: mods.append("Ctrl")
        if e.modifiers() & Qt.AltModifier: mods.append("Alt")
        full="+".join(mods+[name]) if mods else name
        self.captured.emit({"type":"keyboard", "value":full, "vk":key, "mods":mods})
        self.hideOverlay()

    def wheelEvent(self, e):
        if self._input_type != "mouse" or not self._listening_active:
            return super().wheelEvent(e)
        delta = e.angleDelta()
        if delta.x() != 0:
            name = "Wheel Right" if delta.x() > 0 else "Wheel Left"
        else:
            name = "Wheel Up" if delta.y() > 0 else "Wheel Down"
        self.captured.emit({"type":"mouse", "value":name, "button":name, "delta": {"x": delta.x(), "y": delta.y()}})
        self.hideOverlay()
        e.accept()

    def mousePressEvent(self, e):
        if self._input_type != "mouse" or not self._listening_active:
            return super().mousePressEvent(e)
        btn_map={Qt.LeftButton:"Left", Qt.RightButton:"Right", Qt.MiddleButton:"Middle", Qt.XButton1:"XButton1 (Side)", Qt.XButton2:"XButton2 (Side)"}
        raw = btn_map.get(e.button(), f"Mouse_{e.button().name if hasattr(e.button(),'name') else str(e.button())}")
        name = _normalize_mouse_button_name(raw)
        if name in {"Left", "Right", "Middle", "XButton1 (Side)", "XButton2 (Side)", "Wheel Up", "Wheel Down", "Wheel Left", "Wheel Right"}:
            self.captured.emit({"type":"mouse", "value":name, "button":e.button().value if hasattr(e.button(),'value') else int(e.button())})
            self.hideOverlay()
            e.accept()
            return
        return super().mousePressEvent(e)

    def _keyboard_vkey(self, value):
        mapping = {
            "Shift": Qt.Key_Shift, "Ctrl": Qt.Key_Control, "Alt": Qt.Key_Alt, "CapsLock": Qt.Key_CapsLock,
            "Tab": Qt.Key_Tab, "Esc": Qt.Key_Escape, "Enter": Qt.Key_Enter, "Space": Qt.Key_Space,
            "Backspace": Qt.Key_Backspace, "Slash": Qt.Key_Slash, "Backslash": Qt.Key_Backslash,
            "A": Qt.Key_A, "W": Qt.Key_W, "S": Qt.Key_S, "D": Qt.Key_D, "Q": Qt.Key_Q, "E": Qt.Key_E,
            "F": Qt.Key_F, "Z": Qt.Key_Z, "X": Qt.Key_X, "C": Qt.Key_C, "V": Qt.Key_V,
            "1": Qt.Key_1, "2": Qt.Key_2, "3": Qt.Key_3, "4": Qt.Key_4, "5": Qt.Key_5,
            "Up": Qt.Key_Up, "Down": Qt.Key_Down, "Left": Qt.Key_Left, "Right": Qt.Key_Right,
        }
        return mapping.get(value, 0)

    def _mouse_button(self, value):
        mapping = {
            "Left": Qt.LeftButton, "Right": Qt.RightButton, "Middle": Qt.MiddleButton,
            "XButton1 (Side)": Qt.XButton1, "XButton2 (Side)": Qt.XButton2,
            "Mouse 4": Qt.XButton1, "Mouse 5": Qt.XButton2,
            "Wheel Up": Qt.NoButton, "Wheel Down": Qt.NoButton, "Wheel Left": Qt.NoButton, "Wheel Right": Qt.NoButton,
        }
        return mapping.get(value, Qt.NoButton)

    def _poll_controller(self):
        if self._input_type != "controller" or not self._listening_active:
            return
        for index in range(4):
            button_set = _read_controller_state(index)
            if not button_set:
                continue
            if button_set - self._controller_state:
                choice = sorted(button_set - self._controller_state)[0]
                self._controller_state = button_set
                self.captured.emit({"type": "controller", "value": choice})
                self.hideOverlay()
                return
            self._controller_state = button_set
            return
        self._controller_state = set()




