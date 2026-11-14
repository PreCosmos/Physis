import sys
sys.path.insert(0,'Tools')
hf=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/hudfont.py').read()
exec(hf[:hf.index("var(H,'LineY','float')")])
m=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/menu.py').read()
i=hf.index("M=B+'BP_MenuHUD.BP_MenuHUD'")
exec(hf[i:].replace("hit('Enter','SpaceBar'","hit('E','Enter','SpaceBar'") if False else "")
M=B+'BP_MenuHUD.BP_MenuHUD'
code=m[m.index('def hit('):m.index("print('events'")].replace("len(label)*7.4","len(label)*9.2").replace("(* u 210.0)","(* u 300.0)").replace("(* u 420.0)","(* u 600.0)").replace(":ScreenH (* u 64.0)",":ScreenH (* u 72.0)").replace("(y+13)","(y+8)").replace("'(* u 2.1)'","'(* u 2.2)'").replace("row('New Game',0,700)","row('New Game',0,680)").replace("row('Exit Game',1,780)","row('Exit Game',1,790)").replace("hit('Enter','SpaceBar'","hit('E','Enter','SpaceBar'")
exec(code);comp(M)
