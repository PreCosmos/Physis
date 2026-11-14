import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:2800,-400,110'); time.sleep(.4); run('play:pie_call:PhysisVisorToggle'); time.sleep(.6)
for i in range(5): run('aaa:pie_aim:Live Power'); time.sleep(.4)
run('play:pie_call:PhysisScan'); time.sleep(2.8)
print('scanned',run('aaa:pie_voice')[-80:])
run('play:pie_call:PhysisScan'); time.sleep(.5); print('closed',run('aaa:pie_voice')[-80:])
run('play:pie_call:PhysisScan'); time.sleep(.4); print('rescan instant',run('aaa:pie_scandbg:Live Power')[-80:])
run('play:pie_call:PhysisVisorToggle'); time.sleep(.4)
