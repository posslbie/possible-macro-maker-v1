import os
from pathlib import Path

APP_DIR_NAME = "PossibleMacroMaker"


def _local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Local"


def app_data_root() -> Path:
    root = _local_root() / APP_DIR_NAME
    return root


def ensure_storage_dirs() -> Path:
    root = app_data_root()
    storage = root / "storage"
    (storage / "macros").mkdir(parents=True, exist_ok=True)
    (storage / "profiles").mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    storage.mkdir(parents=True, exist_ok=True)
    return storage


def settings_path() -> Path:
    return ensure_storage_dirs() / "settings.json"


def macro_dir() -> Path:
    return ensure_storage_dirs() / "macros"


def profile_dir() -> Path:
    return ensure_storage_dirs() / "profiles"
