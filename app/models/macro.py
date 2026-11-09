from dataclasses import dataclass, field
from typing import List, Dict, Any
from .step import Step

@dataclass
class Macro:
    name: str
    enabled: bool = True
    steps: List[Step] = field(default_factory=list)
    conditions: List[Dict[str,Any]] = field(default_factory=list)
    alt_conditions: List[Dict[str,Any]] = field(default_factory=list)
    category: str = "Uncategorized"
    kind: str = "standard"  # standard|reactive
    exclusive_condition_listening: bool = False
    focus_window: str = ""  # window lock title, empty = always
    bind: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "name": self.name, "enabled": self.enabled, "category": self.category, "kind": self.kind,
            "exclusive_condition_listening": self.exclusive_condition_listening,
            "focus_window": self.focus_window,
            "bind": self.bind,
            "steps": [s.to_dict() for s in self.steps],
            "conditions": self.conditions, "alt_conditions": self.alt_conditions
        }
    @classmethod
    def from_dict(cls, d):
        return cls(
            d.get("name","Unnamed"), d.get("enabled",True),
            [Step.from_dict(s) for s in d.get("steps",[])],
            [c for c in d.get("conditions",[]) if c.get("type") != "Toggle With Input"],
            [c for c in d.get("alt_conditions",[]) if c.get("type") != "Toggle With Input"],
            d.get("category","Uncategorized"), d.get("kind","standard"),
            d.get("exclusive_condition_listening", False),
            d.get("focus_window",""), d.get("bind",{})
        )
