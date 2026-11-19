#!/usr/bin/env python3
"""tt.py EXPR: evaluates EXPR with trailer_ue imported as t in the running editor and prints its result as JSON.
e.g. tt.py "t.build('Grove')"   tt.py "t.render('Grove', 1280, 720, temporal=2)"
tt.py wait LEVEL: blocks until that render's _done.json appears."""
import sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
from unreal_mcp import UnrealMCP
if sys.argv[1] == 'wait':
    done = ROOT / 'Saved/Trailer/v2/frames' / sys.argv[2] / '_done.json'
    limit = time.time() + float(sys.argv[3]) if len(sys.argv) > 3 else None
    while not done.exists():
        if limit and time.time() > limit:
            print('STILL RENDERING', len(list(done.parent.glob('*.jpeg'))), 'frames'); sys.exit(2)
        time.sleep(3)
    print(done.read_text(), len(list(done.parent.glob('*.jpeg'))), 'frames'); sys.exit(0)
res = ROOT / 'Saved/Trailer/v2/_result.json'
src = '''
import sys, json, importlib, traceback
sys.path.insert(0, %r)
import trailer_ue as t
importlib.reload(t)
try:
    out = {'ok': %s}
except Exception:
    out = {'error': traceback.format_exc()}
open(%r, 'w').write(json.dumps(out, default=str))
''' % (str(ROOT / 'Tools/trailer'), sys.argv[1], str(res))
c = UnrealMCP(600); c.initialize()
r = c.call('call_tool', {'toolset_name': 'editor_toolset.toolsets.python_scripting.PythonScriptingTools', 'tool_name': 'execute_python', 'arguments': {'script': {'content': src, 'language': 'Python'}}})
if r.get('isError'):
    print(''.join(p.get('text', '') for p in r.get('content', []))[:1500])
out = json.loads(res.read_text())
print(out.get('error') or json.dumps(out['ok']))
