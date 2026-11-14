import time,subprocess,re
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
def st(t):
    o=run('aaa:pie_state'); m=re.search(r'flags.*',o); print(t,(m.group(0) if m else o[-200:])[:190].replace('\\\\','').replace('\\"',''),flush=True)
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:2640,0,110'); time.sleep(1); run('play:pie_shot'); time.sleep(2)
print(run('aaa:pie_scanat:AL Drone')[-40:]); print(run('aaa:pie_scanat:Reactor Fuse')[-40:])
print(run('aaa:pie_quest')[-120:])
run('play:pie_call:PhysisPause'); time.sleep(1); run('play:pie_shot'); time.sleep(2)
for p in (0,1,2):
    print(run('aaa:pie_page:%d'%p)[-40:]); time.sleep(.8); run('play:pie_shot'); time.sleep(2)
run('aaa:pie_page:0'); time.sleep(1.2); print(run('aaa:pie_voice')[-110:]); print(run('aaa:pie_page:3')[-40:]); run('play:pie_call:PhysisPause'); time.sleep(.4); run('aaa:pie_go:4800,0,110'); time.sleep(.3); print(run('aaa:pie_kill:1')[-40:]); time.sleep(.8); st('room1'); run('play:pie_call:PhysisPause'); time.sleep(.4); run('play:pie_call:PhysisSaveGame'); time.sleep(.8); st('saved')
run('play:pie_call:PhysisPause'); time.sleep(.6)
run('play:pie_call:PhysisLoadGame'); time.sleep(7); st('loaded'); print(run('aaa:pie_drones')[-90:])
