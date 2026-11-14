#!/bin/sh
# Starts Physis as a standalone game. Add this to Steam as a Non-Steam Game so Steam Input
# presents the Steam Controller to the game as a gamepad instead of keyboard and mouse.
cd "$(dirname "$0")/.." || exit 1
__GLX_VENDOR_LIBRARY_NAME=nvidia exec "$HOME/UnrealEngine/Linux_Unreal_Engine_5.9.0_preview-1/Engine/Binaries/Linux/UnrealEditor" "$PWD/Physis.uproject" -game -log \
    -ExecCmds="r.Nanite 0,r.Streaming.PoolSize 1400,sg.GlobalIlluminationQuality 1,sg.ReflectionQuality 1,sg.ShadowQuality 2,sg.EffectsQuality 2,sg.PostProcessQuality 3"
