from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget,
)

from ...models.macro import Macro
from ...storage.macro_codes import decode_macro_code, encode_macro
from ...storage.macro_store import delete_macro, load_all, save_macro
from ...storage.profile_store import add_macro_to_profile, get_active_profile_name
from ...storage.profile_store import load_single as load_profile_single
from .macro_card import MacroCard
from .overlay import RenameOverlay, build_dialog, present_dialog
from .theme import (
    C, CAPSULE_SCROLL, QSS_PRIMARY, QSS_SECONDARY, Button, fade_in, panel_title,
)

_FIELD = (
    "QLineEdit{background:%s; color:%s; border:1px solid %s; border-radius:9px; padding:9px 10px;}"
    "QLineEdit:focus{border:1px solid %s;}" % (C.field, C.text, C.border, C.accent)
)


class MacroListPage(QWidget):
    edit_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(16)

        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title = QLabel("Macros")
        self.title.setStyleSheet("color:#ffffff; font-size:26px; font-weight:800; background:transparent;")
        title_col.addWidget(self.title)
        self.sub = QLabel("")
        self.sub.setStyleSheet("color:%s; font-size:12px; font-weight:600; background:transparent;" % C.muted)
        title_col.addWidget(self.sub)
        hdr.addLayout(title_col)
        hdr.addStretch(1)
        imp = Button("Import")
        imp.setFixedSize(88, 34)
        imp.setStyleSheet(QSS_SECONDARY)
        imp.clicked.connect(self._import_overlay)
        hdr.addWidget(imp)
        create = Button("+ Create")
        create.setFixedSize(98, 34)
        create.setStyleSheet(QSS_PRIMARY)
        create.clicked.connect(self._create)
        hdr.addWidget(create)
        lay.addLayout(hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet(CAPSULE_SCROLL)
        self.container = QWidget()
        self.container.setStyleSheet("background:transparent;")
        self.clay = QVBoxLayout(self.container)
        self.clay.setContentsMargins(0, 0, 6, 8)
        self.clay.setSpacing(10)
        self.clay.addStretch(1)
        self.scroll.setWidget(self.container)
        lay.addWidget(self.scroll, 1)

        self._rename_target = None
        self._rename_overlay = RenameOverlay(self)
        self._rename_overlay.renamed.connect(self._do_rename)
        self._overlay = None
        self._cards = []

        self._disable_all_on_startup()
        self.refresh()

    # ---- lifecycle ---------------------------------------------------------
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

    def _disable_all_on_startup(self):
        for m in load_all():
            if m.enabled:
                m.enabled = False
                save_macro(m)

    def set_active(self, name):
        self.refresh()
        self._play_entrance()

    def refresh(self):
        if getattr(self, "_in_refresh", False):
            return
        self._in_refresh = True
        try:
            active_name = get_active_profile_name()
            self.sub.setText("Profile: %s" % active_name if active_name else "No profile")
            while self.clay.count() > 1:
                it = self.clay.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()
            self._cards = []
            macros = load_all()
            profile = load_profile_single(active_name) if active_name else None
            if profile is not None:
                by_name = {"%s.json" % m.name: m for m in macros}
                macros = [by_name[f] for f in list(profile.macro_files) if f in by_name]
            if not macros:
                self.clay.insertWidget(0, self._empty_state(profile is not None))
                return
            for m in list(macros):
                card = MacroCard(m)
                card.edit_clicked.connect(self.edit_requested.emit)
                card.delete_clicked.connect(lambda _, mac=m: self._delete(mac))
                card.toggle_clicked.connect(lambda _, mac=m, c=card: self._toggle(mac, c))
                card.rename_clicked.connect(lambda _, mac=m: self._rename(mac))
                card.export_clicked.connect(lambda _, mac=m: self._export(mac))
                card.assign_window_clicked.connect(lambda _, mac=m: self._assign_to_window(mac))
                self.clay.insertWidget(self.clay.count() - 1, card)
                self._cards.append(card)
        finally:
            self._in_refresh = False

    def _empty_state(self, in_profile):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 70, 0, 0)
        v.setSpacing(8)
        v.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        t = QLabel("No macros in this profile" if in_profile else "No macros yet")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("color:%s; font-size:17px; font-weight:700; background:transparent;" % C.text2)
        s = QLabel("Create one to get started, or import a code from a friend.")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setStyleSheet("color:%s; font-size:12px; background:transparent;" % C.muted)
        b = Button("+ Create macro")
        b.setFixedSize(150, 38)
        b.setStyleSheet(QSS_PRIMARY)
        b.clicked.connect(self._create)
        v.addWidget(t)
        v.addWidget(s)
        v.addSpacing(10)
        v.addWidget(b, alignment=Qt.AlignmentFlag.AlignHCenter)
        return box

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_rename_overlay") and self._rename_overlay.isVisible():
            self._rename_overlay.setGeometry(self.rect())
        if self._overlay and self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())

    # ---- actions -----------------------------------------------------------
    def _create(self):
        base = "New Macro"
        name = base
        i = 1
        existing = {x.name for x in load_all()}
        while name in existing:
            name = "%s (%d)" % (base, i)
            i += 1
        m = Macro(name=name, enabled=False)
        save_macro(m)
        active = get_active_profile_name()
        if active:
            add_macro_to_profile(active, m.name)
        try:
            from ...native.bridge import sync_all
            sync_all()
        except Exception:
            pass
        self.refresh()
        self._play_entrance()

    def _delete(self, macro):
        try:
            from ...storage.profile_store import load_profiles, save_profile
            fname = "%s.json" % macro.name
            for p in load_profiles():
                if fname in p.macro_files:
                    p.macro_files.remove(fname)
                    save_profile(p)
        except Exception:
            pass
        delete_macro(macro.name)
        try:
            from ...native.bridge import sync_all
            sync_all()
        except Exception:
            pass
        # defer so we never delete a card from inside its own click handler
        QTimer.singleShot(0, self.refresh)

    def _toggle(self, macro, card=None):
        try:
            on = card.switch.isChecked() if card is not None else (not macro.enabled)
            macro.enabled = bool(on)
            save_macro(macro)
            try:
                from ...native.bridge import set_enabled
                set_enabled(macro.name, macro.enabled)
            except Exception:
                pass
            if card is not None:
                card.apply_enabled(macro.enabled)  # in-place update keeps the animation visible
        except Exception:
            try:
                self.refresh()
            except Exception:
                pass

    def _assign_to_window(self, macro):
        win = self.window()
        if not win:
            return
        if hasattr(win, "_nav"):
            win._nav("settings")
        if hasattr(win, "settings") and hasattr(win.settings, "focus_window_lock"):
            QTimer.singleShot(0, win.settings.focus_window_lock)

    def _rename(self, macro):
        self._rename_target = macro
        self._rename_overlay.setGeometry(self.rect())
        self._rename_overlay.set_title("Rename Macro")
        self._rename_overlay.open(macro.name)

    def _do_rename(self, new):
        if self._rename_target and new and new != self._rename_target.name:
            old_name = self._rename_target.name
            try:
                from ...storage.profile_store import load_profiles, save_profile
                for p in load_profiles():
                    fname_old = "%s.json" % old_name
                    if fname_old in p.macro_files:
                        p.macro_files = ["%s.json" % new if f == fname_old else f for f in p.macro_files]
                        save_profile(p)
            except Exception:
                pass
            delete_macro(old_name)
            self._rename_target.name = new
            save_macro(self._rename_target)
            try:
                from ...native.bridge import sync_all
                sync_all()
            except Exception:
                pass
            self.refresh()
        self._rename_target = None

    def _close_dialog(self):
        ov = self._overlay
        self._overlay = None
        if ov is not None:
            ov.hideOverlay()
            ov.deleteLater()

    def _export(self, macro):
        code = encode_macro(macro)
        if self._overlay:
            self._overlay.deleteLater()
        self._overlay, panel, lay = build_dialog(self, 440, 210)
        lay.addWidget(panel_title("Export — %s" % macro.name))
        edit = QLineEdit()
        edit.setText(code)
        edit.setReadOnly(True)
        edit.selectAll()
        edit.setStyleSheet(_FIELD)
        lay.addWidget(edit)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(8)
        close = Button("Close")
        close.setStyleSheet(QSS_SECONDARY)
        close.clicked.connect(self._close_dialog)
        copy = Button("Copy")
        copy.setStyleSheet(QSS_PRIMARY)

        def do_copy():
            QApplication.clipboard().setText(code)
            copy.setText("Copied!")

        copy.clicked.connect(do_copy)
        row.addStretch(1)
        row.addWidget(close)
        row.addWidget(copy)
        lay.addLayout(row)
        present_dialog(self, self._overlay, panel)

    def _import_overlay(self):
        if self._overlay:
            self._overlay.deleteLater()
        self._overlay, panel, lay = build_dialog(self, 440, 230)
        lay.addWidget(panel_title("Import Macro Code"))
        edit = QLineEdit()
        edit.setPlaceholderText("Paste code...")
        edit.setStyleSheet(_FIELD)
        lay.addWidget(edit)
        status = QLabel("")
        status.setStyleSheet("color:%s; font-size:11px; background:transparent;" % C.danger)
        lay.addWidget(status)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(8)
        cancel = Button("Cancel")
        cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(self._close_dialog)
        imp = Button("Import")
        imp.setStyleSheet(QSS_PRIMARY)

        def do_imp():
            data = decode_macro_code(edit.text().strip())
            if not data:
                status.setText("Invalid code")
                return
            m = Macro.from_dict(data)
            base = m.name
            i = 1
            existing = {x.name for x in load_all()}
            while m.name in existing:
                m.name = "%s (%d)" % (base, i)
                i += 1
            save_macro(m)
            active = get_active_profile_name()
            if active:
                add_macro_to_profile(active, m.name)
            self._close_dialog()
            self.refresh()
            self._play_entrance()

        imp.clicked.connect(do_imp)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(imp)
        lay.addLayout(row)
        present_dialog(self, self._overlay, panel)
        edit.setFocus()
