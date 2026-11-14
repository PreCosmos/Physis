import sys
sys.path.insert(0,'Tools')
cb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
exec(cb.split("call('add_object_variable'")[0])
TARGETS='(Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_ScanTarget.BP_ScanTarget_C")'
fn(P,'PhysisVisorToggle',"""(fn PhysisVisorToggle ()
  (if (not (Variables|Default|GetCinematic))
    (Variables|Default|SetScanVisorOn (not (Variables|Default|GetScanVisorOn)))
    (Variables|Default|SetScanHeld false)
    (Variables|Default|SetLockHeld false)
    (CallFunction|PhysisVoiceStop)
    (CallFunction|PhysisLockClear)
    (for found %s
      (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
        (:then (Class|BPScanTarget|VisorClear :self item))
        (:CastFailed)))))"""%TARGETS)
fn(P,'PhysisScan',"""(fn PhysisScan ()
  (if (not (Variables|Default|GetCinematic))
    (if (Variables|Default|GetScanVisorOn)
      (bind screen (Utilities|Casting|CastToBP_PhysisHUD :Object (HUD|GetHUD (Game|GetPlayerController 0)))
        (:then
          (if (> (Class|BPPhysisHUD|GetScanResultHideAt :self screen) (Utilities|Time|GetGameTimeinSeconds))
            (Class|BPPhysisHUD|SetScanResultHideAt :self screen :ScanResultHideAt 0.0)
            (CallFunction|PhysisVoiceStop)
            (else
              (Variables|Default|SetScanHeld true))))
        (:CastFailed))
      (else
        (Variables|Default|SetLockHeld true)
        (CallFunction|PhysisLockFind)))))""")
comp(P)
