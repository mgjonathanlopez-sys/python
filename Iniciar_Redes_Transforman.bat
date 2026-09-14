@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "redes_transforman.py"
) else (
  py -3 "redes_transforman.py"
)
endlocal
