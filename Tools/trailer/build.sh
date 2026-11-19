#!/bin/sh
# build.sh LEVEL [LEVEL ...]: rebuilds trailer sequences from shots.py without the GUI editor. Result: Saved/Trailer/v2/build.json
cd "/mnt/Games/Unreal Projects/Physis" || exit 1
rm -f Saved/Trailer/v2/build.json
"$HOME/UnrealEngine/Linux_Unreal_Engine_5.9.0_preview-1/Engine/Binaries/Linux/UnrealEditor-Cmd" "$PWD/Physis.uproject" \
  -ExecutePythonScript="$PWD/Tools/trailer/build_headless.py $*" -nullrhi -unattended -nosplash -nosound -nosteam -stdout > Saved/Trailer/v2/build.log 2>&1
echo "exit $?"; cat Saved/Trailer/v2/build.json
