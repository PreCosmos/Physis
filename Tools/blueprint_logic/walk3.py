import time,subprocess,re
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
def go(x,y,z,w=.5): run('aaa:pie_go:%s,%s,%s'%(x,y,z)); time.sleep(w)
time.sleep(45)
go(1900,0,110,.8); run('play:pie_shot'); time.sleep(.8)
run('aaa:pie_scan:Live power')
go(2130,640,240,.3); run('aaa:pie_state'); 
go(1600,300,300,.4); go(2130,640,240,.5); run('play:pie_call:PhysisInteract'); time.sleep(.5)
go(1950,0,110,.6); run('play:pie_shot'); time.sleep(2.2); run('play:pie_shot'); time.sleep(.8)
go(2700,0,110,1.3); run('play:pie_shot'); time.sleep(.8)
go(3330,0,100,.7); o=run('aaa:pie_state'); print(re.findall(r'hp[^,]*|at[^}]*',o)[:3]); run('play:pie_shot'); time.sleep(1)
print(run('aaa:pie_state')[-120:])
go(4400,0,110,.3); print(run('aaa:pie_drones')[-110:])
go(5400,0,110,.3); time.sleep(11); print(run('aaa:pie_drones')[-110:]); run('play:pie_shot'); time.sleep(1)
