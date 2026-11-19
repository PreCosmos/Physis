# Morrow, the Valley Before Morning (level 8, Earth): build contract

Design: GAME_ROADMAP.md, section "Level 8 — Earth: Morrow, the Valley Before Morning". This file is the contract every
script of the level follows: names, sizes, pivots and the run order. Change it before changing an interface.

## The level in one paragraph

Morrow is a reservoir town of the Just in Earth's northern mountains. Its Warden, Maren Holt, read the letter that told
her of her son Tam's death at Meridian on the dam's crest at sunrise, and turned the Hold's cold engine, the Lull, on her
own valley: for forty days it has been the hour before that sunrise. The grieving are Stilled in the Rime where they
stood. Edda Holt, Maren's mother, teaches Physis **Sit With**. Physis wakes the miller and the bridge keeper, crosses
the Gorge, wakes the three who loved Tam best (Ada Lowe, Jory Pike, Ines Okon) and carries what they remember up the
Dam Stair to Maren. The Hold is hardened: she goes into Maren's mind, the Morning (the kitchen, the hall, the field, the
crest as Maren remembers it), fights the Unrisen until it stops, sits with it through the spoken final stage, and the
sun comes up.

## Author rules (2026-11-19)

1. The level after Hesper is the third Earth Great Installation and the first hardened one (an Inner Installation in a
   Just mind); the ability is **Sit With**.
2. **Look: realistic, cold dawn.** The sun 5 degrees up in the east-south-east, under the eastern ridge, so the valley
   is in blue shadow and the western peaks take the first light; mist in the low ground; frost on everything. Three
   lights: the Just's machines amber, the Rime (forced Divinity) magenta in white frost, Sit With a warm ember rose.
   When the Unrisen is sat with the sun clears the ridge.
3. Standing rules: no 3D text; one editor at a time.

## Files

| File | Contents |
| --- | --- |
| `Content/Python/physis_morrow_plan.py` | The world plan: every place, height and street, the dam, the Morning's rooms (metres, x north, y east) |
| `Tools/morrow_meshes/kit.py`, `check.py` | Mesh kit (slots, Morrow's palette) on the Grove's; validator and previewer (`--preview` to `Saved/Morrow/preview`) |
| `Tools/morrow_meshes/land.py` | Terrain (height grid, tiles with the Grove ground shader's layer weights), the reservoir's sheet, the Gorge's ice, scatter (Halcyon's houses, orchards, firs, boulders, riprap) |
| `Tools/morrow_meshes/structures.py` | The Rime (wall, mound, door), chapel, mill and wheel, Edda's bench, the Ferry Bridge, school, hangar, glider, telegraph, the dam's crest sections, the Hold, the stair's flights, the ice house, ice disc, satchel, lantern; the Morning's kitchen, Tam's chair, the hall, islands, walks |
| `Tools/morrow_meshes/figures.py` | The Stilled (eight people), the Rime-shapes (Shade, Mourner), the Unrisen (fighting) and the kneeling Unrisen |
| `Tools/build_physis_morrow.py` | Blender entry point: every module's meshes as FBX, height.bin, scatter.json (`Art/Meshes/Morrow`) |
| `Tools/build_physis_morrow_map.py` | The pause menu's map art (`Art/UI/T_UI_MapMorrow.png`) |
| `Content/Python/physis_morrow_lore.py` | All text: scans, people, the Stilled, the Morning's memories, the spoken stage, quests, enemies, tutorials |
| `Content/Python/physis_morrow_tools.py` | `morrow:` operations: materials (the frost masters `M_MW_Surface`, `M_MW_Plain`, `M_MW_Ground`; `M_MW_Stilled`, `M_MW_Ember`; frosted twins of borrowed materials, `regrade()`), import, audio, blueprints, input, map_art, level, scenario, portal |
| `Content/Python/physis_morrow_level.py` | The level build: terrain, the reservoir (ice and water) and swimming, the look, scatter (frosted), start |
| `Content/Python/physis_morrow_scenario.py` | Gameplay placement (on the Grove's scenario), the Morning, and the Center's current |
| `Tools/blueprint_logic/morrow_logic.py`, `morrow_shared.py` | Blueprint logic: Sit With, `BP_Stilled`, `BP_SitWith`, the director (the Morning, the sunrise), the current, travel; Morrow's branches in graphs other levels own (fidelity, music, load, save world 8, the map page, relics) |
| `Tools/build_physis_voice.py --morrow` | Divinity's lines, the people's pages, the Stilled's words and Maren's stage lines (Kokoro) into `Art/Audio/Morrow/Voice` (`Saved/Morrow/run/voice.sh`) |
| `Tools/build_physis_morrow_audio.py` | The music, S_Music_Morrow (a Muse Sounds score in D minor turning to D major: the lullaby), the beds S_Amb_Morrow, S_Amb_Lull (tag MorrowHush), S_Amb_Morning, and the effects S_SitWith, S_Wake, S_Inner |

## Run order

```
python3 Tools/morrow_meshes/check.py land structures figures
blender -b --factory-startup --python-exit-code 1 --python Tools/build_physis_morrow.py [-- names | --terrain | --scatter]
python3 Tools/build_physis_morrow_map.py
Saved/Morrow/run/voice.sh                                              # Kokoro, the voices
PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/build_physis_morrow_audio.py
Saved/Morrow/run/live.sh materials import map_art blueprints level audio    # the open GUI editor (import needs it)
python3 Tools/blueprint_logic/morrow_logic.py                          # stilled glow director current physis input
python3 Tools/blueprint_logic/morrow_logic.py shared hud relic music
Saved/Morrow/run/live.sh scenario portal
```

## Meshes

Conventions are Arche's (`Tools/arche/README.md`): metres, x forward (+x is a mesh's front), y right, z up; 'base'
pivots stand on z 0 with the footprint centred, except where named. Prefixes: `SM_OT_` terrain and water, `SM_ON_`
structures, props and the Morning's rooms, `SM_OE_` the Rime-shapes and the Unrisen, `SM_OP_` the Stilled. Halcyon's
houses, lamps, crates and caches (`SM_HN_`) and the Grove's trees, scans and Hedge machines are borrowed, frosted.

| Mesh | Size (x by y by z) | Notes |
| --- | --- | --- |
| `SM_ON_RimeWall` | 3 x 12 x 6 | A wall of Rime; box collision; tag MorrowScar where placed |
| `SM_ON_RimeMound` | 34 x 9 x 7 | The Rime over the Ferry Bridge; tag MorrowBridge (goes with `,mw_bridge,`) |
| `SM_ON_RimeDoor` | 0.8 x 1.8 x 2.6 | Rime in a doorway of the Morning; tags MorrowRoom1, MorrowRoom2 |
| `SM_ON_Bridge` | 32 x 5.6 | The Ferry Bridge. **Pivot at the deck's top centre** |
| `SM_ON_Wheel` | 5.2 across | The mill wheel, its axle along y; 'centre' pivot |
| `SM_ON_Dam0`, `SM_ON_Dam1` | 16 x 24 | A crest section (Dam1 leaves the kerb open for the stair). **Pivot: the roadway's top at the middle** |
| `SM_ON_Hold` | 14 x 14 x 24 | The Hold; its doors on its front (+x) |
| `SM_ON_Stair` | 10.35 x 10 x 4.49 | One flight of the Dam Stair, 15 steps of 0.30 by 0.69. **Pivot: the bottom front edge's middle** |
| `SM_ON_Kitchen` | 14.6 x 12.6 x 3.6 | The Morning's kitchen; complex collision. **Pivot: the floor's middle** |
| `SM_ON_Hall0`, `SM_ON_Hall1` | 8 x 5.4 x 3.7 | A length of the Long Hall (Hall1 holds his door). Pivot: the floor's middle |
| `SM_ON_Island` | 20 across, 8.8 deep | Ground standing in the mist, scaled per room. Pivot: its top's middle |
| `SM_ON_Walk` | 10 x 2.4 | A plank walk. Pivot at the deck's top centre |
| `SM_OP_Stilled0`..`7` | 1.66 to 1.83 m | One slot, worn in `M_MW_Stilled` (frost by custom primitive data 0) |
| `SM_OP_Unrisen` | 5.2 x 5.1 x 6.4 | The Unrisen kneeling; rests on z 0 |
| `SM_OE_Shade`, `SM_OE_Mourner`, `SM_OE_Unrisen` | 2, 4.1, 9.2 m tall | 'centre' pivot (they hover) |
| `SM_OT_Lake` | to the far shore | The reservoir's surface at plan.ICE_Z; worn as ice (MorrowScar, walkable) and as water (MorrowBloom) |

## Gameplay pieces

**Sit With** (`BP_Physis.PhysisSitWith`, input `IA_SitWith`: **H**, and the pad's **D-pad left held 0.45 s**; a tap is
still Mend, which also fires as a hold begins, as Reload and the weapon switch do for the other two holds). Needs
`,sitwith,`; no cost. She must be still (under 60 cm/s): she kneels (the get-up clip held at 13.4 s on `Body`),
`Sitting` is set, `SitAt`, `SitHealth` are noted, `,sitwith,` is reported to `PhysisUsedAbility`, and `BP_SitWith` (the
ember glow) is spawned. Pressing again (`PhysisStand`), moving faster than 45 cm/s after 0.4 s, being struck
(`PhysisHealth` < `SitHealth`), a cinematic or death ends it: the Animation Blueprint takes her back.

**`BP_Stilled`** (instance-editable `Show`, `Hide`, `Need`, `Give`, `Done`, `Denied`, `Key`, `Pages`, `Step`, `Hold`,
`Radius` cm): shown while Show is held (or empty) and Hide is not. While she sits within Radius of it, `Held` counts;
at Hold it wakes: thaws (custom primitive data 0 from 1 to 0 at 0.45 a second), gives Give, says Done, plays
"Talk <Key> 0". If Need is not held it says Denied after 2 s instead. With Pages (`|` between them) it is the spoken
stage: page k shows (and plays "Talk <Key> <k>") at k * Step + 0.4 s of sitting; Held pauses when she stands; it wakes
after Count * Step. A Stilled whose Give is held starts woken.

**`BP_MorrowDirector`**: arrival (`,morrow,` `,at_morrow,`, the first quest, Divinity's line once); every 0.25 s the
tags (MorrowScar hidden and MorrowBloom shown once `,unrisen,` is held; MorrowBridge with `,mw_bridge,`; MorrowRoom1-2
with `,mw_room1-2,`; MorrowWay shown with `,mw_room3,`), the quests that follow a token, and the way in and out: with
`,mw_inner,` she is taken to the TargetPoint MorrowInner (`,mw_in,`), with `,unrisen,` back out to MorrowCrest
(`,mw_out,`, and `SunAt`); below plan.INNER_KILL_Z in the Morning she is put back in the kitchen. Every 0.1 s the sun
(tag MorrowSun) from pitch -5, 9 lux, rose gold to pitch -26, 15 lux, warm white over 40 s after `SunAt`, and
`MPC_Grove` Heal with it (the frost thaws); `MorrowHush` sounds fade once the Unrisen is sat with: over 3 s in play, and at once after a load that finds it done
(`grove_logic.hush`, 2026-11-19).

**Travel**: `BP_MorrowCurrent` (token `,trip_m,`, tags `MorrowArrival` / `MorrowReturn`), in the Center's sanctum 16 m
south-east of the Heartbloom (Need `,cantor,`) and at the Pass Chapel. Saves on Morrow hold `,at_morrow,` and load
`L_Morrow`; the save's exact spot is world 8.

**Tested in Play-in-Editor**: see GAME_ROADMAP.md, Level 8, "Status".
