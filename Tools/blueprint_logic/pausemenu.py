# Retired 2026-11-09. It rewrote only DrawPauseMenu from pause.py, the station's menu without the Map tab and, until
# then, with Exit Game as Settings row 9. The live DrawPauseMenu belongs to Tools/blueprint_logic/center_overrides.py
# part map (Settings row 9 is the Divine Parry assist, Exit Game row 10, Map tab). Run that part instead, as the only
# BP_PhysisHUD write of a fresh editor launch.
import sys
sys.exit('pausemenu.py is retired: run center_overrides.py part map for DrawPauseMenu.')
