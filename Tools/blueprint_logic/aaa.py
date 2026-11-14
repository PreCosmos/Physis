import sys,time,json
sys.path.insert(0,'/var/home/precosmos/Έγγραφα/Unreal Projects/Physis/Tools')
from unreal_mcp import UnrealMCP
c=UnrealMCP(timeout=900); c.initialize()
for op in sys.argv[1:]:
    t=time.time()
    r=c.call('call_tool',{'toolset_name':'physis_character_tools.PhysisCharacterTools','tool_name':'outfit_operation','arguments':{'operation':op}})
    print(op,round(time.time()-t),json.dumps(r,ensure_ascii=False)[:5000],flush=True)
