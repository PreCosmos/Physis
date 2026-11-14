# Runs last in the logic rebuild: timer beside the vitals panel, aligned intro skip prompt.
import sys
sys.path.insert(0,'Tools')
hf=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/hudfont.py').read()
exec(hf[:hf.index("var(H,'LineY','float')")])
f2=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/feat2.py').read()
exec(f2.split('\n')[4])
i=f2.index("fn(H,'DrawTimer'"); j=f2.index('(:CastFailed)))""")',i)+len('(:CastFailed)))""")')
timer=f2[i:j]
# The countdown gets its own framed panel under the vitals: small label left, large time right.
x=timer.index('      (if (not (Class|BPPhysis|GetLevelDone :self physis))'); y=timer.index('      (if (< (Utilities|Time|GetRealTimeSeconds)',x)
panel="""      (if (not (Class|BPPhysis|GetLevelDone :self physis))
        (bind urgent (< left 120.0))
        """+tex('T_UI_Panel','(* u 22.0)','(* u 172.0)','(* u 604.0)','(* u 80.0)','(Utilities|Struct|MakeLinearColor :R 1.0 :G (select urgent 0.55 0.95) :B (select urgent 0.5 0.85) :A 0.95)')+"""
        """+text('"EMERGENCY DESTRUCTION"','(* u 48.0)','(* u 190.0)','(* u 0.8)','"(R=0.62,G=0.95,B=0.88,A=1.0)"')+"""
        """+text('"SEQUENCE"','(* u 48.0)','(* u 216.0)','(* u 0.8)','"(R=0.62,G=0.95,B=0.88,A=1.0)"')+"""
        (bind (tw th) (HUD|GetTextSize :Text label :Font "/Game/UI/F_Physis.F_Physis" :Scale (* (* u 1.9) 0.35)))
        """+text('label','(- (* u 596.0) tw)','(- (* u 212.0) (/ th 2.0))','(* u 1.9)','(Utilities|Struct|MakeLinearColor :R 1.0 :G (select urgent 0.32 0.84) :B (select urgent 0.26 0.46) :A 1.0)')+""")
"""
timer=timer[:x]+panel+timer[y:]
# Keep the graphics fidelity stage in step with progress (also after loading a save).
t=timer.index('    (:then\n')+len('    (:then\n')
timer=timer[:t]+'      (Class|BPPhysis|PhysisFidelity :self physis)\n'+timer[t:]
# Second health bar (Life Augmentation): a slimmer bar under the first, filled by health above 10.
bar2="""      (if (> (Class|BPPhysis|GetMaxHealth :self physis) 10.0)
        (bind extra (- (Class|BPPhysis|GetPhysisHealth :self physis) 10.0))
        (HUD|DrawRect :RectColor "(R=0.05,G=0.02,B=0.02,A=0.75)" :ScreenX (* u 106.0) :ScreenY (* u 84.0) :ScreenW (* u 440.0) :ScreenH (* u 14.0))
        (HUD|DrawTexture :Texture "/Game/UI/T_UI_BarHealth.T_UI_BarHealth" :ScreenX (* u 106.0) :ScreenY (* u 84.0) :ScreenW (* u (* 44.0 (select (< extra 0.0) 0.0 extra))) :ScreenH (* u 14.0) :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor "(R=1.0,G=0.86,B=0.55,A=1.0)"))
"""
t2=timer.index('      (Class|BPPhysis|PhysisFidelity :self physis)\n')+len('      (Class|BPPhysis|PhysisFidelity :self physis)\n')
timer=timer[:t2]+bar2+timer[t2:]
exec(timer)
cb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
i=cb.index("fn(H,'DrawCinema'");cin=cb[i:cb.index("print('hud',call",i)]
old_skip=cin[cin.index('  """+text(\'"Skip:'):cin.index('""")""")')]
new_skip='''  (bind (sw sh) (HUD|GetTextSize :Text "Skip:  E  /" :Font "%s" :Scale (* (* u 1.3) 0.35)))
  """+text('"Skip:  E  /"','(- SizeX (+ (* u 104.0) sw))','(- SizeY (+ (* u 52.0) (/ sh 2.0)))','(* u 1.3)')+"""
  """+tex('T_Pad_X','(- SizeX (* u 92.0))','(- SizeY (* u 78.0))','(* u 52.0)','(* u 52.0)')+'''%FONTPATH
cin=cin.replace(old_skip,new_skip)
k=cin.rindex('""")""")')
cin=cin[:k]+'"""\n  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))\n    (:then (Class|BPPhysis|PhysisFidelity :self physis))\n    (:CastFailed))\n  """+'+cin[k:]
print(cin[-700:])
exec(cin)
comp(H)
