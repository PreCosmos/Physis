cd "/var/home/precosmos/Έγγραφα/Unreal Projects/Physis"
for i in 1 2 3 4 5 6 7 8; do python3 Tools/unreal_mcp.py call call_tool '{"toolset_name":"EditorToolset.EditorAppToolset","tool_name":"IsPIERunning","arguments":{}}' 2>&1 | grep -q 'returnValue\\":false' && break; sleep 1; done
echo == logic
timeout 400 python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/scenario_bp.py 2>&1 | grep -E "FAILED|Traceback" | cut -c1-160
timeout 600 python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/pause.py 2>&1 | grep -E "FAILED|Traceback" | cut -c1-160
timeout 300 python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/gunfix.py 2>&1 | grep -E "FAILED|Traceback" | cut -c1-160
python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/skip.py 2>&1 | grep -E "ERR|Traceback" | cut -c1-120
python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/g.py >/dev/null 2>&1
timeout 300 python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/feat.py 2>&1 | grep -E "FAILED|Traceback" | cut -c1-160
python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/menutheme.py >/dev/null 2>&1
echo == level
timeout 900 python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py aaa:save_all play:save_gameplay "open_level:/Game/Levels/L_BattleStation" aaa:wing_build aaa:dress aaa:mood aaa:pause_assets aaa:scenario_place aaa:pool_fix aaa:capture_logs aaa:scenario_place aaa:pool_fix aaa:save_all 2>&1 | cut -c1-200
echo DONE
