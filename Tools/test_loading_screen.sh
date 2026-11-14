#!/bin/sh
# Loading-screen test in a standalone game (2026-11-07). Run it on the host: flatpak-spawn --host sh Tools/test_loading_screen.sh OUTDIR "MAP?OPTIONS" MAPNAME
# e.g. "L_BattleStation" (New Game) or "L_CenterOfTheUniverse?nocine,load" (Continue with a Center save). Close every editor first;
# back up Saved/SaveGames/*.sav and Saved/Config/LinuxEditor/GameUserSettings.ini first and restore them after (a -game run rewrites the ini).
# -nosteam: from a terminal the engine's Steam online module ends the process at start-up. spectacle saves nothing from a Terminal-panel tab.
# It opens the menu, then MAP?OPTIONS as New Game and Continue do (OpenLevel), takes a shot about every second until the log says MAPNAME is ready, then quits.
OUT="$1"; OPEN="$2"; MAP="$3"
P=/home/precosmos/PhysisProject
LOG="$P/Saved/Logs/Physis.log"
mkdir -p "$OUT"
rm -f "$OUT"/shot_*.png
START=$(date +%s)
"/home/precosmos/UnrealEngine/Linux_Unreal_Engine_5.9.0_preview-1/Engine/Binaries/Linux/UnrealEditor" "$P/Physis.uproject" /Game/Levels/L_MainMenu \
  -game -nosteam -windowed -ResX=1600 -ResY=900 -noraytracing -ExecCmds="open $OPEN" > "$OUT/game.out" 2>&1 &
GAME=$!
i=0
ready=0
while [ $i -lt 400 ] && kill -0 $GAME 2>/dev/null; do
  sleep 0.3
  spectacle -b -n -a -o "$OUT/shot_$(printf %03d $i)_$(( $(date +%s) - START ))s.png" >/dev/null 2>&1
  i=$((i+1))
  if grep -q "LogPhysisLoading: $MAP ready" "$LOG" 2>/dev/null; then
    ready=$((ready+1))
    [ $ready -gt 3 ] && break
  fi
done
grep -E "LogPhysisLoading|LogMoviePlayer|Took .* seconds to LoadMap" "$LOG" > "$OUT/loading_lines.txt"
kill $GAME 2>/dev/null
sleep 5
kill -9 $GAME 2>/dev/null
cp "$LOG" "$OUT/Physis.log" 2>/dev/null
echo "done: $i shots, ready=$ready, $(( $(date +%s) - START )) s"
