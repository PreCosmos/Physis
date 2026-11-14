import sys,re
sys.path.insert(0,'Tools')
src=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
def cut(a,b):
    i=src.index(a); return src[i:src.index(b,i)]
exec(src.split("call('add_object_variable'")[0])
exec('def tex'+src.split('def tex',1)[1].split("TEAL=")[0])
SHIPS=re.search(r'^SHIPS=.*$',src,re.M).group(0) if re.search(r'^SHIPS=',src,re.M) else None
exec(SHIPS) if SHIPS else None
A='/Game/Audio/'
def snd(n,vol=1.0): return '(Audio|PlaySound2D :Sound "%s%s.%s" :VolumeMultiplier %s)'%(A,n,n,vol)
def at(n,where,vol=1.0): return '(Audio|PlaySoundatLocation :Sound "%s%s.%s" :Location %s :VolumeMultiplier %s)'%(A,n,n,where,vol)
def spawn(bp,where,rot='(Math|Rotator|MakeRotator :Yaw 0.0)'):
    return '(Game|SpawnActorfromClass :Class "%s%s.%s_C" :SpawnTransform (Math|Transform|MakeTransform :Location %s :Rotation %s :Scale (Math|Vector|MakeVector :X 1.0 :Y 1.0 :Z 1.0)) :CollisionHandlingOverride "AlwaysSpawn")'%(B,bp,bp,where,rot)
UP='(+ (Transformation|GetActorLocation) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z %s))'
# Effect actors: name, size range, life, whether they fade, facing, companion smoke.
FX=(('BP_Burst',30.0,120.0,2.6,'BP_Smoke',True),('BP_DroneBurst',3.6,4.8,1.5,'BP_DroneSmoke',True),('BP_Smoke',40.0,140.0,5.0,None,True),('BP_DroneSmoke',4.5,6.0,3.0,None,True),('BP_Spark',1.1,1.7,.32,None,True),('BP_SlashFX',1.0,1.0,.17,None,False))
for name,low,high,life,smoke,face in FX:
    X=B+name+'.'+name
    extra=spawn(smoke,'(Transformation|GetActorLocation)') if smoke else ''
    grow=' (bind grown (* (Variables|Default|GetSize) (+ 0.4 (* 0.6 norm))))\n  (Transformation|SetActorScale3D :NewScale3D (Math|Vector|MakeVector :X grown :Y grown :Z grown))\n  (Transformation|SetActorRotation :NewRotation (Math|Rotator|MakeRotfromZ :Z (- (Camera|GetCameraLocation :self (Game|GetPlayerCameraManager 0)) (Transformation|GetActorLocation))) :bTeleportPhysics false)' if face else ''
    print(name,call('write_graph_dsl',{'graph':{'refPath':X+':EventGraph'},'code':"""(event EventBeginPlay
  (Variables|Default|SetSize (Math|Random|RandomFloatinRange :Min %s :Max %s))
  %s)

(event EventTick (DeltaSeconds)
  (Variables|Default|SetAge (+ (Variables|Default|GetAge) DeltaSeconds))
  (bind norm (/ (Variables|Default|GetAge) %s))
  %s
  (Rendering|Material|SetCustomPrimitiveDataFloat :self (Variables|Default|GetShape) :DataIndex 0 :Value norm)
  (Rendering|Material|SetCustomPrimitiveDataFloat :self (Variables|Default|GetShape) :DataIndex 1 :Value (- 1.0 (* norm norm)))
  (if (>= norm 1.0)
    (Actor|DestroyActor)))"""%(low,high,extra,life,grow)}))
    comp(X)
R=B+'BP_BattleDirector.BP_BattleDirector'
AIM=re.search(r"^AIM='(.*)'$",src,re.M).group(1)
block=cut("print('director'","comp(R)")
block=block.replace('(Math|Random|RandomFloatinRange :Min 0.0 :Max 1.0) 0.8)','(Math|Random|RandomFloatinRange :Min 0.0 :Max 1.0) 0.975)')
sound='(switch int (Math|Random|RandomIntegerinRange :Min 0 :Max 2) (:0 '+snd('S_Explosion1','(Math|Random|RandomFloatinRange :Min 0.2 :Max 0.55)')+') (:1 '+snd('S_Explosion2','(Math|Random|RandomFloatinRange :Min 0.2 :Max 0.55)')+') (:Default '+snd('S_Explosion3','(Math|Random|RandomFloatinRange :Min 0.2 :Max 0.55)')+'))'
i=block.index('(Game|SpawnActorfromClass :Class "/Game/Characters/Physis/Blueprints/BP_Burst.BP_Burst_C"');d=0;j=i
while True:
    d+=(block[j]=='(')-(block[j]==')');j+=1
    if d==0:break
block=block[:j]+'\n      '+sound+block[j:]
exec(block);comp(R)
var(P,'SkillLevel','int');shell(P,'PhysisLearn');var(P,'ParryUntil','float');var(P,'ShakeAmount','float');var(D,'Warned','bool')
call('add_object_variable',{'blueprint':{'refPath':P},'name':'MusicComp','object_class':{'refPath':'/Script/Engine.AudioComponent'}},True)
shell(P,'PhysisSlow',[('Rate','float'),('Seconds','float')]);shell(P,'PhysisSlowEnd');shell(P,'PhysisFeelTick',[('DeltaSeconds','float')]);shell(P,'PhysisMusic')
fn(P,'PhysisSlow',"""(fn PhysisSlow (Rate Seconds)
  (Utilities|Time|SetGlobalTimeDilation :TimeDilation Rate)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisSlowEnd" :Time (* Rate Seconds) :bLooping false))""")
fn(P,'PhysisSlowEnd',"""(fn PhysisSlowEnd ()
  (Utilities|Time|SetGlobalTimeDilation :TimeDilation 1.0))""")
fn(P,'PhysisFeelTick',"""(fn PhysisFeelTick (DeltaSeconds)
  (bind left (- (Variables|Default|GetShakeAmount) (* DeltaSeconds 26.0)))
  (Variables|Default|SetShakeAmount (select (< left 0.0) 0.0 left))
  (bind amount (Variables|Default|GetShakeAmount))
  (Transformation|SetRelativeLocation :self (Variables|Default|GetFollowCamera) :NewLocation (Math|Vector|MakeVector :X 0.0 :Y (Math|Random|RandomFloatinRange :Min (* amount -1.0) :Max amount) :Z (Math|Random|RandomFloatinRange :Min (* amount -1.0) :Max amount)) :bSweep false :bTeleport false))""")
print('tick',call('write_graph_dsl',{'graph':{'refPath':P+':EventGraph'},'code':"""(event EventTick (DeltaSeconds)
  (CallFunction|PhysisVisorTick :DeltaSeconds DeltaSeconds)
  (CallFunction|PhysisLockTick :DeltaSeconds DeltaSeconds)
  (CallFunction|PhysisFeelTick :DeltaSeconds DeltaSeconds))"""}))
COMBAT='(Variables|Default|SetMusicComp (Audio|SpawnSound2D :Sound "%sS_Music_Combat.S_Music_Combat" :VolumeMultiplier 0.8 :FadeInTime 2.0))'%A if False else '(Variables|Default|SetMusicComp (Audio|SpawnSound2D :Sound "%sS_Music_Combat.S_Music_Combat" :VolumeMultiplier 0.8))'%A
fn(P,'PhysisMusic',"""(fn PhysisMusic ()
  (Utilities|IsValid (Variables|Default|GetMusicComp)
    (:"Is Valid"
      (Class|AudioComponent|SetVolumeMultiplier :self (Variables|Default|GetMusicComp) :VolumeMultiplier 0.0)
      %s)
    (:"Is Not Valid"
      %s)))"""%(COMBAT,COMBAT))
exec(cut("fn(P,'PhysisCinemaCleanup'","fn(P,'PhysisCinemaStart'").replace('(fn PhysisCinemaCleanup ()','(fn PhysisCinemaCleanup ()\n  (CallFunction|PhysisMusic)\n  (for hull (Actor|GetAllActorswithTag :Tag "CineOnly")\n    (Actor|DestroyActor :self hull))'))
exec(cut("fn(P,'PhysisCinemaStart'","fn(P,'PhysisCinemaEnd'").replace('(Sequencer|Player|Play','(Variables|Default|SetMusicComp (Audio|SpawnSound2D :Sound "%sS_Music_Theme.S_Music_Theme" :VolumeMultiplier 0.6))\n      (Sequencer|Player|Play'%A,1))
# Faster openers, a held heavy finisher: the rate changes give the string its rhythm.
RATES=(1.75,1.5,1.15,1.7,1.95,1.25,1.8,2.0,1.1)
def chain(names,damage):
    out=[]
    for i,n in enumerate(names):
        r=RATES[i]
        out.append('(:%d (CallFunction|PhysisSwung :Length (* %s %s) :Damage %d))'%(i,play(n,r),round(1.4/r,3),damage+(1 if i in(2,5,8) else 0)))
    return ' '.join(out)
exec(cut("fn(P,'PhysisSwung'","fn(P,'PhysisStrikeNow'").replace('(>= following 9)','(>= following (+ 3 (Variables|Default|GetSkillLevel)))').replace('(fn PhysisSwung (Length Damage)','(fn PhysisSwung (Length Damage)\n  (Audio|PlaySound2D :Sound "/Game/Audio/S_SwordSwing1.S_SwordSwing1" :VolumeMultiplier 0.7 :PitchMultiplier (Math|Random|RandomFloatinRange :Min 0.8 :Max 1.25))'))
fn(P,'PhysisStrikeNow',"""(fn PhysisStrikeNow ()
  (bind amount (Variables|Default|GetPendingDamage))
  """+spawn('BP_SlashFX',UP%'100.0','(Math|Rotator|CombineRotators :A (Math|Rotator|MakeRotator :Roll (Math|Random|RandomFloatinRange :Min -38.0 :Max 38.0) :Pitch 0.0 :Yaw 0.0) :B (Transformation|GetActorRotation))')+"""
  (for found """+DRONES+"""
    (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found)
      (:then
        (if (and (< (Transformation|GetDistanceTo :OtherActor drone) 300.0) (> (Transformation|GetDotProductTo :OtherActor drone) 0.2))
          """+at('S_SwordHit1','(Transformation|GetActorLocation :self drone)')+"""
          """+spawn('BP_Spark','(Transformation|GetActorLocation :self drone)')+"""
          (Variables|Default|SetShakeAmount (+ 2.5 (* amount 1.5)))
          (CallFunction|PhysisSlow :Rate 0.08 :Seconds (+ 0.05 (* amount 0.025)))
          (Class|BPTrainingDrone|TakeHit :self drone :Amount amount)))
      (:CastFailed))))""")
exec(cut("fn(P,'PhysisAttack'","fn(P,'PhysisDodge'"))
exec(cut("fn(P,'PhysisBlock'","fn(P,'PhysisHurt'").replace('(if (and %s %s)','(if (and (and %s (not (Variables|Default|GetScanVisorOn))) (> (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetBlockUntil)))').replace('%(ANIM,READY,ALIVE,play','%(ANIM,ALIVE,play').replace("1.1))))","0.7))\n    (Variables|Default|SetParryUntil (+ (Utilities|Time|GetGameTimeinSeconds) 0.3))))"))
hurt=cut("fn(P,'PhysisHurt'","fn(P,'PhysisRestart'")
PARRY="""(if (< now (Variables|Default|GetParryUntil))
        """+snd('S_Parry',1.0)+"""
        """+spawn('BP_Spark',UP%'120.0')+"""
        (Variables|Default|SetShakeAmount 7.0)
        (Variables|Default|SetSafeUntil (+ now 1.2))
        (CallFunction|PhysisSlow :Rate 0.1 :Seconds 0.32)
        (CallFunction|PhysisSwung :Length (* """+play('Stab',1.9)+""" 0.737) :Damage 3)
        (else
          """+snd('S_Block',.8)+"""
          %s
          (Variables|Default|SetShakeAmount 3.0)
          (Variables|Default|SetSafeUntil (+ now 0.8))))"""
hurt=hurt.replace("""      %s
      (Variables|Default|SetSafeUntil (+ now 0.8))""","""      PARRYHERE""")
hurt=hurt.replace("""(Variables|Default|SetPhysisHealth (- (Variables|Default|GetPhysisHealth) 1.0))""","""(Variables|Default|SetPhysisHealth (- (Variables|Default|GetPhysisHealth) 1.0))
        (Variables|Default|SetShakeAmount 5.0)
        """+snd('S_SwordHit2',.9).replace('"','\\"') if False else """(Variables|Default|SetPhysisHealth (- (Variables|Default|GetPhysisHealth) 1.0))
        (Variables|Default|SetShakeAmount 5.0)""")
hurt=hurt.replace('PARRYHERE',PARRY%play('Impact')).replace("%(ANIM,ALIVE,play('Impact'),play('Dead',1.0)","%(ANIM,ALIVE,play('Dead',1.0)")
exec(hurt)
print('hurt done')
comp(P)
fn(P,'PhysisLearn',"""(fn PhysisLearn ()
  (if (< (Variables|Default|GetSkillLevel) 6)
    (Variables|Default|SetSkillLevel (+ (Variables|Default|GetSkillLevel) 1))
    (switch int (- (Variables|Default|GetSkillLevel) 1)
      (:0 (CallFunction|PhysisSay :Message "New technique: Rising Cut. Combos are one strike longer.")) (:1 (CallFunction|PhysisSay :Message "New technique: Crescent Step. Combos are one strike longer.")) (:2 (CallFunction|PhysisSay :Message "New technique: Falling Moon. Combos are one strike longer.")) (:3 (CallFunction|PhysisSay :Message "New technique: Thousand Petals. Combos are one strike longer.")) (:4 (CallFunction|PhysisSay :Message "New technique: Severing Wind. Combos are one strike longer.")) (:5 (CallFunction|PhysisSay :Message "New technique: Final Bloom. Combos are one strike longer."))
      (:Default))))""")
comp(P)
fn(D,'TakeHit',"""(fn TakeHit (Amount)
  (Variables|Default|SetHealth (- (Variables|Default|GetHealth) Amount))
  (if (<= (Variables|Default|GetHealth) 0)
    """+at('S_DroneExplosion','(Transformation|GetActorLocation)')+"""
    """+spawn('BP_DroneBurst','(Transformation|GetActorLocation)')+"""
    (for tag (Actor|GetAttachedActors)
      (Actor|DestroyActor :self tag))
    (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
      (:then
        (Class|BPPhysis|PhysisSlow :self physis :Rate 0.22 :Seconds 0.55)
        (Class|BPPhysis|PhysisLearn :self physis)
        (Actor|DestroyActor))
      (:CastFailed
        (Actor|DestroyActor)))))""")
fn(D,'DroneThink',"""(fn DroneThink (DeltaSeconds)
  (Variables|Default|SetCooldown (- (Variables|Default|GetCooldown) DeltaSeconds))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (if (and (< (Variables|Default|GetCooldown) 0.6) (and (not (Variables|Default|GetWarned)) (< (Transformation|GetDistanceTo :OtherActor physis) 260.0)))
        (Variables|Default|SetWarned true)
        """+at('S_SwordHeavy','(Transformation|GetActorLocation)',1.0)+"""
        """+spawn('BP_Spark','(Transformation|GetActorLocation)')+""")
      (if (<= (Variables|Default|GetCooldown) 0.0)
        (Variables|Default|SetCooldown 3.0)
        (Variables|Default|SetWarned false)
        (if (< (Transformation|GetDistanceTo :OtherActor physis) 230.0)
          (Class|BPPhysis|PhysisHurt :self physis :FromAhead (> (Transformation|GetDotProductTo :self physis :OtherActor self) 0.0)))))
    (:CastFailed)))""")
comp(D)
M=B+'BP_MenuHUD.BP_MenuHUD'
print('menu',call('write_graph_dsl',{'graph':{'refPath':M+':EventGraph'},'code':'''(event EventBeginPlay
  (Audio|SpawnSound2D :Sound "/Game/Audio/S_Music_MainTheme.S_Music_MainTheme" :VolumeMultiplier 0.7))'''}))
comp(M)
fn(P,'PhysisSprintOff',"""(fn PhysisSprintOff ()
  (Class|CharacterMovementComponent|SetMaxWalkSpeed 1000.0 (Variables|Character|GetCharacterMovement)))""")
comp(P)
