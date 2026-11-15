#!/bin/sh
# Copies what the Windows package needs into ~/PhysisWin, which the WinBoat VM sees as \\host.lan\Data\PhysisWin
# (only the home folder is shared with the VM; the project lives outside it).
set -e
cd "$(dirname "$0")/../.."
mkdir -p "$HOME/PhysisWin"
rsync -a --delete --info=stats1 --exclude='/Build' --exclude='/vm_*.log' \
    Physis.uproject Config Source Content "$HOME/PhysisWin/"
mkdir -p "$HOME/PhysisWin/Tools"
rsync -a --delete Tools/package_physis_windows.bat Tools/winboat "$HOME/PhysisWin/Tools/"
