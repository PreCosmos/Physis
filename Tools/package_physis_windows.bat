@echo off
rem Cooks and packages Physis for Windows (Win64 Shipping) into Build\Windows.
rem Run inside Windows (for example WinBoat) with Unreal Engine 5.9 for Windows and
rem Visual Studio 2022 17.14 (MSVC 14.44, Windows 11 SDK 26100) installed; Tools\winboat\setup_vm.ps1 installs the compiler.
rem Copy the project to a short local ASCII path first, such as C:\PhysisProject:
rem the ONNX runtime used while cooking cannot open files under non-ASCII folders,
rem and cooking from a network share is slow and unreliable.
rem Only the game maps are cooked: main menu, Meridian Station, Center of the Universe and Conclave.
rem -prereqs stages Engine\Extras\Redist\en-us\vc_redist.x64.exe: the Physis.exe launcher checks for the
rem VC++ 14.50+ runtime and quits without starting the game if it is older and the installer is missing (seen under Proton).
setlocal
cd /d "%~dp0.."
if not defined ENGINE set ENGINE=C:\Program Files\Epic Games\UE_5.9
if not exist "%ENGINE%\Engine\Build\BatchFiles\RunUAT.bat" (
    echo Unreal Engine 5.9 was not found at "%ENGINE%". Set ENGINE to its folder.
    exit /b 1
)
call "%ENGINE%\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun ^
    -project="%CD%\Physis.uproject" -platform=Win64 -clientconfig=Shipping ^
    -cook -map=/Game/Levels/L_MainMenu+/Game/Levels/L_BattleStation+/Game/Levels/L_CenterOfTheUniverse+/Game/Levels/L_Conclave -build -stage -pak -iostore -package -archive -archivedirectory="%CD%\Build" ^
    -prereqs -IgnoreCookErrors -nop4 -utf8output
if errorlevel 1 exit /b 1
rem Lets the packaged build find Steam when launched outside the Steam client.
echo 4673680> "%CD%\Build\Windows\steam_appid.txt"
echo Packaged to %CD%\Build\Windows
