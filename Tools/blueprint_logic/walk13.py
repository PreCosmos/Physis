import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
def speed(k):
    run('aaa:pie_speed:'+k); time.sleep(1.8); return open('Saved/Connection/speed.txt').read()
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:4500,0,110'); time.sleep(.6)
print('free fwd',speed('fwd'),'side',speed('side'))
run('aaa:pie_go:4700,0,110'); time.sleep(.4)
print(run('aaa:pie_lockon')[-60:])
print('lock fwd',speed('fwd'),'side',speed('side'))
run('play:pie_call:PhysisLockClear')
run('play:pie_call:PhysisSwitchWeapon'); time.sleep(1.5)
print(run('play:pie_combat')[-200:])
run('play:pie_call:PhysisAttack'); time.sleep(.6); run('play:pie_shot'); time.sleep(.5)
print(run('play:pie_combat')[-200:])
