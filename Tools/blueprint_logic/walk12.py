import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
print(run('aaa:pie_scanat:Reactor Fuse')[-40:])
run('play:pie_call:PhysisPause'); time.sleep(1.2); run('play:pie_shot'); time.sleep(2)
run('aaa:pie_page:0'); time.sleep(1); run('play:pie_shot'); time.sleep(2)
run('aaa:pie_page:2'); time.sleep(1); run('play:pie_shot'); time.sleep(2)
