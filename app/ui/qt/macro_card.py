from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...storage.macro_store import save_macro
from .theme import (
    C, QSS_SMALL_DANGER, QSS_SMALL_GHOST, QSS_SMALL_SECONDARY, Button, Surface, Toggle, Tween,
    chip, mix, qcolor, style_row, with_alpha,
)

_MAXH = 16777215


class StatusDot(QWidget):
    def __init__(self, on=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._t = Tween(self, 280, self.update)
        self._t.value = 1.0 if on else 0.0

    def set_on(self, on, animate=True):
        self._t.to(1.0 if on else 0.0, animate)

    def paintEvent(self, e):
        t = self._t.value
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        c = mix(qcolor(C.faint), qcolor(C.ok), t)
        if t > 0.01:
            p.setBrush(with_alpha(C.ok, 0.22 * t))
            p.drawEllipse(QRectF(0, 0, 16, 16))
        p.setBrush(c)
        p.drawEllipse(QRectF(4, 4, 8, 8))
        p.end()


class MacroCard(Surface):
    edit_clicked = Signal(object)
    delete_clicked = Signal(object)
    toggle_clicked = Signal(object)
    rename_clicked = Signal(object)
    export_clicked = Signal(object)
    assign_window_clicked = Signal(object)

    def __init__(self, macro, parent=None):
        super().__init__(parent, radius=14, bg=C.card, border=C.border, hover_bg=C.card_hi, hover_border=C.border_hi)
        self.macro = macro
        self.expanded = False
        self.set_accent(C.ok)
        self.set_accent_level(1.0 if macro.enabled else 0.0, animate=False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 14, 12)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.expand_btn = Button("▸")
        self.expand_btn.setFixedSize(26, 26)
        self.expand_btn.setStyleSheet(
            "QPushButton{background:%s; color:%s; border:none; border-radius:8px; font-size:11px; font-weight:700;}"
            "QPushButton:hover{background:%s; color:#ffffff;}" % (C.control, C.text2, C.control_hi)
        )
        self.expand_btn.clicked.connect(self._toggle_expanded)
        top.addWidget(self.expand_btn)

        self.dot = StatusDot(macro.enabled)
        top.addWidget(self.dot)
        name = QLabel(macro.name)
        name.setStyleSheet("color:#ffffff; font-size:14px; font-weight:700; background:transparent; border:none;")
        top.addWidget(name)
        top.addStretch(1)

        self.bind_button = Button(macro.bind.get("value", "Set bind") if macro.bind else "Set bind")
        self.bind_button.setFixedHeight(26)
        self.bind_button.setStyleSheet(
            "QPushButton{background:%s; color:%s; border:none; border-radius:13px; padding:0 14px; font-size:11px; font-weight:600;}"
            "QPushButton:hover{background:%s; color:#ffffff;}" % (C.control, C.text2, C.control_hi)
        )
        self.bind_button.clicked.connect(self._capture_bind)
        top.addWidget(self.bind_button)

        self.switch = Toggle(macro.enabled)
        self.switch.toggled.connect(lambda on: self.toggle_clicked.emit(self.macro))
        top.addWidget(self.switch)
        lay.addLayout(top)

        total_conditions = len(getattr(macro, "conditions", [])) + len(getattr(macro, "alt_conditions", []))
        n_steps = len(macro.steps)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        chips.setContentsMargins(36, 0, 0, 0)
        chips.addWidget(chip("%d condition%s" % (total_conditions, "" if total_conditions == 1 else "s")))
        chips.addWidget(chip("%d action%s" % (n_steps, "" if n_steps == 1 else "s")))
        if macro.category:
            chips.addWidget(chip(str(macro.category), color=C.accent_hi, bg="#221f47"))
        chips.addStretch(1)
        lay.addLayout(chips)

        # collapsible extra section
        self.extra = QWidget()
        self.extra.setVisible(False)
        self.extra.setMaximumHeight(0)
        extra_outer = QVBoxLayout(self.extra)
        extra_outer.setContentsMargins(0, 0, 0, 0)
        from PySide6.QtWidgets import QFrame
        box = QFrame()
        style_row(box)
        extra_lay = QVBoxLayout(box)
        extra_lay.setContentsMargins(14, 12, 12, 12)
        extra_lay.setSpacing(10)
        extra_outer.addWidget(box)

        excl = QHBoxLayout()
        excl.setSpacing(8)
        excl_label = QLabel("Exclusive condition listening")
        excl_label.setStyleSheet("color:%s; font-size:12px; background:transparent; border:none;" % C.text2)
        excl.addWidget(excl_label)
        excl.addStretch(1)
        self.exclusive_switch = Toggle(getattr(macro, "exclusive_condition_listening", False))
        self.exclusive_switch.toggled.connect(self._on_exclusive_toggle)
        excl.addWidget(self.exclusive_switch)
        extra_lay.addLayout(excl)

        assign_row = QHBoxLayout()
        assign_row.setSpacing(8)
        assign_label = QLabel("Window lock")
        assign_label.setStyleSheet("color:%s; font-size:12px; background:transparent; border:none;" % C.text2)
        assign_row.addWidget(assign_label)
        assign_row.addStretch(1)
        aw = Button("Assign to window")
        aw.setFixedHeight(28)
        aw.setStyleSheet(QSS_SMALL_SECONDARY)
        aw.clicked.connect(lambda: self.assign_window_clicked.emit(self.macro))
        assign_row.addWidget(aw)
        extra_lay.addLayout(assign_row)
        lay.addWidget(self.extra)

        self._exp_anim = QPropertyAnimation(self.extra, b"maximumHeight", self)
        self._exp_anim.setDuration(220)
        self._exp_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._exp_anim.finished.connect(self._exp_finished)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        for text, sig in (("Edit", self.edit_clicked), ("Rename", self.rename_clicked)):
            b = Button(text)
            b.setFixedHeight(30)
            b.setStyleSheet(QSS_SMALL_SECONDARY)
            b.clicked.connect(lambda _=False, s=sig: s.emit(self.macro))
            btns.addWidget(b)
        btns.addStretch(1)
        eb = Button("Export")
        eb.setFixedHeight(30)
        eb.setStyleSheet(QSS_SMALL_GHOST)
        eb.clicked.connect(lambda: self.export_clicked.emit(self.macro))
        btns.addWidget(eb)
        db = Button("Delete")
        db.setFixedHeight(30)
        db.setStyleSheet(QSS_SMALL_DANGER)
        db.clicked.connect(lambda: self.delete_clicked.emit(self.macro))
        btns.addWidget(db)
        lay.addLayout(btns)

    # ---- state ------------------------------------------------------------
    def apply_enabled(self, on):
        """Update visuals in place (no rebuild) so the toggle animation stays visible."""
        self.switch.setChecked(on)
        self.dot.set_on(on)
        self.set_accent_level(1.0 if on else 0.0)

    # ---- expand / collapse ------------------------------------------------
    def _toggle_expanded(self):
        self.expanded = not self.expanded
        self.expand_btn.setText("▾" if self.expanded else "▸")
        self._exp_anim.stop()
        if self.expanded:
            self.extra.setVisible(True)
            start = self.extra.height() if self.extra.maximumHeight() < _MAXH else 0
            end = max(1, self.extra.sizeHint().height())
        else:
            start = self.extra.height()
            end = 0
        self._exp_anim.setStartValue(int(start))
        self._exp_anim.setEndValue(int(end))
        self._exp_anim.start()

    def _exp_finished(self):
        if self.expanded:
            self.extra.setMaximumHeight(_MAXH)
        else:
            self.extra.setVisible(False)

    def _on_exclusive_toggle(self, on):
        self.macro.exclusive_condition_listening = bool(on)
        save_macro(self.macro)

    def _capture_bind(self):
        from .overlay import BindCaptureOverlay
        host = self.window() or self
        overlay = BindCaptureOverlay(host)
        overlay.setGeometry(host.rect())

        def on_captured(data):
            self.macro.bind = data
            save_macro(self.macro)
            self.bind_button.setText(data.get("value", "Set bind"))
            try:
                from ...native.bridge import sync_all
                sync_all()
            except Exception:
                pass

        overlay.captured.connect(on_captured)
        overlay.closed.connect(overlay.deleteLater)
        overlay.showOverlay()
