# Charge orb behaviour: grows over the 0.9 s charge, pulses, flickers fast and lights up when full.
import json,sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
O=B+'BP_ChargeOrb.BP_ChargeOrb'
var(O,'Age','float')
print('orb',call('write_graph_dsl',{'graph':{'refPath':O+':EventGraph'},'code':'''(event EventTick (DeltaSeconds)
  (Variables|Default|SetAge (+ (Variables|Default|GetAge) DeltaSeconds))
  (bind raw (/ (Variables|Default|GetAge) 0.9))
  (bind charge (select (> raw 1.0) 1.0 raw))
  (bind pulse (+ 1.0 (* (select (>= raw 1.0) 0.18 0.1) (Math|Trig|Sin(Radians) (* (Variables|Default|GetAge) (select (>= raw 1.0) 34.0 15.0))))))
  (bind size (* (+ 0.03 (* 0.08 charge)) pulse))
  (Transformation|SetActorScale3D :NewScale3D (Math|Vector|MakeVector :X size :Y size :Z size))
  (Rendering|Material|SetCustomPrimitiveDataFloat :self (Variables|Default|GetShape) :DataIndex 0 :Value charge)
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetGlow) :NewIntensity (* 2600.0 (* charge pulse))))'''}))
comp(O)
