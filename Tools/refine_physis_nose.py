#!/usr/bin/env python3
"""Give Physis the concept-sheet nose through Unreal MCP, then capture a portrait.

Run from the project folder with the editor open and the MCP server running:
    python3 Tools/refine_physis_nose.py
The result is saved to MH_Physis. The portrait is written to
Art/Characters/Physis/physis-unreal-portrait.png.
"""
import json
import subprocess
import sys
from pathlib import Path
from unreal_mcp import UnrealMCP

client = UnrealMCP(timeout=180)
client.initialize()
result = client.call('call_tool', {
    'toolset_name': 'physis_character_tools.PhysisCharacterTools',
    'tool_name': 'outfit_operation',
    'arguments': {'operation': 'refine_nose'}})
print(json.dumps(result, indent=2, ensure_ascii=False))
if result.get('isError'):
    raise SystemExit('Nose refinement failed; check the editor before retrying.')

here = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(here / 'capture_physis_preview.py'), '--portrait'], check=False)
