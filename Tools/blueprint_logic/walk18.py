import time,subprocess,re,sys
sys.path.insert(0,'Content/Python')
import physis_lore as L
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
def flags():
    o=run('aaa:pie_state'); m=re.search(r'flags[^,]*: ([^"\\]*)',o.replace('\\\\','')); return o[o.find('flags'):o.find('fuses')][:300]
def go(p,w=.5): run('aaa:pie_go:%s,%s,%s'%(p[0],p[1],p[2])); time.sleep(w)
def use(): run('play:pie_call:PhysisInteract'); time.sleep(.4)
def along(i,t,side=0,z=110):
    x1,x2,y1,y2,e,x=L.wing_room(i); dx,dy=x[0]-e[0],x[1]-e[1]; n=(dx*dx+dy*dy)**.5; dx,dy=dx/n,dy/n; px,py=-dy,dx
    return (e[0]+dx*n*t+px*side, e[1]+dy*n*t+py*side, z)
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
go((4800,0,110),.5); run('aaa:pie_kill:1'); time.sleep(.8)
go((5600,1200,110),1.0); run('play:pie_shot'); time.sleep(1)
for i,(name,kind,g) in enumerate(L.WING):
    go(along(i,.1),.6)
    if kind=='enemies': run('aaa:pie_kill:%d'%(101+i)); time.sleep(.8)
    if kind in('relay','triage'):
        run('aaa:pie_scan:'+('relay node that drives' if kind=='relay' else 'triage console that locks')); time.sleep(.6)
        go(along(i,.85,420-0,110),.3); use()
    if kind=='sequence':
        for t,c in ((.5,'Gold'),(.72,'Blue'),(.28,'Red')): go(along(i,t,600-80,110),.3); use()
    if kind=='locks':
        go(along(i,.85,500-80,110),.3); use(); go(along(i,.2,-600+80,110),.3); use(); go(along(i,.85,500-80,110),.3); use()
    if kind=='node':
        go(along(i,.1,-500,110),.4); go(along(i,.1,-250,110),.4); go(along(i,.12,600-80,110),.3); use()
    if kind=='final': go(along(i,.6,450-80,110),.3); use()
    if i in (0,5,11): go(along(i,.12,0,110),1.2); run('play:pie_shot'); time.sleep(1.2)
    time.sleep(1.3)
print(flags())
go((7200,1200,110),1); go((7200,600,110),1)
print(run('aaa:pie_state')[-160:])
for t,c in ((7500,'Red'),(8000,'Gold'),(6900,'Blue')): go((t,-620,110),.3); use()
print('armory',flags())
