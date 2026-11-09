from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ...models.profile import Profile
from ...storage.profile_store import (
    delete_profile, ensure_default, get_active_profile_name, load_profiles,
    rename_profile, save_profile, set_active_profile_name,
)
from .overlay import RenameOverlay, build_dialog, present_dialog
from .theme import (
    C, CAPSULE_SCROLL, QSS_PRIMARY, QSS_SECONDARY, QSS_SMALL_DANGER, QSS_SMALL_SECONDARY, QSS_DANGER,
    Button, Surface, chip, fade_in, label, panel_title,
)


class ProfilesPage(QWidget):
    active_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(16)
        hdr = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("Profiles")
        t.setStyleSheet("color:#ffffff; font-size:26px; font-weight:800; background:transparent;")
        s = QLabel("Group macros and switch setups in one click")
        s.setStyleSheet("color:%s; font-size:12px; font-weight:600; background:transparent;" % C.muted)
        col.addWidget(t)
        col.addWidget(s)
        hdr.addLayout(col)
        hdr.addStretch(1)
        b = Button("+ New Profile")
        b.setFixedSize(128, 34)
        b.setStyleSheet(QSS_PRIMARY)
        b.clicked.connect(self._create)
        hdr.addWidget(b)
        lay.addLayout(hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet(CAPSULE_SCROLL)
        self.inner = QWidget()
        self.inner.setStyleSheet("background:transparent;")
        self.v = QVBoxLayout(self.inner)
        self.v.setContentsMargins(0, 0, 6, 8)
        self.v.setSpacing(10)
        self.scroll.setWidget(self.inner)
        lay.addWidget(self.scroll, 1)

        self._rename_target = None
        self._rename_overlay = RenameOverlay(self)
        self._rename_overlay.renamed.connect(self._do_rename)
        self._overlay = None
        self._cards = []

        ensure_default()
        self.refresh()

    def showEvent(self, e):
        super().showEvent(e)
        fade_in(self, 0, 200)
        self._play_entrance()

    def _play_entrance(self):
        for i, card in enumerate(self._cards[:14]):
            try:
                fade_in(card, delay=40 + i * 35, duration=260)
            except RuntimeError:
                pass

    def refresh(self):
        while self.v.count():
            it = self.v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self._cards = []
        profiles = load_profiles()
        active = get_active_profile_name()
        if not profiles:
            l = QLabel("No profiles")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet("color:%s; padding:40px; background:transparent;" % C.faint)
            self.v.addWidget(l)
            return

        self.v.addWidget(self._section("ACTIVE"))
        act = next((p for p in profiles if p.name == active), profiles[0])
        self.v.addWidget(self._card(act, True))
        others = [p for p in profiles if p.name != act.name]
        if others:
            self.v.addSpacing(6)
            self.v.addWidget(self._section("OTHER PROFILES"))
            for p in others:
                self.v.addWidget(self._card(p, False))
        self.v.addStretch(1)

    def _section(self, text):
        return label(text, 10, 700, C.faint)

    def _card(self, profile, is_active):
        card = Surface(radius=14, bg=C.card, border=C.border, hover_bg=C.card_hi, hover_border=C.border_hi)
        card.set_accent(C.accent)
        card.set_accent_level(1.0 if is_active else 0.0, animate=False)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 14, 12)
        lay.setSpacing(8)
        top = QHBoxLayout()
        top.setSpacing(10)
        name = QLabel(profile.name)
        name.setStyleSheet("color:#ffffff; font-size:15px; font-weight:700; background:transparent;")
        top.addWidget(name)
        if is_active:
            top.addWidget(chip("ACTIVE", color=C.accent_hi, bg="#221f47"))
        top.addStretch(1)
        n = len(profile.macro_files)
        top.addWidget(chip("%d macro%s" % (n, "" if n == 1 else "s")))
        lay.addLayout(top)
        btns = QHBoxLayout()
        btns.setSpacing(6)
        if not is_active:
            sel = Button("Select")
            sel.setFixedHeight(30)
            sel.setStyleSheet(QSS_SMALL_SECONDARY)
            sel.clicked.connect(lambda _=False, n=profile.name: self._select(n))
            btns.addWidget(sel)
        ren = Button("Rename")
        ren.setFixedHeight(30)
        ren.setStyleSheet(QSS_SMALL_SECONDARY)
        ren.clicked.connect(lambda _=False, n=profile.name: self._rename(n))
        btns.addWidget(ren)
        btns.addStretch(1)
        dele = Button("Delete")
        dele.setFixedHeight(30)
        dele.setStyleSheet(QSS_SMALL_DANGER)
        dele.clicked.connect(lambda _=False, n=profile.name: self._delete(n))
        btns.addWidget(dele)
        lay.addLayout(btns)
        self._cards.append(card)
        return card

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._rename_overlay.isVisible():
            self._rename_overlay.setGeometry(self.rect())
        if self._overlay and self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())

    def _create(self):
        self._rename_target = "__create__"
        self._rename_overlay.setGeometry(self.rect())
        self._rename_overlay.edit.setPlaceholderText("Profile name")
        self._rename_overlay.set_title("New Profile")
        self._rename_overlay.open("")

    def _rename(self, name):
        self._rename_target = name
        self._rename_overlay.setGeometry(self.rect())
        self._rename_overlay.set_title("Rename Profile")
        self._rename_overlay.open(name)

    def _do_rename(self, new):
        if self._rename_target == "__create__":
            if new:
                existing = {p.name for p in load_profiles()}
                base = new
                i = 1
                while new in existing:
                    new = "%s (%d)" % (base, i)
                    i += 1
                save_profile(Profile(new))
                self.refresh()
                self._play_entrance()
        elif self._rename_target and new and new != self._rename_target:
            rename_profile(self._rename_target, new)
            self.refresh()
            self.active_changed.emit(get_active_profile_name())
        self._rename_target = None

    def _select(self, name):
        set_active_profile_name(name)
        self.refresh()
        self._play_entrance()
        self.active_changed.emit(name)

    def _close_dialog(self):
        ov = self._overlay
        self._overlay = None
        if ov is not None:
            ov.hideOverlay()
            ov.deleteLater()

    def _delete(self, name):
        if self._overlay:
            self._overlay.deleteLater()
        if len(load_profiles()) <= 1:
            self._overlay, panel, lay = build_dialog(self, 360, 150)
            lay.addWidget(panel_title("Cannot delete last profile"))
            lay.addWidget(label("You must have at least one profile.", 12, 400, C.muted))
            lay.addStretch(1)
            ok = Button("OK")
            ok.setStyleSheet(QSS_SECONDARY)
            ok.clicked.connect(self._close_dialog)
            lay.addWidget(ok, alignment=Qt.AlignmentFlag.AlignRight)
            present_dialog(self, self._overlay, panel)
            return
        self._overlay, panel, lay = build_dialog(self, 380, 170)
        lay.addWidget(panel_title('Delete "%s"?' % name))
        lay.addWidget(label("This removes the profile and all macros stored in it.", 12, 400, C.muted, wrap=True))
        lay.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(8)
        cancel = Button("Cancel")
        cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(self._close_dialog)
        dele = Button("Delete")
        dele.setStyleSheet(QSS_DANGER)

        def do_del():
            delete_profile(name)
            self._close_dialog()
            self.refresh()
            self._play_entrance()
            self.active_changed.emit(get_active_profile_name())

        dele.clicked.connect(do_del)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(dele)
        lay.addLayout(row)
        present_dialog(self, self._overlay, panel)
