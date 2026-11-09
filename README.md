# Possible Macro Maker

A modern macro maker with a clean, animated interface.

## Features
- Dark theme with smooth animations (page fades, animated toggles, hover/press effects)
- Macro list, profiles, settings and macro editor
- Tray icon with quick macro switches

## Run from source (Windows, 64-bit Python 3.10+)
```
run.bat
```

## Build the exe
```
build.bat              # folder build -> dist\PossibleMacroMaker\
build-single-exe.bat   # single file  -> dist\PossibleMacroMaker.exe
```
No Python? Use GitHub: **Actions -> Build exe -> Run workflow**, then download the artifact.

## Customize
- Links: `app/ui/qt/sidebar.py` (top of file)
- Colors: `app/ui/qt/theme.py` (class `C`)
