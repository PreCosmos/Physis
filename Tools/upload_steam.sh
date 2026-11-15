#!/bin/sh
# Uploads Build/Linux (depot 4673681) and Build/Windows (depot 4673682) to Steam app 4673680. Run it yourself: steamcmd asks for your
# Steamworks login and Steam Guard code. The build is uploaded but not set live;
# make it live from Steamworks > SteamPipe > Builds.
set -e
cd "$(dirname "$0")/.."
# steamcmd is a 32-bit program. Inside a Flatpak sandbox (such as an app's built-in terminal)
# there are no 32-bit libraries, so hand the whole script over to the host system.
if [ -f /.flatpak-info ] && command -v flatpak-spawn >/dev/null 2>&1; then
    exec flatpak-spawn --host sh "$PWD/Tools/upload_steam.sh"
fi
[ -f Build/Linux/Physis.sh ] || { echo "No Linux package yet. Run Tools/package_physis.sh first."; exit 1; }
[ -f Build/Windows/Physis/Binaries/Win64/Physis-Win64-Shipping.exe ] || { echo "No Windows package in Build/Windows. Package it in WinBoat and copy it there."; exit 1; }
STEAMCMD="${STEAMCMD:-$(command -v steamcmd || echo "$HOME/steamcmd/steamcmd.sh")}"
if [ ! -x "$STEAMCMD" ]; then
    echo "Installing steamcmd into ~/steamcmd from Valve..."
    mkdir -p "$HOME/steamcmd"
    curl -fsSL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz | tar -xz -C "$HOME/steamcmd"
fi
printf 'Steamworks account name: '
read -r ACCOUNT
"$STEAMCMD" +login "$ACCOUNT" +run_app_build "$PWD/Tools/steam/app_build_4673680.vdf" +quit
