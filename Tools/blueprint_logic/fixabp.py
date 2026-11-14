import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=90);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
B='/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed.Physis_ABP_Unarmed'
A=B+':AnimGraph'
def call(t,a):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    if r.get('isError'):raise RuntimeError(t+' '+r['content'][0]['text'][:400])
    return json.loads(r['content'][0]['text'])['returnValue']
nodes={n['refPath'].split('.')[-1]:n for n in call('find_nodes',{'graph':{'refPath':A},'title':''})}
infos=lambda n:call('get_node_infos',{'nodes':[n]})[0]
slot=next(p['pin_id'] for p in infos(nodes['AnimGraphNode_Slot_0'])['output_pins'] if p['name']=='Pose')
root=next(p['pin_id'] for p in infos(nodes['AnimGraphNode_Root_0'])['input_pins'] if p['name']=='Result')
d=json.loads(c.call('describe_toolset',{'toolset_name':T})['content'][0]['text'])
print([ (t['name'].split('.')[-1],list(t['inputSchema']['properties'])) for t in d['tools'] if t['name'].endswith(('break_pins','delete_node'))])
ctrl=nodes['AnimGraphNode_ControlRig_0']
call('delete_node',{'node':ctrl})
call('connect_pins',{'output_pin':slot,'input_pin':root})
print(call('compile_blueprint',{'blueprint':{'refPath':B}}))
