import os

from PySide6.QtCore import QPointF, QRectF, QUrl, Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .theme import C, Button, Tween, asset_path, mix, qcolor, with_alpha

# ---- Branding (edit freely) -------------------------------------------------
APP_TITLE = "POSSIBLE"
APP_SUBTITLE = "Macro Maker"
LINKS = [
    ("GitHub", "https://github.com/posslbie/possible-macro-maker-v1/releases/tag/macro"),
    ("TikTok", "https://www.tiktok.com/@posslbie"),
    ("Discord", "https://discord.gg/tuasK3dUxs"),
]
# -----------------------------------------------------------------------------


def _draw_icon(p, key, x, y, color):
    p.save()
    p.translate(x, y)
    p.setPen(QPen(color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if key == "macros":
        path = QPainterPath()
        path.moveTo(10.5, 1.5)
        path.lineTo(3.5, 10)
        path.lineTo(8.6, 10)
        path.lineTo(7.5, 16.5)
        path.lineTo(14.5, 8)
        path.lineTo(9.4, 8)
        path.closeSubpath()
        p.drawPath(path)
    elif key == "profiles":
        p.drawEllipse(QPointF(9, 6), 3.2, 3.2)
        path = QPainterPath()
        path.moveTo(3, 16)
        path.cubicTo(3, 11.2, 15, 11.2, 15, 16)
        p.drawPath(path)
    else:  # settings: sliders
        for yy, kx in ((4, 6), (9, 12), (14, 8)):
            p.drawLine(QPointF(2, yy), QPointF(16, yy))
            p.setBrush(qcolor(C.sidebar))
            p.drawEllipse(QPointF(kx, yy), 2.2, 2.2)
            p.setBrush(Qt.BrushStyle.NoBrush)
    p.restore()


class NavButton(QAbstractButton):
    def __init__(self, key, text, parent=None):
        super().__init__(parent)
        self.key = key
        self.setText(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(42)
        self._active = Tween(self, 240, self.update)
        self._hover = Tween(self, 140, self.update)

    def set_active(self, on, animate=True):
        self._active.to(1.0 if on else 0.0, animate)

    def enterEvent(self, e):
        self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover.to(0.0)
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        a, h = self._active.value, self._hover.value
        r = QRectF(self.rect()).adjusted(0, 2, 0, -2)
        p.setPen(Qt.PenStyle.NoPen)
        if h > 0.01 and a < 0.99:
            p.setBrush(with_alpha("#ffffff", 0.05 * h * (1 - a)))
            p.drawRoundedRect(r, 10, 10)
        if a > 0.01:
            p.setBrush(with_alpha(C.accent, 0.16 * a))
            p.drawRoundedRect(r, 10, 10)
            bar_h = 22 * a
            p.setBrush(qcolor(C.accent))
            p.drawRoundedRect(QRectF(0, r.center().y() - bar_h / 2, 3, bar_h), 1.5, 1.5)
        color = mix(qcolor(C.muted), qcolor("#ffffff"), max(a, h * 0.75))
        _draw_icon(p, self.key, 16, self.height() / 2 - 9, color)
        f = QFont(self.font())
        f.setPixelSize(13)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(color)
        p.drawText(
            QRectF(46, 0, self.width() - 46, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text(),
        )
        p.end()


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(224)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 22, 16, 16)
        lay.setSpacing(4)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        icon_path = asset_path("icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(
                38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            icon_lbl = QLabel()
            icon_lbl.setPixmap(pix)
            icon_lbl.setStyleSheet("background:transparent;")
            logo_row.addWidget(icon_lbl)
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        title = QLabel(APP_TITLE)
        title.setStyleSheet("color:#ffffff; font-size:17px; font-weight:800; background:transparent;")
        sub = QLabel(APP_SUBTITLE)
        sub.setStyleSheet("color:%s; font-size:12px; background:transparent;" % C.muted)
        text_col.addWidget(title)
        text_col.addWidget(sub)
        logo_row.addLayout(text_col)
        logo_row.addStretch(1)
        lay.addLayout(logo_row)
        lay.addSpacing(22)

        section = QLabel("MENU")
        section.setStyleSheet("color:%s; font-size:10px; font-weight:700; background:transparent; padding-left:6px;" % C.faint)
        lay.addWidget(section)
        lay.addSpacing(4)

        self.btns = {}
        self.active = None
        for key, text in (("macros", "Macros"), ("profiles", "Profiles"), ("settings", "Settings")):
            b = NavButton(key, text)
            b.clicked.connect(lambda _=False, k=key: self._go(k))
            lay.addWidget(b)
            self.btns[key] = b

        lay.addStretch(1)

        links_row = QHBoxLayout()
        links_row.setSpacing(2)
        for text, url in LINKS:
            btn = Button(text)
            btn.setFixedHeight(24)
            btn.setStyleSheet(
                "QPushButton{background:transparent; color:%s; border:none; border-radius:6px; padding:0 6px; font-size:11px;}"
                "QPushButton:hover{background:%s; color:#ffffff;}" % (C.accent2, C.control)
            )
            btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            links_row.addWidget(btn)
        links_row.addStretch(1)
        lay.addLayout(links_row)

        self.select("macros", emit=False, animate=False)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(C.sidebar))
        p.setPen(QPen(QColor(C.border), 1))
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        p.end()

    def select(self, key, emit=True, animate=True):
        if key not in self.btns or self.active == key:
            return
        if self.active in self.btns:
            self.btns[self.active].set_active(False, animate)
        self.btns[key].set_active(True, animate)
        self.active = key
        if emit:
            self.navigate.emit(key)

    def _go(self, key):
        self.select(key, emit=True)

    def set_active(self, key):
        self._go(key)
