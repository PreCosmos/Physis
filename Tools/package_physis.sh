#!/bin/sh
# Cooks and packages Physis for Linux (Shipping) into Build/Linux.
# Close the Unreal editor first: cooking alongside it can run out of memory.
# The Steam plugin makes this a project with its own editor target, so UAT builds PhysisEditor first.
# Run it from an ASCII path (~/PhysisProject symlink): the ONNX runtime used while cooking cannot open
# files under the Greek 'Έγγραφα' folder. -NoUBA keeps the build accelerator from tripping over the symlink.
# -IgnoreCookErrors: the only cook "errors" are the editor failing to find /usr/bin/git, which is not installed.
# Check Saved/package_linux.log for any other LogCook errors after each build.
# Only the game's own maps are cooked; keep this list in step with MapsToCook in DefaultGame.ini.
set -e
cd "$(dirname "$0")/.."
ENGINE="$HOME/UnrealEngine/Linux_Unreal_Engine_5.9.0_preview-1"
"$ENGINE/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun \
    -project="$PWD/Physis.uproject" -platform=Linux -clientconfig=Shipping \
    -cook -map=/Game/Levels/L_MainMenu+/Game/Levels/L_BattleStation+/Game/Levels/L_CenterOfTheUniverse+/Game/Levels/L_Conclave+/Game/Levels/L_Grove+/Game/Levels/L_Arche -build -stage -pak -iostore -package -archive -archivedirectory="$PWD/Build" \
    -ubtargs="-NoUBA" -IgnoreCookErrors -nop4 -utf8output
# Lets the packaged build find Steam when launched outside the Steam client.
echo 4673680 > "$PWD/Build/Linux/steam_appid.txt"
echo "Packaged to $PWD/Build/Linux"
