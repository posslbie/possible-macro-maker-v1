"""Shared look & feel for Possible Macro Maker.

Palette, global stylesheet, animation helpers and a few small custom widgets
(animated Button / Toggle / Surface). Everything else in the UI builds on this.
"""
import os
import re
import sys

from PySide6.QtCore import (
    QAbstractAnimation, QEasingCurve, QPropertyAnimation, QRectF,
    QSequentialAnimationGroup, Qt, QTimer, QVariantAnimation, Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QLabel, QPushButton, QWidget


class C:
    """Colour palette."""
    bg = "#0b0d12"
    sidebar = "#0e1117"
    card = "#141922"
    card_hi = "#181e29"
    panel = "#1a202b"
    field = "#11151c"
    row = "#171c26"
    item = "#222938"
    control = "#1c222d"
    control_hi = "#2a3242"
    border = "#1f2632"
    border_hi = "#2f394b"
    text = "#eef1f7"
    text2 = "#c7cedb"
    muted = "#8b95a7"
    faint = "#566073"
    accent = "#7c6cff"
    accent_hi = "#9285ff"
    accent_lo = "#6a5ae8"
    accent2 = "#4fa3ff"
    ok = "#34d399"
    danger = "#f87171"
    danger_bg = "#2a1518"
    danger_hi = "#3d1c21"


# --------------------------------------------------------------------------- colours
def qcolor(value, fallback=None):
    if isinstance(value, QColor):
        return QColor(value)
    if value is None:
        return QColor(fallback) if fallback else QColor(0, 0, 0, 0)
    s = str(value).strip()
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", s)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if m.group(4) is None:
            a = 255
        else:
            af = float(m.group(4))
            a = int(af * 255) if af <= 1.0 else int(af)
        return QColor(r, g, b, max(0, min(255, a)))
    c = QColor(s)
    if not c.isValid():
        return QColor(fallback) if fallback else QColor(0, 0, 0, 0)
    return c


def mix(a, b, t):
    a, b = QColor(a), QColor(b)
    t = max(0.0, min(1.0, float(t)))
    if a.alpha() == 0:
        a = QColor(b.red(), b.green(), b.blue(), 0)
    elif b.alpha() == 0:
        b = QColor(a.red(), a.green(), a.blue(), 0)
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def with_alpha(color, alpha):
    c = qcolor(color)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


# --------------------------------------------------------------------------- paths
def project_root():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    here = os.path.dirname(os.path.abspath(__file__))  # app/ui/qt
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def asset_path(name):
    return os.path.join(project_root(), "assets", name)


# --------------------------------------------------------------------------- animation helpers
class Tween:
    """Small 0..1 value animator owned by a widget; calls `on_change` per frame."""

    def __init__(self, owner, duration=150, on_change=None, curve=QEasingCurve.Type.OutCubic):
        self.value = 0.0
        self._cb = on_change
        self._anim = QVariantAnimation(owner)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(curve)
        self._anim.valueChanged.connect(self._tick)

    def _tick(self, v):
        self.value = float(v)
        if self._cb:
            self._cb()

    def to(self, target, animate=True):
        target = float(target)
        self._anim.stop()
        if not animate:
            self.value = target
            if self._cb:
                self._cb()
            return
        self._anim.setStartValue(float(self.value))
        self._anim.setEndValue(target)
        self._anim.start()


def fade_in(widget, delay=0, duration=220):
    """Fade a widget in (optionally after `delay` ms). Safe to call repeatedly."""
    try:
        fx = QGraphicsOpacityEffect(widget)
        fx.setOpacity(0.0)
        widget.setGraphicsEffect(fx)
        token = object()
        widget._fade_token = token

        anim = QPropertyAnimation(fx, b"opacity", widget)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QSequentialAnimationGroup(widget)
        if delay > 0:
            group.addPause(int(delay))
        group.addAnimation(anim)

        def done():
            try:
                if getattr(widget, "_fade_token", None) is token:
                    widget.setGraphicsEffect(None)
            except RuntimeError:
                pass

        group.finished.connect(done)
        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    except RuntimeError:
        pass


# --------------------------------------------------------------------------- Button
_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_DECL_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;]+?)\s*(?:;|$)")


def _px(v, default=0.0):
    m = re.search(r"-?[\d.]+", str(v))
    return float(m.group(0)) if m else default


class _Style:
    def __init__(self):
        self.bg = None
        self.fg = None
        self.border_w = 0.0
        self.border_c = None
        self.radius = 8.0
        self.align_left = False
        self.pad_l = 0.0
        self.pad_r = 0.0
        self.font_px = 0
        self.weight = 0  # 0 normal, 1 semibold, 2 bold

    def copy(self):
        n = _Style()
        n.__dict__.update(self.__dict__)
        return n

    def apply(self, d):
        for k, v in d.items():
            if k in ("background", "background-color"):
                self.bg = None if v == "none" else qcolor(v)
            elif k == "color":
                self.fg = qcolor(v)
            elif k == "border":
                if v.strip() == "none":
                    self.border_w = 0.0
                else:
                    parts = v.split()
                    self.border_w = _px(parts[0])
                    self.border_c = qcolor(parts[-1])
            elif k == "border-radius":
                self.radius = _px(v)
            elif k == "text-align":
                self.align_left = v.strip() == "left"
            elif k == "padding-left":
                self.pad_l = _px(v)
            elif k == "padding":
                parts = [_px(x) for x in v.split()]
                if len(parts) == 1:
                    self.pad_l = self.pad_r = parts[0]
                elif len(parts) >= 2:
                    self.pad_l = self.pad_r = parts[1]
            elif k == "font-size":
                self.font_px = int(_px(v))
            elif k == "font-weight":
                w = v.strip().lower()
                if w in ("bold", "700", "800", "900"):
                    self.weight = 2
                elif w in ("600", "500"):
                    self.weight = 1


def _decls(body):
    return {m.group(1).lower(): m.group(2) for m in _DECL_RE.finditer(body)}


def _parse_button_css(css):
    """Turn the QSS a button was given into animated-paint states (or None)."""
    css = css or ""
    rules = {"base": {}, "hover": {}, "pressed": {}, "disabled": {}, "checked": {}}
    found = False
    for sel, body in _RULE_RE.findall(css):
        s = sel.strip().replace(" ", "")
        key = {
            "QPushButton": "base", "QPushButton:hover": "hover",
            "QPushButton:pressed": "pressed", "QPushButton:disabled": "disabled",
            "QPushButton:checked": "checked",
        }.get(s)
        if key:
            rules[key].update(_decls(body))
            found = True
    if not found and "{" not in css and ":" in css:
        rules["base"].update(_decls(css))
        found = True
    if not found or not any(k in rules["base"] for k in ("background", "background-color")):
        return None
    base = _Style()
    base.apply(rules["base"])
    hover = base.copy()
    hover.apply(rules["hover"])
    pressed = hover.copy()
    pressed.apply(rules["pressed"])
    if not any(k in rules["pressed"] for k in ("background", "background-color")):
        b = pressed.bg or base.bg
        if b is not None and b.alpha() > 0:
            pressed.bg = b.darker(112)
    disabled = base.copy()
    disabled.apply(rules["disabled"])
    checked = base.copy()
    checked.apply(rules["checked"])
    return {"base": base, "hover": hover, "pressed": pressed, "disabled": disabled, "checked": checked}


class Button(QPushButton):
    """QPushButton that keeps the legacy QSS API but paints with smooth hover/press animation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spec = None
        self._pressed = False
        self._hover = Tween(self, 140, self.update)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setStyleSheet(self, css):
        try:
            self._spec = _parse_button_css(css)
        except Exception:
            self._spec = None
        super().setStyleSheet(css)  # kept for sizing/padding + fallback rendering
        self.update()

    def enterEvent(self, e):
        self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover.to(0.0)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        spec = self._spec
        if not spec:
            return super().paintEvent(e)
        enabled = self.isEnabled()
        base = spec["checked"] if self.isChecked() else spec["base"]
        if not enabled:
            st = spec["disabled"]
            bg, fg, bc = st.bg, st.fg, st.border_c
            opacity = 0.5
        else:
            t = self._hover.value
            hov, prs = spec["hover"], spec["pressed"]
            bg = self._mix_opt(base.bg, hov.bg, t)
            fg = self._mix_opt(base.fg, hov.fg, t)
            bc = self._mix_opt(base.border_c, hov.border_c, t)
            if self._pressed and prs.bg is not None:
                bg = prs.bg
            st = base
            opacity = 1.0
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setOpacity(opacity)
        r = QRectF(self.rect())
        bw = st.border_w if bc is not None else 0.0
        rr = r.adjusted(bw / 2, bw / 2, -bw / 2, -bw / 2)
        radius = min(st.radius, rr.height() / 2)
        if bw > 0:
            p.setPen(QPen(bc, bw))
        else:
            p.setPen(Qt.PenStyle.NoPen)
        if bg is not None and bg.alpha() > 0:
            p.setBrush(bg)
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rr, radius, radius)

        f = QFont(self.font())
        if st.font_px:
            f.setPixelSize(st.font_px)
        if st.weight == 2:
            f.setWeight(QFont.Weight.Bold)
        elif st.weight == 1:
            f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(fg if fg is not None else qcolor(C.text2))
        if st.align_left:
            tr = self.rect().adjusted(int(st.pad_l or 10), 0, -int(st.pad_r or 6), 0)
            p.drawText(tr, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        else:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()

    @staticmethod
    def _mix_opt(a, b, t):
        if a is None and b is None:
            return None
        if a is None:
            a = QColor(b.red(), b.green(), b.blue(), 0)
        if b is None:
            b = a
        return mix(a, b, t)


# --------------------------------------------------------------------------- Toggle
class Toggle(QWidget):
    """Animated on/off switch. API: toggled(bool) signal, setChecked(), isChecked()."""
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._on = bool(checked)
        self._t = Tween(self, 190, self.update)
        self._t.value = 1.0 if self._on else 0.0

    def isChecked(self):
        return self._on

    def setChecked(self, v, animate=True):
        v = bool(v)
        if v == self._on:
            return
        self._on = v
        self._t.to(1.0 if v else 0.0, animate)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._on = not self._on
            self._t.to(1.0 if self._on else 0.0)
            self.toggled.emit(self._on)

    def paintEvent(self, e):
        t = self._t.value
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix(qcolor(C.control_hi), qcolor(C.accent), t))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        d = h - 8
        x = 4 + (w - 8 - d) * t
        p.setBrush(mix(qcolor(C.text2), qcolor("#ffffff"), t))
        p.drawEllipse(QRectF(x, 4, d, d))
        p.end()


# --------------------------------------------------------------------------- Surface (card)
class Surface(QFrame):
    """Rounded card that eases its border/background on hover and can show an accent edge."""

    def __init__(self, parent=None, radius=14, bg=None, border=None, hover_bg=None, hover_border=None):
        super().__init__(parent)
        self._radius = radius
        self._bg = qcolor(bg or C.card)
        self._border = qcolor(border or C.border)
        self._hbg = qcolor(hover_bg) if hover_bg else None
        self._hborder = qcolor(hover_border) if hover_border else None
        self._hover = Tween(self, 170, self.update)
        self._accent = Tween(self, 280, self.update)
        self._accent_color = qcolor(C.accent)

    def set_accent(self, color):
        self._accent_color = qcolor(color)
        self.update()

    def set_accent_level(self, level, animate=True):
        self._accent.to(level, animate)

    def enterEvent(self, e):
        if self._hbg or self._hborder:
            self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self._hbg or self._hborder:
            self._hover.to(0.0)
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._hover.value
        bg = mix(self._bg, self._hbg, t) if self._hbg else self._bg
        bc = mix(self._border, self._hborder, t) if self._hborder else self._border
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)
        p.fillPath(path, bg)
        a = self._accent.value
        if a > 0.01:
            p.save()
            p.setClipPath(path)
            c = QColor(self._accent_color)
            c.setAlphaF(max(0.0, min(1.0, a)))
            p.fillRect(QRectF(0, 0, 3, self.height()), c)
            p.restore()
        p.setPen(QPen(bc, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()


# --------------------------------------------------------------------------- small widget helpers
def label(text="", size=13, weight=400, color=None, wrap=False):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color:%s; font-size:%dpx; font-weight:%d; background:transparent; border:none;"
        % (color or C.text, size, weight)
    )
    lbl.setWordWrap(wrap)
    return lbl


def heading(text):
    return label(text, 15, 700, C.text)


def panel_title(text):
    return label(text, 16, 700, C.text)


def chip(text, color=None, bg=None):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "background:%s; color:%s; border:none; border-radius:9px; padding:3px 9px; font-size:11px; font-weight:600;"
        % (bg or C.control, color or C.muted)
    )
    return lbl


def style_panel(panel):
    panel.setObjectName("panel")
    panel.setStyleSheet(
        "QFrame#panel{background:%s; border:1px solid %s; border-radius:16px;}" % (C.panel, C.border_hi)
    )


def style_card(w, radius=14):
    w.setObjectName("card")
    w.setStyleSheet(
        "QFrame#card{background:%s; border:1px solid %s; border-radius:%dpx;}" % (C.card, C.border, radius)
    )


def style_row(w):
    w.setObjectName("row")
    w.setStyleSheet("QFrame#row{background:%s; border:none; border-radius:10px;}" % C.row)


def style_item(w):
    w.setObjectName("item")
    w.setStyleSheet("QFrame#item{background:%s; border:none; border-radius:8px;}" % C.item)


# Ready-made button styles (all go through Button's animated painter)
QSS_PRIMARY = (
    "QPushButton{background:%s; color:#ffffff; border:none; border-radius:9px; padding:8px 18px; font-weight:700;}"
    "QPushButton:hover{background:%s; color:#ffffff;} QPushButton:pressed{background:%s;}"
    % (C.accent, C.accent_hi, C.accent_lo)
)
QSS_SECONDARY = (
    "QPushButton{background:%s; color:%s; border:none; border-radius:9px; padding:8px 16px;}"
    "QPushButton:hover{background:%s; color:#ffffff;}" % (C.control, C.text2, C.control_hi)
)
QSS_GHOST = (
    "QPushButton{background:transparent; color:%s; border:1px solid %s; border-radius:9px; padding:8px 16px;}"
    "QPushButton:hover{background:%s; color:#ffffff; border:1px solid %s;}"
    % (C.muted, C.border_hi, C.control, C.border_hi)
)
QSS_DANGER = (
    "QPushButton{background:%s; color:%s; border:none; border-radius:9px; padding:8px 16px;}"
    "QPushButton:hover{background:%s; color:#ffffff;}" % (C.danger_bg, C.danger, C.danger_hi)
)
QSS_SMALL_SECONDARY = (
    "QPushButton{background:%s; color:%s; border:none; border-radius:8px; padding:0 14px; font-size:12px; font-weight:600;}"
    "QPushButton:hover{background:%s; color:#ffffff;}" % (C.control, C.text2, C.control_hi)
)
QSS_SMALL_GHOST = (
    "QPushButton{background:transparent; color:%s; border:none; border-radius:8px; padding:0 12px; font-size:12px;}"
    "QPushButton:hover{background:%s; color:#ffffff;}" % (C.muted, C.control)
)
QSS_SMALL_DANGER = (
    "QPushButton{background:transparent; color:%s; border:none; border-radius:8px; padding:0 12px; font-size:12px;}"
    "QPushButton:hover{background:%s; color:%s;}" % (C.muted, C.danger_bg, C.danger)
)

CAPSULE_SCROLL = (
    "QScrollArea{background:transparent; border:none;}"
    "QScrollBar:vertical{background:transparent; width:10px; margin:2px;}"
    "QScrollBar::handle:vertical{background:%s; border-radius:3px; min-height:28px;}"
    "QScrollBar::handle:vertical:hover{background:%s;}"
    "QScrollBar:horizontal{background:transparent; height:10px; margin:2px;}"
    "QScrollBar::handle:horizontal{background:%s; border-radius:3px; min-width:28px;}"
    "QScrollBar::add-line, QScrollBar::sub-line{height:0; width:0; border:none; background:none;}"
    "QScrollBar::add-page, QScrollBar::sub-page{background:transparent;}"
    % (C.control_hi, C.border_hi, C.control_hi)
)

GLOBAL_QSS = """
QToolTip{background:%(panel)s; color:%(text2)s; border:1px solid %(border_hi)s; padding:5px 8px; border-radius:6px;}
QMenu{background:%(card)s; color:%(text2)s; border:1px solid %(border_hi)s; border-radius:10px; padding:6px;}
QMenu::item{padding:7px 18px; border-radius:6px;}
QMenu::item:selected{background:%(item)s; color:#ffffff;}
QMenu::separator{height:1px; background:%(border)s; margin:6px 8px;}
QScrollBar:vertical{background:transparent; width:10px; margin:2px;}
QScrollBar::handle:vertical{background:%(control_hi)s; border-radius:3px; min-height:28px;}
QScrollBar::handle:vertical:hover{background:%(border_hi)s;}
QScrollBar:horizontal{background:transparent; height:10px; margin:2px;}
QScrollBar::handle:horizontal{background:%(control_hi)s; border-radius:3px; min-width:28px;}
QScrollBar::add-line, QScrollBar::sub-line{height:0; width:0; border:none; background:none;}
QScrollBar::add-page, QScrollBar::sub-page{background:transparent;}
QComboBox QAbstractItemView{background:%(panel)s; color:%(text2)s; selection-background-color:%(control_hi)s; border:1px solid %(border_hi)s; outline:0;}
QCheckBox{color:%(text2)s; spacing:8px;}
""" % {k: v for k, v in vars(C).items() if not k.startswith("_")}

_installed = False


def install(app):
    """Apply dark palette, font and global stylesheet once."""
    global _installed
    if _installed:
        return
    _installed = True
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: C.bg,
        QPalette.ColorRole.WindowText: C.text,
        QPalette.ColorRole.Base: C.field,
        QPalette.ColorRole.AlternateBase: C.row,
        QPalette.ColorRole.ToolTipBase: C.panel,
        QPalette.ColorRole.ToolTipText: C.text2,
        QPalette.ColorRole.Text: C.text,
        QPalette.ColorRole.Button: C.control,
        QPalette.ColorRole.ButtonText: C.text2,
        QPalette.ColorRole.BrightText: "#ffffff",
        QPalette.ColorRole.Highlight: C.accent,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: C.faint,
        QPalette.ColorRole.Link: C.accent2,
    }
    for role, col in roles.items():
        pal.setColor(role, QColor(col))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(C.faint))
    app.setPalette(pal)
    try:
        f = QFont(app.font())
        f.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "Arial"])
        f.setPointSizeF(10.0)
        app.setFont(f)
    except Exception:
        pass
    app.setStyleSheet((app.styleSheet() or "") + GLOBAL_QSS)
