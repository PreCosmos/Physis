import json,sys,re
sys.path.insert(0,'Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=200);c.initialize()
T='editor_toolset.toolsets.blueprint.BlueprintTools'
P='/Game/Characters/Physis/Blueprints/BP_Physis.BP_Physis'
d=json.loads(c.call('describe_toolset',{'toolset_name':T})['content'][0]['text'])
schema=next(t for t in d['tools'] if t['name'].endswith('.add_function_graph'))['inputSchema']
print(list(schema['properties']),schema.get('required'))
name_key=next(k for k in schema['properties'] if 'name' in k.lower())
code=open(sys.argv[1],encoding='utf8').read()
forms=[f.strip() for f in re.split(r'\n(?=\(fn )',code) if f.strip()]
existing=json.dumps(c.call('call_tool',{'toolset_name':T,'tool_name':'list_graphs','arguments':{'blueprint':{'refPath':P}}}))
for f in forms:
    name=re.match(r'\(fn (\w+)',f)[1]
    if ':'+name+'\\' not in existing:
        r=c.call('call_tool',{'toolset_name':T,'tool_name':'add_function_graph','arguments':{'blueprint':{'refPath':P},name_key:name}})
        if r.get('isError'):print('ADD',name,json.dumps(r)[:300]);continue
    r=c.call('call_tool',{'toolset_name':T,'tool_name':'write_graph_dsl','arguments':{'graph':{'refPath':P+':'+name},'code':f}})
    print(name,'ERROR '+r['content'][0]['text'][:300] if r.get('isError') else 'ok')
