import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(17.5); run('play:pie_shot'); time.sleep(5); run('play:pie_shot'); time.sleep(2)
run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:1800,-500,110'); time.sleep(.4)
w=subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py','aaa:pie_look:-2,-90'],capture_output=True,text=True); time.sleep(2.5); run('play:pie_shot'); time.sleep(1.5)
print(run('aaa:pie_time:300')[-50:])
run('aaa:pie_go:18050,0,110'); time.sleep(.6); run('play:pie_call:PhysisInteract'); time.sleep(1.5); run('play:pie_shot'); time.sleep(1)
print(run('aaa:pie_ach')[-110:])
time.sleep(6.5); run('play:pie_shot'); time.sleep(1); print(run('aaa:pie_ach')[-110:])
