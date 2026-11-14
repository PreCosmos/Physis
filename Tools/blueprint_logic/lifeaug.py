# Life Augmentation: pickup kind 4 grants ,lifeaug, and a second bar of health (max 20).
import sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
var(P,'MaxHealth','float')
MAX='(select (> (Variables|Default|GetMaxHealth) 0.0) (Variables|Default|GetMaxHealth) 10.0)'
sb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/scenario_bp.py').read()
i=sb.index("fn(P,'PhysisCollect',\"\"\"(fn PhysisCollect"); src=sb[i:sb.index('""")',i)+4]
old='(Variables|Default|SetPhysisHealth (select (> (Variables|Default|GetPhysisHealth) 7.0) 10.0 (+ (Variables|Default|GetPhysisHealth) 3.0)))'
assert old in src
src=src.replace(old,'(Variables|Default|SetPhysisHealth (select (> (Variables|Default|GetPhysisHealth) (- %s 3.0)) %s (+ (Variables|Default|GetPhysisHealth) 3.0)))'%(MAX,MAX))
# The switch node only has pins 0-3, so the augmentation (kind 4) is handled before it.
src=src.replace('(fn PhysisCollect (Kind)\n  (switch int Kind','''(fn PhysisCollect (Kind)
  (if (== Kind 4)
    (CallFunction|PhysisGive :Token ",lifeaug,")
    (Variables|Default|SetMaxHealth 20.0)
    (Variables|Default|SetPhysisHealth 20.0)
    (Audio|PlaySound2D :Sound "/Game/Audio/S_ChargeReady.S_ChargeReady")
    (CallFunction|PhysisSay :Message "Life Augmentation absorbed.~Physis gains a second bar of health.")
    (else
  (switch int Kind''',1)
end=src.rindex('"""')
src=src[:end]+'))'+src[end:]
assert '(== Kind 4)' in src
exec(src)
fe=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/feat.py').read()
i=fe.index("fn(P,'PhysisRestart',"); src=fe[i:fe.index('""")',i)+4]
assert '(Variables|Default|SetPhysisHealth 10.0)' in src
exec(src.replace('(Variables|Default|SetPhysisHealth 10.0)','(Variables|Default|SetPhysisHealth %s)'%MAX))
comp(P)
