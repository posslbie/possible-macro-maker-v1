import os, json, glob
from ..models.macro import Macro
from .local_data import macro_dir

MACRO_DIR = str(macro_dir())
os.makedirs(MACRO_DIR, exist_ok=True)


def save_macro(macro: Macro):
    path = os.path.join(MACRO_DIR, f"{macro.name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(macro.to_dict(), f, indent=2)
    return path


def load_single_macro(path):
    with open(path, encoding="utf-8") as f:
        return Macro.from_dict(json.load(f))


def load_all():
    files=glob.glob(os.path.join(MACRO_DIR, "*.json"))
    try: files.sort(key=lambda p: os.path.getctime(p))
    except: pass
    macros=[]
    for p in files:
        try: macros.append(load_single_macro(p))
        except: pass
    return macros


def delete_macro(name):
    macro_name = str(name).strip()
    if not macro_name:
        return
    p = os.path.join(MACRO_DIR, f"{macro_name}.json")
    if os.path.exists(p):
        os.remove(p)

    try:
        from .profile_store import load_profiles, save_profile
        for profile in load_profiles():
            fname = f"{macro_name}.json"
            if fname in profile.macro_files:
                profile.macro_files = [f for f in profile.macro_files if f != fname]
                save_profile(profile)
    except Exception:
        pass
