@echo off
rem Run inside the WinBoat VM. Mirrors the project from the Linux home share to C:\PhysisProject,
rem packages Win64 Shipping there, and copies Build\Windows back to the share.
rem The Linux side stages the project into ~/PhysisWin first and collects ~/PhysisWin/Build/Windows after
rem (Tools/winboat/stage.sh and collect.sh). Log: \\host.lan\Data\PhysisWin\vm_package.log
setlocal
set SHARE=\\host.lan\Data\PhysisWin
set LOCAL=C:\PhysisProject
set LOG=%SHARE%\vm_package.log
echo START %DATE% %TIME% > "%LOG%"
robocopy "%SHARE%" "%LOCAL%" /MIR /MT:16 /R:2 /W:2 /NFL /NDL /NP /XD Build Saved Intermediate Binaries DerivedDataCache /XF vm_*.log >> "%LOG%" 2>&1
if errorlevel 8 (echo COPY FAILED >> "%LOG%" & exit /b 1)
call "%~dp0probe.bat"
rem Use the folder the Epic launcher installed Unreal Engine 5.9 into, wherever that is.
for /f "usebackq delims=" %%i in (`powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%LOCAL%\Tools\winboat\find_engine.ps1"`) do set ENGINE=%%i
echo ENGINE=%ENGINE% >> "%LOG%"
if exist "%LOCAL%\Build\Windows" rmdir /s /q "%LOCAL%\Build\Windows"
call "%LOCAL%\Tools\package_physis_windows.bat" > "%LOCAL%\package_windows.log" 2>&1
set RC=%ERRORLEVEL%
copy /y "%LOCAL%\package_windows.log" "%SHARE%\vm_package_uat.log" > nul
if not "%RC%"=="0" (echo PACKAGE FAILED %RC% >> "%LOG%" & exit /b 1)
robocopy "%LOCAL%\Build\Windows" "%SHARE%\Build\Windows" /MIR /MT:16 /R:2 /W:2 /NFL /NDL /NP >> "%LOG%" 2>&1
if errorlevel 8 (echo COPYBACK FAILED >> "%LOG%" & exit /b 1)
echo PACKAGE DONE %DATE% %TIME% >> "%LOG%"
