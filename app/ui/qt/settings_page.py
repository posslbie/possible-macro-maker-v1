from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QSpinBox, QPlainTextEdit, QComboBox
from PySide6.QtCore import Qt, QTimer
from ...storage.settings_store import get, set as set_setting
from ...native.bridge import set_tick_ms, get_tick_ms, get_loop_ms, set_window_lock_enabled, get_window_lock_enabled, set_window_blacklist, get_window_blacklist, set_window_blacklist_enabled, get_window_blacklist_enabled
from .theme import (
    C, CAPSULE_SCROLL, QSS_PRIMARY, QSS_SECONDARY, Button, Toggle, fade_in, heading, panel_title,
    style_card, style_panel, style_row,
)

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(20,16,20,20); lay.setSpacing(10)
        hdr = QHBoxLayout(); t=QLabel("Settings"); t.setStyleSheet("color:#ffffff; font-size:22px; font-weight:800;")
        hdr.addWidget(t); hdr.addStretch(1); lay.addLayout(hdr)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(CAPSULE_SCROLL)
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        v = QVBoxLayout(inner); v.setContentsMargins(0,0,0,0); v.setSpacing(12)
        scroll.setWidget(inner); lay.addWidget(scroll,1)

        # General
        gen = QFrame(); style_card(gen)
        gl=QVBoxLayout(gen); gl.setContentsMargins(16,16,16,16); gl.setSpacing(8)
        gl.addWidget(heading("General"))
        row=QHBoxLayout(); row.addWidget(QLabel("Minimize to tray on close")); row.addStretch(1)
        self.tray_sw=Toggle(bool(get("minimize_to_tray"))); self.tray_sw.toggled.connect(lambda v: set_setting("minimize_to_tray", bool(v)))
        row.addWidget(self.tray_sw); gl.addLayout(row)
        hint2=QLabel("When enabled, closing keeps engine running in tray. Double-click tray to restore."); hint2.setStyleSheet("color:#6b7587; font-size:11px;"); hint2.setWordWrap(True); gl.addWidget(hint2)
        v.addWidget(gen)

        # Window Lock
        self.win = QFrame(); style_card(self.win)
        win = self.win
        wl=QVBoxLayout(win); wl.setContentsMargins(16,16,16,16); wl.setSpacing(10)
        top=QHBoxLayout(); top.addWidget(heading("Window lock")); top.addStretch(1)
        self.win_toggle=Toggle(bool(get_window_lock_enabled())); self.win_toggle.toggled.connect(self._on_win_toggle)
        top.addWidget(self.win_toggle)
        wl.addLayout(top)
        desc=QLabel("Only fire macros when a selected window is in focus."); desc.setStyleSheet("color:#6b7587; font-size:11px;"); desc.setWordWrap(True); wl.addWidget(desc)
        self.win_scroll=QScrollArea(); self.win_scroll.setFixedHeight(240); self.win_scroll.setWidgetResizable(True); self.win_scroll.setFrameShape(QFrame.NoFrame)
        self.win_scroll.setStyleSheet("QScrollArea{background:transparent; border:none; border-radius:10px;} QScrollBar:vertical{background:transparent; width:8px; margin:2px;} QScrollBar::handle:vertical{background:#222938; border-radius:4px; min-height:24px;}")
        self.win_inner=QWidget(); self.win_inner.setStyleSheet("background:transparent;")
        self.win_lay=QVBoxLayout(self.win_inner); self.win_lay.setContentsMargins(8,8,8,8); self.win_lay.setSpacing(8); self.win_lay.addStretch(1)
        self.win_scroll.setWidget(self.win_inner); wl.addWidget(self.win_scroll)
        btn_row=QHBoxLayout()
        add_win=Button("Add Window"); add_win.setFixedHeight(32); add_win.setCursor(Qt.PointingHandCursor)
        add_win.setStyleSheet("QPushButton{background:#1c222d; color:#ffffff; border:none; border-radius:8px; padding:0 12px;} QPushButton:hover{background:#2a3242;}")
        add_win.clicked.connect(self._add_window)
        btn_row.addWidget(add_win); btn_row.addStretch(1)
        refresh=Button("Refresh"); refresh.setFixedHeight(32); refresh.setCursor(Qt.PointingHandCursor)
        refresh.setStyleSheet("QPushButton{background:transparent; color:#8b95a7; border:none; border-radius:8px; padding:0 12px;} QPushButton:hover{color:#ffffff;}")
        refresh.clicked.connect(self._refresh_windows)
        btn_row.addWidget(refresh)
        wl.addLayout(btn_row)
        v.addWidget(win)

        # Window Blacklist
        black = QFrame(); style_card(black)
        bl=QVBoxLayout(black); bl.setContentsMargins(16,16,16,16); bl.setSpacing(10)
        black_top=QHBoxLayout(); black_top.addWidget(heading("Window blacklist")); black_top.addStretch(1)
        self.black_toggle=Toggle(bool(get_window_blacklist_enabled())); self.black_toggle.toggled.connect(self._on_black_toggle)
        black_top.addWidget(self.black_toggle)
        bl.addLayout(black_top)
        bl_desc = QLabel("Macros will not run while a blocked window is focused.")
        bl_desc.setStyleSheet("color:#6b7587; font-size:11px;"); bl_desc.setWordWrap(True)
        bl.addWidget(bl_desc)
        self.black_scroll = QScrollArea(); self.black_scroll.setFixedHeight(160); self.black_scroll.setWidgetResizable(True); self.black_scroll.setFrameShape(QFrame.NoFrame)
        self.black_scroll.setStyleSheet("QScrollArea{background:transparent; border:none; border-radius:10px;} QScrollBar:vertical{background:transparent; width:8px; margin:2px;} QScrollBar::handle:vertical{background:#222938; border-radius:4px; min-height:24px;}")
        self.black_inner=QWidget(); self.black_inner.setStyleSheet("background:transparent;")
        self.black_lay=QVBoxLayout(self.black_inner); self.black_lay.setContentsMargins(8,8,8,8); self.black_lay.setSpacing(8); self.black_lay.addStretch(1)
        self.black_scroll.setWidget(self.black_inner); bl.addWidget(self.black_scroll)
        black_row = QHBoxLayout()
        add_black = Button("Add blocked window"); add_black.setFixedHeight(32); add_black.setCursor(Qt.PointingHandCursor)
        add_black.setStyleSheet("QPushButton{background:#1c222d; color:#ffffff; border:none; border-radius:8px; padding:0 12px;} QPushButton:hover{background:#2a3242;}")
        add_black.clicked.connect(self._add_blacklist_window)
        black_row.addWidget(add_black)
        clear_black = Button("Clear"); clear_black.setFixedHeight(32); clear_black.setCursor(Qt.PointingHandCursor)
        clear_black.setStyleSheet("QPushButton{background:transparent; color:#8b95a7; border:none; border-radius:8px; padding:0 12px;} QPushButton:hover{color:#ffffff;}")
        clear_black.clicked.connect(self._clear_blacklist)
        black_row.addWidget(clear_black)
        bl.addLayout(black_row)
        v.addWidget(black)

        # Engine at bottom
        eng = QFrame(); style_card(eng)
        el=QVBoxLayout(eng); el.setContentsMargins(16,16,16,16); el.setSpacing(10)
        el.addWidget(heading("Engine"))
        row=QHBoxLayout(); row.addWidget(QLabel("Tick rate (ms)")); row.addStretch(1)
        self.tick_locked = True
        self.spin=QSpinBox(); self.spin.setRange(1,50); self.spin.setValue(int(get("engine_tick_ms") or get_tick_ms()))
        self.spin.setButtonSymbols(QSpinBox.NoButtons)
        self.spin.setEnabled(False)
        self.spin.setStyleSheet("QSpinBox{background:#171c26; color:#6b7587; border:1px solid #1e2531; border-radius:8px; padding:8px; min-width:60px;} QSpinBox:focus{border:1px solid #7c6cff;} QSpinBox::up-button, QSpinBox::down-button{width:0; height:0; border:none; background:transparent;} QSpinBox::up-arrow, QSpinBox::down-arrow{width:0; height:0;}")
        self.spin.valueChanged.connect(self._on_tick)
        row.addWidget(self.spin)
        self.tick_lock_btn = Button("🔒 Locked"); self.tick_lock_btn.setFixedHeight(28); self.tick_lock_btn.setCursor(Qt.PointingHandCursor)
        self.tick_lock_btn.setStyleSheet("QPushButton{background:#222938; color:#e3e8f0; border:none; border-radius:6px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#2a3242; color:#ffffff;}")
        self.tick_lock_btn.clicked.connect(self._toggle_tick_lock)
        row.addWidget(self.tick_lock_btn)
        self.reset_btn=Button("Reset"); self.reset_btn.setFixedHeight(28); self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setStyleSheet("QPushButton{background:#1c222d; color:#8b95a7; border:none; border-radius:6px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#2a3242; color:#c7cedb;}")
        self.reset_btn.clicked.connect(lambda: self.spin.setValue(1) if not self.tick_locked else None)
        self.reset_btn.setEnabled(False)
        row.addWidget(self.reset_btn)
        el.addLayout(row)
        hint=QLabel("1ms = 1000Hz fastest, 30-50ms idle friendly. Restart not needed.")
        hint.setStyleSheet("color:#6b7587; font-size:11px;"); hint.setWordWrap(True); el.addWidget(hint)
        self.loop_lbl=QLabel("Loop: — ms"); self.loop_lbl.setStyleSheet("color:#c7cedb; font-size:11px; background:#11151c; border-radius:8px; padding:8px;")
        el.addWidget(self.loop_lbl)
        self._timer=QTimer(self); self._timer.timeout.connect(self._poll); self._timer.start(250)
        v.addWidget(eng)

        test = QFrame(); style_card(test)
        tl=QVBoxLayout(test); tl.setContentsMargins(16,16,16,16); tl.setSpacing(10)
        tl.addWidget(heading("Engine Test"))
        desc2=QLabel("Live staged bench at your tick rate — consistency, speed, jitter.")
        desc2.setStyleSheet("color:#6b7587; font-size:11px;"); desc2.setWordWrap(True); tl.addWidget(desc2)
        self.test_btn=Button("Test Engine"); self.test_btn.setCursor(Qt.PointingHandCursor); self.test_btn.setFixedHeight(36)
        self.test_btn.setStyleSheet("QPushButton{background:#222938; color:#ffffff; border:none; border-radius:8px; font-weight:700;} QPushButton:hover{background:#2a3242;}")
        self.test_btn.clicked.connect(self._test)
        tl.addWidget(self.test_btn)
        self.out=QPlainTextEdit(); self.out.setReadOnly(True); self.out.setFixedHeight(180)
        self.out.setStyleSheet("QPlainTextEdit{background:#11151c; color:#c7cedb; border:none; border-radius:8px; padding:8px; font-family: Consolas, monospace; font-size:11px;} QScrollBar:vertical{background:transparent; width:8px;} QScrollBar::handle:vertical{background:#222938; border-radius:4px;}")
        self.out.hide(); tl.addWidget(self.out)
        v.addWidget(test); v.addStretch(1)

        self._refresh_windows()
        self._refresh_blacklist()

    def showEvent(self, e):
        super().showEvent(e)
        fade_in(self, 0, 200)
        self._refresh_windows()
        self._refresh_blacklist()

    def focus_window_lock(self):
        if hasattr(self, "win_scroll") and hasattr(self, "win"):
            self.win_scroll.ensureWidgetVisible(self.win, 0, 0)
            vbar = self.win_scroll.verticalScrollBar()
            if vbar is not None:
                vbar.setValue(vbar.maximum())

    def _on_win_toggle(self, v):
        set_setting("window_lock_enabled", bool(v))
        set_window_lock_enabled(bool(v))

    def _on_black_toggle(self, v):
        set_setting("window_blacklist_enabled", bool(v))
        set_window_blacklist_enabled(bool(v))
        self.black_scroll.setVisible(bool(v))
        if not v:
            empty=QLabel("Blacklist disabled")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#566073; background:transparent; padding:16px; font-size:11px;")
            while self.black_lay.count():
                it=self.black_lay.takeAt(0)
                if it.widget(): it.widget().deleteLater()
            self.black_lay.addWidget(empty)
        else:
            self._refresh_blacklist()

    def _refresh_windows(self):
        while self.win_lay.count()>1:
            it=self.win_lay.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        try:
            from ...storage.macro_store import load_all
            from ...storage.settings_store import get as sget
            macros=load_all()
            # existing windows from settings + from macros (for legacy)
            stored = list(sget("window_lock_windows") or [])
            # dedupe with current macros' focus_windows
            for m in macros:
                if m.focus_window and m.focus_window not in stored:
                    stored.append(m.focus_window)
            # only show stored windows, empty by default
            if not stored:
                empty=QLabel("No window locks\nAdd a window to assign macros."); empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet("color:#566073; background:transparent; padding:20px; font-size:11px;")
                self.win_lay.insertWidget(0, empty)
                return
            for win_title in sorted(stored):
                # current macros for this window (only current, not deleted)
                ms=[m for m in macros if m.focus_window==win_title]
                card=QFrame(); style_row(card)
                cl=QVBoxLayout(card); cl.setContentsMargins(10,10,10,10); cl.setSpacing(8)
                hdr=QHBoxLayout()
                icon=QLabel("◧"); icon.setStyleSheet("color:#566073; font-size:14px;")
                hdr.addWidget(icon)
                title=QLabel(win_title); title.setStyleSheet("color:#c7cedb; font-size:12px; font-weight:600;")
                hdr.addWidget(title)
                hdr.addStretch(1)
                cnt=QLabel(f"{len(ms)} macros"); cnt.setStyleSheet("color:#6b7587; font-size:11px; background:#1c222d; border-radius:6px; padding:2px 8px;")
                hdr.addWidget(cnt)
                cl.addLayout(hdr)
                if ms:
                    chips=QHBoxLayout(); chips.setSpacing(6)
                    for m in ms[:6]:
                        chip=QLabel(m.name); chip.setStyleSheet("background:#1c222d; color:#a4adbd; border-radius:6px; padding:3px 8px; font-size:11px;")
                        chips.addWidget(chip)
                    if len(ms)>6:
                        more=QLabel(f"+{len(ms)-6}"); more.setStyleSheet("color:#6b7587; font-size:11px;"); chips.addWidget(more)
                    chips.addStretch(1)
                    cl.addLayout(chips)
                else:
                    hint=QLabel("No macros assigned"); hint.setStyleSheet("color:#566073; font-size:11px; padding:4px 2px;")
                    cl.addWidget(hint)
                btn_row=QHBoxLayout()
                assign=Button("Add macro"); assign.setFixedHeight(26); assign.setCursor(Qt.PointingHandCursor)
                assign.setStyleSheet("QPushButton{background:#1c222d; color:#a4adbd; border:none; border-radius:6px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#2a3242; color:#c7cedb;}")
                assign.clicked.connect(lambda _, w=win_title: self._assign_to_window(w))
                btn_row.addWidget(assign)
                remove_win=Button("Remove window"); remove_win.setFixedHeight(26); remove_win.setCursor(Qt.PointingHandCursor)
                remove_win.setStyleSheet("QPushButton{background:transparent; color:#6b7587; border:none; border-radius:6px; padding:0 10px; font-size:11px;} QPushButton:hover{color:#f87171;}")
                remove_win.clicked.connect(lambda _, w=win_title: self._remove_window(w))
                btn_row.addWidget(remove_win)
                btn_row.addStretch(1)
                cl.addLayout(btn_row)
                self.win_lay.insertWidget(self.win_lay.count()-1, card)
        except Exception as e:
            l=QLabel(f"Error: {e}"); l.setStyleSheet("color:#f87171;"); self.win_lay.insertWidget(0,l)

    def _add_window(self):
        from ...storage.window_info import list_windows
        from ...storage.settings_store import get as sget, set as sset
        from .overlay import BaseOverlay
        wins=list_windows()
        if not wins:
            return
        ov=BaseOverlay(self); ov.setGeometry(self.rect())
        panel=QFrame(ov); panel.setFixedSize(380, 360)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)
        lay.addWidget(panel_title("Select Window"))
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(CAPSULE_SCROLL)
        inner=QWidget(); inner.setStyleSheet("background:transparent;")
        v=QVBoxLayout(inner); v.setSpacing(6)
        for w in wins:
            b=Button(w); b.setFixedHeight(34); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{background:#1c222d; color:#c7cedb; border:none; border-radius:8px; text-align:left; padding-left:12px;} QPushButton:hover{background:#2a3242;}")
            def make(win):
                def cb():
                    # persist window even if no macros yet
                    cur=list(sget("window_lock_windows") or [])
                    if win not in cur:
                        cur.append(win); sset("window_lock_windows", cur)
                    if not bool(get_window_lock_enabled()):
                        self.win_toggle.setChecked(True)
                        self._on_win_toggle(True)
                    ov.hideOverlay(); ov.deleteLater()
                    self._refresh_windows()
                    # then assign
                    self._assign_to_window(win)
                return cb
            b.clicked.connect(make(w))
            v.addWidget(b)
        v.addStretch(1); scroll.setWidget(inner); lay.addWidget(scroll,1)
        cancel=Button("Cancel"); cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (ov.hideOverlay(), ov.deleteLater()))
        lay.addWidget(cancel)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        ov.showOverlay()
        self._ov=ov

    def _add_blacklist_window(self):
        from ...storage.window_info import list_windows
        from .overlay import BaseOverlay
        wins=list_windows()
        if not wins:
            return
        ov=BaseOverlay(self); ov.setGeometry(self.rect())
        panel=QFrame(ov); panel.setFixedSize(380, 320)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)
        lay.addWidget(panel_title("Block Window"))
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(CAPSULE_SCROLL)
        inner=QWidget(); inner.setStyleSheet("background:transparent;")
        v=QVBoxLayout(inner); v.setSpacing(6)
        for w in wins:
            b=Button(w); b.setFixedHeight(34); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{background:#1c222d; color:#c7cedb; border:none; border-radius:8px; text-align:left; padding-left:12px;} QPushButton:hover{background:#2a3242;}")
            def make(win):
                def cb():
                    cur=list(get_window_blacklist())
                    if win not in cur:
                        cur.append(win)
                        set_window_blacklist(cur)
                    if not bool(get_window_blacklist_enabled()):
                        self.black_toggle.setChecked(True)
                        self._on_black_toggle(True)
                    ov.hideOverlay(); ov.deleteLater()
                    self._refresh_blacklist()
                return cb
            b.clicked.connect(make(w))
            v.addWidget(b)
        v.addStretch(1); scroll.setWidget(inner); lay.addWidget(scroll,1)
        cancel=Button("Cancel"); cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (ov.hideOverlay(), ov.deleteLater()))
        lay.addWidget(cancel)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        ov.showOverlay()
        self._ov_black = ov

    def _refresh_blacklist(self):
        while self.black_lay.count()>1:
            it=self.black_lay.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        blocked = list(get_window_blacklist())
        if not blocked:
            empty=QLabel("No blocked windows")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#566073; background:transparent; padding:16px; font-size:11px;")
            self.black_lay.insertWidget(0, empty)
            return
        for win_title in sorted(blocked):
            row=QFrame(); style_row(row)
            lay=QHBoxLayout(row); lay.setContentsMargins(10,8,10,8); lay.setSpacing(8)
            label=QLabel(win_title); label.setStyleSheet("color:#c7cedb; font-size:12px; font-weight:600;")
            lay.addWidget(label)
            lay.addStretch(1)
            remove=Button("Remove"); remove.setFixedHeight(24); remove.setCursor(Qt.PointingHandCursor)
            remove.setStyleSheet("QPushButton{background:transparent; color:#6b7587; border:none; border-radius:6px; padding:0 10px; font-size:11px;} QPushButton:hover{color:#f87171;}")
            remove.clicked.connect(lambda _, w=win_title: self._remove_blacklist_window(w))
            lay.addWidget(remove)
            self.black_lay.insertWidget(self.black_lay.count()-1, row)

    def _remove_blacklist_window(self, win_title):
        cur=list(get_window_blacklist())
        if win_title in cur:
            cur.remove(win_title)
            set_window_blacklist(cur)
        self._refresh_blacklist()

    def _clear_blacklist(self):
        set_window_blacklist([])
        self._refresh_blacklist()

    def _remove_window(self, win_title):
        from ...storage.settings_store import get as sget, set as sset
        cur=list(sget("window_lock_windows") or [])
        if win_title in cur:
            cur.remove(win_title); sset("window_lock_windows", cur)
        # clear macros assigned to this window
        from ...storage.macro_store import load_all, save_macro
        for m in load_all():
            if m.focus_window==win_title:
                m.focus_window=""; save_macro(m)
        try:
            from ...native.bridge import sync_all; sync_all()
        except: pass
        self._refresh_windows()

    def _assign_to_window(self, win_title):
        from ...storage.settings_store import get as sget, set as sset
        # ensure window in list
        cur=list(sget("window_lock_windows") or [])
        if win_title not in cur:
            cur.append(win_title); sset("window_lock_windows", cur)
        from ...storage.macro_store import load_all, save_macro
        from .overlay import BaseOverlay
        macros=[m for m in load_all() if m.name]  # only current macros, not deleted
        ov=BaseOverlay(self); ov.setGeometry(self.rect())
        panel=QFrame(ov); panel.setFixedSize(400, 380)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)
        title="Always" if win_title=="Always" else win_title
        lay.addWidget(QLabel(f"Assign to: {title}"))
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(CAPSULE_SCROLL)
        inner=QWidget(); inner.setStyleSheet("background:transparent;")
        v=QVBoxLayout(inner); v.setSpacing(6)
        checks=[]
        for m in macros:
            from PySide6.QtWidgets import QCheckBox
            cb=QCheckBox(m.name); cb.setStyleSheet("QCheckBox{color:#c7cedb;} QCheckBox::indicator{width:16px; height:16px; border-radius:4px; border:none; background:#1c222d;} QCheckBox::indicator:checked{background:#7c6cff; border-color:#7c6cff;}")
            is_assigned = (m.focus_window or "") == ("" if win_title=="Always" else win_title)
            cb.setChecked(is_assigned)
            v.addWidget(cb); checks.append((m, cb))
        v.addStretch(1); scroll.setWidget(inner); lay.addWidget(scroll,1)
        row=QHBoxLayout()
        cancel=Button("Cancel"); cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (ov.hideOverlay(), ov.deleteLater()))
        save=Button("Save"); save.setStyleSheet(QSS_PRIMARY)
        def do_save():
            for m, cb in checks:
                m.focus_window = "" if win_title=="Always" else win_title if cb.isChecked() else (m.focus_window if m.focus_window != ("" if win_title=="Always" else win_title) else "")
                # if checked, set to win_title, if unchecked and was this window, clear
                if cb.isChecked():
                    m.focus_window = "" if win_title=="Always" else win_title
                else:
                    if (m.focus_window or "") == ("" if win_title=="Always" else win_title):
                        m.focus_window = ""
                save_macro(m)
            try:
                from ...native.bridge import sync_all; sync_all()
            except: pass
            ov.hideOverlay(); ov.deleteLater(); self._refresh_windows()
        save.clicked.connect(do_save)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(save); lay.addLayout(row)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        ov.showOverlay()
        self._ov2=ov

    def _clear_window(self, win_title):
        from ...storage.macro_store import load_all, save_macro
        for m in load_all():
            if m.focus_window == win_title:
                m.focus_window=""; save_macro(m)
        try:
            from ...native.bridge import sync_all; sync_all()
        except: pass
        self._refresh_windows()

    def _toggle_tick_lock(self):
        self.tick_locked = not self.tick_locked
        self.spin.setEnabled(not self.tick_locked)
        self.reset_btn.setEnabled(not self.tick_locked)
        self.tick_lock_btn.setText("🔒 Locked" if self.tick_locked else "🔓 Unlocked")
        self.tick_lock_btn.setStyleSheet(
            "QPushButton{background:%s; color:%s; border:none; border-radius:6px; padding:0 10px; font-size:11px;} QPushButton:hover{background:%s; color:%s;}" % (
                "#222938" if self.tick_locked else "#2b2a5e",
                "#e3e8f0" if self.tick_locked else "#ddd9ff",
                "#2a3242" if self.tick_locked else "#9285ff",
                "#ffffff" if self.tick_locked else "#ffffff",
            )
        )
        if self.tick_locked:
            self.spin.blockSignals(True)
            self.spin.setValue(int(get("engine_tick_ms") or get_tick_ms()))
            self.spin.blockSignals(False)

    def _on_tick(self, v):
        if self.tick_locked:
            self.spin.blockSignals(True)
            self.spin.setValue(int(get("engine_tick_ms") or get_tick_ms()))
            self.spin.blockSignals(False)
            return
        set_setting("engine_tick_ms", int(v))
        try: set_tick_ms(int(v))
        except: pass

    def _poll(self):
        try: ms=get_loop_ms()
        except: ms=0
        self.loop_lbl.setText(f"Loop: {ms:.2f} ms  •  Tick {get_tick_ms()} ms")

    def _log(self, s):
        self.out.appendPlainText(s)
        self.out.verticalScrollBar().setValue(self.out.verticalScrollBar().maximum())
        from PySide6.QtWidgets import QApplication; QApplication.processEvents()

    def _test(self):
        self.test_btn.setEnabled(False); self.test_btn.setText("Running…")
        self.out.clear(); self.out.show()
        tick=get_tick_ms()
        import random, time
        self._log(f"Tick {tick}ms ({1000//tick if tick else 0}Hz) — starting staged bench…")
        target=random.randint(20,50)
        self._log(f"\n[1/3] Consistency — target {target}ms ×8")
        errs=[]
        for i in range(8):
            t0=time.perf_counter()
            time.sleep(target/1000.0)
            actual=(time.perf_counter()-t0)*1000
            err=actual-target
            errs.append(abs(err))
            self._log(f"  {i+1}: {actual:5.2f}ms err {err:+5.2f}ms {'✓' if abs(err)<2 else '•'}")
        avg_err=sum(errs)/len(errs) if errs else 0
        max_err=max(errs) if errs else 0
        cons="Excellent" if avg_err<1.0 else ("Good" if avg_err<2.5 else "Drift")
        self._log(f" -> avg err {avg_err:.2f}ms max {max_err:.2f}ms — {cons}")
        self._log(f"\n[2/3] Speed — count to 10000")
        t0=time.perf_counter()
        c=0
        for _ in range(10000): c+=1
        elapsed=(time.perf_counter()-t0)*1000
        self._log(f"  counted {c} in {elapsed:.2f}ms ({elapsed/10000*1000:.1f}µs/iter)")
        self._log(f"  -> {10000/elapsed*1000:.0f}k ops/s" if elapsed else "")
        self._log(f"\n[3/3] Jitter — sampling loop {tick}ms for 0.8s")
        samples=[]
        t0=time.perf_counter()
        def collect():
            try: v=get_loop_ms()
            except: v=0
            samples.append(v)
            if v> tick*1.8 and tick<=5:
                self._log(f"  hitch {v:.2f}ms")
            if time.perf_counter()-t0 < 0.8:
                QTimer.singleShot(5, collect)
            else:
                self._finish_jitter(samples)
        self._j_samples=samples
        QTimer.singleShot(5, collect)

    def _finish_jitter(self, samples):
        if not samples: samples=self._j_samples
        avg=sum(samples)/len(samples) if samples else 0
        mn=min(samples) if samples else 0; mx=max(samples) if samples else 0
        jitter=mx-mn
        hitches=sum(1 for v in samples if v > get_tick_ms()*1.8) if samples else 0
        status="Clean" if jitter<0.7 and hitches==0 else ("1-2 hitches" if hitches<=2 else f"{hitches} hitches")
        self._log(f"  samples {len(samples)} avg {avg:.2f}ms min {mn:.2f} max {mx:.2f} jitter {jitter:.2f}ms — {status}")
        self._log(f"\nDone — tick {get_tick_ms()}ms {'✓' if jitter<1.0 and hitches==0 else '• check tick'}")
        self.test_btn.setEnabled(True); self.test_btn.setText("Test Engine")


