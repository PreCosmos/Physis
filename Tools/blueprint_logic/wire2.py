import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=120);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
P='/Game/Characters/Physis/Blueprints/BP_Physis.BP_Physis'
G={'refPath':P+':EventGraph'}
def call(tool,args):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':tool,'arguments':args})
    if r.get('isError'):raise RuntimeError(tool+': '+r['content'][0]['text'][:500])
    return json.loads(r['content'][0]['text'])['returnValue']
def info(n):return call('get_node_infos',{'nodes':[n]})[0]
def pin(n,name,side):
    d=info(n)
    return next(p['pin_id'] for p in d[side] if p['name']==name)
def node(t,x,y):return call('create_node',{'graph':G,'type_id':t,'pos':{'x':x,'y':y}})
def link(a,out,b):
    call('connect_pins',{'output_pin':pin(a,out,'output_pins'),'input_pin':pin(b,'execute','input_pins')})
d=json.loads(c.call('describe_toolset',{'toolset_name':T})['content'][0]['text'])
fs=next(t for t in d['tools'] if t['name'].endswith('.find_nodes'))['inputSchema']
print(list(fs['properties']),fs.get('required'))
y=2000
move={'refPath':P+':EventGraph.K2Node_EnhancedInputAction_1'}
link(move,'Triggered',node('CallFunction|PhysisMove',0,y))
wires=[('IA_Look',[('Triggered','CallFunction|PhysisLookStick')]),
       ('IA_MouseLook',[('Triggered','CallFunction|PhysisLookMouse')]),
       ('IA_Jump',[('Started','Character|Jump'),('Completed','Character|StopJumping')]),
       ('IA_Sprint',[('Started','CallFunction|PhysisSprintOn'),('Completed','CallFunction|PhysisSprintOff')]),
       ('IA_Dodge',[('Started','CallFunction|PhysisDodge')]),
       ('IA_Attack',[('Started','CallFunction|PhysisAttack')]),
       ('IA_Scan',[('Started','CallFunction|PhysisScan')]),
       ('IA_Interact',[('Started','CallFunction|PhysisInteract')])]
for action,items in wires:
    y+=350
    event=node('Input|EnhancedActionEvents|'+action,-400,y)
    for i,(out,target) in enumerate(items):
        link(event,out,node(target,0,y+i*180))
    print('wired',action)
