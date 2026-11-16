# Arche, the First Ones' Planet (level 5): build contract

Design: GAME_ROADMAP.md, section "Level 5 — Arche: the City of the Descent". This file is the contract every script
of the level follows: names, sizes, slots and pivots. Change it before changing an interface.

## The level in one paragraph

Arche ("the Beginning") is the First Ones' homeworld. Kathodos, the city of the Descent, climbs a canyon basin in
three tiers. Ages ago the Vigil built the **Sundering Lens** at its head, a defence that unweaves matter, and when
the war came they fed it their own city: every bridge and stair of Kathodos was unmade so that no invader could walk
it. The stones still hang in the air where they were unwoven. The Lens's AL keepers never stopped. The Serene, who
would not leave, live cut off on the Lower Tier. Physis arrives by a Divinity current, meets **Aeon**, learns
**Reweave** (a thing remembering its shape), crosses the Great Chasm, climbs the tiers, turns three great Mirrors on
the Veil that seals the Lens Court, and stops the Sunderer.

## Author rules (2026-11-16)

1. The planet is the First Ones' Planet; its name, Arche, is proposed. The ability is **Reweave**.
2. **Look: realistic, in a cool palette.** Physically based, as realistic as the Grove, but pale stone, dark rock,
   silver, ice-blue and violet crystal with luminous edges, under a cold sun. No post-process stylisation.
3. **Aeon appears in person**, in a designed native First One form (a built figure, not a MetaHuman), with Serene
   keepers.
4. About an hour: a Great Installation (one ability, one boss, one shortcut, side requests, optional areas).
5. Standing rules: no 3D text; one editor at a time.

## Look

Three lights tell three things apart: the Serene's light is a pale **ice blue**, the Vigil's works (the Lens, the
veils, the unweaving) glow a cold **violet**, and Reweave glows a warm **pearl gold**. The AL keep their red. The
First Ones built in large, calm forms: battered (inward-leaning) walls, tall narrow openings with pointed or
parabolic heads, long unbroken courses of pale stone with one thin line of electrum inlay, silver alloy fittings,
deep blue glazed tile in the wet places, crystal set where humans would set glass. Nothing is square-cut and
brutal like the Just's concrete, and nothing is ornate: weight, proportion and one line of light. Everything is very
old: edges softened, courses stepped out of true, lichen on north faces, dust in the lee. Base colours come from
`Tools/arche_meshes/kit.py`; the surface detail comes from scanned texture sets laid on by slot.

## Files

| File | Contents |
| --- | --- |
| `Content/Python/physis_arche_plan.py` | The world plan |
| `Tools/arche_meshes/kit.py`, `check.py` | Mesh kit (slots, palette, helpers) on the Grove's and the Conclave's; validator and previewer |
| `Tools/arche_meshes/land.py` | Terrain (height grid, tiles, colours), water, scatter |
| `Tools/arche_meshes/structures.py` | The city's architecture, the weave pieces, props |
| `Tools/arche_meshes/figures.py` | The First Ones, the Sunderer, crystals, items |
| `Tools/arche_meshes/creatures.py` | Arche's animals (`SM_AE_Mote` to `SM_AE_Leviathan`) |
| `Tools/build_physis_arche.py` | Blender entry point: every module's meshes as FBX, height.bin, scatter.json |
| `Content/Python/physis_arche_lore.py` | All text |
| `Content/Python/physis_arche_tools.py`, `physis_arche_level.py`, `physis_arche_scenario.py` | `arche:` operations, the level build, gameplay placement |
| `Tools/blueprint_logic/arche_logic.py`, `arche_shared.py` | Blueprint logic: Reweave, `BP_Weave`, the director, travel; and the Arche branches in graphs other levels own |
| `Tools/build_physis_arche_map.py`, `Tools/build_physis_arche_audio.py`, `Tools/build_physis_voice.py --arche`, `Tools/build_physis_divinity_voice.py` (set `arche`) | Map art, music and effects, the people's voices, Divinity's voice |

## Meshes

Generators are Python modules under `Tools/arche_meshes/` that `from kit import *` and expose `MESHES` (a list of
builders, each returning a `Part`), optional `VARIANTS` ({builder: count}; the builder then takes the variant index)
and `CONTRACT` ({mesh name: {'size': (x, y, z) metres, 0 = any; 'tol': fraction; 'pivot': 'base' | 'centre' |
'any'; 'top': z}}). They must not import bpy. `python3 Tools/arche_meshes/check.py <module>` must pass, and
`check.py <module> --preview` draws each mesh into `Saved/Arche/preview/` so it can be looked at.

- Units metres; x forward, y right, z up; faces wound counter-clockwise seen from outside. A mesh with a front faces
  **+x**.
- Pivot: what stands on the ground has its lowest point at z 0 and its footprint centred on the origin ('base');
  what hovers or is picked up is centred on the origin ('centre'); exceptions are named below ('any').
- Prefixes and LOD 0 triangle budgets: `SM_AT_` terrain 150,000; `SM_AN_` structures and props 40,000; `SM_AV_`
  crystals and rocks 8,000; `SM_AE_` enemies 60,000; `SM_AP_` people 40,000 (exceptions in `check.py`).
- Slots (kit.py): STONE, ROCK, ALLOY, ENAMEL, ELECTRUM, RED, TILE, CLOTH, LICHEN, GLOW, CRYSTAL. Vertex colour is
  the albedo (at most 0.9); the slot decides the surface. Every declared slot must be used.
- Realism: true proportions, bevelled edges (nothing knife-sharp), courses and joints modelled where a hand could
  feel them, weathering in vertex colour (darker toward the ground and in crevices, lichen on tops and north
  sides, dust in the lee), varied by seed. Surfaces a player walks on are flat and continuous: no lips over 5 cm.

### Structures (`structures.py`)

| Mesh | Size (x by y by z) | What |
| --- | --- | --- |
| `SM_AN_Span` | 32 x 6 x 3.5 | The Sundered Span: one bridge along x, a continuous walkable deck 5 m wide with low parapets (0.9 m), three shallow parabolic ribs beneath. **Pivot at the deck's top centre** (deck top z 0 from end to end; the ribs hang to about -2.5) |
| `SM_AN_Stair` | 18 x 9 x 13.1 | A grand stair climbing toward +x: its foot at x -9, z 0; treads 0.4 m deep rising 0.3 m each (walkable: 37 degrees), 8 m clear between cheek walls; a top landing 2 m deep at exactly z 12.0, flush with x +9. Solid beneath (it stands against a cliff). 'base' pivot, footprint centred |
| `SM_AN_StepSlab` | 3.2 x 3.2 x 0.7 | A floating stepping slab, hexagonal, flat top. **Pivot at its top centre** |
| `SM_AN_Causeway` | 9 x 3.4 x 1.0 | A causeway slab along x, flat top. **Pivot at its top centre** |
| `SM_AN_Bulwark` | 0.9 x 4.5 x 2.4 | A cover wall along y, facing +x: battered, a crystal slit, a line of inlay |
| `SM_AN_Shard` (4 variants: `SM_AN_Shard0` to `3`) | 1.2 to 3.0 across | A drifting fragment of unwoven masonry: a broken block with one dressed face and a violet-lit fracture (GLOW, GLOW_VIGIL). 'centre' pivot |
| `SM_AN_Knot` | 1.4 across | The mark of something that can be rewoven: a ring of six small stone slivers round a pearl-gold core (GLOW, GLOW_WEAVE). 'centre' pivot |
| `SM_AN_Column` | 2.2 x 2.2 x 12 | A First One column: slightly tapering, twelve-sided, a plain flared head, one electrum band |
| `SM_AN_ColumnBroken` | 2.4 x 2.4 x 4.5 | The same, snapped, its break violet-scorched |
| `SM_AN_Arch` | 3 x 12 x 13 | The First Arch: a free-standing parabolic arch across y, passage along x 6.5 m wide and 10 m high |
| `SM_AN_Wall` | 1.6 x 12 x 9 | A battered court wall panel along y, facing +x, walkable top not needed |
| `SM_AN_GateFrame` | 3 x 16 x 12.5 | The portal in the Lens Court's wall: an opening 10 m wide and 10 m high, passage along x |
| `SM_AN_Veil` | 0.6 x 10 x 10 | The Veil that fills that opening: a lattice of hard violet light in an alloy frame (GLOW_VIGIL; mostly GLOW and CRYSTAL) |
| `SM_AN_House0`, `SM_AN_House1` | 8 x 7 x 6; 6 x 6 x 7.5 | Serene dwellings: battered stone cells with a tall pointed doorway on +x (1.4 x 3 m) into one open room, a crystal window, a tiled roof |
| `SM_AN_Hall` | 22 x 14 x 11 | The Hearthold's hall: an open colonnade on three sides under a tiled roof, a floor 0.6 m above the ground with steps on +x |
| `SM_AN_Mirror` | 2.5 x 5 x 7 | A great mirror on a gimballed stand, facing +x: a disc 4.4 m across of polished alloy (ALLOY, bright) in an electrum rim, its centre 4.6 m up |
| `SM_AN_Lens` | 9 x 36 x 40 | The Sundering Lens, facing -x (toward the court): a ring 30 m across on two great pylons, a faceted crystal lens in it, a violet core (GLOW_VIGIL), cables and focusing vanes |
| `SM_AN_Obelisk` | 1.2 x 1.2 x 4.2 | A record stele: four tapering faces, a crystal tip |
| `SM_AN_Lantern` | 0.7 x 0.7 x 3.2 | A First One street lantern: a slender stem, a crystal held in three alloy fingers (GLOW_SERENE) |
| `SM_AN_Pedestal` | 1.5 x 1.5 x 1.1 | A plain plinth |
| `SM_AN_Basin` | 6 x 6 x 1.0 | A round cistern basin: stone rim, blue tile lining (hollow: the water is placed separately) |
| `SM_AN_VaultDoor` | 1 x 6 x 6 | A sealed vault door along y, facing +x: one slab with a round crystal lock |
| `SM_AN_Bench` | 0.7 x 2.4 x 0.9 | A stone bench |
| `SM_AN_Urn` | 0.9 x 0.9 x 1.3 | A tall glazed urn (TILE) |

### Figures, crystals and items (`figures.py`)

The First Ones' native form (proposed design, 2026-11-16): tall and slender, about 2.3 m; a body of pale, layered
mineral plates like folded stone over a dark core that shows in the joints; a long smooth head with no face in the
human sense, only one vertical seam of light (GLOW) where a face would be; a crown of five to seven thin slivers
that float a hand's width off the head; long arms with four long fingers; they wear a mantle and a long skirt of
heavy cloth, and stand very still. The Serene wear pearl and indigo and their seam is ice blue (GLOW_SERENE); Aeon
is older than the others: taller, the plates more weathered, an electrum collar, the crown incomplete (two slivers
missing). The Vigil's colour is violet.

| Mesh | Size | What |
| --- | --- | --- |
| `SM_AP_Aeon` | 2.45 m tall | Aeon, standing, hands folded before the chest. Stands on z 0, faces +x |
| `SM_AP_Serene0`, `1`, `2` (3 variants) | 2.1 to 2.3 m tall | Serene keepers: one holds a lantern, one a tablet, one has open hands |
| `SM_AP_Vigil` | 2.35 m tall | Maruth, Lens-keeper of the Vigil: the same form in a violet mantle over night-blue enamel, a high alloy collar and pauldrons, a violet seam (GLOW_VIGIL), a full rigid crown, one hand on a crystal-tipped staff |
| `SM_AE_Sunderer` | about 8 m across, 9 m tall | The boss: the Lens's AL command frame. A ring of white enamel plates (ENAMEL) and black frame round a great violet eye (GLOW_VIGIL) at +x, four long unweaving arms ending in crystal tines, red AL signal lights, and at its back (-x) an exposed crystal heart. 'centre' pivot (it hovers) |
| `SM_AE_Mote` | 0.8 m across | Drift Mote: a small finned air-swimmer with light organs under clear crystal. All six animals (`Tools/arche_meshes/creatures.py`) have a 'centre' pivot, face +x, and wear hide (`CN_Bark` → `MI_AR_Hide`), CRYSTAL and GLOW; violet fractures show where the Lens has hurt them |
| `SM_AE_Medusa` | 1.6 m across, 2.6 m tall | Bell Medusa: a drifting bell, frilled mouth-arms (LICHEN) and long tendrils |
| `SM_AE_Shellback` | 2.2 m long | Shellback: a coiled, plated shell (ROCK) with crystal in the seams, a hooded head, beak and eight arms |
| `SM_AE_Ray` | 2.4 m long, 3.2 m span | Sky Ray: one flattened wing-body with head fins, gill slits and a tail |
| `SM_AE_Stalker` | 2.8 m long, 2.2 m tall | Crest Stalker: a long-necked crested hunter on four fin-limbs, seven violet fractures |
| `SM_AE_Leviathan` | 9 m long, 4 m tall | Leviathan: a whale-like air-swimmer with crystal barnacles and one scorched wound on its right flank |
| `SM_AV_Crystal` (3 variants: `SM_AV_Crystal0` to `2`) | 1.5, 2.5 and 4 m tall | Crystal clusters growing from a rock foot: hexagonal prisms, ice blue to violet (CRYSTAL), a little light at their cores (GLOW), ROCK foot |
| `SM_AV_CrystalGreat` | 18 m tall | A great crystal spire, a landmark of the Garden |
| `SM_AN_Cache` | 0.9 across | A geode cache: a split stone holding small bright crystals. 'centre' pivot |
| `SM_AN_Chime` | 0.6 across | A Serene wind chime: alloy tubes on a ring. 'centre' pivot |
| `SM_AN_Tablet` | 0.6 across | A record tablet: a stone leaf with a crystal inlay. 'centre' pivot |
| `SM_AN_Seedstone` | 0.5 across | A seed-crystal: a smooth egg of clear crystal with a pearl-gold core. 'centre' pivot |

No collision: `SM_AE_*`, `SM_AP_*`, `SM_AN_Shard*`, `SM_AN_Knot`, `SM_AN_Cache`, `SM_AN_Chime`, `SM_AN_Tablet`,
`SM_AN_Seedstone`. Box collision: `SM_AN_Veil`, `SM_AN_VaultDoor`, `SM_AN_Bulwark`. Everything else collides as it
is modelled.

## Gameplay pieces (as built, 2026-11-16)

**Reweave** (`BP_Physis.PhysisReweave`, input `IA_Reweave`: **B** / right stick click; V is Settle's). One press, 0.8 s
between presses, no cost, needs `,reweave,`; it reports `,reweave,` to `PhysisUsedAbility` first. The target is the
`BP_Weave` whose mark is nearest the view's centre (within 30 degrees; of marks in one line the nearer wins), within
its `Range`, shown, and either sundered or restless, with its mark in plain sight (a complex trace from her head).
`BP_ArcheDirector` runs `PhysisWeaveFind` every frame once she has the ability, so the aimed mark swells.

**`BP_Weave`** (instance-editable): `Need`, `Hide` (tokens), `Give`, `Done` (token and message when first woven),
`Hold` (seconds it stands; 0 for good), `Loom` and `Limit` (weaves sharing a loom: one more than Limit and the oldest
lets go), `Range` (cm), `Drift` (cm: how wide its slivers circle). Components: `Shape` (the thing, given its mesh and
scale per instance; hidden and without collision while sundered, it grows in over 0.8 s and is solid from 97 %),
`Mark` (the turning ring of slivers and pearl light, `SM_AN_Knot`, placed per instance), `Glow`, and `P0` to `P5`
(shards that circle the mark and fall into it as it knits). A weave whose `Give` token is held, and whose `Hold` is
0, is whole from the first frame (after a load). Restless weaves are never saved.

**`BP_ArcheDirector`**: the arrival (`,arche,` `,at_arche,`, the first quest, Divinity's line once); every 0.25 s it
hides actors tagged `ArcheScar` and shows those tagged `ArcheBloom` once `,sunderer,` is held, shows each Mirror's
shaft of light and glow (`ArcheMirrorW`, `E`, `N`) by its token, and sets the quests that follow from a token
(`,ar_q_span,` `,ar_q_mirrors,` `,ar_q_sunderer,` mark each as given).

**Travel**: `BP_ArcheCurrent` (the Grove current's graph with `,trip_a,`, tags `ArcheArrival` / `ArcheReturn`): in the
Center's sanctum 16 m west of the Heartbloom's pedestal (Need `,warden,`), and at the Landing. Saves made on Arche
hold `,at_arche,` and load `L_Arche`; the save's exact spot is world 5.

**Placement** (`physis_arche_scenario.py`): the report's `blocked` (link hops) and `hidden` (weave marks out of sight
from where she is expected to stand) must both be empty. The Chasm's rescue knots hang out over its wall so they
show from the floor; the northern one wakes only with `,ar_span,`, so the link alone never crosses.

**Borrowed**: the Ward is the Conclave's AL meshes; scanned boulders, stones and cliff faces are the Grove's,
regraded (`MI_AR_Scan_*`); the Still Point ring, the current's column and relic glows are the Conclave's; the link
knots are the Grove's. No new downloads.

**Tested in Play-in-Editor (2026-11-16, scripted)**: arrival and first quest; Aeon's talk (`,aeon,`) and the First Arch
(`,reweave,`); the Span rewoven and stood on (`,ar_span,`); both Stairs; a restless causeway letting go; the Garden's
loom dropping its oldest weave; the three Mirrors and the Veil (`,ar_veil,`); the Sunderer's room ending the level
(`,sunderer,`, the scar actors hidden, Maruth shown); the Center's current to Arche, save and load on Arche, the
current home. Not played by hand: any fight, the walk between places, the side requests' rewards, the Ossuary.

**Animals (2026-11-16)**: `ARCHE_ENEMIES` 8 to 13 in `physis_arche_lore.py` are Arche's own animals. The scenario's
`WILD` table turns every open-ground pack (room 0) from Ward tiers 1 to 6 into the animal of the same tier; the Ward
keeps the rooms it guards (Stairs, Mirrors, the Sunderer's court). The Leviathan circles the Ossuary and Crest
Stalkers keep three caches. They use the shared enemy behaviours of their tier; the story's rule for the living (they
scatter and gather again, they are not destroyed) is told in their scans, not yet shown by a different defeat effect.

**Smoothed since the first build**: the tier risers and the chasm sides are faced with `SM_AN_Wall` retaining panels;
rock and stone carry a large-scale colour breakup so the scan's repeat no longer reads; the Lens is placed twice (lit,
tagged `ArcheScar`, and a dark twin with `MI_AR_GlowOff`, tagged `ArcheBloom`) so its glow goes out with it.

**Known rough edges**: Earth-style frost grass was dropped (it stayed green under any tint); the animals share the
Ward's hit and defeat effects; crystal translucency on the animals was judged in engine only from stills.