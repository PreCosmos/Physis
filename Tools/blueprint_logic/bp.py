import json,sys,subprocess
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=200);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
P='/Game/Characters/Physis/Blueprints/BP_Physis.BP_Physis'
def call(tool,args):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':tool,'arguments':args})
    return r
if sys.argv[1]=='read':
    r=call('read_graph_dsl',{'graph':{'refPath':P+':'+sys.argv[2]}})
    t=r['content'][0]['text']
    try:print(json.loads(t)['returnValue'][:2500])
    except Exception:print(t[:800])
elif sys.argv[1]=='write':
    r=call('write_graph_dsl',{'graph':{'refPath':P+':'+sys.argv[2]},'code':open(sys.argv[3],encoding='utf8').read()})
    print(json.dumps(r)[:1500])
elif sys.argv[1]=='types':
    for f in sys.argv[2:]:
        r=call('find_node_types',{'graph':{'refPath':P+':EventGraph'},'type_id_filter':f,'context_pins':[]})
        print(f,r['content'][0]['text'][:360])
if sys.argv[1]=='readall':
    for g in sys.argv[2:]:
        r=call('read_graph_dsl',{'graph':{'refPath':P+':'+g}});print(g,r['content'][0]['text'][:420])
if sys.argv[1]=='alltypes':
    for f in sys.argv[2:]:
        r=call('find_node_types',{'graph':{'refPath':P+':EventGraph'},'type_id_filter':f,'context_pins':[]})
        print(f,r['content'][0]['text'][:300])
