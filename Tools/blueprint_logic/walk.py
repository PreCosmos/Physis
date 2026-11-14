import time,subprocess,re,json
def run(*a):
    o=subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
    return o
def st(tag):
    o=run('aaa:pie_state'); m=re.search(r'returnValue.*',o); print(tag, (m.group(0) if m else o)[:230].replace('\\\\\\"','').replace('\\"',''),flush=True)
def go(x,y,z,w=.5): run('aaa:pie_go:%s,%s,%s'%(x,y,z)); time.sleep(w)
def use(): run('play:pie_call:PhysisInteract'); time.sleep(.4)
time.sleep(45); st('start')
go(1600,300,300,1); st('fuse1')
go(2130,640,240,.8); use(); st('breaker'); time.sleep(1.5)
go(2700,0,110,.6); st('door1 passed')
go(4060,540,110,.5); use(); st('valve denied')
print(run('aaa:pie_scan:Live power')[-70:]); time.sleep(.5); use(); st('valve ok'); time.sleep(1.5)
go(4800,0,110,1); st('crew'); print(run('aaa:pie_kill:1')[-60:]); time.sleep(.6); st('room1 clear')
go(5300,700,260,.8); st('fuse2'); time.sleep(1.2)
go(6900,-620,110,.4); use(); st('blue first wrong')
go(7500,-620,110,.4); use(); go(8000,-620,110,.4); use(); go(6900,-620,110,.4); use(); st('code'); time.sleep(1.5)
go(8680,0,200,.8); st('spine1')
go(9650,-260,220,.8); st('fuse3'); run('play:pie_shot'); time.sleep(1)
go(11200,0,110,1); st('reactor'); print(run('aaa:pie_kill:2')[-60:]); time.sleep(.6); st('room2')
go(11650,-560,240,.5); run('play:pie_shot'); time.sleep(.8)
go(12800,-300,620,.8); use(); st('vent'); time.sleep(1.5)
go(13700,0,110,1); st('bridge'); run('play:pie_shot'); time.sleep(.6); print(run('aaa:pie_boss_gun')[-90:])
print(run('aaa:pie_scan:Hull seam')[-70:]); time.sleep(.6); st('seam'); print(run('aaa:pie_boss_gun')[-90:]); print(run('aaa:pie_kill:3')[-60:]); time.sleep(.8); st('boss dead'); time.sleep(1.5)
go(18050,0,110,.6); use(); st('finish'); run('play:pie_shot'); time.sleep(1)
