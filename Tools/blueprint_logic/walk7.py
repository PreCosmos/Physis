import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
run('aaa:pie_go:1640,620,110'); time.sleep(.5)
run('aaa:pie_look:-40,0'); time.sleep(1); print(run('play:pie_shot')[-60:]); time.sleep(4)
run('aaa:pie_go:2780,0,110'); time.sleep(.4); run('aaa:pie_look:-30,0'); time.sleep(1.2); run('play:pie_shot'); time.sleep(2.5)
run('aaa:pie_go:8320,0,130'); time.sleep(.4); run('aaa:pie_look:-25,0'); time.sleep(1.2); run('play:pie_shot'); time.sleep(2.5)
