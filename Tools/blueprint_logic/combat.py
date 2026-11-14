import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=600);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
B='/Game/Characters/Physis/Blueprints/'
P=B+'BP_Physis.BP_Physis';S=B+'BP_ScanTarget.BP_ScanTarget';H=B+'BP_PhysisHUD.BP_PhysisHUD';D=B+'BP_TrainingDrone.BP_TrainingDrone'
# Graphs Tools/blueprint_logic/center_overrides.py writes whole (its header lists them; agreed with the Center session,
# 2026-11-08/09). The station scripts still name them, but call() skips those writes, so a station script run on its
# own can never put an older version back (rebuild2.sh's center_music.py runs every center_overrides part anyway).
# Change these graphs in center_overrides.py. DrawInteract and PhysisInteract are the Conclave's (conclave_hud.py,
# part conclave): feat.py and scenario_bp.py used to undo them, and the Conclave's people stopped talking.
CENTER_OWNED={
    'BP_Physis':{'PhysisMusic','PhysisMusicPick','PhysisMusicStop','PhysisCinemaStart','PhysisCenterStart','PhysisCenterPrepare',
                 'PhysisRestart','PhysisScanShow','PhysisSaveGame','PhysisRestore','PhysisClearRoom','PhysisFinish','PhysisLoadGame',
                 'PhysisFidelity','PhysisAddLog','PhysisScanKnown','PhysisScanCount','PhysisVisorToggle','PhysisStrikeNow',
                 'PhysisShotHit','PhysisHurt','PhysisBlock','PhysisThreatCheck','PhysisMenu','PhysisInteract'},
    'BP_Checkpoint':{'EventGraph'},'BP_Encounter':{'EventGraph','FightLine'},'BP_ScanTarget':{'VisorMeasure','VisorApply','TagSetup'},
    'BP_Pickup':{'PickupSetup','EventGraph'},'BP_PhysisHUD':{'DrawVisor','DrawPauseMenu','PageMap','MapMark','DrawInteract'},
    'BP_TrainingDrone':{'DroneThink','DroneStuckCheck','DroneHover','DroneArena','DroneSeparate','DroneSeparateAll',
                        'DroneSeparateCenter','TakeHit','DroneArmour','DroneDrop','DroneDropOne'},
    'BP_Switch':{'UseSwitch'},'BP_MenuHUD':{'DrawMenu','MenuContinue'}}
def center_owned(ref):
    bp,_,graph=ref.rpartition(':')
    return graph in CENTER_OWNED.get(bp.rsplit('.',1)[-1],())
def call(t,a,quiet=False):
    if t=='write_graph_dsl' and center_owned(a['graph']['refPath']):
        print('skipped',a['graph']['refPath'].rsplit('/',1)[-1],'(center_overrides.py owns it)',flush=True)
        return 'skipped'
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    x=r['content'][0]['text']
    if r.get('isError') and not quiet:print('ERR',t,x[:600])
    if t=='write_graph_dsl' and not r.get('isError'):prune(a['graph']['refPath'])
    return None if r.get('isError') else x
def prune(ref):
    # After every graph write (author approved, 2026-11-07): write_graph_dsl leaves the previous version's nodes behind,
    # still linked to the entry's parameter pins, so every rewrite added a dead copy (89% of all nodes by then).
    # center:prune (Content/Python/physis_graph_prune.py) removes the dead ones and checks the live DSL is unchanged.
    # same False or an error stops the script: then do not save, and reload the Blueprint from disk.
    r=c.call('call_tool',{'toolset_name':'physis_character_tools.PhysisCharacterTools','tool_name':'outfit_operation','arguments':{'operation':'center:prune:'+ref}})
    x=r['content'][0]['text']
    row=None if r.get('isError') else json.loads(json.loads(x)['returnValue'])
    if not row or not row.get('same'):raise RuntimeError('PRUNE FAILED, do not save: %s %s'%(ref,row or x[:300]))
    if row.get('removed'):print('pruned',row['removed'],'dead nodes in',row['graph'],flush=True)
def var(bp,name,kind,edit=False):
    # Only when missing (Center session, 2026-11-07): add_variable on a name in use adds a numbered copy (Need_0,
    # Need_1, ...), and set_variable_instance_editable marks the Blueprint changed on every call.
    have=call('list_variables',{'blueprint':{'refPath':bp}},True)
    if have and name in (json.loads(have).get('returnValue') or []):return
    call('add_variable',{'blueprint':{'refPath':bp},'name':name,'type_name':kind},True)
    if edit:call('set_variable_instance_editable',{'blueprint':{'refPath':bp},'variable_name':name,'instance_editable':True})
def shell(bp,name,params=()):
    if call('add_function_graph',{'blueprint':{'refPath':bp},'graph_name':name},True) is None:return
    for pn,pt in params:call('add_function_param',{'graph':{'refPath':bp+':'+name},'param_name':pn,'param_type':pt,'input_param':True})
def fn(bp,name,code):
    if center_owned(bp+':'+name):
        print(name,'skipped (center_overrides.py owns it)',flush=True);return
    print(name,'ok' if call('write_graph_dsl',{'graph':{'refPath':bp+':'+name},'code':code}) else 'FAILED')
def comp(bp):call('compile_blueprint',{'blueprint':{'refPath':bp}})
ANIM='(bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))'
def play(n,rate=1.4):
    return '(Animation|Montage|MontagePlay :self anim :MontageToPlay "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_%s.AM_Physis_%s" :InPlayRate %s)'%(n,n,rate)
def chain(names,damage):
    return ' '.join('(:%d (CallFunction|PhysisSwung :Length %s :Damage %d))'%(i,play(n),damage) for i,n in enumerate(names))
LIGHT=('Slash','Slash2','Slash3','Slash4','Slash5','Slash6','Slash7','Slash8','Slash9')
HEAVY=('Stab','Kick1','Combo1','Kick2','Combo2','Combo3','Stab','Combo5','Combo4')
FREE='(or (not (Animation|Montage|IsAnyMontagePlaying :self anim)) (and (> (Variables|Default|GetChainOpenAt) 0.0) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetChainOpenAt))))'
READY='(and (not (Variables|Default|GetScanVisorOn)) '+FREE+')'
ALIVE='(and (not (Variables|Default|GetPhysisDead)) (not (Variables|Default|GetCinematic)))'
DRONES='(Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_TrainingDrone.BP_TrainingDrone_C")'
TARGETS='(Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_ScanTarget.BP_ScanTarget_C")'
def attack(name,names,air,damage):
    return """(fn %s ()
  %s
  (if (Variables|Default|GetGunEquipped)
    (CallFunction|%s)
    (else
      (if (and %s %s)
        (if (Movement|IsFalling :self (Variables|Character|GetCharacterMovement))
          (CallFunction|PhysisSwung :Length %s :Damage %d)
          (else
            (CallFunction|PhysisChainCheck)
            (switch int (Variables|Default|GetChainStep) %s (:Default))))))))"""%(name,ANIM,'PhysisFire' if damage==1 else 'PhysisFireDivine',READY,ALIVE,play(air),damage,chain(names,damage))
call('add_object_variable',{'blueprint':{'refPath':P},'name':'LockTarget','object_class':{'refPath':'/Script/Engine.Actor'}},True)
var(P,'ChainStep','int');var(P,'PendingDamage','int')
for n in('LockHeld','PhysisDead'):var(P,n,'bool')
for n in('ChainOpenAt','ChainUntil','BlockUntil','SafeUntil','LockBest','PhysisHealth'):var(P,n,'float')
var(D,'Cooldown','float')
var(P,'GunEquipped','bool')
var(P,'Cinematic','bool');var(P,'CinemaStartedAt','float')
for n in ('PhysisCinemaStart','PhysisCinemaEnd','PhysisCinemaCleanup'):shell(P,n)
for n in('GunAmmo','GunReserve','ReloadTake'):var(P,n,'int')
for n in('Divinity','AimBlend','ShotBest'):var(P,n,'float')
call('add_object_variable',{'blueprint':{'refPath':P},'name':'ShotTarget','object_class':{'refPath':'/Script/Engine.Actor'}},True)
for n,ps in (('PhysisFire',()),('PhysisFireDivine',()),('PhysisShot',[('Damage','int')]),('PhysisSwitchWeapon',()),('PhysisReload',()),('PhysisCollect',[('Kind','int')])):
    shell(P,n,ps)
for n,ps in (('PhysisChainCheck',()),('PhysisSwung',[('Length','float'),('Damage','int')]),('PhysisStrikeNow',()),('PhysisAttackHeavy',()),('PhysisBlock',()),
             ('PhysisHurt',[('FromAhead','bool')]),('PhysisRestart',()),('PhysisLockFind',()),('PhysisLockClear',()),('PhysisLockTick',[('DeltaSeconds','float')])):
    shell(P,n,ps)
call('add_function_param',{'graph':{'refPath':D+':TakeHit'},'param_name':'Amount','param_type':'int','input_param':True},True)
fn(D,'TakeHit',"""(fn TakeHit (Amount)
  (Variables|Default|SetHealth (- (Variables|Default|GetHealth) Amount))
  (if (<= (Variables|Default|GetHealth) 0)
    (for tag (Actor|GetAttachedActors)
      (Actor|DestroyActor :self tag))
    (Actor|DestroyActor)))""")
comp(D)
PICK=B+'BP_Pickup.BP_Pickup'
var(PICK,'Kind','int',True)
shell(PICK,'PickupSetup',[('Value','int')])
fn(PICK,'PickupSetup',"""(fn PickupSetup (Value)
  (Variables|Default|SetKind Value)
  (switch int Value
    (:0 (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh "/Game/Gameplay/SM_Pickup_Health.SM_Pickup_Health"))
    (:1 (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh "/Game/Gameplay/SM_Pickup_Divinity.SM_Pickup_Divinity"))
    (:Default (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh "/Game/Gameplay/SM_Pickup_Ammo.SM_Pickup_Ammo"))))""")
comp(PICK)

fn(P,'PhysisChainCheck',"""(fn PhysisChainCheck ()
  (if (> (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetChainUntil))
    (Variables|Default|SetChainStep 0)))""")
fn(P,'PhysisSwung',"""(fn PhysisSwung (Length Damage)
  (Variables|Default|SetChainUntil (+ (+ (Utilities|Time|GetGameTimeinSeconds) (* Length 0.71)) 1.2))
  (bind following (+ (Variables|Default|GetChainStep) 1))
  (Variables|Default|SetChainStep (select (>= following 9) 0 following))
  (Variables|Default|SetPendingDamage Damage)
  (Variables|Default|SetChainOpenAt (+ (Utilities|Time|GetGameTimeinSeconds) (* Length 0.5)))
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisStrikeNow" :Time (* Length 0.29) :bLooping false)
  (Utilities|IsValid (Variables|Default|GetLockTarget)
    (:"Is Valid" (Character|LaunchCharacter :LaunchVelocity (* (Transformation|GetActorForwardVector) 1200.0) :bXYOverride true))
    (:"Is Not Valid")))""")
fn(P,'PhysisStrikeNow',"""(fn PhysisStrikeNow ()
  (bind amount (Variables|Default|GetPendingDamage))
  (for found %s
    (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found)
      (:then
        (if (and (< (Transformation|GetDistanceTo :OtherActor drone) 300.0) (> (Transformation|GetDotProductTo :OtherActor drone) 0.2))
          (Class|BPTrainingDrone|TakeHit :self drone :Amount amount)))
      (:CastFailed))))"""%DRONES)
fn(P,'PhysisAttack',attack('PhysisAttack',LIGHT,'JumpAttack1',1))
fn(P,'PhysisAttackHeavy',attack('PhysisAttackHeavy',HEAVY,'JumpAttack2',2))
fn(P,'PhysisDodge',"""(fn PhysisDodge ()
  %s
  (if (and %s %s)
    (Variables|Default|SetChainOpenAt 0.0)
    (Variables|Default|SetSafeUntil (+ (Utilities|Time|GetGameTimeinSeconds) 0.6))
    (bind wanted (Pawn|Input|GetLastMovementInputVector))
    (if (> (Math|Vector|VectorLength wanted) 0.1)
      %s
      (Character|LaunchCharacter :LaunchVelocity (* (Math|Vector|Normalize wanted) 3000.0) :bXYOverride true)
      (else
        %s
        (Character|LaunchCharacter :LaunchVelocity (* (Transformation|GetActorForwardVector) -2200.0) :bXYOverride true)))))"""%(ANIM,ALIVE,FREE,play('Dodge',1.0),play('Evade',1.0)))
fn(P,'PhysisBlock',"""(fn PhysisBlock ()
  %s
  (if (and %s %s)
    (Variables|Default|SetChainOpenAt 0.0)
    %s
    (Variables|Default|SetBlockUntil (+ (Utilities|Time|GetGameTimeinSeconds) 1.1))))"""%(ANIM,READY,ALIVE,play('Block',1.2)))
fn(P,'PhysisHurt',"""(fn PhysisHurt (FromAhead)
  %s
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (if (and %s (> now (Variables|Default|GetSafeUntil)))
    (Variables|Default|SetChainOpenAt 0.0)
    (if (and FromAhead (< now (Variables|Default|GetBlockUntil)))
      %s
      (Variables|Default|SetSafeUntil (+ now 0.8))
      (else
        (Variables|Default|SetPhysisHealth (- (Variables|Default|GetPhysisHealth) 1.0))
        (Variables|Default|SetSafeUntil (+ now 1.0))
        (if (<= (Variables|Default|GetPhysisHealth) 0.0)
          (Variables|Default|SetPhysisDead true)
          %s
          (Input|DisableInput :PlayerController (Game|GetPlayerController 0))
          (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisRestart" :Time 1.8 :bLooping false)
          (elif FromAhead
            (switch int (Math|Random|RandomIntegerinRange :Min 0 :Max 3)
              (:0 %s) (:1 %s) (:2 %s) (:3 %s) (:Default))
            (else %s)))))))"""%(ANIM,ALIVE,play('Impact'),play('Dead',1.0),play('Hit_Front_Small'),play('Hit_Front_Small1'),play('Hit_Front_Big1'),play('Hit_Front_Big2'),play('Hit_Back_Small')))
fn(P,'PhysisRestart',"""(fn PhysisRestart ()
  (Game|OpenLevel(byName) :LevelName "L_BattleStation" :Options "nocine"))""")
fn(P,'PhysisScan',"""(fn PhysisScan ()
  (if (not (Variables|Default|GetCinematic))
    (if (Variables|Default|GetScanVisorOn)
      (Variables|Default|SetScanHeld true)
      (else
        (Variables|Default|SetLockHeld true)
        (CallFunction|PhysisLockFind)))))""")
fn(P,'PhysisLockClear',"""(fn PhysisLockClear ()
  (Variables|Default|SetLockTarget)
  (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self (Variables|Character|GetCharacterMovement) :bOrientRotationToMovement true))""")
fn(P,'PhysisScanRelease',"""(fn PhysisScanRelease ()
  (Variables|Default|SetScanHeld false)
  (Variables|Default|SetLockHeld false)
  (CallFunction|PhysisLockClear))""")
fn(P,'PhysisLockFind',"""(fn PhysisLockFind ()
  (bind camera (Variables|Default|GetFollowCamera))
  (bind eye (Transformation|GetWorldLocation :self camera))
  (bind look (Transformation|GetForwardVector :self camera))
  (Variables|Default|SetLockBest 1800.0)
  (for found %s
    (bind there (- (Transformation|GetActorLocation :self found) eye))
    (bind reach (Transformation|GetDistanceTo :OtherActor found))
    (if (and (< reach (Variables|Default|GetLockBest)) (> (Math|Vector|DotProduct look (Math|Vector|Normalize there)) 0.3))
      (if (Controller|LineOfSightTo :self (Game|GetPlayerController 0) :Other found)
        (Variables|Default|SetLockBest reach)
        (Variables|Default|SetLockTarget found)
        (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self (Variables|Character|GetCharacterMovement) :bOrientRotationToMovement false)))))"""%DRONES)
fn(P,'PhysisLockTick',"""(fn PhysisLockTick (DeltaSeconds)
  (bind target (Variables|Default|GetLockTarget))
  (Utilities|IsValid target
    (:"Is Valid"
      (if (> (Transformation|GetDistanceTo :OtherActor target) 2000.0)
        (CallFunction|PhysisLockClear)
        (else
          (bind spot (Transformation|GetActorLocation :self target))
          (bind face (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation) :Target spot))
          (Transformation|SetActorRotation :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw face)) :bTeleportPhysics false)
          (bind player (Game|GetPlayerController 0))
          (bind aim (Math|Rotator|FindLookatRotation :Start (Transformation|GetWorldLocation :self (Variables|Default|GetFollowCamera)) :Target spot))
          (Pawn|SetControlRotation :self player :NewRotation (Math|Interpolation|RInterpTo :Current (Pawn|GetControlRotation :self player) :Target aim :DeltaTime DeltaSeconds :InterpSpeed 8.0)))))
    (:"Is Not Valid"
      (if (Variables|Default|GetLockHeld)
        (CallFunction|PhysisLockFind)))))""")
fn(P,'PhysisVisorToggle',"""(fn PhysisVisorToggle ()
  (if (not (Variables|Default|GetCinematic))
    (Variables|Default|SetScanVisorOn (not (Variables|Default|GetScanVisorOn)))
    (Variables|Default|SetScanHeld false)
    (Variables|Default|SetLockHeld false)
    (CallFunction|PhysisLockClear)
    (for found %s
      (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
        (:then (Class|BPScanTarget|VisorClear :self item))
        (:CastFailed)))))"""%TARGETS)
fn(P,'PhysisVisorTick',"""(fn PhysisVisorTick (DeltaSeconds)
  (bind on (Variables|Default|GetScanVisorOn))
  (bind camera (Variables|Default|GetFollowCamera))
  (bind blend (Math|Interpolation|FInterptoConstant :Current (Variables|Default|GetVisorBlend) :Target (select on 1.0 0.0) :DeltaTime DeltaSeconds :InterpSpeed 6.0))
  (Variables|Default|SetVisorBlend blend)
  (bind shift (Math|Interpolation|FInterptoConstant :Current (Variables|Default|GetAimBlend) :Target (select (or on (Variables|Default|GetGunEquipped)) 1.0 0.0) :DeltaTime DeltaSeconds :InterpSpeed 6.0))
  (Variables|Default|SetAimBlend shift)
  (Camera|SetPostProcessBlendWeight :self camera :InPostProcessBlendWeight blend)
  (Class|SpringArmComponent|SetSocketOffset :self (Variables|Default|GetCameraBoom) :SocketOffset (Math|Vector|MakeVector :X 0.0 :Y (* shift 90.0) :Z 0.0))
  (if on
    (bind eye (Transformation|GetWorldLocation :self camera))
    (bind look (Transformation|GetForwardVector :self camera))
    (Variables|Default|SetVisorBest -1.0)
    (for found %s
      (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
        (:then
          (Class|BPScanTarget|VisorMeasure :self item :Eye eye :Look look)
          (bind aimdot (Class|BPScanTarget|GetScanAimDot :self item))
          (if (> aimdot (Variables|Default|GetVisorBest))
            (Variables|Default|SetVisorBest aimdot)))
        (:CastFailed)))
    (bind best (Variables|Default|GetVisorBest))
    (bind held (Variables|Default|GetScanHeld))
    (for again %s
      (bind item2 (Utilities|Casting|CastToBP_ScanTarget :Object again)
        (:then (Class|BPScanTarget|VisorApply :self item2 :Best best :Held held :Seconds DeltaSeconds))
        (:CastFailed)))))"""%(TARGETS,TARGETS))
comp(P)
print('tick',call('write_graph_dsl',{'graph':{'refPath':P+':EventGraph'},'code':"""(event EventTick (DeltaSeconds)
  (CallFunction|PhysisVisorTick :DeltaSeconds DeltaSeconds)
  (CallFunction|PhysisLockTick :DeltaSeconds DeltaSeconds))"""}))
comp(P)
shell(D,'DroneThink',[('DeltaSeconds','float')])
fn(D,'DroneThink',"""(fn DroneThink (DeltaSeconds)
  (Variables|Default|SetCooldown (- (Variables|Default|GetCooldown) DeltaSeconds))
  (if (<= (Variables|Default|GetCooldown) 0.0)
    (Variables|Default|SetCooldown 3.0)
    (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
      (:then
        (if (< (Transformation|GetDistanceTo :OtherActor physis) 230.0)
          (Class|BPPhysis|PhysisHurt :self physis :FromAhead (> (Transformation|GetDotProductTo :self physis :OtherActor self) 0.0))))
      (:CastFailed))))""")
print('dronetick',call('write_graph_dsl',{'graph':{'refPath':D+':EventGraph'},'code':"""(event EventTick (DeltaSeconds)
  (CallFunction|DroneThink :DeltaSeconds DeltaSeconds))"""}))
comp(D)

fn(P,'PhysisEquip',"""(fn PhysisEquip ()
  (Transformation|AttachComponentToComponent (Variables|Default|GetKatana) (Variables|Default|GetBody) "hand_r" "KeepRelative" "KeepRelative" "KeepRelative" false)
  (Transformation|AttachComponentToComponent (Variables|Default|GetGun) (Variables|Default|GetBody) "hand_r" "KeepRelative" "KeepRelative" "KeepRelative" false)
  (CallFunction|PhysisCinemaStart))""")
fn(P,'PhysisInteract',"""(fn PhysisInteract ()
  (if (Variables|Default|GetCinematic)
    (CallFunction|PhysisCinemaEnd)
    (else
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
        (CallFunction|PhysisSay :Message "Nothing to interact with here")))))""")
SHIPS='"/Game/Characters/Physis/Blueprints/BP_FleetShip.BP_FleetShip_C"'
fn(P,'PhysisCinemaCleanup',"""(fn PhysisCinemaCleanup ()
  (for ship (Actor|GetAllActorsOfClass :ActorClass %s)
    (Actor|DestroyActor :self ship))
  (for boss (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_BattleDirector.BP_BattleDirector_C")
    (Actor|DestroyActor :self boss)))"""%SHIPS)
fn(P,'PhysisCinemaStart',"""(fn PhysisCinemaStart ()
  (if (Utilities|String|Contains :SearchIn (Class|GameModeBase|GetOptionsString :self (Game|GetGameMode)) :Substring "nocine")
    (CallFunction|PhysisCinemaCleanup)
    (else
      (bind player (Game|GetPlayerController 0))
      (Variables|Default|SetCinematic true)
      (Variables|Default|SetCinemaStartedAt (Utilities|Time|GetGameTimeinSeconds))
      (Input|SetIgnoreMoveInput :self player :bNewMoveInput true)
      (Input|SetIgnoreLookInput :self player :bNewLookInput true)
      (Sequencer|Player|Play :self (Class|LevelSequenceActor|GetSequencePlayer :self (Actor|GetActorOfClass :ActorClass "/Script/LevelSequence.LevelSequenceActor")))
      (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisCinemaEnd" :Time 40.0 :bLooping false))))""")
fn(P,'PhysisCinemaEnd',"""(fn PhysisCinemaEnd ()
  (if (Variables|Default|GetCinematic)
    (bind player (Game|GetPlayerController 0))
    (Variables|Default|SetCinematic false)
    (Sequencer|Player|Stop :self (Class|LevelSequenceActor|GetSequencePlayer :self (Actor|GetActorOfClass :ActorClass "/Script/LevelSequence.LevelSequenceActor")))
    (Input|ResetIgnoreMoveInput :self player)
    (Input|ResetIgnoreLookInput :self player)
    (CallFunction|PhysisCinemaCleanup)
    (CallFunction|PhysisSay :Message "Move: W A S D / |LS|     Look: Mouse / |RS|")))""")
fn(P,'PhysisSwitchWeapon',"""(fn PhysisSwitchWeapon ()
  %s
  (if (and %s %s)
    (Variables|Default|SetChainOpenAt 0.0)
    (Variables|Default|SetGunEquipped (not (Variables|Default|GetGunEquipped)))
    (bind out (Variables|Default|GetGunEquipped))
    (Rendering|SetVisibility :self (Variables|Default|GetKatana) :bNewVisibility (not out))
    (Rendering|SetVisibility :self (Variables|Default|GetGun) :bNewVisibility out)
    (if out
      (Components|SkeletalMesh|SetAnimInstanceClass :self (Variables|Default|GetBody) :NewClass "/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Pistol.Physis_ABP_Pistol_C")
      (bind pistol (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))
      (Animation|Montage|MontagePlay :self pistol :MontageToPlay "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Pistol_Equip.AM_Physis_Pistol_Equip" :InPlayRate 1.6)
      (else
        (Components|SkeletalMesh|SetAnimInstanceClass :self (Variables|Default|GetBody) :NewClass "/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed.Physis_ABP_Unarmed_C")))))"""%(ANIM,READY,ALIVE))
shell(P,'PhysisTracer',[('From','vector'),('To','vector')])
shell(P,'PhysisShotHit',[('Damage','int'),('Muzzle','vector'),('Far','vector')])
fn(P,'PhysisShotHit',"""(fn PhysisShotHit (Damage Muzzle Far)
  (bind target (Variables|Default|GetShotTarget))
  (Utilities|IsValid target
    (:"Is Valid"
      (bind spot (Transformation|GetActorLocation :self target))
      (CallFunction|PhysisTracer :From Muzzle :To spot)
      (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object target)
        (:then (Class|BPTrainingDrone|TakeHit :self drone :Amount Damage))
        (:CastFailed)))
    (:"Is Not Valid" (CallFunction|PhysisTracer :From Muzzle :To Far))))""")
shell(P,'PhysisTracer',[('From','vector'),('To','vector')])
fn(P,'PhysisTracer',"""(fn PhysisTracer (From To)
  (bind span (- To From))
  (bind size (Math|Vector|VectorLength span))
  (Game|SpawnActorfromClass :Class "/Game/Characters/Physis/Blueprints/BP_GunTracer.BP_GunTracer_C"
    :SpawnTransform (Math|Transform|MakeTransform :Location (+ From (* span 0.5)) :Rotation (Math|Rotator|FindLookatRotation :Start From :Target To) :Scale (Math|Vector|MakeVector :X (/ size 100.0) :Y 0.025 :Z 0.025))
    :CollisionHandlingOverride "AlwaysSpawn"))""")
fn(P,'PhysisShot',"""(fn PhysisShot (Damage)
  (bind camera (Variables|Default|GetFollowCamera))
  (bind eye (Transformation|GetWorldLocation :self camera))
  (bind look (Transformation|GetForwardVector :self camera))
  (bind muzzle (Transformation|GetWorldLocation :self (Variables|Default|GetGun)))
  (Variables|Default|SetShotTarget (Variables|Default|GetLockTarget))
  (Variables|Default|SetShotBest 3500.0)
  (bind far (+ eye (* look 3000.0)))
  (Utilities|IsValid (Variables|Default|GetLockTarget)
    (:"Is Valid" (CallFunction|PhysisShotHit :Damage Damage :Muzzle muzzle :Far far))
    (:"Is Not Valid"
      (for found %s
        (bind there (- (Transformation|GetActorLocation :self found) eye))
        (bind reach (Math|Vector|VectorLength there))
        (if (and (< reach (Variables|Default|GetShotBest)) (> (Math|Vector|DotProduct look (Math|Vector|Normalize there)) 0.985))
          (if (Controller|LineOfSightTo :self (Game|GetPlayerController 0) :Other found)
            (Variables|Default|SetShotBest reach)
            (Variables|Default|SetShotTarget found))))
      (CallFunction|PhysisShotHit :Damage Damage :Muzzle muzzle :Far far))))"""%DRONES)
FIRE='(Variables|Default|SetChainOpenAt (+ (Utilities|Time|GetGameTimeinSeconds) 0.3))'
comp(P)
fn(P,'PhysisFire',"""(fn PhysisFire ()
  %s
  (if (and %s %s)
    (if (> (Variables|Default|GetGunAmmo) 0)
      (Variables|Default|SetGunAmmo (- (Variables|Default|GetGunAmmo) 1))
      %s
      %s
      (CallFunction|PhysisShot :Damage 1)
      (else
        %s
        (Variables|Default|SetChainOpenAt 0.0)
        (CallFunction|PhysisSay :Message "Out of ammo.   Reload: R / |DD|")))))"""%(ANIM,READY,ALIVE,play('Pistol_Fire',1.0),FIRE,play('Pistol_DryFire',1.4)))
fn(P,'PhysisFireDivine',"""(fn PhysisFireDivine ()
  %s
  (if (and %s %s)
    (if (>= (Variables|Default|GetDivinity) 25.0)
      (Variables|Default|SetDivinity (- (Variables|Default|GetDivinity) 25.0))
      %s
      %s
      (CallFunction|PhysisShot :Damage 4)
      (else
        (CallFunction|PhysisSay :Message "A Divinity Shot needs 25 Divinity")))))"""%(ANIM,READY,ALIVE,play('Pistol_Fire',.7),FIRE))
fn(P,'PhysisReload',"""(fn PhysisReload ()
  %s
  (bind need (- 12 (Variables|Default|GetGunAmmo)))
  (bind held (Variables|Default|GetGunReserve))
  (if (and (Variables|Default|GetGunEquipped) (and (and %s %s) (and (> need 0) (> held 0))))
    (Variables|Default|SetReloadTake (select (< held need) held need))
    (Variables|Default|SetGunAmmo (+ (Variables|Default|GetGunAmmo) (Variables|Default|GetReloadTake)))
    (Variables|Default|SetGunReserve (- (Variables|Default|GetGunReserve) (Variables|Default|GetReloadTake)))
    (Variables|Default|SetChainOpenAt 0.0)
    %s))"""%(ANIM,READY,ALIVE,play('Pistol_Reload',1.3)))
fn(P,'PhysisCollect',"""(fn PhysisCollect (Kind)
  (switch int Kind
    (:0
      (Variables|Default|SetPhysisHealth (select (> (Variables|Default|GetPhysisHealth) 7.0) 10.0 (+ (Variables|Default|GetPhysisHealth) 3.0)))
      (CallFunction|PhysisSay :Message "Health restored"))
    (:1
      (Variables|Default|SetDivinity (select (> (Variables|Default|GetDivinity) 90.0) 100.0 (+ (Variables|Default|GetDivinity) 10.0)))
      (CallFunction|PhysisSay :Message "Divinity absorbed"))
    (:Default
      (Variables|Default|SetGunReserve (+ (Variables|Default|GetGunReserve) 12))
      (CallFunction|PhysisSay :Message "Ammo cell: 12 rounds"))))""")
comp(P)
fn(P,'PhysisSwitchWeapon',call('read_graph_dsl',{'graph':{'refPath':P+':PhysisSwitchWeapon'}}) and """(fn PhysisSwitchWeapon ()
  %s
  (if (and %s %s)
    (Variables|Default|SetChainOpenAt 0.0)
    (Variables|Default|SetGunEquipped (not (Variables|Default|GetGunEquipped)))
    (bind out (Variables|Default|GetGunEquipped))
    (Rendering|SetVisibility :self (Variables|Default|GetKatana) :bNewVisibility (not out))
    (Rendering|SetVisibility :self (Variables|Default|GetGun) :bNewVisibility out)
    (if out
      (Components|SkeletalMesh|SetAnimInstanceClass :self (Variables|Default|GetBody) :NewClass "/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Pistol.Physis_ABP_Pistol_C")
      (else
        (Components|SkeletalMesh|SetAnimInstanceClass :self (Variables|Default|GetBody) :NewClass "/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed.Physis_ABP_Unarmed_C")))
    (bind pistol (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))
    (if out
      (Animation|Montage|MontagePlay :self pistol :MontageToPlay "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Pistol_Equip.AM_Physis_Pistol_Equip" :InPlayRate 1.6))))"""%(ANIM,READY,ALIVE))
comp(P)
fn(PICK,'PickupSetup',call('read_graph_dsl',{'graph':{'refPath':PICK+':PickupSetup'}}) and "(fn PickupSetup (Value) (Variables|Default|SetKind Value) (switch int Value (:0 (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh \"/Game/Gameplay/SM_Pickup_Health.SM_Pickup_Health\")) (:1 (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh \"/Game/Gameplay/SM_Pickup_Divinity.SM_Pickup_Divinity\")) (:Default (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh \"/Game/Gameplay/SM_Pickup_Ammo.SM_Pickup_Ammo\"))))")
print('pick',call('write_graph_dsl',{'graph':{'refPath':PICK+':EventGraph'},'code':"""(event EventBeginPlay
  (CallFunction|PickupSetup :Value (Variables|Default|GetKind)))

(event EventTick (DeltaSeconds)
  (Transformation|AddActorWorldRotation :DeltaRotation (Math|Rotator|MakeRotator :Yaw (* DeltaSeconds 80.0)) :bSweep false :bTeleport false)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (if (< (Transformation|GetDistanceTo :OtherActor physis) 130.0)
        (Class|BPPhysis|PhysisCollect :self physis :Kind (Variables|Default|GetKind))
        (Actor|DestroyActor)))
    (:CastFailed)))"""}))
comp(PICK)
fn(D,'TakeHit',"""(fn TakeHit (Amount)
  (Variables|Default|SetHealth (- (Variables|Default|GetHealth) Amount))
  (if (<= (Variables|Default|GetHealth) 0)
    (bind drop (Game|SpawnActorfromClass :Class "/Game/Characters/Physis/Blueprints/BP_Pickup.BP_Pickup_C" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation) :Rotation (Math|Rotator|MakeRotator :Yaw 0.0) :Scale (Math|Vector|MakeVector :X 1.3 :Y 1.3 :Z 1.3)) :CollisionHandlingOverride "AlwaysSpawn"))
    (Class|BPPickup|PickupSetup :self drop :Value (Math|Random|RandomIntegerinRange :Min 0 :Max 2))
    (for tag (Actor|GetAttachedActors)
      (Actor|DestroyActor :self tag))
    (Actor|DestroyActor)))""")
comp(D)
def tex(name,x,y,w,h,tint='"(R=1.0,G=1.0,B=1.0,A=1.0)"',extra=''):
    return '(HUD|DrawTexture :Texture "/Game/UI/%s.%s" :ScreenX %s :ScreenY %s :ScreenW %s :ScreenH %s :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor %s%s)'%(name,name,x,y,w,h,tint,extra)
FONT=' :Font "/Engine/EngineFonts/Roboto.Roboto"'
def text(t,x,y,scale,colour='"(R=1.0,G=0.9,B=0.7,A=1.0)"'):
    # Every HUD text sits on a dark plate so it reads over any background.
    # The font is cached at 40 pt (was 14), so every scale is multiplied by 14/40 to keep sizes and stay sharp.
    scale='(* %s 0.35)'%scale
    return '(CallFunction|DrawTextPlate :Text %s :X %s :Y %s :Scale %s)\n    '%(t,x,y,scale)+'(HUD|DrawText :Text %s :TextColor %s :ScreenX %s :ScreenY %s :Scale %s%s)'%(t,colour,x,y,scale,FONT)
TEAL='"(R=0.5,G=1.0,B=0.88,A=1.0)"'
shell(H,'DrawCombat',[('SizeX','float'),('SizeY','float')])
fn(H,'DrawCombat',"""(fn DrawCombat (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (HUD|GetOwningPawn))
    (:then
      """+tex('T_UI_Vitals','(* u 24.0)','(* u 20.0)','(* u 600.0)','(* u 150.0)')+"""
      """+tex('T_UI_IconHealth','(* u 52.0)','(* u 44.0)','(* u 44.0)','(* u 44.0)')+"""
      """+tex('T_UI_BarHealth','(* u 106.0)','(* u 54.0)','(* u (* 44.0 (- (Class|BPPhysis|GetPhysisHealth :self physis) (* 10.0 (Math|Conversions|ToFloat(Integer) (Math|Float|Truncate (/ (- (Class|BPPhysis|GetPhysisHealth :self physis) 0.001) 10.0)))))))','(* u 24.0)')+"""
      """+tex('T_UI_IconDivinity','(* u 52.0)','(* u 94.0)','(* u 44.0)','(* u 44.0)')+"""
      """+tex('T_UI_BarDivinity','(* u 106.0)','(* u 106.0)','(* u (* 4.4 (Class|BPPhysis|GetDivinity :self physis)))','(* u 18.0)')+"""
      (bind wx (- SizeX (* u 350.0)))
      (bind wy (- SizeY (* u 200.0)))
      """+tex('T_UI_Weapon','wx','wy','(* u 320.0)','(* u 160.0)')+"""
      (if (Class|BPPhysis|GetGunEquipped :self physis)
        """+tex('T_UI_IconGun','(+ wx (* u 20.0))','(+ wy (* u 18.0))','(* u 120.0)','(* u 120.0)')+"""
        """+text('(Utilities|String|ToString(Integer) (Class|BPPhysis|GetGunAmmo :self physis))','(+ wx (* u 160.0))','(+ wy (* u 14.0))','(* u 3.4)','"(R=1.0,G=1.0,B=1.0,A=1.0)"')+"""
        """+text('"RESERVE"','(+ wx (* u 160.0))','(+ wy (* u 98.0))','(* u 0.8)','"(R=1.0,G=0.65,B=0.25,A=1.0)"')+"""
        """+text('(Utilities|String|ToString(Integer) (Class|BPPhysis|GetGunReserve :self physis))','(+ wx (* u 245.0))','(+ wy (* u 92.0))','(* u 1.2)')+"""
        (if (not (Class|BPPhysis|GetScanVisorOn :self physis))
          """+tex('T_UI_ReticleGun','(- (/ SizeX 2.0) (* u 44.0))','(- (/ SizeY 2.0) (* u 44.0))','(* u 88.0)','(* u 88.0)')+""")
        (else
          """+tex('T_UI_IconSword','(+ wx (* u 20.0))','(+ wy (* u 18.0))','(* u 120.0)','(* u 120.0)')+"""
          """+text('"KATANA"','(+ wx (* u 160.0))','(+ wy (* u 54.0))','(* u 1.4)')+"""))
      (bind target (Class|BPPhysis|GetLockTarget :self physis))
      (Utilities|IsValid target
        (:"Is Valid"
          (bind at (HUD|Project :Location (Transformation|GetActorLocation :self target) :bClampToZeroPlane false))
          """+tex('T_UI_Lock','(- (.x at) (* u 70.0))','(- (.y at) (* u 70.0))','(* u 140.0)','(* u 140.0)',extra=' :Rotation (* (Utilities|Time|GetGameTimeinSeconds) 60.0) :RotPivot "(X=0.5,Y=0.5)"')+""")
        (:"Is Not Valid")))
    (:CastFailed)))""")
TARG='(Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_ScanTarget.BP_ScanTarget_C")'
fn(H,'DrawVisor',"""(fn DrawVisor (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (HUD|GetOwningPawn))
    (:then
      (bind blend (Class|BPPhysis|GetVisorBlend :self physis))
      (if (> blend 0.01)
        """+tex('T_UI_VisorFrame','0.0','0.0','SizeX','SizeY','(Utilities|Struct|MakeLinearColor :R 1.0 :G 1.0 :B 1.0 :A blend)')+"""
        """+tex('T_UI_Reticle','(- (/ SizeX 2.0) (* u 56.0))','(- (/ SizeY 2.0) (* u 56.0))','(* u 112.0)','(* u 112.0)')+"""
        (Variables|Default|SetLogbookSeen 0)
        (Variables|Default|SetLogbookDone 0)
        (bind clock (Utilities|Time|GetGameTimeinSeconds))
        (for found """+TARG+"""
          (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
            (:then
              (bind done (Class|BPScanTarget|GetScanDone :self item))
              (bind important (Class|BPScanTarget|GetScanImportant :self item))
              (bind aimed (Class|BPScanTarget|GetScanAimed :self item))
              (Variables|Default|SetLogbookSeen (+ (Variables|Default|GetLogbookSeen) 1))
              (if done (Variables|Default|SetLogbookDone (+ (Variables|Default|GetLogbookDone) 1)))
              (if (Class|BPScanTarget|GetScanInView :self item)
                (bind at (HUD|Project :Location (Transformation|GetActorLocation :self item) :bClampToZeroPlane false))
                (bind pulse (+ 62.0 (* 8.0 (Math|Trig|Sin(Radians) (* clock 5.0)))))
                (bind size (* u (select aimed 96.0 (select important pulse 50.0))))
                """+tex('T_UI_ScanMarker','(- (.x at) size)','(- (.y at) size)','(* size 2.0)','(* size 2.0)','(Utilities|Struct|MakeLinearColor :R (select done 0.55 (select important 1.0 0.25)) :G (select done 0.58 (select important 0.82 1.0)) :B (select done 0.6 (select important 0.15 0.55)) :A 1.0)')+"""
                (if (and aimed (not done))
                  (HUD|DrawRect :RectColor "(R=0.0,G=0.1,B=0.1,A=0.8)" :ScreenX (- (.x at) (* u 80.0)) :ScreenY (+ (.y at) (* u 100.0)) :ScreenW (* u 160.0) :ScreenH (* u 12.0))
                  """+tex('T_UI_BarDivinity','(- (.x at) (* u 80.0))','(+ (.y at) (* u 100.0))','(* u (* 160.0 (Class|BPScanTarget|GetScanProgress :self item)))','(* u 12.0)')+""")))
            (:CastFailed)))
        """+tex('T_UI_PanelScan','(- SizeX (* u 320.0))','(* u 24.0)','(* u 296.0)','(* u 74.0)')+"""
        """+text('"SCANS"','(- SizeX (* u 290.0))','(* u 44.0)','(* u 1.1)',TEAL)+"""
        """+text('(Utilities|String|ToString(Integer) (Variables|Default|GetLogbookDone))','(- SizeX (* u 180.0))','(* u 44.0)','(* u 1.1)',TEAL)+"""
        """+text('"/"','(- SizeX (* u 135.0))','(* u 44.0)','(* u 1.1)',TEAL)+"""
        """+text('(Utilities|String|ToString(Integer) (Variables|Default|GetLogbookSeen))','(- SizeX (* u 112.0))','(* u 44.0)','(* u 1.1)',TEAL)+"""
        (if (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetScanResultHideAt))
          (bind message (Variables|Default|GetScanResult))
          (bind (width high) (HUD|GetTextSize :Text message :Font "/Engine/EngineFonts/Roboto.Roboto" :Scale (* u 1.2)))
          (bind panelX (/ (- SizeX width) 2.0))
          (bind panelY (* SizeY 0.56))
          """+tex('T_UI_PanelScan','(- panelX (* u 60.0))','(- panelY (* u 34.0))','(+ width (* u 120.0))','(+ high (* u 68.0))')+"""
          """+text('message','panelX','panelY','(* u 1.2)','"(R=0.75,G=1.0,B=0.92,A=1.0)"')+"""))
      )
    (:CastFailed)))""")
var(H,'TutorialIcon','bool')
for n in('TutorialWidth','TutorialX'):var(H,n,'float')
shell(H,'DrawTutorial',[('SizeX','float'),('SizeY','float')])
ICONS=('A','B','X','Y','LB','RB','LT','RT','LS','RS','L3','DU','DD')
def glyphs():
    return ' '.join('(if (Utilities|String|EqualExactly(String) :A piece :B "%s") %s)'%(n,tex('T_Pad_'+n,'x','(- top (* u 12.0))','(* u 56.0)','(* u 56.0)')) for n in ICONS)
fn(H,'DrawTutorial',"""(fn DrawTutorial (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind scale (* u 1.2))
  (bind top (- SizeY (* u 300.0)))
  (bind parts (Utilities|String|ParseIntoArray :SourceString (Variables|Default|GetTutorialText) :Delimiter "|" :CullEmptyStrings false))
  (Variables|Default|SetTutorialIcon false)
  (Variables|Default|SetTutorialWidth 0.0)
  (for part parts
    (bind (width high) (HUD|GetTextSize :Text part :Font "/Engine/EngineFonts/Roboto.Roboto" :Scale scale))
    (Variables|Default|SetTutorialWidth (+ (Variables|Default|GetTutorialWidth) (select (Variables|Default|GetTutorialIcon) (* u 62.0) width)))
    (Variables|Default|SetTutorialIcon (not (Variables|Default|GetTutorialIcon))))
  (bind total (Variables|Default|GetTutorialWidth))
  """+tex('T_UI_Panel','(- (/ (- SizeX total) 2.0) (* u 60.0))','(- top (* u 34.0))','(+ total (* u 120.0))','(* u 98.0)')+"""
  (Variables|Default|SetTutorialX (/ (- SizeX total) 2.0))
  (Variables|Default|SetTutorialIcon false)
  (for piece parts
    (bind (wide tall) (HUD|GetTextSize :Text piece :Font "/Engine/EngineFonts/Roboto.Roboto" :Scale scale))
    (bind x (Variables|Default|GetTutorialX))
    (if (Variables|Default|GetTutorialIcon)
      """+glyphs()+"""
      (else """+text('piece','x','top','scale')+"""))
    (Variables|Default|SetTutorialX (+ (Variables|Default|GetTutorialX) (select (Variables|Default|GetTutorialIcon) (* u 62.0) wide)))
    (Variables|Default|SetTutorialIcon (not (Variables|Default|GetTutorialIcon)))))""")
shell(H,'DrawCinema',[('SizeX','float'),('SizeY','float'),('Elapsed','float')])
fn(H,'DrawCinema',"""(fn DrawCinema (SizeX SizeY Elapsed)
  (bind u (/ SizeY 1080.0))
  (HUD|DrawRect :RectColor "(R=0.0,G=0.0,B=0.0,A=1.0)" :ScreenX 0.0 :ScreenY 0.0 :ScreenW SizeX :ScreenH (* u 104.0))
  (HUD|DrawRect :RectColor "(R=0.0,G=0.0,B=0.0,A=1.0)" :ScreenX 0.0 :ScreenY (- SizeY (* u 104.0)) :ScreenW SizeX :ScreenH (* u 104.0))
  (bind up (/ (- Elapsed 19.0) 1.6))
  (bind rise (select (< up 0.0) 0.0 (select (> up 1.0) 1.0 up)))
  (bind down (/ (- 27.0 Elapsed) 1.6))
  (bind fall (select (< down 0.0) 0.0 (select (> down 1.0) 1.0 down)))
  (bind show (* rise fall))
  (bind wide (select (< SizeX (* u 1120.0)) (* SizeX 0.86) (* u 960.0)))
  (if (> show 0.0)
    """+tex('T_UI_Title','(- (/ SizeX 2.0) (/ wide 2.0))','(- (* SizeY 0.46) (* wide 0.3125))','wide','(* wide 0.625)','(Utilities|Struct|MakeLinearColor :R 1.0 :G 1.0 :B 1.0 :A show)')+""")
  """+text('"Skip:   E  /"','(- SizeX (* u 280.0))','(- SizeY (* u 76.0))','(* u 1.6)')+"""
  """+tex('T_Pad_X','(- SizeX (* u 110.0))','(- SizeY (* u 84.0))','(* u 52.0)','(* u 52.0)')+""")""")
print('hud',call('write_graph_dsl',{'graph':{'refPath':H+':EventGraph'},'code':"""(event EventBeginPlay
  (CallFunction|ShowTutorial "Move: W A S D / |LS|     Look: Mouse / |RS|"))

(event EventReceiveDrawHUD (SizeX SizeY)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (HUD|GetOwningPawn))
    (:then
      (if (Class|BPPhysis|GetCinematic :self physis)
        (CallFunction|DrawCinema :SizeX SizeX :SizeY SizeY :Elapsed (- (Utilities|Time|GetGameTimeinSeconds) (Class|BPPhysis|GetCinemaStartedAt :self physis)))
        (else
          (CallFunction|DrawVisor :SizeX SizeX :SizeY SizeY)
          (CallFunction|DrawCombat :SizeX SizeX :SizeY SizeY)
          (if (and (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetTutorialHideAt)) (not (Utilities|String|EqualExactly(String) :A (Variables|Default|GetTutorialText) :B "")))
            (CallFunction|DrawTutorial :SizeX SizeX :SizeY SizeY)))))
    (:CastFailed)))"""}))
comp(H)
F=B+'BP_FleetShip.BP_FleetShip';U=B+'BP_Burst.BP_Burst';R=B+'BP_BattleDirector.BP_BattleDirector'
var(F,'SpeedX','float',True)
print('ship',call('write_graph_dsl',{'graph':{'refPath':F+':EventGraph'},'code':"""(event EventTick (DeltaSeconds)
  (Transformation|AddActorWorldOffset :DeltaLocation (Math|Vector|MakeVector :X (* (Variables|Default|GetSpeedX) DeltaSeconds) :Y 0.0 :Z 0.0) :bSweep false :bTeleport false))"""}))
comp(F)
var(U,'Age','float');var(U,'Size','float')
print('burst',call('write_graph_dsl',{'graph':{'refPath':U+':EventGraph'},'code':"""(event EventBeginPlay
  (Variables|Default|SetSize (Math|Random|RandomFloatinRange :Min 30.0 :Max 120.0)))

(event EventTick (DeltaSeconds)
  (Variables|Default|SetAge (+ (Variables|Default|GetAge) DeltaSeconds))
  (bind grown (* (Variables|Default|GetSize) (+ 0.25 (* 0.75 (Variables|Default|GetAge)))))
  (Transformation|SetActorScale3D :NewScale3D (Math|Vector|MakeVector :X grown :Y grown :Z grown))
  (bind left (- 1.0 (/ (Variables|Default|GetAge) 1.4)))
  (Rendering|Material|SetCustomPrimitiveDataFloat :self (Variables|Default|GetShape) :DataIndex 0 :Value (* left left))
  (if (<= left 0.0)
    (Actor|DestroyActor)))"""}))
comp(U)
var(R,'Clock','float')
shell(R,'FireBolt',[('Teal','bool')])
AIM='(Math|Vector|MakeVector :X (Math|Random|RandomFloatinRange :Min -36000.0 :Max 36000.0) :Y (Math|Random|RandomFloatinRange :Min -170000.0 :Max -90000.0) :Z (Math|Random|RandomFloatinRange :Min 0.0 :Max 30000.0))'
BOLT=':SpawnTransform (Math|Transform|MakeTransform :Location spot :Rotation (Math|Rotator|MakeRotator :Yaw (Math|Random|RandomFloatinRange :Min -8.0 :Max 8.0)) :Scale (Math|Vector|MakeVector :X 130.0 :Y 0.7 :Z 0.7)) :CollisionHandlingOverride "AlwaysSpawn"'
fn(R,'FireBolt',"""(fn FireBolt (Teal)
  (bind spot (+ """+AIM+""" (Math|Vector|MakeVector :X 8500.0 :Y 0.0 :Z 0.0)))
  (if Teal
    (Game|SpawnActorfromClass :Class "/Game/Characters/Physis/Blueprints/BP_BoltTeal.BP_BoltTeal_C" """+BOLT+""")
    (else
      (Game|SpawnActorfromClass :Class "/Game/Characters/Physis/Blueprints/BP_GunTracer.BP_GunTracer_C" """+BOLT+"""))))""")
comp(R)
print('director',call('write_graph_dsl',{'graph':{'refPath':R+':EventGraph'},'code':"""(event EventTick (DeltaSeconds)
  (Variables|Default|SetClock (+ (Variables|Default|GetClock) DeltaSeconds))
  (if (and (> (Variables|Default|GetClock) 7.0) (< (Variables|Default|GetClock) 34.0))
    (CallFunction|FireBolt :Teal true)
    (CallFunction|FireBolt :Teal false)
    (if (> (Math|Random|RandomFloatinRange :Min 0.0 :Max 1.0) 0.8)
      (Game|SpawnActorfromClass :Class "/Game/Characters/Physis/Blueprints/BP_Burst.BP_Burst_C" :SpawnTransform (Math|Transform|MakeTransform :Location (+ """+AIM+""" (Math|Vector|MakeVector :X 8500.0 :Y 0.0 :Z 0.0)) :Rotation (Math|Rotator|MakeRotator :Yaw 0.0) :Scale (Math|Vector|MakeVector :X 60.0 :Y 60.0 :Z 60.0)) :CollisionHandlingOverride "AlwaysSpawn"))))"""}))
comp(R)
