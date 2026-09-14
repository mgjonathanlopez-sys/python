@echo off
setlocal
title Instalador - Gestor de Proyectos de Investigacion
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python no esta instalado o no esta disponible en PATH.
  echo Instale Python 3.11 o superior desde https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
echo Creando entorno privado de Python...
py -3 -m venv .venv
if errorlevel 1 goto error
echo Instalando componentes...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
echo Creando acceso directo...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Gestor de Proyectos de Investigacion.lnk'); $s.TargetPath='%CD%\.venv\Scripts\pythonw.exe'; $s.Arguments='\"%CD%\gestor_proyectos.py\"'; $s.WorkingDirectory='%CD%'; $s.Description='Gestor local de proyectos de investigacion'; $s.Save()"
echo.
echo Instalacion completada.
start "" ".venv\Scripts\pythonw.exe" "gestor_proyectos.py"
exit /b 0
:error
echo No fue posible completar la instalacion.
pause
exit /b 1
