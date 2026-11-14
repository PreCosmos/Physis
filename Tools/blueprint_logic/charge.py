# Charged sidearm shot: hold fire ~0.9 s, release to spend 5 ammo on a 5-damage blast.
import json,sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
var(P,'ChargeStart','float');var(P,'Charging','bool')
call('add_object_variable',{'blueprint':{'refPath':P},'name':'ChargeOrb','object_class':{'refPath':'/Script/Engine.Actor'}},True)
shell(P,'PhysisChargeReady');shell(P,'PhysisOrbClear');shell(P,'PhysisFireRelease')
NOW='(Utilities|Time|GetGameTimeinSeconds)'
fn(P,'PhysisChargeReady',"""(fn PhysisChargeReady ()
  (if (and (Variables|Default|GetCharging) (>= (- %s (Variables|Default|GetChargeStart)) 0.85))
    (Audio|PlaySound2D :Sound "/Game/Audio/S_ChargeReady.S_ChargeReady" :VolumeMultiplier 0.85)))"""%NOW)
fn(P,'PhysisOrbClear',"""(fn PhysisOrbClear ()
  (Utilities|IsValid (Variables|Default|GetChargeOrb)
    (:"Is Valid" (Actor|DestroyActor :self (Variables|Default|GetChargeOrb)))
    (:"Is Not Valid")))""")
fn(P,'PhysisFireRelease',"""(fn PhysisFireRelease ()
  (if (Variables|Default|GetCharging)
    (Variables|Default|SetCharging false)
    (CallFunction|PhysisOrbClear)
    (if (and (Variables|Default|GetGunEquipped) (>= (- %s (Variables|Default|GetChargeStart)) 0.85))
      (if (>= (Variables|Default|GetGunAmmo) 5)
        (Variables|Default|SetGunAmmo (- (Variables|Default|GetGunAmmo) 5))
        (Animation|Montage|MontagePlay :self (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)) :MontageToPlay "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Pistol_Fire.AM_Physis_Pistol_Fire" :InPlayRate 0.8)
        (Audio|PlaySound2D :Sound "/Game/Audio/S_ChargedShot.S_ChargedShot" :VolumeMultiplier 1.0)
        (Variables|Default|SetShakeAmount 7.0)
        (Variables|Default|SetFireReady (+ %s 0.5))
        (CallFunction|PhysisShot :Damage 5)
        (else
          (CallFunction|PhysisSay :Message "A charged shot needs 5 ammo.   Reload: R / |DD|"))))))"""%(NOW,NOW))
comp(P)
# Wire the fire button's release to PhysisFireRelease (once).
G={'refPath':P+':EventGraph'}
def j(tool,args):
    r=call(tool,args)
    return json.loads(r)['returnValue'] if r else None
attack=j('find_nodes',{'graph':G,'title':'IA_Attack'})[0]
info=j('get_node_infos',{'nodes':[attack]})[0]
done=next(p for p in info['output_pins'] if p['name']=='Completed')
if not done.get('connected_pins'):
    release=j('create_node',{'graph':G,'type_id':'CallFunction|PhysisFireRelease','pos':{'x':0,'y':7400}})
    entry=next(p for p in j('get_node_infos',{'nodes':[release]})[0]['input_pins'] if p['name']=='execute')
    call('connect_pins',{'output_pin':done['pin_id'],'input_pin':entry['pin_id']})
    print('wired release')
else:
    print('release already wired')
comp(P)
