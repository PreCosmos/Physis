import sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=90);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
B='/Game/Characters/Physis/Blueprints/'
D=B+'BP_StationDoor.BP_StationDoor';P=B+'BP_Physis.BP_Physis'
def call(t,a):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    print(t,r['content'][0]['text'][:200],'ERR' if r.get('isError') else '')
call('remove_variable',{'blueprint':{'refPath':D},'name':'Locked'})
call('compile_blueprint',{'blueprint':{'refPath':D}})
call('write_graph_dsl',{'graph':{'refPath':P+':PhysisDodge'},'code':'''(fn PhysisDodge ()
  (bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))
  (if (not (Animation|Montage|IsAnyMontagePlaying :self anim))
    (Animation|Montage|MontagePlay anim "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Dodge.AM_Physis_Dodge")
    (bind wanted (Pawn|Input|GetLastMovementInputVector))
    (bind heading (select (> (Math|Vector|VectorLength wanted) 0.1) (Math|Vector|Normalize wanted) (Transformation|GetActorForwardVector)))
    (Character|LaunchCharacter :LaunchVelocity (* heading 3000.0) :bXYOverride true)))'''})
call('compile_blueprint',{'blueprint':{'refPath':P}})
