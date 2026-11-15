@echo off
rem Double-click inside the WinBoat VM: installs everything the Windows package needs except Unreal Engine 5.9.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_vm.ps1"
