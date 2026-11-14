import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=120);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
B='/Game/Characters/Physis/Blueprints/'
P=B+'BP_Physis.BP_Physis';S=B+'BP_ScanTarget.BP_ScanTarget';H=B+'BP_PhysisHUD.BP_PhysisHUD';D=B+'BP_TrainingDrone.BP_TrainingDrone'
def call(t,a,quiet=False):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    x=r['content'][0]['text']
    if r.get('isError') and not quiet:print('ERR',t,x[:600])
    return None if r.get('isError') else x
def var(bp,name,kind,edit=False):
    call('add_variable',{'blueprint':{'refPath':bp},'name':name,'type_name':kind},True)
    if edit:call('set_variable_instance_editable',{'blueprint':{'refPath':bp},'variable_name':name,'instance_editable':True})
def shell(bp,name,params=()):
    if call('add_function_graph',{'blueprint':{'refPath':bp},'graph_name':name},True) is None:return
    for pn,pt in params:call('add_function_param',{'graph':{'refPath':bp+':'+name},'param_name':pn,'param_type':pt,'input_param':True})
def fn(bp,name,code):
    print(name,'ok' if call('write_graph_dsl',{'graph':{'refPath':bp+':'+name},'code':code}) else 'FAILED')
def comp(bp):call('compile_blueprint',{'blueprint':{'refPath':bp}})
fn(H,'DrawVisor','''(fn DrawVisor (SizeX SizeY)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (HUD|GetOwningPawn))
    (:then
      (if (> (Class|BPPhysis|GetVisorBlend :self physis) 0.01)
        (HUD|DrawRect :RectColor "(R=0.0,G=0.45,B=0.4,A=0.07)" :ScreenX 0.0 :ScreenY 0.0 :ScreenW SizeX :ScreenH SizeY)
        (CallFunction|DrawMarker :X (/ SizeX 2.0) :Y (/ SizeY 2.0) :Size 7.0 :Red 0.3 :Green 1.0 :Blue 0.8)
        (Variables|Default|SetLogbookSeen 0)
        (Variables|Default|SetLogbookDone 0)
        (bind clock (Utilities|Time|GetGameTimeinSeconds))
        (for found (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_ScanTarget.BP_ScanTarget_C")
          (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
            (:then
              (bind done (Class|BPScanTarget|GetScanDone :self item))
              (bind important (Class|BPScanTarget|GetScanImportant :self item))
              (bind aimed (Class|BPScanTarget|GetScanAimed :self item))
              (Variables|Default|SetLogbookSeen (+ (Variables|Default|GetLogbookSeen) 1))
              (if done (Variables|Default|SetLogbookDone (+ (Variables|Default|GetLogbookDone) 1)))
              (if (Class|BPScanTarget|GetScanInView :self item)
                (bind at (HUD|Project :Location (Transformation|GetActorLocation :self item) :bClampToZeroPlane false))
                (bind pulse (+ 22.0 (* 4.0 (Math|Trig|Sin(Radians) (* clock 5.0)))))
                (bind size (select aimed 38.0 (select important pulse 18.0)))
                (CallFunction|DrawMarker :X (.x at) :Y (.y at) :Size size
                  :Red (select done 0.55 (select important 1.0 0.2))
                  :Green (select done 0.58 (select important 0.85 1.0))
                  :Blue (select done 0.6 (select important 0.1 0.45)))
                (if (and aimed (not done))
                  (HUD|DrawRect :RectColor "(R=0.0,G=0.1,B=0.1,A=0.8)" :ScreenX (- (.x at) 60.0) :ScreenY (+ (.y at) 50.0) :ScreenW 120.0 :ScreenH 8.0)
                  (HUD|DrawRect :RectColor "(R=0.2,G=1.0,B=0.5,A=1.0)" :ScreenX (- (.x at) 60.0) :ScreenY (+ (.y at) 50.0) :ScreenW (* 120.0 (Class|BPScanTarget|GetScanProgress :self item)) :ScreenH 8.0))))
            (:CastFailed)))
        (HUD|DrawText :Text "SCANS" :TextColor "(R=0.3,G=1.0,B=0.8,A=1.0)" :ScreenX (- SizeX 240.0) :ScreenY 40.0 :Scale 1.4)
        (HUD|DrawText :Text (Utilities|String|ToString(Integer) (Variables|Default|GetLogbookDone)) :TextColor "(R=0.3,G=1.0,B=0.8,A=1.0)" :ScreenX (- SizeX 150.0) :ScreenY 40.0 :Scale 1.4)
        (HUD|DrawText :Text "/" :TextColor "(R=0.3,G=1.0,B=0.8,A=1.0)" :ScreenX (- SizeX 115.0) :ScreenY 40.0 :Scale 1.4)
        (HUD|DrawText :Text (Utilities|String|ToString(Integer) (Variables|Default|GetLogbookSeen)) :TextColor "(R=0.3,G=1.0,B=0.8,A=1.0)" :ScreenX (- SizeX 95.0) :ScreenY 40.0 :Scale 1.4)
        (if (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetScanResultHideAt))
          (bind text (Variables|Default|GetScanResult))
          (bind (width high) (HUD|GetTextSize :Text text :Scale 1.3))
          (bind panelX (/ (- SizeX width) 2.0))
          (bind panelY (* SizeY 0.68))
          (HUD|DrawRect :RectColor "(R=0.0,G=0.08,B=0.08,A=0.82)" :ScreenX (- panelX 24.0) :ScreenY (- panelY 14.0) :ScreenW (+ width 48.0) :ScreenH 58.0)
          (HUD|DrawText :Text text :TextColor "(R=0.6,G=1.0,B=0.85,A=1.0)" :ScreenX panelX :ScreenY panelY :Scale 1.3))))
    (:CastFailed)))''')
print('hud draw',call('write_graph_dsl',{'graph':{'refPath':H+':EventGraph'},'code':'''(event EventReceiveDrawHUD (SizeX SizeY)
  (CallFunction|DrawVisor :SizeX SizeX :SizeY SizeY)
  (bind _tutorialtext (Variables|Default|GetTutorialText))
  (bind (_outwidth high) (HUD|GetTextSize :Text _tutorialtext :Scale 1.6))
  (bind _returnvalue_3 (/ (- SizeX _outwidth) 2.0))
  (bind _returnvalue_4 (- SizeY 170.0))
  (if (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetTutorialHideAt))
    (HUD|DrawRect :RectColor "(R=0.0,G=0.02,B=0.05,A=0.72)" :ScreenX (- _returnvalue_3 24.0) :ScreenY (- _returnvalue_4 14.0) :ScreenW (+ _outwidth 48.0) :ScreenH 58.0)
    (HUD|DrawText :Text _tutorialtext :TextColor "(R=1.0,G=0.85,B=0.55,A=1.0)" :ScreenX _returnvalue_3 :ScreenY _returnvalue_4 :Scale 1.6)))'''}))
comp(H)
print('tick',call('write_graph_dsl',{'graph':{'refPath':P+':EventGraph'},'code':'''(event EventTick (DeltaSeconds)
  (CallFunction|PhysisVisorTick :DeltaSeconds DeltaSeconds))'''}))
comp(P)
for g in (H+':DrawVisor',H+':EventGraph'):
    print(call('read_graph_dsl',{'graph':{'refPath':g}}).replace('\\n','\n').replace('\\"','"')[:900])
