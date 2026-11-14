# WARNING (2026-11-05, updated 2026-11-07): a full run writes BP_PhysisHUD several times in one editor session
# (textplate, pause, hudfont, hudfix, then center_overrides part map). In 2026-11 that ran the editor out of memory and
# froze the machine, when the HUD was 129 MB of mostly dead nodes. Since 2026-11-07 it is 12 MB and every write prunes
# itself, so this is probably safe now, but it has not been measured. Until a run with a RAM trace (free -m every few
# seconds) stays near one HUD write's peak, keep one HUD-writing script per fresh launch. The measured run: the
# HUD-writing scripts in one launch with the trace, stopping if RAM passes about 24 GB of 31; if it stays near the
# 2026-11-07 peaks (about 15-19 GB), relax the rule and update these lines. See memory note unreal-mcp-access.
cd "/var/home/precosmos/Έγγραφα/Unreal Projects/Physis"
if timeout 120 python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py aaa:tag_info 2>&1 | grep -q L_CenterOfTheUniverse; then echo "STOP: L_CenterOfTheUniverse is open. The level step saves every unsaved package, maps included, and the Center map may hold BP_Awakening TestArrival ticked but unsaved. Tell the Center session, open L_BattleStation without saving the Center map, then rerun."; exit 1; fi
for i in 1 2 3 4 5 6 7 8; do python3 Tools/unreal_mcp.py call call_tool '{"toolset_name":"EditorToolset.EditorAppToolset","tool_name":"IsPIERunning","arguments":{}}' 2>&1 | grep -q 'returnValue\\":false' && break; sleep 1; done
echo == logic
for f in textplate scenario_bp pause gunfix skip g feat feat2 dronefix cleanup menutheme g5 hudfont firesound charge fidelity quality hudfix lifeaug parry2; do timeout 700 python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/$f.py 2>&1 | grep -E "FAILED|Traceback" | cut -c1-160 | sed "s/^/$f: /"; done
timeout 700 python3 Tools/blueprint_logic/center_music.py 2>&1 | grep -E "ERR|FAILED|Traceback|left as it is" | cut -c1-160 | sed "s/^/center_music: /"
echo == level
timeout 1500 python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py aaa:save_all play:save_gameplay aaa:run_fast aaa:theme_import aaa:pause_assets aaa:surround_assets "open_level:/Game/Levels/L_BattleStation" aaa:mood aaa:scenario_place aaa:pool_fix aaa:capture_logs aaa:scenario_place aaa:pool_fix aaa:tag_hull aaa:save_all 2>&1 | cut -c1-170
echo DONE
# The Conclave (Conclave session; Tools/conclave/README.md, "Graphs a station rebuild rewrites"). Since 2026-11-09
# combat.py's helper head skips every graph center_overrides.py owns (CENTER_OWNED), so scenario_bp.py and feat.py no
# longer write the station's PhysisInteract and DrawInteract over the Conclave's. center_music.py still runs every
# center_overrides.py part; its last, part conclave, writes the Conclave's PhysisInteract (people first) and prints
# "left as it is" while BP_NPC has no TalkStart, which is right only before the Conclave is built. DrawInteract keeps
# the Conclave's version that conclave_hud.py wrote, so conclave_hud.py is no longer needed after a station rebuild.
cat <<'NEXT'
CHECK (Conclave): only if a center_music line above names PhysisInteract (FAILED, or "left as it is" although the
Conclave is built), quit this editor, then in a FRESH editor:
      python3 Tools/blueprint_logic/center_overrides.py conclave
      python3 /var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/aaa.py aaa:save_asset:/Game/Characters/Physis/Blueprints/BP_Switch aaa:save_asset:/Game/Characters/Physis/Blueprints/BP_Physis
    (BP_Switch first: PhysisInteract reads its Reach, which this part makes if it is missing.)
NEXT
