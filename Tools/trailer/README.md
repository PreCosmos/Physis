# Physis trailer

`Saved/Trailer/Physis_Trailer.mp4` (78.1 s, 1920x1080, 30 fps) was made on 2026-11-05 with these scripts.

Footage is rendered with Movie Render Queue (editor-only plugin, enabled in Physis.uproject) through its PIE
executor. Each job uses Movie Render Queue's own game mode, so no player pawn, HUD or level start logic runs
(the station would otherwise start its opening, and the Center would delete the awakening stand-in).

| Step | Script (run in the editor: `run.py "center:exec:<path>"`) | Writes |
| --- | --- | --- |
| Awakening with the stand-in's wake-up clips | `build_trailer_awakening.py` | `/Game/Trailer/SEQ_Trailer_Awakening` |
| Flyover sequence (spawnable cine cameras) | `build_flyover.py` with `flyover_arg.json` (copy `flyover_center.json` or `flyover_station.json`) | `/Game/Trailer/SEQ_Trailer_Center`, `SEQ_Trailer_Station` |
| Render one job | `mrq.py` with `mrq_arg.json` (`name`, `map`, `sequence`, `start`, `end`, `warmup`, optional `w`, `h`) | `Saved/Trailer/<name>/<frame>.jpeg` |
| Cut the trailer (plain Python, needs ffmpeg) | `python3 build_trailer.py --run` | `Saved/Trailer/Physis_Trailer.mp4` |

Combat shots (staged, Center): `combat/k1.py` (katana combo), `k2.py` (Divine Parry), `k3.py` (sidearm) write
`combat/k*.json`; copy one to `combat_arg.json` and run `build_combat.py` in the editor to make `/Game/Trailer/SEQ_Trailer_Combat1-3`.
The stand-in is the level's "Cine Physis" (BP_MH_Physis), with the game's own clips, the weapon on `hand_r` (BP_Physis offsets),
logic-free enemy meshes and the game's effect actors on the hit frames. Facing: katana clips face actor yaw + 90, the female
pistol clips face actor yaw; `Physis_MM_Pistol_Fire` is additive (alone it leaves the bind pose).

Renders used: `awakening` (SEQ_Trailer_Awakening 0-780), `center` (SEQ_Trailer_Center 0-1050),
`station` (SEQ_Trailer_Station 0-360), `opening` (SEQ_Opening 240-1140, L_BattleStation),
`combat1` (0-80), `combat2` (0-105), `combat3` (0-90).

Pitfalls: the engine's older "Render Movie" capture writes black frames on Linux (Vulkan window readback), so use
Movie Render Queue. Its PIE executor loads the map from disk, so unsaved editor changes (TestArrival) never reach it.
Rendered JPEGs are full-range BT.601; `build_trailer.py` converts to limited-range BT.709.
