from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

class StepType:
    KEY_PRESS = "KEY_PRESS"
    KEY_DOWN = "KEY_DOWN"
    KEY_UP = "KEY_UP"
    MOUSE_CLICK = "MOUSE_CLICK"
    DELAY = "DELAY"
    LOOP = "LOOP"
    TYPE_PHRASE = "TYPE_PHRASE"
    MOVE_MOUSE = "MOVE_MOUSE"
    MOUSE_LOOK = "MOUSE_LOOK"

@dataclass
class Step:
    step_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    children: List["Step"] = field(default_factory=list)

    def to_dict(self):
        return {"type": self.step_type, "params": self.params, "children": [c.to_dict() for c in self.children]}

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("type","DELAY"), d.get("params",{}), [cls.from_dict(c) for c in d.get("children",[])])
