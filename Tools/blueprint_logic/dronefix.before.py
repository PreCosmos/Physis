import sys,re
sys.path.insert(0,'Tools')
src=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/feel.py').read()
exec(src[:src.index('# Effect actors')])
combat=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
def ccut(a,b):
    i=combat.index(a); return combat[i:combat.index(b,i)]
G,SW,PL,HZ,CK,EN,WT=[B+n+'.'+n for n in ('BP_Gate','BP_Switch','BP_Platform','BP_Hazard','BP_Checkpoint','BP_Encounter','BP_Watcher')]
PHYSIS='(bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))\n'
HAS=lambda tok:'(Utilities|String|Contains :SearchIn (Class|BPPhysis|GetFlags :self physis) :Substring %s)'%tok

var(D,'Static','bool',True);var(D,'BumpCool','float');shell(D,'DroneSeparate',[('DeltaSeconds','float')])
fn(D,'DroneSeparate',"""(fn DroneSeparate (DeltaSeconds)
  (Variables|Default|SetBumpCool (- (Variables|Default|GetBumpCool) DeltaSeconds))
  (for other (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_TrainingDrone.BP_TrainingDrone_C")
    (bind apart (Transformation|GetDistanceTo :OtherActor other))
    (if (and (> apart 1.0) (< apart (select (Variables|Default|GetBoss) 300.0 150.0)))
      (bind away (Math|Vector|Normalize (- (Transformation|GetActorLocation) (Transformation|GetActorLocation :self other))))
      (Transformation|AddActorWorldOffset :DeltaLocation (* (Math|Vector|MakeVector :X (.x away) :Y (.y away) :Z 0.0) (* DeltaSeconds 600.0)) :bSweep false :bTeleport false)
      (if (and (<= (Variables|Default|GetBumpCool) 0.0) (not (Variables|Default|GetBoss)))
        (Variables|Default|SetBumpCool 1.0)
        """+spawn('BP_Spark','(Transformation|GetActorLocation)')+"""
        (CallFunction|TakeHit :Amount 1)))))""")

BOLT=lambda yaw:'(Game|SpawnActorfromClass :Class "%sBP_EnemyBolt.BP_EnemyBolt_C" :SpawnTransform (Math|Transform|MakeTransform :Location (+ (Transformation|GetActorLocation) (* (Transformation|GetActorForwardVector) 100.0)) :Rotation (Math|Rotator|CombineRotators :A (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw %s) :B (Transformation|GetActorRotation)) :Scale (Math|Vector|MakeVector :X 1.5 :Y 0.07 :Z 0.07)) :CollisionHandlingOverride "AlwaysSpawn")'%(B,yaw)
fn(D,'TakeHit',"""(fn TakeHit (Amount)
  """+PHYSIS+"""    (:then
      (bind there (Math|Vector|Normalize (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation))))
      (if (and (Variables|Default|GetBoss) (< (Math|Vector|DotProduct (Transformation|GetActorForwardVector) there) 0.35))
        (Class|BPPhysis|PhysisSay :self physis :Message "The armor turns your attack. Strike the red eye~on its front.")
        (else
          (Variables|Default|SetHealth (- (Variables|Default|GetHealth) Amount))
          (if (<= (Variables|Default|GetHealth) 0)
            """+at('S_DroneExplosion','(Transformation|GetActorLocation)')+"""
            """+spawn('BP_DroneBurst','(Transformation|GetActorLocation)')+"""
            (bind loot (Math|Vector|MakeVector :X (.x (Transformation|GetActorLocation)) :Y (.y (Transformation|GetActorLocation)) :Z 125.0))
            (bind crystal """+spawn('BP_Pickup','loot')+""")
            (Class|BPPickup|PickupSetup :self crystal :Value 1)
            (bind extra """+spawn('BP_Pickup','(+ loot (Math|Vector|MakeVector :X 70.0 :Y 40.0 :Z 0.0))')+""")
            (Class|BPPickup|PickupSetup :self extra :Value (select (> (Math|Random|RandomFloatinRange :Min 0.0 :Max 1.0) 0.5) 0 2))
            (Class|BPPhysis|PhysisSlow :self physis :Rate 0.22 :Seconds 0.55)
            (Class|BPPhysis|SetBossShown :self physis :BossShown 0.0)
            (for tag (Actor|GetAttachedActors)
              (Actor|DestroyActor :self tag))
            (Actor|DestroyActor)))))
    (:CastFailed)))""")
fn(D,'DroneThink',"""(fn DroneThink (DeltaSeconds)
  (CallFunction|DroneSeparate :DeltaSeconds DeltaSeconds)
  (Variables|Default|SetCooldown (- (Variables|Default|GetCooldown) DeltaSeconds))
  (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) DeltaSeconds))
  """+PHYSIS+"""    (:then
      (bind gap (Transformation|GetDistanceTo :OtherActor physis))
      (bind boss (Variables|Default|GetBoss))
      (bind seen (Controller|LineOfSightTo :self (Game|GetPlayerController 0) :Other self))
      (if (and boss (and (> (.x (Transformation|GetActorLocation :self physis)) 13480.0) (< (.x (Transformation|GetActorLocation :self physis)) 16400.0)))
        (Class|BPPhysis|SetBossShown :self physis :BossShown (/ (Math|Conversions|ToFloat(Integer) (Variables|Default|GetHealth)) 30.0)))
      (if (and (and (< gap 1800.0) seen) (not (Variables|Default|GetStatic)))
        (Transformation|SetActorRotation :NewRotation (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation) :Target (+ (Transformation|GetActorLocation :self physis) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 30.0))) :bTeleportPhysics false)
        (bind step (* (+ (+ (* (Transformation|GetActorForwardVector) (select (> gap (select boss 500.0 560.0)) 1.0 (select (< gap (select boss 300.0 340.0)) -1.0 0.0))) (* (Transformation|GetActorRightVector) (select (> (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 1.1)) 0.0) 0.75 -0.75))) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (+ (* 0.3 (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 3.0))) (select (> (.z (Transformation|GetActorLocation)) (select boss 260.0 165.0)) -0.9 (select (< (.z (Transformation|GetActorLocation)) (select boss 200.0 115.0)) 0.9 0.0))))) (* DeltaSeconds 430.0)))
        (bind (wallhit blocked) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* (Math|Vector|Normalize step) (select boss 240.0 120.0))) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (if (not blocked)
          (Transformation|AddActorWorldOffset :DeltaLocation step :bSweep false :bTeleport false)
          (else
            (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) 2.86))
            (Transformation|AddActorWorldOffset :DeltaLocation (* (Math|Vector|Normalize step) -8.0) :bSweep false :bTeleport false))))
      (if (and (and (< gap 1800.0) (not seen)) (not (Variables|Default|GetStatic)))
        (bind toward (* (Math|Vector|Normalize (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation))) (* DeltaSeconds 300.0)))
        (bind (wallhit2 blocked2) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* (Math|Vector|Normalize toward) 120.0)) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (if (not blocked2)
          (Transformation|AddActorWorldOffset :DeltaLocation toward :bSweep false :bTeleport false)
          (else
            (Transformation|AddActorWorldOffset :DeltaLocation (* (Transformation|GetActorRightVector) (* DeltaSeconds (select (> (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 0.7)) 0.0) 300.0 -300.0))) :bSweep false :bTeleport false))))
      (if (and (and (< (Variables|Default|GetCooldown) 0.6) (not (Variables|Default|GetStatic))) (and (not (Variables|Default|GetWarned)) (and (< gap 1500.0) seen)))
        (Variables|Default|SetWarned true)
        """+at('S_SwordHeavy','(Transformation|GetActorLocation)',.9)+"""
        """+spawn('BP_Spark','(Transformation|GetActorLocation)')+""")
      (if (and (<= (Variables|Default|GetCooldown) 0.0) (not (Variables|Default|GetStatic)))
        (Variables|Default|SetCooldown (select boss (Math|Random|RandomFloatinRange :Min 1.7 :Max 2.6) (Math|Random|RandomFloatinRange :Min 2.8 :Max 4.6)))
        (Variables|Default|SetWarned false)
        (if (< gap (select boss 340.0 240.0))
          (Class|BPPhysis|PhysisHurt :self physis :FromAhead (> (Transformation|GetDotProductTo :self physis :OtherActor self) 0.0))
          (elif (and (< gap 1500.0) seen)
            """+at('S_Laser1','(Transformation|GetActorLocation)')+"""
            """+BOLT('0.0')+"""
            (if boss
              """+BOLT('18.0')+"""
              """+BOLT('-18.0')+""")))))
    (:CastFailed)))""")
comp(D)
