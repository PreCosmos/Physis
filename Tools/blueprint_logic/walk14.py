import time,subprocess,re
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
for t in ('Breach Deck','AL Drone','Crew Log','Reactor Fuse','Mecha Breacher'): run('aaa:pie_scanat:'+t)
run('play:pie_call:PhysisPause'); time.sleep(.5); run('aaa:pie_page:0'); time.sleep(1.5); run('play:pie_shot'); time.sleep(2)
print(run('aaa:pie_voice')[-120:])
run('aaa:pie_page:1'); time.sleep(1); run('play:pie_shot'); time.sleep(2)
run('play:pie_call:PhysisPause'); time.sleep(.5)
run('aaa:pie_go:4600,0,110'); time.sleep(.5)
run('play:pie_call:PhysisSwitchWeapon'); time.sleep(1.2)
o=run('play:pie_combat'); print('before',re.findall(r'gun[^,]*, [^\]]*\]',o))
for i in range(3):
    run('play:pie_call:PhysisAttack'); time.sleep(.45)
o=run('play:pie_combat'); print('after',re.findall(r'gun[^,]*, [^\]]*\]',o), re.findall(r'drones[^\]]*',o))
