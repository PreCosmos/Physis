import sys
sys.path.insert(0,'Tools')
src=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
exec(src.split("ANIM=")[0])
i=src.index("print('hud',call('write_graph_dsl'");b=src[i:src.index("comp(H)",i)]
b=b.replace("""(CallFunction|DrawCombat :SizeX SizeX :SizeY SizeY)""","""(CallFunction|DrawCombat :SizeX SizeX :SizeY SizeY)
          (CallFunction|DrawObjective :SizeX SizeX :SizeY SizeY :Goal (Class|BPPhysis|GetObjective :self physis) :BossHealth (Class|BPPhysis|GetBossShown :self physis))""")
b=b.replace("""(CallFunction|DrawTutorial :SizeX SizeX :SizeY SizeY)""","""(CallFunction|DrawTutorial :SizeX SizeX :SizeY SizeY))
          (if (Class|BPPhysis|GetLogOpen :self physis)
            (CallFunction|DrawLogbook :SizeX SizeX :SizeY SizeY :Data (Class|BPPhysis|GetLogData :self physis))""")
exec(b);comp(H)
