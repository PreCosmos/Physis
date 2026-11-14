import time,subprocess
def run(*a): return subprocess.run(['python3','/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py',*a],capture_output=True,text=True).stdout
time.sleep(6); run('play:pie_call:PhysisCinemaEnd'); time.sleep(2)
for spot,yaw in (((5600,4900,110),90),((5300,5500,110),90),((5600,6100,110),-90)):
    run('aaa:pie_go:%d,%d,%d'%spot); time.sleep(.4); run('aaa:pie_look:-5,%d'%yaw); time.sleep(1.2)
    print(spot,run('aaa:pie_hits:0').replace('\\\\\\"','')[-420:]); run('play:pie_shot'); time.sleep(1.5)
