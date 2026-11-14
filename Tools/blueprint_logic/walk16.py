import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:2050,600,240'); time.sleep(1); run('play:pie_shot'); time.sleep(1.5)
run('aaa:pie_go:2800,-400,110'); time.sleep(.4); run('play:pie_call:PhysisVisorToggle'); time.sleep(.6)
for i in range(5): run('aaa:pie_aim:Live Power'); time.sleep(.4)
run('play:pie_call:PhysisScan'); time.sleep(2.8); run('play:pie_shot'); time.sleep(1.5)
print('paused?',run('aaa:pie_voice')[-70:])
run('play:pie_call:PhysisScan'); time.sleep(.6)
run('play:pie_call:PhysisVisorToggle'); time.sleep(.4)
run('aaa:pie_go:14000,0,110'); time.sleep(1.5); run('play:pie_shot'); time.sleep(1.5)
