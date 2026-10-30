"""Capture the current Physis review viewport through Unreal MCP."""
import argparse
import base64
import json
import math
from pathlib import Path
from unreal_mcp import UnrealMCP

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--portrait',action='store_true')
args=parser.parse_args()
client=UnrealMCP(timeout=120)
client.initialize()
x,y,z,target=(20,95,153,151) if args.portrait else (65,295,100,85)
pose={'location':{'x':x,'y':y,'z':z},'rotation':{
    'pitch':math.degrees(math.atan2(target-z,math.hypot(x,y))),
    'yaw':math.degrees(math.atan2(-y,-x)),'roll':0}}
result=client.call('call_tool',{'toolset_name':'EditorToolset.EditorAppToolset',
    'tool_name':'SetCameraTransform','arguments':{'transform':pose}})
if result.get('isError'):raise RuntimeError(str(result))
import time
time.sleep(1)
result=client.call('call_tool',{'toolset_name':'EditorToolset.EditorAppToolset',
    'tool_name':'CaptureViewport','arguments':{'captureTransform':pose,
    'annotations':{'gridSpacing':0,'gridExtent':0,'gridHeight':0,
    'maxLabelDistance':0,'classFilter':{'refPath':'/Script/Engine.Actor'},'maxLabels':0},'bShowUI':False}})
if result.get('isError'):raise RuntimeError(str(result))
data=json.loads(result['content'][0]['text'])['returnValue']
path=Path(__file__).resolve().parents[1]/'Art/Characters/Physis'/('physis-unreal-portrait.png' if args.portrait else 'physis-unreal-preview.png')
path.write_bytes(base64.b64decode(data['image']['data']))
print(path)
