@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "gestor_proyectos.py"
) else (
  echo La aplicacion no esta instalada. Ejecute Instalar_Gestor.bat
  pause
)
endlocal
