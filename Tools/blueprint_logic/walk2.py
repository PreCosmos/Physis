import time,subprocess,re
def run(*a):
    return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
def st(tag):
    o=run('aaa:pie_state'); m=re.search(r'returnValue.*',o); print(tag,(m.group(0) if m else o)[:150].replace('\\\\\\"','').replace('\\"',''),flush=True)
def go(x,y,z,w=.5): run('aaa:pie_go:%s,%s,%s'%(x,y,z)); time.sleep(w)
time.sleep(45)
go(2700,0,110,.3)
print(run('aaa:pie_scan:Live power')[-110:]); time.sleep(.5)
go(4060,540,110,.5); run('play:pie_call:PhysisInteract'); time.sleep(.4); st('coolant?')
go(13900,0,110,1)
print(run('aaa:pie_boss_gun')[-110:])
print(run('aaa:pie_scan:Hull seam')[-110:]); time.sleep(.6); st('seam?')
for i in range(15):
    o=run('aaa:pie_boss_gun'); time.sleep(.2)
    if 'boss\\\": null' in o or 'null' in o: break
print(o[-90:]); time.sleep(1); st('boss dead?')
