@echo off
rem Opens Oculus Mirror: a desktop window with the exact view of the headset
rem over Link. Record that window (Win+Shift+R, or Win+Alt+R) to get a video of
rem what the operator sees. Start it after Link and Unity Play, or it is black.
rem Extra arguments go to OculusMirror.exe unchanged.
setlocal
set "EXE=%OculusBase%Support\oculus-diagnostics\OculusMirror.exe"
if not exist "%EXE%" set "EXE=%ProgramFiles%\Oculus\Support\oculus-diagnostics\OculusMirror.exe"
if not exist "%EXE%" for /f "delims=" %%F in ('where /R "%ProgramFiles%" OculusMirror.exe 2^>nul') do set "EXE=%%F"
if not exist "%EXE%" (
    echo OculusMirror.exe not found. It comes with the Meta Horizon Link app, in Support\oculus-diagnostics of its install folder.
    exit /b 1
)
echo %EXE%
start "" "%EXE%" %*
