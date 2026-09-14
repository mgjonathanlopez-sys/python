@echo off
setlocal
title Crear EXE - Gestor de Proyectos de Investigacion
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "Gestor_Proyectos_Investigacion" "gestor_proyectos.py"
if errorlevel 1 goto error
echo Ejecutable creado en %CD%\dist\Gestor_Proyectos_Investigacion.exe
explorer "%CD%\dist"
pause
exit /b 0
:error
echo No fue posible generar el ejecutable.
pause
exit /b 1
