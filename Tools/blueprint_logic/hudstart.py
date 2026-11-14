import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=90);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
H='/Game/Characters/Physis/Blueprints/BP_PhysisHUD.BP_PhysisHUD'
def call(t,a):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':t,'arguments':a})
    print(t,r['content'][0]['text'][:260])
print(c.call('call_tool',{'toolset_name':T,'tool_name':'read_graph_dsl','arguments':{'graph':{'refPath':H+':EventGraph'}}})['content'][0]['text'][:200])
call('write_graph_dsl',{'graph':{'refPath':H+':EventGraph'},'code':'''(event EventBeginPlay
  (CallFunction|ShowTutorial :Message "Move: W A S D / Left Stick     Look: Mouse / Right Stick"))'''})
call('compile_blueprint',{'blueprint':{'refPath':H}})
print(c.call('call_tool',{'toolset_name':T,'tool_name':'read_graph_dsl','arguments':{'graph':{'refPath':H+':EventGraph'}}})['content'][0]['text'][:500])
