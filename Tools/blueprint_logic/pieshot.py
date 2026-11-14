import json,sys,base64,math,subprocess
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=60);c.initialize()
def op(o):
    r=c.call('call_tool',{'toolset_name':'physis_character_tools.PhysisCharacterTools','tool_name':'outfit_operation','arguments':{'operation':o}})
    return json.loads(json.loads(r['content'][0]['text'])['returnValue'])
s=op('play:pie_state');print(s)
x,y,z=s['location']
pose={'location':{'x':x-260,'y':y-120,'z':z+60},'rotation':{'pitch':-8,'yaw':25,'roll':0}}
r=c.call('call_tool',{'toolset_name':'EditorToolset.EditorAppToolset','tool_name':'CaptureViewport','arguments':{'captureTransform':pose,
 'annotations':{'gridSpacing':0,'gridExtent':0,'gridHeight':0,'maxLabelDistance':0,'classFilter':{'refPath':'/Script/Engine.Actor'},'maxLabels':0},'bShowUI':False}})
d=json.loads(r['content'][0]['text'])['returnValue']
open(sys.argv[1],'wb').write(base64.b64decode(d['image']['data']))
