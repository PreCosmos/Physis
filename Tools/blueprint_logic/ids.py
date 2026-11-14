import sys,json
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=60);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
B='/Game/Characters/Physis/Blueprints/'
H=B+'BP_PhysisHUD.BP_PhysisHUD:EventGraph'



P=B+'BP_Physis.BP_Physis:EventGraph'
for f in ('GetSequencePlayer','Sequencer|Player','GetActorOfClass','SetIgnoreMoveInput','SetIgnoreLookInput','SetCustomPrimitiveDataFloat','RandomFloatinRange','RandomUnitVector','SetActorScale3D','AddActorWorldOffset','GetOptionsString','GetGameMode','String|Contains','Utilities|String|Contains'):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':'find_node_types','arguments':{'graph':{'refPath':P},'type_id_filter':f,'context_pins':[]}})
    t=r['content'][0]['text']
    try: t=json.loads(t)['returnValue']; t=[x for x in t if 'Casting' not in str(x) and 'Niagara' not in str(x)][:8]
    except Exception: t=t[:200]
    print(f,t)
