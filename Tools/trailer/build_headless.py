"""Run by build.sh in a windowless editor: build_headless.py LEVEL [LEVEL ...] builds each level's trailer sequence
(loading its map first, since the Awakening binds actors in it) and writes Saved/Trailer/v2/build.json."""
import json
import sys
import traceback

import unreal

sys.path.insert(0, '/mnt/Games/Unreal Projects/Physis/Tools/trailer')
import trailer_ue as t
import shots

out = {}
try:
    loaded = None
    for level in sys.argv[1:]:
        m = shots.LEVELS[level]['map']
        if 'anim' in shots.LEVELS[level]['shots'][0] and m != loaded:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(m)
            loaded = m
        out[level] = t.build(level)
    if 'Awakening' in sys.argv[1:]:
        out['face'] = t.face_report()
except Exception:
    out['error'] = traceback.format_exc()
open('/mnt/Games/Unreal Projects/Physis/Saved/Trailer/v2/build.json', 'w').write(json.dumps(out, indent=1, default=str))
