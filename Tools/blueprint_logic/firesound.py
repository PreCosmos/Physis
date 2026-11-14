# Runs last in the logic rebuild: rewrites both fire graphs with the shot sound.
import sys
sys.path.insert(0,'Tools')
cb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
exec(cb.split("call('add_object_variable'")[0])
def cut(a):
    i=cb.index(a); j=cb.index('"""',cb.index('(fn ',i)+4)
    k=cb.index('\n',j); return cb[i:k]
var(P,'ChargeStart','float');var(P,'Charging','bool')
call('add_object_variable',{'blueprint':{'refPath':P},'name':'ChargeOrb','object_class':{'refPath':'/Script/Engine.Actor'}},True)
NEWREADY='(and (not (Variables|Default|GetScanVisorOn)) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetFireReady)))'
FIRE='(Variables|Default|SetFireReady (+ (Utilities|Time|GetGameTimeinSeconds) 0.28))'
SOUND='(Audio|PlaySound2D :Sound "/Game/Audio/S_Laser2.S_Laser2" :VolumeMultiplier 0.9 :PitchMultiplier (Math|Random|RandomFloatinRange :Min 1.25 :Max 1.45))\n      '
for name in ("fn(P,'PhysisFire',","fn(P,'PhysisFireDivine',"):
    src=cut(name)
    print(name, src.count('(CallFunction|PhysisShot :Damage'), src.count('%(ANIM,READY,ALIVE,'))
    src=src.replace('%(ANIM,READY,ALIVE,','%(ANIM,NEWREADY,ALIVE,').replace('(CallFunction|PhysisShot :Damage',SOUND+'(CallFunction|PhysisShot :Damage')
    if name=="fn(P,'PhysisFire',":
        # Holding fire starts a charge; PhysisChargeReady chimes at full charge, PhysisFireRelease fires it.
        src=src.replace('(CallFunction|PhysisShot :Damage 1)','(Variables|Default|SetChargeStart (Utilities|Time|GetGameTimeinSeconds))\n      (Variables|Default|SetCharging true)\n      (Variables|Default|SetChargeOrb (Game|SpawnActorfromClass :Class "/Game/Characters/Physis/Blueprints/BP_ChargeOrb.BP_ChargeOrb_C" :SpawnTransform (Math|Transform|MakeTransform :Location (+ (Transformation|GetWorldLocation :self (Variables|Default|GetGun)) (+ (* (Transformation|GetActorForwardVector) 30.0) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 3.0))))))\n      (Transformation|AttachActorToComponent :self (Variables|Default|GetChargeOrb) :Parent (Variables|Default|GetGun) :SocketName "None" :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "KeepWorld" :bWeldSimulatedBodies false)\\n      (Transformation|SetActorRelativeLocation :self (Variables|Default|GetChargeOrb) :NewRelativeLocation (Math|Vector|MakeVector :X 21.0 :Y 0.0 :Z 4.0) :bSweep false :bTeleport true)\n            (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisChargeReady" :Time 0.9 :bLooping false)\n      (CallFunction|PhysisShot :Damage 1)')
        assert 'PhysisChargeReady' in src
    exec(src)
comp(P)
for f in ('PhysisFire','PhysisFireDivine'):
    print(f,'S_Laser2' in (call('read_graph_dsl',{'graph':{'refPath':P+':'+f}}) or ''))
