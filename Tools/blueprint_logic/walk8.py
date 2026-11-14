import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:1640,620,110'); time.sleep(.5); run('aaa:pie_look:-40,0'); time.sleep(.6)
for m in ('/Game/Art/Materials/M_TestA','/Game/Art/Materials/M_TestC','/Game/Art/Materials/MI_Plasma'):
    print(run('aaa:pie_mat:'+m)[-50:]); time.sleep(1.5); run('play:pie_shot'); time.sleep(2)
