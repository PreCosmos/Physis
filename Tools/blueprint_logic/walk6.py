import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
def go(x,y,z,w=.5): run('aaa:pie_go:%s,%s,%s'%(x,y,z)); time.sleep(w)
time.sleep(5)
print(run('play:pie_call:PhysisCinemaEnd')[-70:]); time.sleep(1.5)
go(8680,0,200,1.2); run('play:pie_shot'); time.sleep(1.2)
