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
    return next(p for p in info(n)[side] if p['name']==name)
def node(t,x,y):return call('create_node',{'graph':G,'type_id':t,'pos':{'x':x,'y':y}})
def link(a,out,b):
    call('connect_pins',{'output_pin':pin(a,out,'output_pins')['pin_id'],'input_pin':pin(b,'execute','input_pins')['pin_id']})
found=call('find_nodes',{'graph':G,'title':'IA_Scan'})
print(str(found)[:400])
scan=found[0] if isinstance(found,list) else found
for p in info(scan)['output_pins']:
    print(p['name'],len(p.get('connected_pins',[])))
y=5200
link(scan,'Completed',node('CallFunction|PhysisScanRelease',0,y))
link(scan,'Canceled',node('CallFunction|PhysisScanRelease',0,y+180))
e=node('Input|EnhancedActionEvents|IA_ScanVisor',-400,y+400)
link(e,'Started',node('CallFunction|PhysisVisorToggle',0,y+400))
for t in('IA_Attack','IA_Dodge','IA_Jump'):
    n=call('find_nodes',{'graph':G,'title':t})[0]
    print(t,[(p['name'],len(p.get('connected_pins',[]))) for p in info(n)['output_pins'] if p['name'] in('Started',)])
call('compile_blueprint',{'blueprint':{'refPath':P}})
