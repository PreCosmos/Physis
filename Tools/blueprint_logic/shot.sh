#!/bin/sh
# shot.sh NAME RES HUD op1 op2 ...  -> Marketing/Steam/<dir>/NAME.png
S=/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad
cd "/var/home/precosmos/Έγγραφα/Unreal Projects/Physis"
name=$1; res=$2; hud=$3; shift 3
dir=Marketing/Steam/Screenshots; [ "$res" = "1920x1080" ] || dir=Marketing/Steam/KeyArt
[ $# -gt 0 ] && timeout 200 python3 $S/aaa.py "$@" >/dev/null 2>&1
[ "$hud" = "nohud" ] && timeout 30 python3 $S/aaa.py "aaa:pie_cmd:ShowHUD" >/dev/null 2>&1
sleep 3
before=$(ls Saved/Screenshots/LinuxEditor | grep -c Highres)
timeout 60 python3 $S/aaa.py "aaa:pie_cmd:HighResShot $res" >/dev/null 2>&1
for i in $(seq 1 30); do [ $(ls Saved/Screenshots/LinuxEditor | grep -c Highres) -gt $before ] && break; sleep 2; done
sleep 2
f=$(ls -t Saved/Screenshots/LinuxEditor/Highres* | head -1); mv "$f" "$dir/$name.png"
[ "$hud" = "nohud" ] && timeout 30 python3 $S/aaa.py "aaa:pie_cmd:ShowHUD" >/dev/null 2>&1
echo "$dir/$name.png"
