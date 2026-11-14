#!/bin/sh
# clip.sh NAME FRAMES hud|nohud [ops to run right after recording starts...]
# Records FRAMES frames at 1/30 s of game time each into Marketing/Trailer/Clips/NAME.
S=/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad
cd "/var/home/precosmos/Έγγραφα/Unreal Projects/Physis"
name=$1; frames=$2; hud=$3; shift 3
dir=Marketing/Trailer/Clips/$name; mkdir -p "$dir"; rm -f "$dir"/*.png Saved/Screenshots/LinuxEditor/MovieFrame*
[ "$hud" = "nohud" ] && timeout 30 python3 $S/aaa.py "aaa:pie_cmd:ShowHUD" >/dev/null 2>&1
timeout 30 python3 $S/aaa.py "aaa:pie_hold_dilation:0.18" "aaa:pie_cmd:r.DumpingMovie $frames" >/dev/null 2>&1
[ $# -gt 0 ] && timeout 60 python3 $S/aaa.py "$@" >/dev/null 2>&1
for i in $(seq 1 400); do n=$(ls Saved/Screenshots/LinuxEditor | grep -c MovieFrame); [ $n -ge $frames ] && break; sleep 1; done
sleep 2
timeout 30 python3 $S/aaa.py "aaa:pie_hold_dilation:0" >/dev/null 2>&1
[ "$hud" = "nohud" ] && timeout 30 python3 $S/aaa.py "aaa:pie_cmd:ShowHUD" >/dev/null 2>&1
mv Saved/Screenshots/LinuxEditor/MovieFrame*.png "$dir"/
echo "$name: $(ls "$dir" | wc -l) frames"
