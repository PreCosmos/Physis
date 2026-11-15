# One-time setup of the WinBoat Windows VM for packaging Physis.
# Installs everything the Windows package needs except Unreal Engine 5.9 itself:
#   - Visual Studio 2022 Build Tools with what UE 5.9 asks for in Engine/Config/Windows/Windows_SDK.json
#     (MSVC 14.44 from VS 17.14, Windows 11 SDK 26100, .NET Framework 4.8 SDK and targeting pack, .NET SDK, MSBuild)
#   - Visual C++ 2015-2022 x64 runtime
#   - Epic Games Launcher (to install Unreal Engine 5.9 afterwards, signed in with your Epic account)
# Run it by double-clicking setup_vm.bat next to this file, or:
#   powershell -ExecutionPolicy Bypass -File \\host.lan\Data\PhysisWin\Tools\winboat\setup_vm.ps1
# Safe to run again: finished parts are skipped. Log: \\host.lan\Data\PhysisWin\vm_setup.log
# (or %TEMP%\physis_vm_setup.log if the share cannot be written).

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest is many times faster without the progress bar

# Ask for administrator rights if we do not have them.
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$log = '\\host.lan\Data\PhysisWin\vm_setup.log'
try { Start-Transcript -Path $log -Force | Out-Null }
catch { $log = "$env:TEMP\physis_vm_setup.log"; Start-Transcript -Path $log -Force | Out-Null }

$work = "$env:TEMP\physis_setup"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$failed = @()

function Get-Installer($url, $name) {
    $path = Join-Path $work $name
    Write-Host "Downloading $name ..."
    Invoke-WebRequest -Uri $url -OutFile $path -UseBasicParsing
    return $path
}

# --- Visual Studio 2022 Build Tools -------------------------------------------------------------
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$components = @(
    'Microsoft.VisualStudio.Workload.VCTools',
    'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
    'Microsoft.VisualStudio.Component.VC.14.44.17.14.x86.x64',
    'Microsoft.VisualStudio.Component.Windows11SDK.26100',
    'Microsoft.Net.Component.4.8.TargetingPack',
    'Microsoft.Net.Component.4.8.SDK',
    'Microsoft.NetCore.Component.SDK',
    'Microsoft.Component.MSBuild'
)
function Test-BuildTools {
    if (-not (Test-Path $vswhere)) { return $false }
    $found = & $vswhere -products * -version '[17.14,18.0)' `
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.Windows11SDK.26100 Microsoft.Net.Component.4.8.SDK `
        -property installationPath
    return [bool]$found
}
try {
    if (Test-BuildTools) {
        Write-Host 'Visual Studio 2022 Build Tools: already installed.'
    } else {
        $exe = Get-Installer 'https://aka.ms/vs/17/release/vs_BuildTools.exe' 'vs_BuildTools.exe'
        $vsArgs = @('--quiet', '--wait', '--norestart', '--nocache') + ($components | ForEach-Object { '--add', $_ })
        # An existing Build Tools install that lacks a component is modified in place.
        $existing = if (Test-Path $vswhere) { & $vswhere -products Microsoft.VisualStudio.Product.BuildTools -version '[17.0,18.0)' -property installationPath | Select-Object -First 1 }
        if ($existing) { $vsArgs = @('modify', '--installPath', "`"$existing`"") + $vsArgs }
        Write-Host 'Installing Visual Studio 2022 Build Tools (several GB, this takes a while) ...'
        $p = Start-Process $exe -ArgumentList $vsArgs -Wait -PassThru
        Write-Host "Build Tools installer exit code: $($p.ExitCode)"   # 0 = done, 3010 = done, restart needed
        if (-not (Test-BuildTools)) { throw "Build Tools are not complete after install (exit $($p.ExitCode))." }
    }
} catch { Write-Host "FAILED: $_" -ForegroundColor Red; $failed += 'Visual Studio Build Tools' }

# --- Visual C++ runtime -------------------------------------------------------------------------
try {
    $vc = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction SilentlyContinue
    if ($vc -and $vc.Installed -eq 1 -and $vc.Minor -ge 44) {
        Write-Host "Visual C++ runtime: already installed (14.$($vc.Minor))."
    } else {
        $exe = Get-Installer 'https://aka.ms/vs/17/release/vc_redist.x64.exe' 'vc_redist.x64.exe'
        $p = Start-Process $exe -ArgumentList '/install', '/quiet', '/norestart' -Wait -PassThru
        Write-Host "Visual C++ runtime installer exit code: $($p.ExitCode)"
        if ($p.ExitCode -notin 0, 1638, 3010) { throw "vc_redist exit $($p.ExitCode)" }
    }
} catch { Write-Host "FAILED: $_" -ForegroundColor Red; $failed += 'Visual C++ runtime' }

# --- Epic Games Launcher ------------------------------------------------------------------------
$launcher = "${env:ProgramFiles(x86)}\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe"
$launcher64 = "$env:ProgramFiles\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"
try {
    if ((Test-Path $launcher) -or (Test-Path $launcher64)) {
        Write-Host 'Epic Games Launcher: already installed.'
    } else {
        $msi = Get-Installer 'https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncherInstaller.msi' 'EpicGamesLauncherInstaller.msi'
        Write-Host 'Installing Epic Games Launcher ...'
        $p = Start-Process msiexec.exe -ArgumentList '/i', "`"$msi`"", '/qn', '/norestart' -Wait -PassThru
        Write-Host "Epic Games Launcher installer exit code: $($p.ExitCode)"
        if (-not ((Test-Path $launcher) -or (Test-Path $launcher64))) { throw "Launcher not found after install (exit $($p.ExitCode))." }
    }
} catch { Write-Host "FAILED: $_" -ForegroundColor Red; $failed += 'Epic Games Launcher' }

# --- Result -------------------------------------------------------------------------------------
Write-Host ''
if ($failed.Count) {
    Write-Host "SETUP FAILED: $($failed -join ', ')" -ForegroundColor Red
} else {
    Write-Host 'SETUP DONE' -ForegroundColor Green
    Write-Host 'Next: open the Epic Games Launcher, sign in, and install Unreal Engine 5.9'
    Write-Host '      to the default folder (C:\Program Files\Epic Games\UE_5.9).'
}
Stop-Transcript | Out-Null
Write-Host "Log: $log"
Read-Host 'Press Enter to close'
