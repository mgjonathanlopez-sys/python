@echo off
setlocal
title Crear EXE - Redes que Transforman
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip pyinstaller
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "Redes_que_Transforman" "redes_transforman.py"
if errorlevel 1 goto error
echo.
echo EXE creado en: %CD%\dist\Redes_que_Transforman.exe
explorer "%CD%\dist"
pause
exit /b 0
:error
echo No fue posible generar el ejecutable.
pause
exit /b 1
endlocal
