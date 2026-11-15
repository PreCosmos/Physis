# Prints the install folder of Unreal Engine 5.9 (nothing if not found).
# The new Epic Games Launcher installs under the user folder and keeps no LauncherInstalled.dat;
# the old one records its installs there and defaults to Program Files.
$candidates = @("$env:USERPROFILE\Epic Games\UE_5.9", "$env:ProgramFiles\Epic Games\UE_5.9")
$dat = 'C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat'
if (Test-Path $dat) {
    $candidates += (Get-Content $dat -Raw | ConvertFrom-Json).InstallationList |
        Where-Object { $_.AppName -like 'UE_5.9*' } | ForEach-Object { $_.InstallLocation }
}
$candidates | Where-Object { $_ -and (Test-Path "$_\Engine\Build\BatchFiles\RunUAT.bat") } | Select-Object -First 1
