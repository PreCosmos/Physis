import time,subprocess,re
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
def st(t):
    o=run('aaa:pie_state'); m=re.search(r'flags.*',o); print(t,(m.group(0) if m else o[-160:])[:150].replace('\\\\','').replace('\\"',''),flush=True)
def go(x,y,z,w=.5): run('aaa:pie_go:%s,%s,%s'%(x,y,z)); time.sleep(w)
def jump(h):
    run('aaa:pie_jump_for:%s'%h); time.sleep(1.8); print('jump',h,open('Saved/Connection/jump.txt').read(),flush=True)
time.sleep(45)

go(2030,250,110,1); run('play:pie_shot'); time.sleep(.8)
go(1600,300,300,.4); go(2130,640,240,.5); run('play:pie_call:PhysisInteract'); time.sleep(.5)
go(2700,0,110,2.5); run('play:pie_shot'); time.sleep(1)
st('before burn'); go(3000,100,95,.0); time.sleep(3.3); st('after strip'); time.sleep(.6)
go(2620,540,110,.4); run('play:pie_call:PhysisInteract'); time.sleep(.5); st('node no divinity')
run('play:pie_shot'); time.sleep(.8)
go(4700,0,110,.3); go(5300,250,110,.8); print(run('aaa:pie_pickups')[-130:]); print(run('aaa:pie_kill:1')[-60:]); time.sleep(.5); print(run('aaa:pie_pickups')[-150:]); st('room1')
go(7500,-400,110,1); run('play:pie_shot'); time.sleep(.8)
go(9000,0,300,.7); run('play:pie_shot'); time.sleep(1)
