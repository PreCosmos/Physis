import sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=90);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
D='/Game/Characters/Physis/Blueprints/BP_StationDoor.BP_StationDoor'
def call(t,a):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    print(t,r['content'][0]['text'][:160],'ERR' if r.get('isError') else '')
call('set_variable_instance_editable',{'blueprint':{'refPath':D},'variable_name':'DoorLocked','instance_editable':True})
call('remove_variable',{'blueprint':{'refPath':D},'variable_name':'Locked'})
call('compile_blueprint',{'blueprint':{'refPath':D}})
