#!/usr/bin/env python3
"""open_map.py /Game/Levels/L_X: opens that map in the running editor, refusing if anything is unsaved or a play session runs."""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
from unreal_mcp import UnrealMCP
res = ROOT / 'Saved/Trailer/v2/_result.json'
src = '''
import unreal, json
dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if dirty or les.is_in_play_in_editor():
    out = {'refused': dirty or 'play session'}
else:
    out = {'loaded': les.load_level(%r)}
open(%r, 'w').write(json.dumps(out))
''' % (sys.argv[1], str(res))
c = UnrealMCP(900); c.initialize()
r = c.call('call_tool', {'toolset_name': 'editor_toolset.toolsets.python_scripting.PythonScriptingTools', 'tool_name': 'execute_python', 'arguments': {'script': {'content': src, 'language': 'Python'}}})
print(res.read_text())
