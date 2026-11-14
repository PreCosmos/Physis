import sys
sys.path.insert(0,'Tools')
hf=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/hudfont.py').read()
exec(hf[:hf.index("var(H,'LineY','float')")])
cb=src
i=cb.index("fn(H,'DrawCinema'");cin=cb[i:cb.index("print('hud',call",i)]
cin=cin.replace("""'"Skip:   E  /"','(- SizeX (* u 280.0))','(- SizeY (* u 76.0))','(* u 1.6)'""","""'"Skip:  E  /"','(- SizeX (* u 210.0))','(- SizeY (* u 72.0))','(* u 1.3)'""")
cin=cin.replace("""'(- SizeX (* u 110.0))','(- SizeY (* u 84.0))','(* u 52.0)','(* u 52.0)'""","""'(- SizeX (* u 92.0))','(- SizeY (* u 80.0))','(* u 56.0)','(* u 56.0)'""")
exec(cin);comp(H)
