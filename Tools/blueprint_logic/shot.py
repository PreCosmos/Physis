import json,sys,base64
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=60);c.initialize()
x,y,z,pitch,yaw=[float(v) for v in sys.argv[2:7]]
pose={'location':{'x':x,'y':y,'z':z},'rotation':{'pitch':pitch,'yaw':yaw,'roll':0}}
r=c.call('call_tool',{'toolset_name':'EditorToolset.EditorAppToolset','tool_name':'CaptureViewport','arguments':{'captureTransform':pose,
 'annotations':{'gridSpacing':0,'gridExtent':0,'gridHeight':0,'maxLabelDistance':0,'classFilter':{'refPath':'/Script/Engine.Actor'},'maxLabels':0},'bShowUI':False}})
open(sys.argv[1],'wb').write(base64.b64decode(json.loads(r['content'][0]['text'])['returnValue']['image']['data']))
