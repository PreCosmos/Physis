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
y=5900
for action,fnname in (('IA_AttackHeavy','PhysisAttackHeavy'),('IA_Block','PhysisBlock')):
    e=node('Input|EnhancedActionEvents|'+action,-400,y)
    link(e,'Started',node('CallFunction|'+fnname,0,y));y+=250
for t in('IA_Attack','IA_Scan','IA_ScanVisor','IA_AttackHeavy','IA_Block','IA_Dodge'):
    n=call('find_nodes',{'graph':G,'title':t})[0]
    print(t,[(p['name'],len(p.get('connected_pins',[]))) for p in info(n)['output_pins'] if p['name'] in('Started','Completed','Canceled')])
call('compile_blueprint',{'blueprint':{'refPath':P}})
