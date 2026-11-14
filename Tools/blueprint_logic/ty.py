import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=60);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
H='/Game/Characters/Physis/Blueprints/BP_PhysisHUD.BP_PhysisHUD'
R='/Game/Characters/Physis/Blueprints/BP_TutorialTrigger.BP_TutorialTrigger'
def types(bp,f):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':'find_node_types','arguments':{'graph':{'refPath':bp+':EventGraph'},'type_id_filter':f,'context_pins':[]}})
    return r['content'][0]['text'][:300]
for f in ('DrawText','DrawRect','ReceiveDrawHUD','GetTextSize','GetGameTimeinSeconds'):print(f,types(H,f))
for f in ('GetHUD','CastToBP_PhysisHUD','CastToCharacter','ActorBeginOverlap'):print(f,types(R,f))
d=json.loads(c.call('describe_toolset',{'toolset_name':T})['content'][0]['text'])
for t in d['tools']:
    n=t['name'].split('.')[-1]
    if n in('add_variable','add_function_param','set_variable_instance_editable'):print(n,[(k,v.get('type')) for k,v in t['inputSchema']['properties'].items()],t['inputSchema'].get('required'))
