import json,sys
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=120);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
P='/Game/Characters/Physis/Blueprints/BP_Physis.BP_Physis'
G={'refPath':P+':EventGraph'}
def call(tool,args):
    r=c.call('call_tool',{'toolset_name':T,'tool_name':tool,'arguments':args})
    if r.get('isError'):raise RuntimeError(tool+': '+r['content'][0]['text'][:400])
    return json.loads(r['content'][0]['text'])['returnValue']
y=[2000]
def node(type_id,x):
    n=call('create_node',{'graph':G,'type_id':type_id,'pos':{'x':x,'y':y[0]}})
    return n
def pins(n):
    ref=n if isinstance(n,dict) and 'refPath' in n else n.get('node',n)
    info=call('get_node_infos',{'nodes':[ref]})
    return info[0] if isinstance(info,list) else info
first=node('Input|EnhancedActionEvents|IA_Move',-400)
print(json.dumps(first)[:300])
print(json.dumps(pins(first))[:900])
d=json.loads(c.call('describe_toolset',{'toolset_name':T})['content'][0]['text'])
print([json.dumps(t['inputSchema'])[:200] for t in d['tools'] if t['name'].endswith('get_node_infos')])
