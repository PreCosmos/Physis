#!/usr/bin/env python3
"""Rebuild Physis's assembled MetaHuman after face or hair edits, then capture her.

Run from the project folder with the editor open and the MCP server running:
    python3 Tools/rebuild_physis.py
Pass --keep-rig when the face shape has not changed, to skip the face rig step. That
step and the texture step contact Epic and may ask for sign-in in the editor. Steps
stop at the first failure; after a timeout, check the editor before running it again.

Assembly bakes textures on the GPU. Run this in a freshly opened editor with the
Creator preview closed and hair not forced to full detail, or VRAM can run out and
stall the whole computer. Pass --full-detail only if the GPU has room to spare.
Low scalability settings help, but keep r.HairStrands.Enable on: with it off, the
groom build reads empty data and crashes the editor.
"""
import json
import subprocess
import sys
import time
from pathlib import Path
from unreal_mcp import UnrealMCP

client = UnrealMCP(timeout=1500)
client.initialize()
rig = () if '--keep-rig' in sys.argv else ('rig_save',)
detail = ('review_lod:0',) if '--full-detail' in sys.argv else ()
for step in ('empty_level', *rig, 'textures_save', 'assemble_low_memory', 'brow_color', 'hair_lightning', 'anim:body_mask', 'anim:set_classes', 'studio', 'review_scene', 'verify', *detail):
    started = time.time()
    print('==', step, flush=True)
    result = client.call('call_tool', {
        'toolset_name': 'physis_character_tools.PhysisCharacterTools',
        'tool_name': 'outfit_operation',
        'arguments': {'operation': step}})
    print(json.dumps(result, ensure_ascii=False)[:800], flush=True)
    print('   %d s' % (time.time() - started), flush=True)
    if result.get('isError'):
        raise SystemExit('Failed at %s; check the editor before retrying.' % step)

here = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(here / 'capture_physis_preview.py'), '--portrait'], check=False)
print('== done', flush=True)
