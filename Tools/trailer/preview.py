#!/usr/bin/env python3
"""preview.py LEVEL [shot ...] [--at 0,.5,1]: scrubs the level's sequence in the editor and captures each shot's view at
those points of the shot (default start, middle, end) into one sheet, Saved/Trailer/v2/scout/pv_LEVEL.jpg."""
import sys, json, math, time, base64, subprocess, pathlib, importlib.util
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools')); sys.path.insert(0, str(ROOT / 'Tools/trailer'))
from unreal_mcp import UnrealMCP
import shots
OUT = ROOT / 'Saved/Trailer/v2/scout'
args = sys.argv[1:]
at = (0, .5, 1)
if '--at' in args:
    i = args.index('--at'); at = tuple(float(v) for v in args[i + 1].split(',')); del args[i:i + 2]
level, want = args[0], args[1:]
c = UnrealMCP(300); c.initialize()
text = lambda r: ''.join(p.get('text', '') for p in r.get('content', []))


def py(src):
    r = c.call('call_tool', {'toolset_name': 'editor_toolset.toolsets.python_scripting.PythonScriptingTools', 'tool_name': 'execute_python', 'arguments': {'script': {'content': src, 'language': 'Python'}}})
    if r.get('isError'):
        print(text(r)[:900])


def smooth(u): return u * u * (3 - 2 * u)


def pose(shot, u):
    keys = shot['keys']
    if shot.get('ease'): u = smooth(u)
    for a, b in zip(keys, keys[1:]):
        if u <= b[0] or b is keys[-1]:
            k = min(1.0, max(0.0, (u - a[0]) / (b[0] - a[0])))
            mix = lambda p, q: tuple(p[i] + (q[i] - p[i]) * k for i in range(3))
            ra, rb = (a[3] if len(a) > 3 else 0.0), (b[3] if len(b) > 3 else 0.0)
            return mix(a[1], b[1]), mix(a[2], b[2]), ra + (rb - ra) * k


T = 'SceneCaptureToolset.SceneCaptureToolset'
worlds = json.loads(text(c.call('call_tool', {'toolset_name': T, 'tool_name': 'ListWorlds', 'arguments': {}})))['returnValue']
world = [x for x in worlds if x['worldType'] == 'Editor'][0]['world']
start, tiles = 0, []
for shot in shots.LEVELS[level]['shots']:
    n = shot['frames']
    if not want or shot['name'] in want:
        for u in at:
            frame = start + int(round(u * (n - 1)))
            py("import sys\nsys.path.insert(0, %r)\nimport trailer_ue as t\nt.realtime(True)\nt.scrub(%r, %d)" % (str(ROOT / 'Tools/trailer'), level, frame))
            time.sleep(1.5)
            eye, look, roll = pose(shot, u)
            d = [look[i] - eye[i] for i in range(3)]
            cam = {'location': dict(zip('xyz', eye)), 'rotation': {'pitch': math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))), 'yaw': math.degrees(math.atan2(d[1], d[0])), 'roll': roll},
                   'projectionMode': 'Perspective', 'fOV': math.degrees(2 * math.atan(24.89 / 2 / shot.get('focal', 24)))}
            r = c.call('call_tool', {'toolset_name': T, 'tool_name': 'Capture', 'arguments': {'world': world, 'camera': cam, 'mode': 'Lit', 'options': {'width': 1280, 'height': 720, 'screenPercentage': 1, 'visualizationSubMode': ''}}})
            img = [p for p in r.get('content', []) if p.get('type') == 'image']
            if not img:
                print('NO IMAGE', shot['name'], text(r)[:300]); continue
            raw = OUT / ('_pv_%s_%d.png' % (shot['name'], frame))
            raw.write_bytes(base64.b64decode(img[0]['data']))
            tile = OUT / ('_pv_%s_%d.jpg' % (shot['name'], frame))
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-vf', "scale=640:360,drawtext=text='%s %.2f':x=8:y=8:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.6" % (shot['name'], u), str(tile)])
            raw.unlink(); tiles.append(tile)
    start += n
cols = len(at)
cmd = ['ffmpeg', '-y', '-loglevel', 'error']
for t in tiles: cmd += ['-i', str(t)]
cmd += ['-filter_complex', 'concat=n=%d:v=1:a=0,tile=%dx%d' % (len(tiles), cols, math.ceil(len(tiles) / cols)), '-frames:v', '1', str(OUT / ('pv_%s.jpg' % level))]
subprocess.run(cmd)
for t in tiles: t.unlink()
print('sheet', OUT / ('pv_%s.jpg' % level))
