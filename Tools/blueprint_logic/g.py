import sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
for v in ('LockHeld','LockTarget','GunEquipped','GunAmmo'):
    call('set_variable_instance_editable',{'blueprint':{'refPath':P},'variable_name':v,'instance_editable':True},True)
comp(P)
