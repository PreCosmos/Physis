import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=60);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
A='/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed.Physis_ABP_Unarmed:AnimGraph'
def call(t,a):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    if r.get('isError'):raise RuntimeError(r['content'][0]['text'][:400])
    return json.loads(r['content'][0]['text'])['returnValue']
nodes=call('find_nodes',{'graph':{'refPath':A},'title':''})
infos=call('get_node_infos',{'nodes':nodes})
for n in infos:
    print(n['node']['refPath'].split('.')[-1],n.get('type_id'))
    for side in('input_pins','output_pins'):
        for p in n[side]:
            print('   ',side[:2],p['name'],p['type_id'][:24],str(p['value'])[:60],[x['node']['refPath'].split('.')[-1] for x in p['connected_pins']])
