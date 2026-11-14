import sys,re,json
sys.path.insert(0,'Tools')
src=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/feel.py').read()
exec(src[:src.index('# Effect actors')])
exec('LENS='+'''{"Cut":1.9,"Slice":1.767,"Whirl":2.0,"Flash":1.7,"Crescent":2.567,"Gale":2.0,"Rush":3.133,"Reaper":2.467,"Meteor":2.1,"Thrust":1.833,"Heel":1.6,"Rend":2.667,"Spin":2.333,"Drive":2.267,"Cyclone":2.4,"Pierce":1.833,"Storm":2.333,"Bloom":3.933}''')
P2=src
exec(cut("ANIM=","call('add_object_variable'") if False else "pass")
ANIM='(bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))'
FREE='(or (not (Animation|Montage|IsAnyMontagePlaying :self anim)) (and (> (Variables|Default|GetChainOpenAt) 0.0) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetChainOpenAt))))'
READY='(and (not (Variables|Default|GetScanVisorOn)) '+FREE+')'
ALIVE='(and (not (Variables|Default|GetPhysisDead)) (not (Variables|Default|GetCinematic)))'
DRONES='(Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_TrainingDrone.BP_TrainingDrone_C")'
LIGHT=('Cut','Slice','Whirl','Flash','Crescent','Gale','Rush','Reaper','Meteor')
HEAVY=('Thrust','Heel','Rend','Spin','Drive','Cyclone','Pierce','Storm','Bloom')
def play(n,rate,start=0.0):
    return '(Animation|Montage|MontagePlay :self anim :MontageToPlay "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_%s.AM_Physis_%s" :InPlayRate %s :InTimeToStartMontageAt %s)'%(n,n,rate,start)
def chain(names,damage,base):
    out=[]
    for i,n in enumerate(names):
        fin=i in(2,5,8)
        r=base*(.8 if fin else 1.0); L=LENS[n]
        out.append('(:%d %s (CallFunction|PhysisSwung :Length %s :Damage %d))'%(i,play('F_'+n,r,round(L*.14,3)),round(.655*L/r,3),damage+(1 if fin else 0)))
    return ' '.join(out)
def attack(name,names,air,damage,base):
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
            (switch int (Variables|Default|GetChainStep) %s (:Default))))))))"""%(name,ANIM,'PhysisFire' if damage==1 else 'PhysisFireDivine',READY,ALIVE,'(Animation|Montage|MontagePlay :self anim :MontageToPlay "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_%s.AM_Physis_%s" :InPlayRate 1.9)'%(air,air),damage,chain(names,damage,base))
var(P,'LungeBest','float');var(P,'LungeX','float')
call('add_object_variable',{'blueprint':{'refPath':P},'name':'LungeTarget','object_class':{'refPath':'/Script/Engine.Actor'}},True)
fn(P,'PhysisSwung',"""(fn PhysisSwung (Length Damage)
  (Audio|PlaySound2D :Sound "/Game/Audio/S_SwordSwing1.S_SwordSwing1" :VolumeMultiplier 0.7 :PitchMultiplier (Math|Random|RandomFloatinRange :Min 0.85 :Max 1.3))
  (Variables|Default|SetChainUntil (+ (+ (Utilities|Time|GetGameTimeinSeconds) (* Length 0.71)) 1.0))
  (bind following (+ (Variables|Default|GetChainStep) 1))
  (Variables|Default|SetChainStep (select (>= following (+ 3 (Variables|Default|GetSkillLevel))) 0 following))
  (Variables|Default|SetPendingDamage Damage)
  (Variables|Default|SetChainOpenAt (+ (Utilities|Time|GetGameTimeinSeconds) (* Length 0.5)))
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisStrikeNow" :Time (* Length 0.29) :bLooping false)
  (Variables|Default|SetLungeBest 750.0)
  (Variables|Default|SetLungeX 0.0)
  (for found """+DRONES+"""
    (bind gap (Transformation|GetDistanceTo :OtherActor found))
    (if (< gap (Variables|Default|GetLungeBest))
      (Variables|Default|SetLungeBest gap)
      (Variables|Default|SetLungeX 1.0)
      (Variables|Default|SetLungeTarget found)))
  (if (> (Variables|Default|GetLungeX) 0.5)
    (Transformation|SetActorRotation :NewRotation (Math|Rotator|MakeRotfromZX :Z (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 1.0) :X (- (Transformation|GetActorLocation :self (Variables|Default|GetLungeTarget)) (Transformation|GetActorLocation))) :bTeleportPhysics false))
  (Character|LaunchCharacter :LaunchVelocity (* (Transformation|GetActorForwardVector) (select (> (Variables|Default|GetLungeX) 0.5) 1700.0 800.0)) :bXYOverride true))""")
fn(P,'PhysisAttack',attack('PhysisAttack',LIGHT,'JumpAttack1',1,2.3))
fn(P,'PhysisAttackHeavy',attack('PhysisAttackHeavy',HEAVY,'JumpAttack2',2,2.0))
hurt=None
comp(P)
BOLT=B+'BP_EnemyBolt.BP_EnemyBolt'
var(BOLT,'Age','float')
print('bolt',call('write_graph_dsl',{'graph':{'refPath':BOLT+':EventGraph'},'code':"""(event EventTick (DeltaSeconds)
  (Variables|Default|SetAge (+ (Variables|Default|GetAge) DeltaSeconds))
  (Transformation|AddActorWorldOffset :DeltaLocation (* (Transformation|GetActorForwardVector) (* DeltaSeconds 1700.0)) :bSweep false :bTeleport false)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (if (< (Transformation|GetDistanceTo :OtherActor physis) 105.0)
        """+snd('S_LaserHit',.9)+"""
        (Class|BPPhysis|PhysisHurt :self physis :FromAhead (> (Transformation|GetDotProductTo :self physis :OtherActor self) 0.0))
        (Actor|DestroyActor)))
    (:CastFailed)))"""}))
comp(BOLT)
var(D,'Phase','float')
BOLTSPAWN='(Game|SpawnActorfromClass :Class "%sBP_EnemyBolt.BP_EnemyBolt_C" :SpawnTransform (Math|Transform|MakeTransform :Location (+ (Transformation|GetActorLocation) (* (Transformation|GetActorForwardVector) 70.0)) :Rotation (Transformation|GetActorRotation) :Scale (Math|Vector|MakeVector :X 1.5 :Y 0.07 :Z 0.07)) :CollisionHandlingOverride "AlwaysSpawn")'%B
fn(D,'DroneThink',"""(fn DroneThink (DeltaSeconds)
  (Variables|Default|SetCooldown (- (Variables|Default|GetCooldown) DeltaSeconds))
  (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) DeltaSeconds))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (bind gap (Transformation|GetDistanceTo :OtherActor physis))
      (bind seen (Controller|LineOfSightTo :self (Game|GetPlayerController 0) :Other self))
      (if (< gap 1800.0)
        (Transformation|SetActorRotation :NewRotation (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation) :Target (+ (Transformation|GetActorLocation :self physis) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 30.0))) :bTeleportPhysics false)
        (Transformation|AddActorWorldOffset :DeltaLocation (* (+ (+ (* (Transformation|GetActorForwardVector) (select (> gap 560.0) 1.0 (select (< gap 340.0) -1.0 0.0))) (* (Transformation|GetActorRightVector) (select (> (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 1.1)) 0.0) 0.75 -0.75))) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (* 0.35 (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 3.0))))) (* DeltaSeconds 430.0)) :bSweep true :bTeleport false))
      (if (and (< (Variables|Default|GetCooldown) 0.6) (and (not (Variables|Default|GetWarned)) (and (< gap 1500.0) seen)))
        (Variables|Default|SetWarned true)
        """+at('S_SwordHeavy','(Transformation|GetActorLocation)',.9)+"""
        """+spawn('BP_Spark','(Transformation|GetActorLocation)')+""")
      (if (<= (Variables|Default|GetCooldown) 0.0)
        (Variables|Default|SetCooldown (Math|Random|RandomFloatinRange :Min 2.8 :Max 4.6))
        (Variables|Default|SetWarned false)
        (if (< gap 240.0)
          (Class|BPPhysis|PhysisHurt :self physis :FromAhead (> (Transformation|GetDotProductTo :self physis :OtherActor self) 0.0))
          (elif (and (< gap 1500.0) seen)
            """+at('S_Laser1','(Transformation|GetActorLocation)')+"""
            """+BOLTSPAWN+"""))))
    (:CastFailed)))""")
comp(D)
COMBAT='(Variables|Default|SetMusicComp (Audio|SpawnSound2D :Sound "/Game/Audio/S_Music_Combat.S_Music_Combat" :VolumeMultiplier 0.85))'
fn(P,'PhysisMusic',"""(fn PhysisMusic ()
  (Utilities|IsValid (Variables|Default|GetMusicComp)
    (:"Is Valid"
      (Class|AudioComponent|SetVolumeMultiplier :self (Variables|Default|GetMusicComp) :VolumeMultiplier 0.0)
      %s)
    (:"Is Not Valid"
      %s)))"""%(COMBAT,COMBAT))
comp(P)
