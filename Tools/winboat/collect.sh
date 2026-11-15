#!/bin/sh
# Brings the Windows package made in the VM (~/PhysisWin/Build/Windows) into Build/Windows.
set -e
cd "$(dirname "$0")/../.."
grep -q "PACKAGE DONE" "$HOME/PhysisWin/vm_package.log" || { echo "The VM has not finished packaging (see ~/PhysisWin/vm_package.log)."; exit 1; }
rsync -a --delete --info=stats1 "$HOME/PhysisWin/Build/Windows/" Build/Windows/
