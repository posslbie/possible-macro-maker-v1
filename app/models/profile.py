from dataclasses import dataclass, field
from typing import List

@dataclass
class Profile:
    name: str
    macro_files: List[str] = field(default_factory=list)  # e.g. ["MyMacro.json"]
    disable_all_bind: dict = field(default_factory=dict)
    enable_all_bind: dict = field(default_factory=dict)

    def to_dict(self):
        return {"name": self.name, "macro_files": self.macro_files, "disable_all_bind": self.disable_all_bind, "enable_all_bind": self.enable_all_bind}

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("name",""), d.get("macro_files",[]), d.get("disable_all_bind",{}), d.get("enable_all_bind",{}))
