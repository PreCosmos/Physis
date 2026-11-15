@echo off
rem Writes what the VM has installed to the share, so the Linux side can check before packaging.
set OUT=\\host.lan\Data\PhysisWin\vm_probe.log
echo PROBE %DATE% %TIME% > "%OUT%"
dir /b "C:\Program Files\Epic Games" >> "%OUT%" 2>&1
type "C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat" >> "%OUT%" 2>&1
dir /b "C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests" >> "%OUT%" 2>&1
"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe" -products * -property installationVersion >> "%OUT%" 2>&1
dir /b "C:\Program Files (x86)\Windows Kits\10\Include" >> "%OUT%" 2>&1
echo PROBE END >> "%OUT%"
