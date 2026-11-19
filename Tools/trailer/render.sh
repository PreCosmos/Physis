#!/bin/sh
# render.sh LEVEL [PRESET]: renders /Game/Trailer/V2/SEQ_T2_<LEVEL> with Movie Render Queue in a windowless game
# process. 8 GB of video memory does not hold a level in the GUI editor and the render together: park the editor on
# an empty map first (open_map.py /Engine/Maps/Entry). Frames land in
# Saved/Trailer/v2/frames/SEQ_T2_<LEVEL>/<shot>.NNNN.jpeg; log in Saved/Trailer/v2/render_<LEVEL>.log.
cd "/mnt/Games/Unreal Projects/Physis" || exit 1
level=$1; preset=${2:-MRQ_Trailer}
map=$(python3 -c "import sys; sys.path.insert(0, 'Tools/trailer'); import shots; print(shots.LEVELS['$level']['map'])")
out="Saved/Trailer/v2/frames/SEQ_T2_$level"; rm -rf "$out"; mkdir -p "$out"
"$HOME/UnrealEngine/Linux_Unreal_Engine_5.9.0_preview-1/Engine/Binaries/Linux/UnrealEditor" "$PWD/Physis.uproject" "$map" -game \
  -LevelSequence="/Game/Trailer/V2/SEQ_T2_$level" -MoviePipelineConfig="/Game/Trailer/V2/$preset" \
  -windowed -ResX=1280 -ResY=720 -RenderOffscreen -nosteam -nosound -nosplash -NoLoadingScreen -unattended -stdout > "Saved/Trailer/v2/render_$level.log" 2>&1
code=$?; mv Saved/Trailer/v2/frames/*.jpeg "$out"/ 2>/dev/null; echo "exit $code frames $(ls "$out" | wc -l)"
