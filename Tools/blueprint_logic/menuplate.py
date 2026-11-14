import sys
sys.path.insert(0,'Tools')
hf=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/hudfont.py').read()
exec(hf[:hf.index("var(H,'LineY','float')")])
M=B+'BP_MenuHUD.BP_MenuHUD'
fn(M,'MenuTextPlate',"""(fn MenuTextPlate (Text X Y Scale)
  (bind (w h) (HUD|GetTextSize :Text Text :Font "%s" :Scale Scale))
  (if (> w 0.5)
    (HUD|DrawRect :RectColor "(R=0.01,G=0.02,B=0.04,A=0.58)" :ScreenX (- X (* h 0.24)) :ScreenY (- Y (* h 0.05)) :ScreenW (+ w (* h 0.48)) :ScreenH (* h 1.08))))"""%FONTPATH)
comp(M)
t=call('read_graph_dsl',{'graph':{'refPath':M+':DrawMenu'}},True) or ''
print('menu uses MenuTextPlate', 'MenuTextPlate' in t, 'has E', '\\"E\\"' in t or '"E"' in t)
