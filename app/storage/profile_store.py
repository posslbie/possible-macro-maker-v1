import os, json, glob
from ..models.profile import Profile
from .local_data import profile_dir, settings_path

PROFILE_DIR = str(profile_dir())
os.makedirs(PROFILE_DIR, exist_ok=True)

SETTINGS_PATH = str(settings_path())


def _profile_path(name): return os.path.join(PROFILE_DIR, f"{name}.json")

def save_profile(p: Profile):
    # dedupe macro_files
    p.macro_files = list(dict.fromkeys(p.macro_files))
    with open(_profile_path(p.name), "w", encoding="utf-8") as f:
        json.dump(p.to_dict(), f, indent=2)
    return p

def load_profiles():
    out=[]
    for fp in glob.glob(os.path.join(PROFILE_DIR, "*.json")):
        try:
            with open(fp, encoding="utf-8") as f:
                out.append(Profile.from_dict(json.load(f)))
        except: pass
    return sorted(out, key=lambda x: x.name.lower())

def load_single(name):
    fp=_profile_path(name)
    if not os.path.exists(fp): return None
    with open(fp, encoding="utf-8") as f:
        return Profile.from_dict(json.load(f))

def delete_profile(name):
    profile_name = str(name).strip()
    if not profile_name:
        return
    p = load_single(profile_name)
    if p:
        for fname in list(p.macro_files):
            try:
                from .macro_store import delete_macro
                delete_macro(os.path.splitext(fname)[0])
            except Exception:
                pass

        for other in load_profiles():
            if other.name == profile_name:
                continue
            other.macro_files = [f for f in other.macro_files if f not in p.macro_files]
            save_profile(other)

    fp=_profile_path(profile_name)
    if os.path.exists(fp): os.remove(fp)
    if get_active_profile_name()==profile_name:
        set_active_profile_name(None)

def rename_profile(old, new):
    if old==new: return
    p=load_single(old)
    if not p: return None
    delete_profile(old)
    p.name=new
    save_profile(p)
    if get_active_profile_name()==old:
        set_active_profile_name(new)
    return p

def add_macro_to_profile(profile_name, macro_name):
    # macro_name without .json or with
    fname = macro_name if macro_name.endswith(".json") else f"{macro_name}.json"
    p=load_single(profile_name)
    if not p: return
    if fname not in p.macro_files:
        p.macro_files.append(fname)
        save_profile(p)

def remove_macro_from_profile(profile_name, macro_name):
    fname = macro_name if macro_name.endswith(".json") else f"{macro_name}.json"
    p=load_single(profile_name)
    if not p: return
    if fname in p.macro_files:
        p.macro_files.remove(fname)
        save_profile(p)

def get_active_profile_name():
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                return json.load(f).get("last_active_profile")
    except: pass
    return None

def set_active_profile_name(name):
    data={}
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                data=json.load(f)
    except: data={}
    data["last_active_profile"]=name
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def ensure_default():
    profiles=load_profiles()
    if not profiles:
        p=Profile("Default")
        save_profile(p)
        set_active_profile_name("Default")
        return p
    active=get_active_profile_name()
    if not active or not load_single(active):
        set_active_profile_name(profiles[0].name)
    return load_single(get_active_profile_name())
