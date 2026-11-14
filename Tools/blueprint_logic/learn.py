import sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
fn(P,'PhysisLearn',"""(fn PhysisLearn ()
  (if (< (Variables|Default|GetSkillLevel) 6)
    (Variables|Default|SetSkillLevel (+ (Variables|Default|GetSkillLevel) 3))
    (if (< (Variables|Default|GetSkillLevel) 6)
      (CallFunction|PhysisSay :Message "New techniques: Rising Cut, Crescent Step, Falling Moon. Combos are 3 strikes longer.")
      (else
        (CallFunction|PhysisSay :Message "New techniques: Thousand Petals, Severing Wind, Final Bloom. Combos are 3 strikes longer.")))))""")
comp(P)
