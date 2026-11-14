import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=60);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
P='/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed.Physis_ABP_Unarmed'
def call(t,a):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a});return r['content'][0]['text']
gs=json.loads(call('list_graphs',{'blueprint':{'refPath':P}}))['returnValue']
print([g['refPath'].split(':')[-1] for g in gs])
for g in gs:
    n=g['refPath'].split(':')[-1]
    if n in('EventGraph',) or 'Update' in n or 'Initial' in n:
        t=call('read_graph_dsl',{'graph':g})
        try:print(n,json.loads(t)['returnValue'][:1600])
        except Exception:print(n,t[:300])
print(call('list_variables',{'blueprint':{'refPath':P}})[:700])
