import sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
for q in ('EqualEqual_Object','Equal(Object','NotEqual(Object'):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':'find_node_types','arguments':{'graph':{'refPath':H+':EventGraph'},'type_id_filter':q,'context_pins':[]}})
    print(q,r['content'][0]['text'][:500])
