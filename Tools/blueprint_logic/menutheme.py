import sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
M=B+'BP_MenuHUD.BP_MenuHUD'
print(call('write_graph_dsl',{'graph':{'refPath':M+':EventGraph'},'code':'''(event EventBeginPlay
  (Audio|SpawnSound2D :Sound "/Game/Audio/S_Music_MainTheme.S_Music_MainTheme" :VolumeMultiplier 0.7))'''}))
comp(M)
