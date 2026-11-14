import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=90);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
H='/Game/Characters/Physis/Blueprints/BP_PhysisHUD.BP_PhysisHUD'
R='/Game/Characters/Physis/Blueprints/BP_TutorialTrigger.BP_TutorialTrigger'
def call(t,a,ok=False):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    txt=r['content'][0]['text']
    if r.get('isError'):
        print('ERR',t,txt[:420])
        return None
    return txt
print('vars',json.dumps(c.call('call_tool',{'toolset_name':T,'tool_name':'list_variables','arguments':{'blueprint':{'refPath':H}}}))[:160])
call('add_variable',{'blueprint':{'refPath':H},'name':'TutorialHideAt','type_name':'float'})
print(call('write_graph_dsl',{'graph':{'refPath':H+':ShowTutorial'},'code':'''(fn ShowTutorial (Message)
  (Variables|Default|SetTutorialText Message)
  (Variables|Default|SetTutorialHideAt (+ (Utilities|Time|GetGameTimeinSeconds) 8.0)))'''}))
print(call('write_graph_dsl',{'graph':{'refPath':H+':EventGraph'},'code':'''(event EventReceiveDrawHUD (SizeX SizeY)
  (if (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetTutorialHideAt))
    (bind message (Variables|Default|GetTutorialText))
    (bind (width height) (HUD|GetTextSize :Text message :Scale 1.6))
    (bind left (/ (- SizeX width) 2.0))
    (bind top (- SizeY 170.0))
    (HUD|DrawRect :RectColor "(R=0.0,G=0.02,B=0.05,A=0.72)" :ScreenX (- left 24.0) :ScreenY (- top 14.0) :ScreenW (+ width 48.0) :ScreenH (+ height 28.0))
    (HUD|DrawText :Text message :TextColor "(R=1.0,G=0.85,B=0.55,A=1.0)" :ScreenX left :ScreenY top :Scale 1.6)))'''}))
print(call('compile_blueprint',{'blueprint':{'refPath':H}}))
r=c.call('call_tool',{'toolset_name':T,'tool_name':'find_node_types','arguments':{'graph':{'refPath':R+':EventGraph'},'type_id_filter':'ShowTutorial','context_pins':[]}})
found=json.loads(r['content'][0]['text'])['returnValue'];print(found)
print(call('write_graph_dsl',{'graph':{'refPath':R+':EventGraph'},'code':'''(event Collision|EventActorBeginOverlap (OtherActor)
  (bind player (Utilities|Casting|CastToBP_Physis :Object OtherActor)
    (:then
      (bind hud (Utilities|Casting|CastToBP_PhysisHUD :Object (HUD|GetHUD (Game|GetPlayerController 0)))
        (:then
          (%s :self hud :Message (Variables|Default|GetMessage)))
        (:CastFailed)))
    (:CastFailed)))''' % found[0]}))
print(call('compile_blueprint',{'blueprint':{'refPath':R}}))
