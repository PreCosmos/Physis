#!/bin/sh
# batch.sh SHEET < lines of "name x y h tx ty th fov" (scout.py look) or "@name x y z tx ty tz fov" (abs): captures and tiles a labelled sheet
cd "/mnt/Games/Unreal Projects/Physis"; D=Saved/Trailer/v2/scout; sheet=$1; in=""; n=0
while read name rest; do [ -z "$name" ] && continue; mode=look; case $name in @*) mode=abs; name=${name#@};; esac
  python3 Tools/trailer/scout.py $mode $name $rest
  ffmpeg -y -loglevel error -i $D/$name.png -vf "scale=640:360,drawtext=text='$name':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6" $D/_l_$name.jpg; in="$in -i $D/_l_$name.jpg"; n=$((n+1)); done
cols=3; rows=$(( (n + 2) / 3 ))
ffmpeg -y -loglevel error $in -filter_complex "concat=n=$n:v=1:a=0,tile=${cols}x${rows}" -frames:v 1 $D/$sheet.jpg; rm -f $D/_l_*.jpg; echo sheet $D/$sheet.jpg
