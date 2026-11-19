# Hesper, the City of One Voice (level 7, Arche): build contract

Design: GAME_ROADMAP.md, section "Level 7 — Arche: Hesper, the City of One Voice". This file is the contract every
script of the level follows: names, sizes, pivots and the run order. Change it before changing an interface.

## The level in one paragraph

Hesper is the Vigil's seat on Arche, a city on a plateau on the line between day and night, where the sun never sets.
When the war began the Vigil raised the Concord, an engine that sounds one tone through the city's Divinity so that
every voice in Hesper agrees with theirs; where the tone is strongest it stands in the air as Unison, walls of amber
light. Aeon brings Physis here and teaches her **Dissonance**, a note of her own that the tone cannot hold. She passes
the Choir Wall, frees Hesper's three voting bells from their shells of Unison (no, not yet, yes), opens the Choir Gate,
silences the Cantor, and hears the city argue again. Vaelun, the Precentor, stays to hear it.

## Author rules (2026-11-18)

1. The level after Halcyon is the second First Ones' Great Installation, on Arche; the ability is **Dissonance**, taught
   by Aeon as preparation for the Reckoning.
2. **Look: realistic, warm dusk.** The sun 7 degrees above the western horizon, for ever: raking gold light, long violet
   shadows, an amber-rose horizon and a deep blue zenith, warm haze in the drop to the west. Four lights: Unison amber
   gold, the Serene ice blue, the Vigil violet, Dissonance blue-white.
3. Standing rules: no 3D text; one editor at a time.

## Files

| File | Contents |
| --- | --- |
| `Content/Python/physis_hesper_plan.py` | The world plan: every place, height, path, pool and the Choir Wall's panels (metres, x north, y east) |
| `Tools/hesper_meshes/kit.py`, `check.py` | Mesh kit (Arche's, plus Hesper's warm palette); validator and previewer (`--preview` to `Saved/Hesper/preview`) |
| `Tools/hesper_meshes/land.py` | Terrain (height grid, tiles with the ground's albedo), the pool sheet, the drop's floor, scatter (Kathodos's houses, columns, lanterns, crystals; the edge's parapet) |
| `Tools/hesper_meshes/structures.py` | Unison panel and shell, the bells, the Concord, its pylons, the Watch Spire, the parapet, Tavor's fork, Anwe's flute, the Cantor |
| `Tools/build_physis_hesper.py` | Blender entry point: every module's meshes as FBX, height.bin, scatter.json (`Art/Meshes/Hesper`) |
| `Tools/build_physis_hesper_map.py` | The pause menu's map art (`Art/UI/T_UI_MapHesper.png`) |
| `Content/Python/physis_hesper_lore.py` | All text: scans, people, bells, quests, enemies, tutorials |
| `Content/Python/physis_hesper_tools.py` | `hesper:` operations: materials (incl. `M_HS_Unison`, `M_HS_Dissonance`, the dusk twins of Arche's), import, audio, blueprints, input, map_art, level, scenario, portal |
| `Content/Python/physis_hesper_level.py` | The level build: terrain, pools, the western edge, the look, scatter (regraded), start |
| `Content/Python/physis_hesper_scenario.py` | Gameplay placement (on Arche's scenario, which is on the Grove's), and the Center's current |
| `Tools/blueprint_logic/hesper_logic.py`, `hesper_shared.py` | Blueprint logic: Dissonance, `BP_Unison`, `BP_Dissonance`, the director, the current, travel; Hesper's branches in graphs other levels own (fidelity, music, load, save world 7, the map page, relics, `BP_EnemyBolt`) |
| `Tools/build_physis_voice.py --hesper` | Divinity's lines and the people's pages (Kokoro) into `Art/Audio/Hesper/Voice` |

## Run order

```
python3 Tools/hesper_meshes/check.py land structures
blender -b --factory-startup --python-exit-code 1 --python Tools/build_physis_hesper.py [-- names | --terrain | --scatter]
python3 Tools/build_physis_hesper_map.py
Saved/Hesper/run/live.sh materials import map_art blueprints level      # the open GUI editor (import needs it)
python3 Tools/blueprint_logic/hesper_logic.py                          # unison ring director current physis input
python3 Tools/blueprint_logic/hesper_logic.py shared hud relic bolt
Saved/Hesper/run/live.sh audio scenario portal
```

## Meshes

Conventions are Arche's (`Tools/arche/README.md`): metres, x forward (+x is a mesh's front), y right, z up; 'base'
pivots stand on z 0 with the footprint centred. Prefixes: `SM_ST_` terrain and water, `SM_SN_` structures and props,
`SM_SE_` the boss. Everything else is Kathodos's (`SM_AN_`, `SM_AV_`, `SM_AP_`, `SM_AE_`) and the Conclave's AL
(`SM_CE_`), worn in Hesper's dusk twins of Arche's materials (`physis_hesper_tools.TWINS`, applied by `regrade()`).

| Mesh | Size (x by y by z) | Notes |
| --- | --- | --- |
| `SM_SN_Unison` | 6 x 12 x 12 | A Choir Wall panel: standing sheets of tone; box collision; worn in `M_HS_Unison` |
| `SM_SN_Shell` | 7 x 7 x 8 | A shell of tone round a thing; box collision; worn in `M_HS_Unison` |
| `SM_SN_Bell` | 5.2 x 5.2 x 7.4 | A great bell in its stone frame |
| `SM_SN_Concord` | 26 x 26 x 30.7 | The engine: drum, twelve pipes, the horn leaning toward the gate (-x) |
| `SM_SN_Pylon` | 2.4 x 2.4 x 7.2 | A tuning pylon (the Cantor's shield answers to four) |
| `SM_SN_Spire` | 11 x 11 x 48 | The Watch Spire (a landmark) |
| `SM_SN_Parapet` | 0.7 x 12 x 1.15 | The western edge's low wall |
| `SM_SE_Cantor` | 8.9 x 11 x 7 | The boss; 'centre' pivot (it hovers) |
| `SM_ST_Pool` | 2 x 2 | A unit sheet of water stretched over each pool |

## Gameplay pieces

**Dissonance** (`BP_Physis.PhysisDissonance`, input `IA_Dissonance`: **C**, and the pad's **D-pad up held 0.45 s**; a
tap still switches weapons). Needs `,dissonance,`; no cost; sets `DissonanceUntil` to now + 8 s and `DissonanceReady`
to now + 10 s; reports `,dissonance,` to `PhysisUsedAbility` (the Center's and the Conclave's Dissonance vaults open
to it); spawns `BP_Dissonance`, the ring (an 18 m sphere in `M_HS_Dissonance`) that follows her and fades as the note
ends.

**`BP_Unison`** (instance-editable `Need`, `Hide` (default in the scenario `,cantor,`), `Give`, `Done`, `Hold` s,
`HalfX/Y/Z` cm): the actor stands at the middle of its shape's box. `Gap` is her distance to the box. She is
`Covered` while her note lasts and `Gap` < 9 m. A wall (Hold 0) thins and loses its collision while covered, and
takes it back only once she is 60 cm clear of the box. A shell (Hold > 0) stays solid; once covered for Hold seconds
in a row it breaks for good: gives `Give`, says `Done`. A shell whose `Give` is held starts broken. Custom primitive
data 0 is its strength.

**`BP_EnemyBolt`**: inside her note (9 m) a bolt falters: a spark, and it is gone.

**`BP_HesperDirector`**: arrival (`,hesper,` `,at_hesper,`, the first quest, Divinity's line once); every 0.25 s
`HesperScar` hidden and `HesperBloom` shown once `,cantor,` is held, the quests that follow a token (`,hs_q_wall,`
`,hs_q_gate,` `,hs_q_cantor,`), `MPC_Grove` Motion, and `HesperHush` sounds faded once the Cantor falls: over 3 s in play, and at once after a load that finds it done
(`grove_logic.hush`, 2026-11-19).

**Travel**: `BP_HesperCurrent` (token `,trip_s,`, tags `HesperArrival` / `HesperReturn`), in the Center's sanctum
16 m north-east of the Heartbloom (Need `,keel,`) and at the Sunward Stair. Saves on Hesper hold `,at_hesper,` and
load `L_Hesper`; the save's exact spot is world 7.

**Tested in Play-in-Editor**: see GAME_ROADMAP.md, Level 7, "Status".
