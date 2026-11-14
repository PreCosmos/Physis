import sys,re
sys.path.insert(0,'Tools')
cb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
exec(cb.split("call('add_object_variable'")[0])
def cut(a):
    i=cb.index(a); j=cb.index('"""',cb.index('(fn ',i)+4)
    k=cb.index('\n',j); return cb[i:k]
var(P,'FireReady','float')
NEWREADY='(and (not (Variables|Default|GetScanVisorOn)) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetFireReady)))'
FIRE='(Variables|Default|SetFireReady (+ (Utilities|Time|GetGameTimeinSeconds) 0.28))'
for name in ("fn(P,'PhysisFire',","fn(P,'PhysisFireDivine',"):
    src=cut(name).replace('%(ANIM,READY,ALIVE,','%(ANIM,NEWREADY,ALIVE,').replace('(CallFunction|PhysisShot :Damage','(Audio|PlaySound2D :Sound "/Game/Audio/S_Laser2.S_Laser2" :VolumeMultiplier 0.8 :PitchMultiplier (Math|Random|RandomFloatinRange :Min 1.25 :Max 1.45))\n      (CallFunction|PhysisShot :Damage')
    exec(src)
sw=cut("fn(P,'PhysisSwitchWeapon',\"\"\"(fn PhysisSwitchWeapon ()").replace('%(ANIM,READY,ALIVE))','%(ANIM,"(not (Variables|Default|GetScanVisorOn))",ALIVE))').replace('(Variables|Default|SetChainOpenAt 0.0)\n    (Variables|Default|SetGunEquipped','(Variables|Default|SetChainOpenAt 0.0)\n    (Animation|Montage|MontageStop :self anim :InBlendOutTime 0.1)\n    (Variables|Default|SetGunEquipped')
exec(sw)
lt=cut("fn(P,'PhysisLockTick',")
lt=lt.replace('''        (CallFunction|PhysisLockClear)
        (else''','''        (CallFunction|PhysisLockClear)
        (else
          (Class|CharacterMovementComponent|SetMaxWalkSpeed 390.0 (Variables|Character|GetCharacterMovement))''').replace('''    (:"Is Not Valid"
      (if''','''    (:"Is Not Valid"
      (Class|CharacterMovementComponent|SetMaxWalkSpeed 750.0 (Variables|Character|GetCharacterMovement))
      (if''')
exec(lt)
comp(P)
exec(open(__file__.replace('gunfix.py','quiet.py')).read().split("exec(cb.split")[1].split("\n",1)[1])

fn(P,'PhysisSprintOn',"""(fn PhysisSprintOn ()
  (Class|CharacterMovementComponent|SetMaxWalkSpeed 750.0 (Variables|Character|GetCharacterMovement)))""")
fn(P,'PhysisSprintOff',"""(fn PhysisSprintOff ()
  (Class|CharacterMovementComponent|SetMaxWalkSpeed 750.0 (Variables|Character|GetCharacterMovement)))""")
comp(P)
# S_GunShot
