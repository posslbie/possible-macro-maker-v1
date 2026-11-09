"""Possible Macro Maker - entry point."""
import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QMenu, QStackedWidget,
    QSystemTrayIcon, QWidget, QWidgetAction,
)

from app.storage.settings_store import get as sget

APP_NAME = "Possible Macro Maker"
APP_ID = "PossibleMacroMaker"


def _base_dir():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


ICON_PNG = os.path.join(_base_dir(), "assets", "icon.png")
ICON_ICO = os.path.join(_base_dir(), "assets", "icon.ico")


def _app_icon():
    for p in (ICON_ICO, ICON_PNG):
        if os.path.exists(p):
            return QIcon(p)
    return QIcon()


def _engine():
    try:
        from app.native.bridge import _get
        return _get()
    except Exception as e:
        print("[engine] load failed:", e)
        return None


def _push_engine_settings():
    """Push persisted window-lock / blacklist settings into the native engine."""
    try:
        from app.native.bridge import (
            set_window_blacklist, set_window_blacklist_enabled, set_window_lock_enabled, sync_all,
        )
        set_window_lock_enabled(bool(sget("window_lock_enabled")))
        set_window_blacklist(list(sget("window_blacklist") or []))
        set_window_blacklist_enabled(bool(sget("window_blacklist_enabled")))
        sync_all()
    except Exception as e:
        print("[engine sync]", e)


class MainWindow(QMainWindow):
    PAGE_INDEX = {"macros": 0, "editor": 1, "profiles": 2, "settings": 3}

    def __init__(self):
        super().__init__()
        from app.ui.qt.macro_editor_page import MacroEditorPage
        from app.ui.qt.macro_list_page import MacroListPage
        from app.ui.qt.profiles_page import ProfilesPage
        from app.ui.qt.settings_page import SettingsPage
        from app.ui.qt.sidebar import Sidebar
        from app.ui.qt.theme import C

        self._force_close = False
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(_app_icon())
        self.resize(1120, 740)
        self.setMinimumSize(940, 620)

        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet("#central{background:%s;}" % C.bg)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.stack = QStackedWidget()
        self.macros = MacroListPage()
        self.editor = MacroEditorPage()
        self.profiles = ProfilesPage()
        self.settings = SettingsPage()
        for page in (self.macros, self.editor, self.profiles, self.settings):
            self.stack.addWidget(page)
        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.sidebar.navigate.connect(self._nav)
        self.macros.edit_requested.connect(self._open_editor)
        self.editor.back_requested.connect(lambda: self._nav("macros"))
        self.editor.save_requested.connect(lambda _m: self.macros.refresh())
        self.profiles.active_changed.connect(self._on_profile_changed)

        self._setup_tray()

    # ---- navigation --------------------------------------------------------
    def _nav(self, key):
        idx = self.PAGE_INDEX.get(key)
        if idx is None:
            return
        self.sidebar.select("macros" if key == "editor" else key, emit=False)
        self.stack.setCurrentIndex(idx)
        if key == "macros":
            self.macros.refresh()
        elif key == "profiles":
            self.profiles.refresh()

    def _open_editor(self, macro):
        self.editor.load(macro)
        self.stack.setCurrentIndex(self.PAGE_INDEX["editor"])

    def _on_profile_changed(self, name):
        self.macros.set_active(name)
        try:
            from app.native.bridge import sync_all
            sync_all()
        except Exception:
            pass

    # ---- tray --------------------------------------------------------------
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(_app_icon(), self)
        self.tray.setToolTip("%s — engine running" % APP_NAME)
        self.tray_menu = QMenu()
        self.tray_menu.aboutToShow.connect(self._rebuild_tray_menu)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self._rebuild_tray_menu()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _switch_row(self, menu, text, checked, on_toggle):
        from app.ui.qt.theme import C, Toggle
        w = QWidget()
        w.setMinimumWidth(250)
        h = QHBoxLayout(w)
        h.setContentsMargins(14, 5, 12, 5)
        lbl = QLabel(text)
        lbl.setStyleSheet("color:%s; font-size:12px; background:transparent;" % C.text2)
        h.addWidget(lbl)
        h.addStretch(1)
        tog = Toggle(checked)
        tog.toggled.connect(on_toggle)
        h.addWidget(tog)
        act = QWidgetAction(menu)
        act.setDefaultWidget(w)
        menu.addAction(act)

    def _rebuild_tray_menu(self):
        from app.storage.macro_store import load_all, save_macro
        from app.storage.profile_store import (
            get_active_profile_name, load_profiles, load_single, set_active_profile_name,
        )
        menu = self.tray_menu
        menu.clear()
        show = menu.addAction("Show %s" % APP_NAME)
        show.triggered.connect(self._show_from_tray)
        menu.addSeparator()

        try:
            active = get_active_profile_name()
            prof_menu = menu.addMenu("Profile: %s" % (active or "—"))
            for p in load_profiles():
                a = prof_menu.addAction(p.name)
                a.setCheckable(True)
                a.setChecked(p.name == active)
                a.triggered.connect(lambda _=False, n=p.name: self._tray_select_profile(n))

            macros = load_all()
            profile = load_single(active) if active else None
            if profile is not None:
                by_name = {"%s.json" % m.name: m for m in macros}
                macros = [by_name[f] for f in list(profile.macro_files) if f in by_name]

            menu.addSeparator()
            if not macros:
                empty = menu.addAction("No macros in profile")
                empty.setEnabled(False)
            else:
                def set_all(on, items=macros):
                    for m in items:
                        self._tray_set_macro(m, on)
                self._switch_row(menu, "All", all(m.enabled for m in macros), set_all)
                for m in macros:
                    self._switch_row(menu, m.name, m.enabled, lambda on, mac=m: self._tray_set_macro(mac, on))
        except Exception as e:
            err = menu.addAction("Error: %s" % e)
            err.setEnabled(False)

        menu.addSeparator()
        try:
            from app.native.bridge import (
                get_window_blacklist_enabled, get_window_lock_enabled,
                set_window_blacklist_enabled, set_window_lock_enabled,
            )
            self._switch_row(menu, "Window lock", get_window_lock_enabled(),
                             lambda on: set_window_lock_enabled(on))
            self._switch_row(menu, "Window blacklist", get_window_blacklist_enabled(),
                             lambda on: set_window_blacklist_enabled(on))
            menu.addSeparator()
        except Exception:
            pass
        quit_act = menu.addAction("Quit")
        quit_act.triggered.connect(self._quit)

    def _tray_set_macro(self, macro, on):
        from app.storage.macro_store import save_macro
        try:
            macro.enabled = bool(on)
            save_macro(macro)
            try:
                from app.native.bridge import set_enabled
                set_enabled(macro.name, macro.enabled)
            except Exception:
                pass
            QTimer.singleShot(0, self.macros.refresh)
        except Exception as e:
            print("[tray toggle]", e)

    def _tray_select_profile(self, name):
        from app.storage.profile_store import set_active_profile_name
        set_active_profile_name(name)
        self.profiles.refresh()
        self._on_profile_changed(name)

    # ---- lifecycle ---------------------------------------------------------
    def _shutdown_engine(self):
        rt = _engine()
        for fn in ("rt_stop", "rt_shutdown"):
            try:
                getattr(rt, fn)()
            except Exception:
                pass

    def _quit(self):
        self._force_close = True
        self.close()

    def closeEvent(self, event):
        minimize = bool(sget("minimize_to_tray"))
        if minimize and not self._force_close and self.tray.isVisible():
            event.ignore()
            self.hide()
            try:
                from app.native.bridge import get_tick_ms
                tick = get_tick_ms()
            except Exception:
                tick = 1
            self.tray.showMessage(
                APP_NAME,
                "Minimized to tray — engine still running (%dms)" % tick,
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            return
        self._shutdown_engine()
        self.tray.hide()
        event.accept()
        QApplication.instance().quit()


def main():
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(_app_icon())

    from app.storage.profile_store import ensure_default
    from app.ui.qt import theme
    theme.install(app)
    ensure_default()

    rt = _engine()
    print("[engine] loaded" if rt else "[engine] not loaded")

    win = MainWindow()
    _push_engine_settings()  # after pages disabled all macros on startup
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
