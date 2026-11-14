import sys
sys.path.insert(0,'Tools')
src=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
exec(src.split("ANIM=")[0])
exec('def tex'+src.split('def tex',1)[1].split("TEAL=")[0])
M=B+'BP_MenuHUD.BP_MenuHUD'
var(M,'Selected','int')
shell(M,'DrawMenu',[('SizeX','float'),('SizeY','float')])
def hit(*keys):
    out='(Game|Player|WasInputKeyJustPressed :self pc :Key "%s")'%keys[0]
    for k in keys[1:]:
        out='(or %s (Game|Player|WasInputKeyJustPressed :self pc :Key "%s"))'%(out,k)
    return out
GOLD='"(R=1.0,G=0.82,B=0.42,A=1.0)"';DIM='"(R=0.62,G=0.66,B=0.72,A=1.0)"'
def row(label,index,y):
    on='(== (Variables|Default|GetSelected) %d)'%index
    return """(HUD|DrawRect :RectColor (Utilities|Struct|MakeLinearColor :R 1.0 :G 0.8 :B 0.4 :A (select %s 0.14 0.0)) :ScreenX (- (/ SizeX 2.0) (* u 210.0)) :ScreenY (* u %s) :ScreenW (* u 420.0) :ScreenH (* u 64.0))
  """%(on,y)+text('"%s"'%label,'(- (/ SizeX 2.0) (* u %s))'%(len(label)*7.4),'(* u %s)'%(y+13),'(* u 2.1)','(Utilities|Struct|MakeLinearColor :R (select %s 1.0 0.62) :G (select %s 0.82 0.66) :B (select %s 0.42 0.72) :A 1.0)'%(on,on,on))
fn(M,'DrawMenu',"""(fn DrawMenu (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind pc (Game|GetPlayerController 0))
  (bind wide (* u 880.0))
  (bind sky (select (> SizeX (* SizeY 2.0)) SizeX (* SizeY 2.0)))
  (HUD|DrawTexture :Texture "/Game/Cinematics/T_Sky_Space.T_Sky_Space" :ScreenX (- (/ SizeX 2.0) (/ sky 2.0)) :ScreenY (- (/ SizeY 2.0) (/ sky 4.0)) :ScreenW sky :ScreenH (/ sky 2.0) :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor "(R=0.75,G=0.75,B=0.8,A=1.0)")
  (HUD|DrawRect :RectColor "(R=0.0,G=0.01,B=0.03,A=0.45)" :ScreenX 0.0 :ScreenY 0.0 :ScreenW SizeX :ScreenH SizeY)
  """+tex('T_UI_Title','(- (/ SizeX 2.0) (/ wide 2.0))','(* u 90.0)','wide','(* wide 0.625)')+"""
  """+row('New Game',0,700)+"""
  """+row('Exit Game',1,780)+"""
  (if """+hit('Up','W','Gamepad_DPad_Up','Gamepad_LeftStick_Up')+"""
    (Variables|Default|SetSelected 0))
  (if """+hit('Down','S','Gamepad_DPad_Down','Gamepad_LeftStick_Down')+"""
    (Variables|Default|SetSelected 1))
  (if """+hit('Enter','SpaceBar','Gamepad_FaceButton_Bottom')+"""
    (if (== (Variables|Default|GetSelected) 0)
      (Game|OpenLevel(byName) :LevelName "L_BattleStation")
      (else
        (Game|QuitGame)))))""")
print('events',call('write_graph_dsl',{'graph':{'refPath':M+':EventGraph'},'code':'''(event EventBeginPlay
  (Class|PlayerController|SetShowMouseCursor :self (Game|GetPlayerController 0) :bShowMouseCursor false))

(event EventReceiveDrawHUD (SizeX SizeY)
  (CallFunction|DrawMenu :SizeX SizeX :SizeY SizeY))'''}))
comp(M)
