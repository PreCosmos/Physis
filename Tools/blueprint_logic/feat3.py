import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=90);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
P='/Game/Characters/Physis/Blueprints/BP_Physis.BP_Physis'
def call(t,a):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    txt=r['content'][0]['text']
    if r.get('isError'):print('ERR',t,txt[:420]);return None
    return txt
call('add_variable',{'blueprint':{'refPath':P},'name':'ActionFound','type_name':'bool'})
D='/Game/Characters/Physis/Blueprints/BP_StationDoor.BP_StationDoor'
call('add_variable',{'blueprint':{'refPath':D},'name':'DoorLocked','type_name':'bool'})
call('compile_blueprint',{'blueprint':{'refPath':D}})
call('compile_blueprint',{'blueprint':{'refPath':P}})
print(call('write_graph_dsl',{'graph':{'refPath':P+':PhysisScan'},'code':'''(fn PhysisScan ()
  (Variables|Default|SetActionFound false)
  (bind camera (Variables|Default|GetFollowCamera))
  (bind eye (Transformation|GetWorldLocation :self camera))
  (bind look (Transformation|GetForwardVector :self camera))
  (for found (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_ScanTarget.BP_ScanTarget_C")
    (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
      (:then
        (bind there (- (Transformation|GetActorLocation :self item) eye))
        (if (and (< (Math|Vector|VectorLength there) 1500.0) (> (Math|Vector|DotProduct look (Math|Vector|Normalize there)) 0.85))
          (Variables|Default|SetActionFound true)
          (CallFunction|PhysisSay :Message (Class|BPScanTarget|GetScanText :self item))))
      (:CastFailed)))
  (if (not (Variables|Default|GetActionFound))
    (CallFunction|PhysisSay :Message "Scan: nothing unusual here")))'''}))
print(call('write_graph_dsl',{'graph':{'refPath':P+':PhysisInteract'},'code':'''(fn PhysisInteract ()
  (Variables|Default|SetActionFound false)
  (for found (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_StationDoor.BP_StationDoor_C")
    (bind door (Utilities|Casting|CastToBP_StationDoor :Object found)
      (:then
        (if (< (Transformation|GetDistanceTo :OtherActor door) 330.0)
          (Variables|Default|SetActionFound true)
          (if (Class|BPStationDoor|GetDoorLocked :self door)
            (CallFunction|PhysisSay :Message (Class|BPStationDoor|GetLockedText :self door))
            (else
              (Class|BPStationDoor|OpenDoor :self door)
              (CallFunction|PhysisSay :Message "Door opened")))))
      (:CastFailed)))
  (if (not (Variables|Default|GetActionFound))
    (CallFunction|PhysisSay :Message "Nothing to interact with here")))'''}))
print(call('compile_blueprint',{'blueprint':{'refPath':P}}))
print(call('read_graph_dsl',{'graph':{'refPath':P+':PhysisInteract'}}))
