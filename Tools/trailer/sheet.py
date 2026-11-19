#!/usr/bin/env python3
"""sheet.py LEVEL [n]: a contact sheet of the rendered frames of a level, n per shot (default 3): Saved/Trailer/v2/scout/rd_LEVEL.jpg"""
import sys, subprocess, pathlib, math
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/trailer'))
import shots
level = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
src = ROOT / 'Saved/Trailer/v2/frames' / ('SEQ_T2_' + level)
cmd, count = ['ffmpeg', '-y', '-loglevel', 'error'], 0
for shot in shots.LEVELS[level]['shots']:
    files = sorted(src.glob(shot['name'] + '.*.jpeg'))
    if not files:
        print('no frames for', shot['name']); continue
    for k in range(n):
        cmd += ['-i', str(files[min(len(files) - 1, round((k + .15) / n * len(files)))])]; count += 1
cmd += ['-filter_complex', 'concat=n=%d:v=1:a=0,scale=640:360,tile=%dx%d' % (count, n, math.ceil(count / n)), '-frames:v', '1', str(ROOT / 'Saved/Trailer/v2/scout' / ('rd_%s.jpg' % level))]
subprocess.run(cmd); print('sheet', ROOT / 'Saved/Trailer/v2/scout' / ('rd_%s.jpg' % level))
