#!/usr/bin/env python3
"""Scouting for trailer shots in the map open in the running editor.

scout.py ground x,y [x,y ...]             ground height (cm) under points given in metres
scout.py look NAME x y h tx ty th [fov]   capture Saved/Trailer/v2/scout/NAME.png from (x, y) metres at h metres above
                                          the ground there, looking at (tx, ty) th metres above the ground there
scout.py abs NAME x y z tx ty tz [fov]    the same with absolute heights (metres)
Prints the camera's world position and target in centimetres, as shots.py wants them.
"""
import sys, json, base64, math, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
from unreal_mcp import UnrealMCP
c = UnrealMCP(180); c.initialize()
OUT = ROOT / 'Saved/Trailer/v2/scout'


def text(r):
    return ''.join(p.get('text', '') for p in r.get('content', []))


def ground(points):
    src = '''
import unreal, json
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
out = []
for x, y in %r:
    hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x * 100, y * 100, 200000), unreal.Vector(x * 100, y * 100, -50000), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    out.append(hit.to_tuple()[4].z if hit else None)
open(%r, 'w').write(json.dumps(out))
''' % (points, str(OUT / '_ground.json'))
    r = c.call('call_tool', {'toolset_name': 'editor_toolset.toolsets.python_scripting.PythonScriptingTools', 'tool_name': 'execute_python', 'arguments': {'script': {'content': src, 'language': 'Python'}}})
    if r.get('isError'):
        print(text(r)[:800])
    return json.load(open(OUT / '_ground.json'))


def capture(name, eye, target, fov):
    dx, dy, dz = (target[i] - eye[i] for i in range(3))
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    T = 'SceneCaptureToolset.SceneCaptureToolset'
    worlds = json.loads(text(c.call('call_tool', {'toolset_name': T, 'tool_name': 'ListWorlds', 'arguments': {}})))['returnValue']
    world = [x for x in worlds if x['worldType'] == 'Editor'][0]['world']
    cam = {'location': dict(zip('xyz', eye)), 'rotation': {'pitch': pitch, 'yaw': yaw, 'roll': 0}, 'projectionMode': 'Perspective', 'fOV': fov}
    r = c.call('call_tool', {'toolset_name': T, 'tool_name': 'Capture', 'arguments': {'world': world, 'camera': cam, 'mode': 'Lit', 'options': {'width': 1280, 'height': 720, 'screenPercentage': 1, 'visualizationSubMode': ''}}})
    for part in r.get('content', []):
        if part.get('type') == 'image':
            (OUT / (name + '.png')).write_bytes(base64.b64decode(part['data']))
            print(name, 'eye (%.0f, %.0f, %.0f) look (%.0f, %.0f, %.0f)' % (*eye, *target))
            return
    print('NO IMAGE', text(r)[:600])


cmd = sys.argv[1]
if cmd == 'ground':
    pts = [tuple(float(v) for v in a.split(',')) for a in sys.argv[2:]]
    print(ground(pts))
else:
    name = sys.argv[2]
    x, y, h, tx, ty, th = (float(v) for v in sys.argv[3:9])
    fov = float(sys.argv[9]) if len(sys.argv) > 9 else 60
    if cmd == 'look':
        g = ground([(x, y), (tx, ty)])
        h, th = (g[0] or 0) / 100 + h, (g[1] or 0) / 100 + th
    capture(name, (x * 100, y * 100, h * 100), (tx * 100, ty * 100, th * 100), fov)
