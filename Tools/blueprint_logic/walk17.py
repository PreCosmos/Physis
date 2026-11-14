import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:13900,300,110'); time.sleep(.5)
for i in range(4): run('aaa:pie_aim:Mecha Breacher'); time.sleep(.3)
run('play:pie_shot'); time.sleep(1.2)
print(run('aaa:pie_scan:Hull seam')[-40:]); time.sleep(.3)
print(run('aaa:pie_boss_gun')[-80:])
for i in range(3): run('aaa:pie_aim:Mecha Breacher'); time.sleep(.3)
run('play:pie_shot'); time.sleep(1.2)
