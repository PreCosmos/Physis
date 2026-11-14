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

var(D,'RoomMin','vector',True);var(D,'RoomMax','vector',True);var(D,'InRoom','bool');var(D,'Blocked','bool');var(D,'Static','bool',True);var(D,'EyeHits','int');var(D,'StunUntil','float');var(D,'LastSpot','vector');var(D,'StuckFor','float');var(D,'SpotActive','bool');shell(D,'DroneStuckCheck',[('DeltaSeconds','float')]);var(D,'BumpCool','float');shell(D,'DroneSeparate',[('DeltaSeconds','float')])
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
      (bind facing (Math|Vector|DotProduct (Transformation|GetActorForwardVector) there))
      (if (and (Variables|Default|GetBoss) (> facing -0.35))
        (if (and (> facing 0.35) (> (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil)))
          (Variables|Default|SetEyeHits (+ (Variables|Default|GetEyeHits) 1))
          """+spawn('BP_Spark','(+ (Transformation|GetActorLocation) (* (Transformation|GetActorForwardVector) 110.0))')+"""
          (if (>= (Variables|Default|GetEyeHits) 3)
            (Variables|Default|SetEyeHits 0)
            (Variables|Default|SetStunUntil (+ (Utilities|Time|GetGameTimeinSeconds) 5.0))
            """+at('S_DroneExplosion','(Transformation|GetActorLocation)',.6)+"""
            (Class|BPPhysis|PhysisSlow :self physis :Rate 0.25 :Seconds 0.4)
            (Class|BPPhysis|PhysisSay :self physis :Message "The Mecha Breacher is paralysed!~Get behind it and strike its back.")
            (else
              (Class|BPPhysis|PhysisSay :self physis :Message "The red eye flickers. Strike it again.")))
          (else
            (Class|BPPhysis|PhysisSay :self physis :Message "The front armor turns your attack.~Its back is the weak point.")))
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
# A drone that is free keeps travelling (it strafes at ~320 u/s). One jammed in a wall, the floor or another drone only
# jitters in place, so the check is net travel over 0.75 s, sampled into LastSpot (StuckFor is the sample clock).
# Only a window the drone spent fully engaged counts (SpotActive), so a drone that just woke up is never judged.
# Hovering never touches the floor: within 60 below, the drone is lifted. A floor surface above its centre means it
# is sunk into the floor, which counts as stuck. Both checks run before the lift, because pure nodes re-read the location.
fn(D,'DroneStuckCheck',"""(fn DroneStuckCheck (DeltaSeconds)
  (if (not (or (Variables|Default|GetBoss) (Variables|Default|GetStatic)))
    (bind here (Transformation|GetActorLocation))
    (bind active (and (< (Transformation|GetDistanceTo :OtherActor (Game|GetPlayerPawn 0)) 1800.0) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil))))
    (Variables|Default|SetStuckFor (+ (Variables|Default|GetStuckFor) DeltaSeconds))
    (if (not active)
      (Variables|Default|SetSpotActive false))
    (for other (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_TrainingDrone.BP_TrainingDrone_C")
      (if (and active (and (> (Transformation|GetDistanceTo :OtherActor other) 1.0) (< (Transformation|GetDistanceTo :OtherActor other) 45.0)))
        (CallFunction|TakeHit :Amount 99)))
    (bind (sunkhit sunk) (Collision|LineTraceByChannel :Start (+ here (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 70.0)) :End here :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
    (if (and active (or sunk (< (.z here) 40.0)))
      (CallFunction|TakeHit :Amount 99))
    (if (>= (Variables|Default|GetStuckFor) 0.75)
      (if (and (and active (Variables|Default|GetSpotActive)) (< (Math|Vector|Distance(Vector) :V1 here :V2 (Variables|Default|GetLastSpot)) 60.0))
        (CallFunction|TakeHit :Amount 99))
      (Variables|Default|SetSpotActive active)
      (Variables|Default|SetStuckFor 0.0)
      (Variables|Default|SetLastSpot (Transformation|GetActorLocation)))
    (bind (floorhit low) (Collision|LineTraceByChannel :Start here :End (- here (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 60.0)) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
    (if low
      (Transformation|AddActorWorldOffset :DeltaLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (* DeltaSeconds 600.0)) :bSweep false :bTeleport false))))""")

# Drones fight only once Physis is inside their room (author, 2026-11-07): from the next room they used to chase
# her through the walls, where the stuck rule destroyed them. RoomMin/RoomMax is the room box the station scenario
# sets on each placed drone (unset, as in the Center, counts as always inside). While she is outside, the
# cooldown is held at 1.2 s, so a drone warns before its first attack when she comes in. DroneStuckCheck
# (center_overrides.py, station branch) only counts a drone as active while InRoom is set.
fn(D,'DroneThink',"""(fn DroneThink (DeltaSeconds)
  (CallFunction|DroneSeparate :DeltaSeconds DeltaSeconds)
  (CallFunction|DroneStuckCheck :DeltaSeconds DeltaSeconds)
  (Variables|Default|SetCooldown (- (Variables|Default|GetCooldown) DeltaSeconds))
  (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) DeltaSeconds))
  """+PHYSIS+"""    (:then
      (bind herspot (Transformation|GetActorLocation :self physis))
      (Variables|Default|SetInRoom (or (<= (.x (Variables|Default|GetRoomMax)) (.x (Variables|Default|GetRoomMin))) (and (and (> (.x herspot) (.x (Variables|Default|GetRoomMin))) (< (.x herspot) (.x (Variables|Default|GetRoomMax)))) (and (> (.y herspot) (.y (Variables|Default|GetRoomMin))) (< (.y herspot) (.y (Variables|Default|GetRoomMax)))))))
      (Variables|Default|SetBlocked false)
      (bind boxed (> (.x (Variables|Default|GetRoomMax)) (.x (Variables|Default|GetRoomMin))))
      (if (and (not (Variables|Default|GetInRoom)) (< (Variables|Default|GetCooldown) 1.2))
        (Variables|Default|SetCooldown 1.2))
      (bind gap (Transformation|GetDistanceTo :OtherActor physis))
      (bind boss (Variables|Default|GetBoss))
      (bind seen (Controller|LineOfSightTo :self (Game|GetPlayerController 0) :Other self))
      (if (and boss (and (> (.x (Transformation|GetActorLocation :self physis)) 13480.0) (< (.x (Transformation|GetActorLocation :self physis)) 16400.0)))
        (Class|BPPhysis|SetBossShown :self physis :BossShown (/ (Math|Conversions|ToFloat(Integer) (Variables|Default|GetHealth)) 30.0))
        (elif boss
          (Class|BPPhysis|SetBossShown :self physis :BossShown 0.0)))
      (if (and (and (< gap 1800.0) seen) (and (Variables|Default|GetInRoom) (not (or (Variables|Default|GetStatic) (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil))))))
        (Transformation|SetActorRotation :NewRotation (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation) :Target (+ (Transformation|GetActorLocation :self physis) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 30.0))) :bTeleportPhysics false)
        (bind fwd (Transformation|GetActorForwardVector))
        (bind ahead (select boxed (Math|Vector|Normalize (Math|Vector|MakeVector :X (.x fwd) :Y (.y fwd) :Z 0.0)) fwd))
        (bind step (* (+ (+ (* ahead (select (> gap (select boss 500.0 560.0)) 1.0 (select (< gap (select boss 300.0 340.0)) -1.0 0.0))) (* (Transformation|GetActorRightVector) (select (> (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 1.1)) 0.0) 0.75 -0.75))) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (+ (* 0.3 (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 3.0))) (select (> (.z (Transformation|GetActorLocation)) (select boss 260.0 165.0)) -0.9 (select (< (.z (Transformation|GetActorLocation)) (select boss 200.0 115.0)) 0.9 0.0))))) (* DeltaSeconds 430.0)))
        (bind (wallhit blocked) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* (Math|Vector|Normalize step) (select boss 240.0 120.0))) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (if (not blocked)
          (Transformation|AddActorWorldOffset :DeltaLocation step :bSweep false :bTeleport false)
          (else
            (Variables|Default|SetBlocked true)
            (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) 2.86))
            (bind flat (Math|Vector|Normalize (Math|Vector|MakeVector :X (.x step) :Y (.y step) :Z 0.0)))
            (bind across (Math|Vector|MakeVector :X (neg (.y flat)) :Y (.x flat) :Z 0.0))
            (bind side (* across (select (> (Math|Vector|DotProduct across (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation))) 0.0) 1.0 -1.0)))
            (bind (sidehit sideblocked) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* side (select boss 240.0 120.0))) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
            (if (not sideblocked)
              (Transformation|AddActorWorldOffset :DeltaLocation (* side (Math|Vector|VectorLength step)) :bSweep false :bTeleport false)
              (else
                (Transformation|AddActorWorldOffset :DeltaLocation (* side (* -1.0 (Math|Vector|VectorLength step))) :bSweep false :bTeleport false))))))
      (if (and (and (< gap 1800.0) (not seen)) (and (Variables|Default|GetInRoom) (not (or (Variables|Default|GetStatic) (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil))))))
        (bind toward0 (* (Math|Vector|Normalize (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation))) (* DeltaSeconds 300.0)))
        (bind toward (select boxed (Math|Vector|MakeVector :X (.x toward0) :Y (.y toward0) :Z 0.0) toward0))
        (bind (wallhit2 blocked2) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* (Math|Vector|Normalize toward) 120.0)) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (if (not blocked2)
          (Transformation|AddActorWorldOffset :DeltaLocation toward :bSweep false :bTeleport false)
          (else
            (Variables|Default|SetBlocked true)
            (bind flat2 (Math|Vector|Normalize (Math|Vector|MakeVector :X (.x toward) :Y (.y toward) :Z 0.0)))
            (bind side2 (* (Math|Vector|MakeVector :X (neg (.y flat2)) :Y (.x flat2) :Z 0.0) (select (> (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 0.7)) 0.0) 1.0 -1.0)))
            (bind (sidehit2 sideblocked2) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* side2 120.0)) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
            (if (not sideblocked2)
              (Transformation|AddActorWorldOffset :DeltaLocation (* side2 (* DeltaSeconds 300.0)) :bSweep false :bTeleport false)
              (else
                (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) 4.49))
                (Transformation|AddActorWorldOffset :DeltaLocation (* side2 (* DeltaSeconds -300.0)) :bSweep false :bTeleport false))))))
      (if (and (and (< (Variables|Default|GetCooldown) 0.6) (and (Variables|Default|GetInRoom) (not (or (Variables|Default|GetStatic) (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil)))))) (and (not (Variables|Default|GetWarned)) (and (< gap 1500.0) seen)))
        (Variables|Default|SetWarned true)
        """+at('S_SwordHeavy','(Transformation|GetActorLocation)',.9)+"""
        """+spawn('BP_Spark','(Transformation|GetActorLocation)')+""")
      (if (and (<= (Variables|Default|GetCooldown) 0.0) (and (Variables|Default|GetInRoom) (not (or (Variables|Default|GetStatic) (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil))))))
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
