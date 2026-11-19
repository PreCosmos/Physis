# Halcyon, the Drowned Harbour (level 6, Earth): build contract

Design: GAME_ROADMAP.md, section "Level 6 — Earth: Halcyon, the Drowned Harbour". This file is the contract every
script of the level follows: names, sizes, pivots and the run order. Change it before changing an interface.

## The level in one paragraph

Port Halcyon is a harbour town on Earth, struck in the war's first year: a First One lance broke its sea wall and the
lower town drowned. The Just built their coastal command, Bastion Halcyon, in the harbour mouth, and the Undertow,
which forces Divinity through the sea so that it stands back from the Bastion in walls (the Held Sea). Kairos and the
Wise are camped at the Signal House, reading the town's past. Physis learns **Trace Reading** at the Clocktower, crosses
the Breach on the Harbour Bridge as it stood, finds the three people who first swore the Halcyon Litany (the
harbourmaster, the foreman, the keeper) where the town remembers them, opens the Sea Gate with their three lines, and
stops the Keel.

## Author rules (2026-11-18)

1. The level after Arche is the second Earth Great Installation; the ability is **Trace Reading**, taught by Kairos
   and the Wise.
2. **Look: realistic, neutral.** Overcast marine light, limestone and render, slate, weathered steel, a grey-green
   sea. Three lights: the Just's machines amber, forced Divinity (the Held Sea) magenta, the past silver.
3. Standing rules: no 3D text; one editor at a time.

## Files

| File | Contents |
| --- | --- |
| `Content/Python/physis_halcyon_plan.py` | The world plan: every place, height and street (metres, x north, y east) |
| `Tools/halcyon_meshes/kit.py`, `check.py` | Mesh kit (slots, palette) on the Grove's; validator and previewer (`--preview` to `Saved/Halcyon/preview`) |
| `Tools/halcyon_meshes/land.py` | Terrain (height grid, tiles with the Grove ground shader's layer weights), the sea, scatter (the town's houses) |
| `Tools/halcyon_meshes/structures.py` | Houses, quay, Mole, clocktower, Signal House, lighthouse, crane, shed, office, Bastion, Sea Gate, Held Sea, pumps, the past's pieces (bridge, catwalk, flight, shelf), props |
| `Tools/halcyon_meshes/figures.py` | The Keel (boss) and the echoes |
| `Tools/build_physis_halcyon.py` | Blender entry point: every module's meshes as FBX, height.bin, scatter.json (`Art/Meshes/Halcyon`) |
| `Tools/build_physis_halcyon_map.py` | The pause menu's map art (`Art/UI/T_UI_MapHalcyon.png`) |
| `Content/Python/physis_halcyon_lore.py` | All text: scans, people, echoes, quests, enemies, tutorials |
| `Content/Python/physis_halcyon_tools.py` | `halcyon:` operations: materials (incl. `M_HA_Trace`), import, audio, blueprints, input, map_art, level, scenario, portal |
| `Content/Python/physis_halcyon_level.py` | The level build: terrain, sea and swimming, the look, scatter, start |
| `Content/Python/physis_halcyon_scenario.py` | Gameplay placement (on the Grove's scenario), and the Center's current |
| `Tools/blueprint_logic/halcyon_logic.py`, `halcyon_shared.py` | Blueprint logic: Trace Reading, `BP_Trace`, the director, the current, travel; the Halcyon branches in graphs other levels own |
| `Tools/build_physis_halcyon_audio.py` | The music, S_Music_Halcyon (a Muse Sounds score in D Dorian: the Litany hymn, the sea, the bell), and the beds S_Amb_Halcyon (surf, wind, gulls, bell buoy), S_Amb_HeldSea (the roar and the pumps; tag HalcyonHush: the director fades it out once the Keel falls, over 3 s in play and at once after a load that finds it fallen (`grove_logic.hush`), since hiding an AmbientSound does not silence it) and S_Amb_Quarter; then `halcyon:audio`, `halcyon_logic.py music` and `halcyon:scenario` |
| `Tools/build_physis_voice.py --halcyon` | Divinity's lines and the people's pages (Kokoro) into `Art/Audio/Halcyon/Voice` |

## Run order

```
python3 Tools/halcyon_meshes/check.py land structures figures
blender -b --factory-startup --python-exit-code 1 --python Tools/build_physis_halcyon.py [-- names | --terrain | --scatter]
python3 Tools/build_physis_halcyon_map.py
Saved/Halcyon/run/live.sh materials import map_art blueprints level      # the open GUI editor (import needs it)
python3 Tools/blueprint_logic/halcyon_logic.py                          # trace director current physis input
python3 Tools/blueprint_logic/halcyon_logic.py shared hud relic
Saved/Halcyon/run/live.sh scenario portal audio
```

## Meshes

Conventions are Arche's (`Tools/arche/README.md`): metres, x forward (+x is a mesh's front), y right, z up; 'base'
pivots stand on z 0 with the footprint centred, except where named. Prefixes: `SM_HT_` terrain and sea, `SM_HN_`
structures and props, `SM_HE_` the boss, `SM_HP_` the echoes.

| Mesh | Size (x by y by z) | Notes |
| --- | --- | --- |
| `SM_HN_House0`..`3` | about 8 x 7 x 9 | Terrace, narrow, ruin, shop; front (+x) to the street; box collision |
| `SM_HN_Quay` | 2.5 x 12 x 10.1 | Sea wall panel, placed on the bed at -7 m |
| `SM_HN_MoleSlab` | 12 x 9 x 4.4 | Deck top at 4.0: placed at -1.0 so the deck is at `plan.MOLE_TOP` |
| `SM_HN_Clocktower` | 6.6 x 6.6 x 27.2 | Dials stopped at 7:14 |
| `SM_HN_Lighthouse` | 9.4 x 9.4 x 28.8 | Walkable gallery at z 22, its railing open on -y (where the past's stair arrives) |
| `SM_HN_Crane` | 22.6 x 9.5 x 22.1 | **Pivot at the portal's centre**, not the footprint's; cab platform top at z 13.46, x -1.4..3.8, y 3.2..5.2 |
| `SM_HN_Office` | 8.3 x 8.3 x 8.05 | Walkable roof at 7.2, parapet top 8.05 |
| `SM_HN_Bridge` | 32 x 7 | Trace. **Pivot at the deck's top centre** |
| `SM_HN_Catwalk` | 9 x 2.4 | Trace (and the footbridge). Pivot at the deck's top centre |
| `SM_HN_Flight` | 9.4 x 2.6 x 6.8 | Trace. Foot at x -4.7, 20 treads of 0.4 x 0.3 m, top landing at z 6 flush with x +4.7, its sides open so switchbacks step across |
| `SM_HN_HeldSea` | 3 x 16.4 x 23 | A section of standing water, face +x toward the rock; tag `HalcyonScar` |
| `SM_HE_Keel` | about 11 x 8 x 6 | 'centre' pivot (it hovers) |
| `SM_HP_Echo0`..`2` | 1.7 to 1.8 m | One slot; worn in `M_HA_Trace` |

## Gameplay pieces

**Trace Reading** (`BP_Physis.PhysisTraceRead`, input `IA_TraceRead`: **T**, and the pad's **D-pad down held 0.45 s**;
a tap is still Reload). Needs `,trace,`; no cost; sets `TraceUntil` to now + 10 s, `TraceReady` to now + 1 s; reports
`,trace,` to `PhysisUsedAbility` (Arche's sealed vault opens to it).

**`BP_Trace`** (instance-editable `Need` (default `,trace,`), `Hide`, `Give`, `Done`, `Range` cm): its `Shape` wears
`M_HA_Trace` on every slot; custom primitive data 0 is its strength T. T goes toward 1 while she reads within Range,
fading over the reading's last 2 s; the Shape shows above 0.01 and is solid above 0.3; the first time T reaches 0.95
it gives `Give` and says `Done` (the echoes' lines, the bridge's token). Traces are never saved.

**`BP_HalcyonDirector`**: arrival (`,halcyon,` `,at_halcyon,`, the first quest, Divinity's line once); every 0.25 s
`HalcyonScar` hidden and `HalcyonBloom` shown once `,keel,` is held (collision follows), the quests that follow a token
(`,ha_q_breach,` `,ha_q_echoes,` `,ha_q_gate,` `,ha_q_keel,`), `,halcyon_done,` after Kairos's reward, and `MPC_Grove`
(Motion 1 with `,resonance,`, Heal 1 with `,keel,`: the forced ground heals).

**Travel**: `BP_HalcyonCurrent` (token `,trip_h,`, tags `HalcyonArrival` / `HalcyonReturn`), in the Center's sanctum
16 m north-west of the Heartbloom (Need `,sunderer,`) and at the Cliff Garden. Saves on Halcyon hold `,at_halcyon,`
and load `L_Halcyon`; the save's exact spot is world 6.

**Tested in Play-in-Editor (2026-11-18, scripted)**: see GAME_ROADMAP.md, Level 6, "Status".
