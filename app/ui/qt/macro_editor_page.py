from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag
from ...models.step import Step
import copy
from .theme import (
    C, QSS_PRIMARY, QSS_SECONDARY, Button, fade_in, panel_title, style_item, style_panel, style_card, style_row,
)

COND_TYPES = [
    ("Always On", "Runs constantly while enabled"),
    ("While Input Down", "Hold to run (Hold/Repeat)"),
    ("Action From Input", "Fires once when you press"),
    ("On Input Up", "Fires once when you release"),
]
ACTION_TYPES = [
    ("KEY_PRESS", "Press Input"), ("KEY_DOWN", "Input Down"), ("KEY_UP", "Input Up"),
    ("DELAY", "Delay"), ("LOOP", "Loop"),
    ("TYPE_PHRASE", "Type Phrase"), ("MOVE_MOUSE", "Move Mouse"), ("MOUSE_LOOK", "Mouse Look"),
]
COND_NEEDS_INPUT = {"While Input Down","Action From Input","On Input Up"}
ACT_NEEDS_INPUT = {"KEY_PRESS","KEY_DOWN","KEY_UP"}

def _friendly_bind(bind):
    if not bind: return ""
    if isinstance(bind, dict):
        v=bind.get("value","")
        t=bind.get("type","")
        if t=="keyboard": return v
        if t=="mouse": return v  # already "XButton1 (Side)" etc
        if t=="controller": return v
        return v
    return str(bind)

class DraggableRow(QFrame):
    def __init__(self, kind, index, is_alt, on_drop=None, parent=None):
        super().__init__(parent)
        self._kind = kind
        self._index = index
        self._is_alt = is_alt
        self._on_drop = on_drop
        self.setAcceptDrops(True)
        self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(f"{self._kind}|{self._index}|{int(self._is_alt)}")
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)
            return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasText() or self._on_drop is None:
            return
        payload = event.mimeData().text().split("|")
        if len(payload) != 3:
            return
        src_kind, src_index, src_alt = payload
        try:
            src_index = int(src_index)
            src_alt = bool(int(src_alt))
            dst_index = self._index
            dst_alt = self._is_alt
            if src_kind == self._kind and src_alt == dst_alt:
                self._on_drop(src_index, dst_index, src_alt)
        except ValueError:
            return
        event.acceptProposedAction()

class MacroEditorPage(QWidget):
    back_requested = Signal()
    save_requested = Signal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.macro=None; self._original=None; self._bind_target=None; self._overlay=None
        lay=QVBoxLayout(self); lay.setContentsMargins(20,12,20,12); lay.setSpacing(8)

        hdr=QHBoxLayout()
        self.back_btn=Button("< Back"); self.back_btn.setFixedHeight(32); self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setStyleSheet("QPushButton{background:#1a202b; color:#c7cedb; border:none; border-radius:8px; padding:0 14px;} QPushButton:hover{background:#222938;}")
        self.back_btn.clicked.connect(self._on_back); hdr.addWidget(self.back_btn)
        cancel=Button("Cancel"); cancel.setFixedHeight(32); cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet("QPushButton{background:transparent; color:#8b95a7; border:1px solid #222938; border-radius:8px; padding:0 12px;}"); cancel.clicked.connect(self._on_cancel)
        hdr.addWidget(cancel)
        self.title=QLabel("Edit Macro"); self.title.setStyleSheet("color:#c7cedb; font-size:16px; font-weight:700; margin-left:4px;")
        hdr.addWidget(self.title); hdr.addStretch(1)
        self.undo_btn=Button("Undo"); self.undo_btn.setFixedHeight(32); self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.setStyleSheet("QPushButton{background:#1a202b; color:#c7cedb; border:none; border-radius:8px; padding:0 14px;}")
        self.undo_btn.clicked.connect(self._undo); hdr.addWidget(self.undo_btn)
        self.save_btn=Button("Save"); self.save_btn.setFixedHeight(32); self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet(QSS_PRIMARY)
        self.save_btn.clicked.connect(self._save); hdr.addWidget(self.save_btn)
        lay.addLayout(hdr)

        self.main_scroll=QScrollArea(); self.main_scroll.setWidgetResizable(True); self.main_scroll.setFrameShape(QFrame.NoFrame)
        self.main_scroll.setStyleSheet("QScrollArea{background:transparent; border:none;} QScrollBar:vertical{background:#0b0d12; width:8px;}")
        self.main_inner=QWidget(); self.main_inner.setStyleSheet("background:transparent;")
        self.main_lay=QVBoxLayout(self.main_inner); self.main_lay.setContentsMargins(0,0,0,0); self.main_lay.setSpacing(12)
        self.main_scroll.setWidget(self.main_inner); lay.addWidget(self.main_scroll,1)

        container=QFrame(); container.setStyleSheet("QFrame{background:#11151c; border-radius:12px;}")
        cl=QVBoxLayout(container); cl.setContentsMargins(16,16,16,16); cl.setSpacing(8)
        cl.addWidget(self._section("Conditions", "Triggers"))
        self.cond_scroll=QScrollArea(); self.cond_scroll.setFixedHeight(220); self.cond_scroll.setWidgetResizable(True); self.cond_scroll.setFrameShape(QFrame.NoFrame)
        self.cond_scroll.setStyleSheet("QScrollArea{background:#1a202b; border:none; border-radius:8px;} QScrollBar:vertical{background:#1a202b; width:6px;}")
        self.cond_inner=QWidget(); self.cond_inner.setStyleSheet("background:#1a202b;")
        self.cond_lay=QVBoxLayout(self.cond_inner); self.cond_lay.setContentsMargins(8,8,8,8); self.cond_lay.setSpacing(6); self.cond_lay.addStretch(1)
        self.cond_scroll.setWidget(self.cond_inner); cl.addWidget(self.cond_scroll)
        rowC=QHBoxLayout(); rowC.setSpacing(8)
        addC=Button("+ Add Condition"); addC.setFixedHeight(34); addC.setCursor(Qt.PointingHandCursor)
        addC.setStyleSheet("QPushButton{background:#222938; color:#c7cedb; border:none; border-radius:8px;}")
        addC.clicked.connect(lambda: self._prompt_add_condition("main"))
        addAlt=Button("+ Add Alt Condition"); addAlt.setFixedHeight(34); addAlt.setCursor(Qt.PointingHandCursor)
        addAlt.setStyleSheet("QPushButton{background:#1a202b; color:#c7cedb; border:none; border-radius:8px;} QPushButton:hover{border-color:#222938;}")
        addAlt.clicked.connect(lambda: self._prompt_add_condition("alt"))
        rowC.addWidget(addC); rowC.addWidget(addAlt); cl.addLayout(rowC)
        div=QFrame(); div.setFixedHeight(1); div.setStyleSheet("background:#222938;"); cl.addWidget(div)
        cl.addWidget(self._section("Actions", "Steps in order"))
        self.act_scroll=QScrollArea(); self.act_scroll.setFixedHeight(280); self.act_scroll.setWidgetResizable(True); self.act_scroll.setFrameShape(QFrame.NoFrame)
        self.act_scroll.setStyleSheet("QScrollArea{background:#1a202b; border:none; border-radius:8px;} QScrollBar:vertical{background:#1a202b; width:6px;}")
        self.act_inner=QWidget(); self.act_inner.setStyleSheet("background:#1a202b;")
        self.act_lay=QVBoxLayout(self.act_inner); self.act_lay.setContentsMargins(8,8,8,8); self.act_lay.setSpacing(6); self.act_lay.addStretch(1)
        self.act_scroll.setWidget(self.act_inner); cl.addWidget(self.act_scroll)
        addA=Button("+ Add Action"); addA.setFixedHeight(34); addA.setCursor(Qt.PointingHandCursor)
        addA.setStyleSheet("QPushButton{background:#222938; color:#c7cedb; border:none; border-radius:8px;}")
        addA.clicked.connect(self._prompt_add_action); cl.addWidget(addA)
        self.main_lay.addWidget(container)

        from .overlay import BindCaptureOverlay
        self._bind_overlay = BindCaptureOverlay(self)
        self._bind_overlay.captured.connect(self._on_bind_captured)

    def _section(self, title, sub):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(1)
        t=QLabel(title); t.setStyleSheet("color:#c7cedb; font-size:13px; font-weight:700; background:transparent;")
        s=QLabel(sub); s.setStyleSheet("color:#6b7587; font-size:11px; background:transparent;")
        l.addWidget(t); l.addWidget(s); return w

    def load(self, macro):
        self._original = copy.deepcopy(macro)
        self.macro = copy.deepcopy(macro)
        self.title.setText(macro.name)
        self._refresh()

    def _refresh(self):
        for lay in [self.cond_lay, self.act_lay]:
            while lay.count()>1:
                it=lay.takeAt(0)
                if it.widget(): it.widget().deleteLater()
        if not self.macro: return
        while self.cond_lay.count()>1:
            it=self.cond_lay.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        has=False
        # flat list: main then alt with "alt" tag per row, no separate sections
        all_conds=[]
        for i,c in enumerate(self.macro.conditions or []):
            all_conds.append((c,i,False))
        for i,c in enumerate(self.macro.alt_conditions or []):
            all_conds.append((c,i,True))
        if all_conds:
            has=True
            for idx,(c,i,is_alt) in enumerate(all_conds):
                self.cond_lay.insertWidget(idx, self._cond_row(c,i,is_alt))
        if not has:
            e=QLabel("No triggers"); e.setAlignment(Qt.AlignCenter)
            e.setStyleSheet("color:#566073; background:transparent; padding:28px; font-size:12px;")
            self.cond_lay.insertWidget(0,e)
        if not self.macro.steps:
            e=QLabel("No steps"); e.setAlignment(Qt.AlignCenter)
            e.setStyleSheet("color:#566073; background:transparent; padding:28px; font-size:12px;")
            self.act_lay.insertWidget(0,e)
        else:
            for i,s in enumerate(self.macro.steps):
                self.act_lay.insertWidget(i, self._act_row(s,i))

    def _reorder_condition_list(self, src_idx, dst_idx, is_alt):
        if is_alt:
            items = self.macro.alt_conditions
        else:
            items = self.macro.conditions
        if not (0 <= src_idx < len(items) and 0 <= dst_idx < len(items)):
            return
        if src_idx == dst_idx:
            return
        item = items.pop(src_idx)
        items.insert(dst_idx, item)
        self._refresh()

    def _reorder_action_list(self, src_idx, dst_idx):
        if not (0 <= src_idx < len(self.macro.steps) and 0 <= dst_idx < len(self.macro.steps)):
            return
        if src_idx == dst_idx:
            return
        step = self.macro.steps.pop(src_idx)
        self.macro.steps.insert(dst_idx, step)
        self._refresh()

    def _cond_row(self, cond, idx, is_alt):
        row=DraggableRow("condition", idx, is_alt, self._reorder_condition_list)
        style_item(row)
        lay=QHBoxLayout(row); lay.setContentsMargins(12,10,8,10); lay.setSpacing(8)
        if is_alt:
            tag=QLabel("alt"); tag.setStyleSheet("background:#2a3242; color:#e3e8f0; border-radius:6px; padding:2px 6px; font-size:10px; font-weight:700;")
            lay.addWidget(tag)
        t=cond.get("type","Unknown") if isinstance(cond, dict) else str(cond)
        lab=QLabel(t); lab.setStyleSheet("color:#e3e8f0; background:transparent; font-size:12px;")
        lay.addWidget(lab)
        if t=="While Input Down":
            mode=cond.get("mode","Single") if isinstance(cond, dict) else "Single"
            if mode=="Hold": mode="Single"
            pill=Button(mode); pill.setFixedHeight(26); pill.setCursor(Qt.PointingHandCursor)
            # same styling for Single and Loop, only text differs
            pill.setStyleSheet("QPushButton{background:#1c222d; color:#a4adbd; border:none; border-radius:13px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#2a3242; color:#c7cedb;}")
            pill.clicked.connect(lambda _, i=idx, alt=is_alt: self._toggle_while_mode(i, alt))
            lay.addWidget(pill)
        if t in COND_NEEDS_INPUT:
            bind=cond.get("bind") if isinstance(cond, dict) else None
            friendly=_friendly_bind(bind)
            is_set=bool(friendly)
            txt = friendly if is_set else "Set input"
            pill=Button(txt); pill.setFixedHeight(26); pill.setCursor(Qt.PointingHandCursor)
            pill.setStyleSheet(f"QPushButton{{background:{'#2a3242' if is_set else '#1c222d'}; color:{'#c7cedb' if is_set else '#8b95a7'}; border:none; border-radius:13px; padding:0 12px; font-size:11px;}} QPushButton:hover{{background:{'#2f394b' if is_set else '#2a3242'};}}")
            pill.clicked.connect(lambda _, i=idx, alt=is_alt: self._capture_bind("cond", i, alt))
            lay.addWidget(pill)
        lay.addStretch(1)
        d=Button("×"); d.setFixedSize(26,26); d.setCursor(Qt.PointingHandCursor)
        d.setStyleSheet("QPushButton{background:transparent; color:#6b7587; border:none; border-radius:13px; font-size:16px;} QPushButton:hover{background:#2a1518; color:#f87171;}")
        d.clicked.connect(lambda _, i=idx, alt=is_alt: self._delete_condition(i, alt))
        lay.addWidget(d); return row

    def _act_row(self, step, idx):
        row=DraggableRow("action", idx, False, lambda src_idx, dst_idx, _is_alt=None: self._reorder_action_list(src_idx, dst_idx))
        style_item(row)
        lay=QHBoxLayout(row); lay.setContentsMargins(12,10,8,10); lay.setSpacing(8)
        lab=QLabel(step.step_type.replace("_"," ").title()); lab.setStyleSheet("color:#e3e8f0; background:transparent; font-size:12px;")
        lay.addWidget(lab)
        # clickable param pills for editable types
        if step.step_type=="KEY_PRESS":
            btn=Button(f"{step.params.get('hold_ms',3)} ms"); btn.setFixedHeight(26); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton{background:#2a3242; color:#ffffff; border:none; border-radius:13px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#2f394b; color:#ffffff;}")
            btn.clicked.connect(lambda _, i=idx: self._edit_press(i)); lay.addWidget(btn)
        elif step.step_type=="DELAY":
            unit=step.params.get("unit", "ms")
            value=step.params.get("value", step.params.get("ms",50))
            btn=Button(f"{value} {unit}"); btn.setFixedHeight(26); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton{background:#2a3242; color:#ffffff; border:none; border-radius:13px; padding:0 10px; font-size:11px; font-weight:600;} QPushButton:hover{background:#2f394b; color:#ffffff;}")
            btn.clicked.connect(lambda _, i=idx: self._edit_delay(i)); lay.addWidget(btn)
        elif step.step_type=="LOOP":
            txt=f"×{step.params.get('count',3)}" if step.params.get('count',3)!=-1 else "∞ loops"
            btn=Button(txt); btn.setFixedHeight(26); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton{background:#2a3242; color:#ffffff; border:none; border-radius:13px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#2f394b; color:#ffffff;}")
            btn.clicked.connect(lambda _, i=idx: self._edit_loop(i)); lay.addWidget(btn)
        elif step.step_type=="TYPE_PHRASE":
            txt=f"\"{step.params.get('text','')[:16]}\" {step.params.get('speed',3)}ms"
            btn=Button(txt); btn.setFixedHeight(26); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton{background:#2a3242; color:#8b95a7; border:1px solid #354055; border-radius:13px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#354055; color:#c7cedb;}")
            btn.clicked.connect(lambda _, i=idx: self._edit_phrase(i)); lay.addWidget(btn)
        elif step.step_type=="MOVE_MOUSE":
            txt=f"{step.params.get('x',500)},{step.params.get('y',500)} {step.params.get('duration',200)}ms"
            btn=Button(txt); btn.setFixedHeight(26); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton{background:#2a3242; color:#8b95a7; border:1px solid #2a3242; border-radius:13px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#2a3242; color:#c7cedb;}")
            btn.clicked.connect(lambda _, i=idx: self._edit_move(i)); lay.addWidget(btn)
        elif step.step_type=="MOUSE_LOOK":
            txt=f"look {step.params.get('radius',50)}px"
            btn=Button(txt); btn.setFixedHeight(26); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton{background:#2a3242; color:#8b95a7; border:1px solid #2a3242; border-radius:13px; padding:0 10px; font-size:11px;} QPushButton:hover{background:#2a3242; color:#c7cedb;}")
            btn.clicked.connect(lambda _, i=idx: self._edit_look(i)); lay.addWidget(btn)
        if step.step_type in ACT_NEEDS_INPUT:
            bind=step.params.get("bind") if isinstance(step.params, dict) else None
            friendly=_friendly_bind(bind)
            is_set=bool(friendly)
            txt = friendly if is_set else "Set input"
            pill=Button(txt); pill.setFixedHeight(26); pill.setCursor(Qt.PointingHandCursor)
            pill.setStyleSheet(f"QPushButton{{background:{'#2a3242' if is_set else '#1c222d'}; color:{'#c7cedb' if is_set else '#8b95a7'}; border:none; border-radius:13px; padding:0 12px; font-size:11px;}} QPushButton:hover{{background:{'#2f394b' if is_set else '#2a3242'};}}")
            pill.clicked.connect(lambda _, i=idx: self._capture_bind("act", i, False))
            lay.addWidget(pill)
        lay.addStretch(1)
        d=Button("×"); d.setFixedSize(26,26); d.setCursor(Qt.PointingHandCursor)
        d.setStyleSheet("QPushButton{background:transparent; color:#6b7587; border:none; border-radius:13px; font-size:16px;} QPushButton:hover{background:#2a1518; color:#f87171;}")
        d.clicked.connect(lambda _, i=idx: self._delete_action(i))
        lay.addWidget(d); return row

    def _capture_bind(self, kind, idx, is_alt):
        self._bind_target=(kind, idx, is_alt)
        self._bind_overlay.setGeometry(self.rect())
        self._bind_overlay.showOverlay()
    def _on_bind_captured(self, data):
        kind, idx, is_alt = self._bind_target or (None,None,None)
        if kind=="cond":
            target = self.macro.alt_conditions if is_alt else self.macro.conditions
            if 0<=idx<len(target): target[idx]["bind"]=data
        elif kind=="act":
            if 0<=idx<len(self.macro.steps): self.macro.steps[idx].params["bind"]=data
        self._refresh()
    def showEvent(self, e):
        super().showEvent(e)
        fade_in(self, 0, 200)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_bind_overlay") and self._bind_overlay.isVisible(): self._bind_overlay.setGeometry(self.rect())
        if self._overlay and hasattr(self, "_overlay") and self._overlay and self._overlay.isVisible(): self._overlay.setGeometry(self.rect())

    def _show_chooser_overlay(self, title, options, on_pick):
        from .overlay import BaseOverlay
        if self._overlay: self._overlay.deleteLater()
        self._overlay = BaseOverlay(self); self._overlay.setGeometry(self.rect())
        panel = QFrame(self._overlay); panel.setFixedSize(360, 340)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(8)
        h=QLabel(title); h.setStyleSheet("color:#c7cedb; font-size:14px; font-weight:700; background:transparent;"); lay.addWidget(h)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:#11151c; border:none; border-radius:8px;}")
        inner=QWidget(); inner.setStyleSheet("background:#11151c;")
        v=QVBoxLayout(inner); v.setSpacing(6)
        for val, label in options:
            b=Button(label); b.setFixedHeight(36); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{background:#222938; color:#c7cedb; border-radius:6px; text-align:left; padding-left:12px;} QPushButton:hover{background:#2a3242;}")
            def make(v):
                def cb():
                    self._overlay.hideOverlay(); self._overlay.deleteLater(); self._overlay=None; on_pick(v)
                return cb
            b.clicked.connect(make(val)); v.addWidget(b)
        v.addStretch(1); scroll.setWidget(inner); lay.addWidget(scroll,1)
        cancel=Button("Cancel"); cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (self._overlay.hideOverlay(), self._overlay.deleteLater(), setattr(self,'_overlay',None)))
        lay.addWidget(cancel)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        self._overlay.showOverlay()

    def _prompt_add_condition(self, branch="main"):
        self._pick_cond_type(branch)
    def _toggle_while_mode(self, idx, is_alt):
        target = self.macro.alt_conditions if is_alt else self.macro.conditions
        if 0<=idx<len(target):
            cur=target[idx].get("mode","Single")
            if cur=="Hold": cur="Single"
            target[idx]["mode"]="Loop" if cur=="Single" else "Single"
            self._refresh()

    def _pick_cond_type(self, branch):
        def on_pick(v):
            target = self.macro.alt_conditions if branch=="alt" else self.macro.conditions
            if v=="While Input Down": target.append({"type": v, "mode":"Single"})
            else: target.append({"type": v})
            self._refresh()
        self._show_chooser_overlay("Choose Condition", [(c[0], c[0]) for c in COND_TYPES], on_pick)

    def _prompt_add_action(self):
        def on_pick(v):
            defaults={"DELAY":{"value":50,"unit":"ms"},"LOOP":{"count":3,"endless":False},"TYPE_PHRASE":{"text":"hello","speed":3},"MOVE_MOUSE":{"x":500,"y":500,"duration":200},"MOUSE_LOOK":{"dx":50,"dy":0,"radius":50}}
            self.macro.steps.append(Step(v, defaults.get(v,{}))); self._refresh()
        self._show_chooser_overlay("Choose Action", [(v,l) for v,l in ACTION_TYPES], on_pick)

    def _delete_condition(self, idx, is_alt):
        if is_alt:
            if 0<=idx<len(self.macro.alt_conditions): self.macro.alt_conditions.pop(idx)
        else:
            if 0<=idx<len(self.macro.conditions): self.macro.conditions.pop(idx)
        self._refresh()
    def _delete_action(self, idx):
        if 0<=idx<len(self.macro.steps): self.macro.steps.pop(idx); self._refresh()
    def _edit_delay(self, idx):
        if not (0 <= idx < len(self.macro.steps)): return
        step=self.macro.steps[idx]
        if step.step_type!="DELAY": return
        from .overlay import BaseOverlay
        if self._overlay: self._overlay.deleteLater()
        self._overlay=BaseOverlay(self); self._overlay.setGeometry(self.rect())
        panel=QFrame(self._overlay); panel.setFixedSize(360, 180)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(18,18,18,18); lay.setSpacing(12)

        title=QLabel("Edit Delay"); title.setStyleSheet("color:#ffffff; font-size:14px; font-weight:700; background:transparent;")
        lay.addWidget(title)

        field=QFrame(); style_row(field)
        field_lay=QHBoxLayout(field); field_lay.setContentsMargins(12,10,12,10); field_lay.setSpacing(10)
        from PySide6.QtWidgets import QSpinBox, QComboBox

        unit=step.params.get("unit", "ms")
        current_value=step.params.get("value")
        if current_value is None:
            current_value=step.params.get("ms",50)

        label=QLabel("Duration"); label.setStyleSheet("color:#b4bccb; font-size:12px; background:transparent;")
        field_lay.addWidget(label)
        spin=QSpinBox(); spin.setRange(1, 60000); spin.setValue(int(current_value))
        spin.setButtonSymbols(QSpinBox.NoButtons)
        spin.setStyleSheet("QSpinBox{background:#0f1319; color:#ffffff; border:1px solid #1e2531; border-radius:8px; padding:8px 10px; min-width:100px;} QSpinBox:focus{border:1px solid #7c6cff;} QSpinBox::up-button, QSpinBox::down-button{width:0; height:0; border:none; background:transparent;} QSpinBox::up-arrow, QSpinBox::down-arrow{width:0; height:0;}")
        field_lay.addWidget(spin)

        units=QComboBox(); units.addItems(["ms", "seconds", "minutes"]); units.setCurrentText(unit)
        units.setStyleSheet("QComboBox{background:#0f1319; color:#ffffff; border:1px solid #1e2531; border-radius:8px; padding:6px 8px; min-width:120px;} QComboBox::drop-down{border:none; background:transparent;} QComboBox QAbstractItemView{background:#1a202b; color:#ffffff; selection-background-color:#2a3242;}")
        field_lay.addWidget(units)
        lay.addWidget(field)

        row=QHBoxLayout(); row.setSpacing(8)
        cancel=Button("Cancel"); cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (self._overlay.hideOverlay(), self._overlay.deleteLater(), setattr(self,'_overlay',None)))
        save=Button("Save"); save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(QSS_PRIMARY)
        def do_save():
            step.params["value"]=int(spin.value()); step.params["unit"]=units.currentText()
            step.params.pop("ms", None)
            self._overlay.hideOverlay(); self._overlay.deleteLater(); self._overlay=None
            self._refresh()
        save.clicked.connect(do_save)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(save); lay.addLayout(row)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        self._overlay.showOverlay()
        spin.setFocus()

    def _edit_press(self, idx):
        if not (0 <= idx < len(self.macro.steps)): return
        step=self.macro.steps[idx]
        from .overlay import BaseOverlay
        if self._overlay: self._overlay.deleteLater()
        self._overlay=BaseOverlay(self); self._overlay.setGeometry(self.rect())
        panel=QFrame(self._overlay); panel.setFixedSize(340, 170)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)
        lay.addWidget(panel_title("Edit Press Hold (ms)"))
        from PySide6.QtWidgets import QSpinBox
        spin=QSpinBox(); spin.setRange(1, 1000); spin.setValue(int(step.params.get("hold_ms",3)))
        spin.setStyleSheet("QSpinBox{background:#11151c; color:#c7cedb; border:1px solid #1e2531; border-radius:8px; padding:6px;} QSpinBox:focus{border:1px solid #7c6cff;}")
        lay.addWidget(spin)
        row=QHBoxLayout(); cancel=Button("Cancel"); save=Button("Save")
        cancel.clicked.connect(lambda: (self._overlay.hideOverlay(), self._overlay.deleteLater(), setattr(self,'_overlay',None)))
        def do_save():
            step.params["hold_ms"]=int(spin.value()); self._overlay.hideOverlay(); self._overlay.deleteLater(); self._overlay=None; self._refresh()
        save.clicked.connect(do_save); row.addStretch(1); row.addWidget(cancel); row.addWidget(save); lay.addLayout(row)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2); self._overlay.showOverlay(); spin.setFocus()

    def _edit_loop(self, idx):
        step=self.macro.steps[idx]
        from .overlay import BaseOverlay
        if self._overlay: self._overlay.deleteLater()
        self._overlay=BaseOverlay(self); self._overlay.setGeometry(self.rect())
        panel=QFrame(self._overlay); panel.setFixedSize(400, 320)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)
        lay.addWidget(panel_title("Edit Loop"))
        from PySide6.QtWidgets import QSpinBox, QCheckBox, QListWidget
        spin=QSpinBox(); spin.setRange(1, 100000); spin.setValue(int(step.params.get("count",3)) if step.params.get("count",3)!=-1 else 3)
        spin.setStyleSheet("QSpinBox{background:#11151c; color:#c7cedb; border:1px solid #1e2531; border-radius:8px; padding:6px;} QSpinBox:focus{border:1px solid #7c6cff;}")
        lay.addWidget(spin)
        chk=QCheckBox("Endless while condition is true"); chk.setChecked(step.params.get("endless", False) or step.params.get("count",3)==-1)
        chk.setStyleSheet("QCheckBox{color:#c7cedb;}")
        has_action_condition=any(c.get("type") == "Action From Input" for c in self.macro.conditions + self.macro.alt_conditions)
        chk.setEnabled(not has_action_condition)
        if has_action_condition: chk.setChecked(False)
        lay.addWidget(chk)
        def on_chk(v): spin.setEnabled(not v)
        chk.toggled.connect(on_chk); on_chk(chk.isChecked())
        children=QListWidget(); children.setStyleSheet("QListWidget{background:#11151c; color:#c7cedb; border:none; border-radius:8px;}")
        for child in step.children:
            children.addItem(child.step_type.replace("_", " ").title())
        lay.addWidget(children)
        add=Button("Add nested action")
        add.setFixedHeight(30); add.setCursor(Qt.PointingHandCursor)
        add.setStyleSheet("QPushButton{background:#2a3242; color:#c7cedb; border:none; border-radius:15px; padding:0 14px;} QPushButton:hover{background:#2f394b; color:#ffffff;}")
        def add_child():
            self._show_chooser_overlay("Choose Nested Action", [(v,l) for v,l in ACTION_TYPES], lambda v: (step.children.append(Step(v, {"value":50,"unit":"ms"} if v=="DELAY" else {"count":3,"endless":False} if v=="LOOP" else {})), children.addItem(v.replace("_", " ").title())))
        add.clicked.connect(add_child); lay.addWidget(add)
        remove=Button("Remove selected")
        remove.setFixedHeight(30); remove.setCursor(Qt.PointingHandCursor)
        remove.setStyleSheet("QPushButton{background:#1c222d; color:#a4adbd; border:none; border-radius:15px; padding:0 14px;} QPushButton:hover{background:#2a3242; color:#c7cedb;}")
        def remove_child():
            row=children.currentRow()
            if row>=0: children.takeItem(row); step.children.pop(row)
        remove.clicked.connect(remove_child); lay.addWidget(remove)
        row=QHBoxLayout()
        cancel=Button("Cancel"); cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (self._overlay.hideOverlay(), self._overlay.deleteLater(), setattr(self,'_overlay',None)))
        save=Button("Save"); save.setStyleSheet(QSS_PRIMARY)
        def do_save():
            step.params["endless"]=chk.isChecked() and not has_action_condition; step.params["count"]=int(spin.value())
            self._overlay.hideOverlay(); self._overlay.deleteLater(); self._overlay=None; self._refresh()
        save.clicked.connect(do_save)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(save); lay.addLayout(row)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        self._overlay.showOverlay()

    def _edit_phrase(self, idx):
        step=self.macro.steps[idx]
        from .overlay import BaseOverlay
        if self._overlay: self._overlay.deleteLater()
        self._overlay=BaseOverlay(self); self._overlay.setGeometry(self.rect())
        panel=QFrame(self._overlay); panel.setFixedSize(380, 220)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)
        lay.addWidget(panel_title("Edit Type Phrase"))
        from PySide6.QtWidgets import QLineEdit, QComboBox
        edit=QLineEdit(); edit.setText(step.params.get("text","")); edit.setPlaceholderText("Text to type")
        edit.setStyleSheet("QLineEdit{background:#11151c; color:#c7cedb; border:1px solid #1e2531; border-radius:8px; padding:8px;} QLineEdit:focus{border:1px solid #7c6cff;}")
        lay.addWidget(edit)
        lay.addWidget(QLabel("Speed (ms per char)"))
        combo=QComboBox(); combo.addItems(["1","3","6"]); combo.setCurrentText(str(step.params.get("speed",3)))
        combo.setStyleSheet("QComboBox{background:#11151c; color:#c7cedb; border:1px solid #1e2531; border-radius:8px; padding:6px;}")
        lay.addWidget(combo)
        row=QHBoxLayout()
        cancel=Button("Cancel"); cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (self._overlay.hideOverlay(), self._overlay.deleteLater(), setattr(self,'_overlay',None)))
        save=Button("Save"); save.setStyleSheet(QSS_PRIMARY)
        def do_save():
            step.params["text"]=edit.text(); step.params["speed"]=int(combo.currentText())
            self._overlay.hideOverlay(); self._overlay.deleteLater(); self._overlay=None; self._refresh()
        save.clicked.connect(do_save)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(save); lay.addLayout(row)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        self._overlay.showOverlay(); edit.setFocus()

    def _edit_move(self, idx):
        step=self.macro.steps[idx]
        from .overlay import BaseOverlay
        if self._overlay: self._overlay.deleteLater()
        self._overlay=BaseOverlay(self); self._overlay.setGeometry(self.rect())
        panel=QFrame(self._overlay); panel.setFixedSize(380, 260)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(8)
        lay.addWidget(panel_title("Edit Move Mouse"))
        from PySide6.QtWidgets import QSpinBox
        row1=QHBoxLayout(); row1.addWidget(QLabel("X:")); sx=QSpinBox(); sx.setRange(0, 4000); sx.setValue(int(step.params.get("x",500))); sx.setStyleSheet("QSpinBox{background:#11151c; color:#c7cedb; border:1px solid #1e2531; border-radius:8px; padding:6px;} QSpinBox:focus{border:1px solid #7c6cff;}"); row1.addWidget(sx)
        row1.addWidget(QLabel("Y:")); sy=QSpinBox(); sy.setRange(0, 4000); sy.setValue(int(step.params.get("y",500))); sy.setStyleSheet("QSpinBox{background:#11151c; color:#c7cedb; border:1px solid #1e2531; border-radius:8px; padding:6px;} QSpinBox:focus{border:1px solid #7c6cff;}"); row1.addWidget(sy)
        lay.addLayout(row1)
        lay.addWidget(QLabel("Duration (ms) 0=instant"))
        sd=QSpinBox(); sd.setRange(0, 5000); sd.setValue(int(step.params.get("duration",200))); sd.setStyleSheet("QSpinBox{background:#11151c; color:#c7cedb; border:1px solid #1e2531; border-radius:8px; padding:6px;} QSpinBox:focus{border:1px solid #7c6cff;}"); lay.addWidget(sd)
        row=QHBoxLayout()
        cancel=Button("Cancel"); cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (self._overlay.hideOverlay(), self._overlay.deleteLater(), setattr(self,'_overlay',None)))
        save=Button("Save"); save.setStyleSheet(QSS_PRIMARY)
        def do_save():
            step.params["x"]=int(sx.value()); step.params["y"]=int(sy.value()); step.params["duration"]=int(sd.value())
            self._overlay.hideOverlay(); self._overlay.deleteLater(); self._overlay=None; self._refresh()
        save.clicked.connect(do_save)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(save); lay.addLayout(row)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        self._overlay.showOverlay()

    def _edit_look(self, idx):
        step=self.macro.steps[idx]
        from .overlay import BaseOverlay
        if self._overlay: self._overlay.deleteLater()
        self._overlay=BaseOverlay(self); self._overlay.setGeometry(self.rect())
        panel=QFrame(self._overlay); panel.setFixedSize(340, 180)
        style_panel(panel)
        lay=QVBoxLayout(panel); lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)
        lay.addWidget(panel_title("Edit Mouse Look (radius px)"))
        from PySide6.QtWidgets import QSpinBox
        spin=QSpinBox(); spin.setRange(10, 500); spin.setValue(int(step.params.get("radius",50)))
        spin.setStyleSheet("QSpinBox{background:#11151c; color:#c7cedb; border:1px solid #1e2531; border-radius:8px; padding:6px;} QSpinBox:focus{border:1px solid #7c6cff;}")
        lay.addWidget(spin)
        row=QHBoxLayout()
        cancel=Button("Cancel"); cancel.setStyleSheet(QSS_SECONDARY)
        cancel.clicked.connect(lambda: (self._overlay.hideOverlay(), self._overlay.deleteLater(), setattr(self,'_overlay',None)))
        save=Button("Save"); save.setStyleSheet(QSS_PRIMARY)
        def do_save():
            step.params["radius"]=int(spin.value())
            self._overlay.hideOverlay(); self._overlay.deleteLater(); self._overlay=None; self._refresh()
        save.clicked.connect(do_save)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(save); lay.addLayout(row)
        panel.move((self.width()-panel.width())//2, (self.height()-panel.height())//2)
        self._overlay.showOverlay()
        spin.setFocus()

    def _save(self):
        from ...storage.macro_store import save_macro, delete_macro
        if self._original and self.macro.name != self._original.name: delete_macro(self._original.name)
        save_macro(self.macro); self._original = copy.deepcopy(self.macro)
        try:
            from ...native.bridge import sync_all
            sync_all()
        except: pass
        self.save_requested.emit(self.macro)
        self.back_requested.emit()
    def _undo(self):
        if self._original: self.macro = copy.deepcopy(self._original); self._refresh()
    def _on_back(self): self.back_requested.emit()
    def _on_cancel(self): self._undo(); self.back_requested.emit()






