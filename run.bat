@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run install.bat first. & pause & exit /b 1)
if exist "config.local.json" (
  ".venv\Scripts\python.exe" -m persian_dubbing.cli --config config.local.json gui
) else (
  ".venv\Scripts\python.exe" -m persian_dubbing.cli gui
)
if errorlevel 1 pause
