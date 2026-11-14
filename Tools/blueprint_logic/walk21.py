import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:5600,4900,110'); time.sleep(.4); run('aaa:pie_look:-5,90'); time.sleep(1.5); run('play:pie_shot'); time.sleep(1.5)
run('aaa:pie_go:5600,3300,110'); time.sleep(.5); run('play:pie_call:PhysisVisorToggle'); time.sleep(.5)
for i in range(4): run('aaa:pie_aim:AL Drone'); time.sleep(.35)
run('play:pie_call:PhysisScan'); time.sleep(2.6); run('play:pie_shot'); time.sleep(1.5)
run('play:pie_call:PhysisScan'); time.sleep(.4)
