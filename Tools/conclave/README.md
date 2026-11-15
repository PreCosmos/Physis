# The Conclave (level 3): build contract

Design: GAME_ROADMAP.md, section "Level 3 — The Conclave". This file is the contract every script of
the level follows: names, sizes, slots, variables and tokens. Change it before changing an interface.

## Author rules (2026-11-06)

1. **Realistic shading. No cel shading anywhere in the level**: no PP_CenterCel or any post-process
   material, no ink lines, no quantised light bands. PBR materials (real roughness, metallic, normal
   detail), physically plausible albedo (no albedo above 0.9), real lights, fog, AO, reflections.
2. **Six colours only: gold, light blue, red, green, black and white** (green added by the author on
   2026-11-08). Greys are mixes of black and white (stone, skin, metal). Nothing brown, olive, orange,
   yellow, purple, pink, teal or navy: not plants,
   soil, wood, water, lights, the sky, effects, or shared actors reskinned for the level.
   The one exception (author, 2026-11-09): people's bodies. Skin, lips, nails, eyes and hair (brows, lashes,
   beards included) have natural colours on the MetaHuman people (Tools/conclave/PEOPLE_DESIGN.md); their clothes,
   headwear, makeup and props keep the six colours.
   `Tools/conclave_meshes/palette.py` holds the rule (`allowed()`) and the named colours; every vertex
   colour, material constant and light colour must pass it. Soil is black; wood is painted white,
   black or red; foliage is gold, red, white or light blue; water is light blue over black.
3. The level is reached by a Divinity current in the Center's temple after Mend; it is large (about an
   hour); people are authored and voiced (Kokoro), no microphone.

Physis, her weapons and the HUD keep their own look.

## Coordinates and the world plan

`Content/Python/physis_conclave_plan.py` (pure Python) is the world plan: metres, Unreal axes (x north
along the drum's axis, y east, z up). The drum: radius `R` 700 m around the line (y 0, z `AXIS_Z` 706 m);
the floor strip follows the circle (z 6 m at y 0, rising to ~73 m at |y| 300 m, the walk limit). Water
stands at z 0 (the lake only). End caps at x = ±800 m. Regions, roads and landmark places are named
there; use them, never re-type their numbers.

Unreal placement is in centimetres (multiply plan metres by 100). The map frame is the Center's
(±920 m, north up), shared by the pause menu.

The plan also gives the ground shader its roads (round 2): `road_segments()` returns `[(ax, ay, bx, by, half, arc0)]`
in metres, in `drum.road_lines()` order (the `CONNECTORS` after path 7), with half widths 4.5 m on PATHS 0 and 7,
3.5 m on the others and 3.0 m on the two connectors, and arc0 the arc length from the polyline's start; `PLAZAS` are
the paved circles (`ORRERY` 45 m, `SPIRE` 60 m). They copy drum.py's roads, so the two must stay equal.

## Files and owners

| File | Contents |
| --- | --- |
| `Tools/conclave_meshes/palette.py`, `toolkit.py`, `check.py` | Palette rule, mesh toolkit (pure numpy), offline validator |
| `Tools/conclave_meshes/drum.py` | Terrain (height grid, tiles, colours), water, windows, upper land, end caps, Spine, parapets, scatter and town layout |
| `Tools/conclave_meshes/architecture.py` | Commons, Wellspring and Old Quarter buildings and street props |
| `Tools/conclave_meshes/districts.py` | Terraces, Reservoir, Foundry, pylons, Spire, docks, gates, portal, items, augmentations, pickups |
| `Tools/conclave_meshes/people.py` | Garments for the Mannequin people, and the robots, Mechanoid, Mecha, Lightforms |
| `Tools/conclave_meshes/al_flora.py` | AL enemies and all vegetation |
| `Tools/build_physis_conclave.py` | Blender entry point: builds every module's meshes and exports FBX, height.bin, scatter.json |
| `Content/Python/physis_conclave_tools.py` | `conclave:` operations: materials, import, audio import, level, Blueprints, input, save |
| `Content/Python/physis_conclave_ground.py` | M_CNGround and M_CNWater (round 2; `materials()` builds them through it) |
| `Content/Python/physis_conclave_fab.py` | The Fab packs in the palette: M_CNFab, M_CNFabLeaf and the placed pack meshes (folder `Conclave/Fab`) |
| `Tools/conclave/apply_look.py` | A lighting pass without a level rebuild (`conclave:exec`) |
| `Tools/conclave_textures/textures.py`, `atlas.py`, `scans.py` | Texture sets, the foliage atlas, Megascans downloads as greyscale sets |
| `Content/Python/physis_conclave_scenario.py` | Gameplay placement (the scenario), the Center's portal |
| `Content/Python/physis_conclave_lore.py` | All text: scans, people, enemies, tutorials, messages |
| `Tools/blueprint_logic/conclave_logic.py` | Blueprint logic: BP_NPC, BP_Current, BP_ConclaveDirector, BP_LightTrail, BP_Physis additions, input |
| `Tools/blueprint_logic/conclave_hud.py` | The one BP_PhysisHUD batch: DrawInteract, DrawTalk, PageMap |
| `Tools/blueprint_logic/center_overrides.py` | Conclave branches in shared graphs (see below) |
| `Tools/build_physis_conclave_audio.py`, `Tools/build_physis_voice.py --conclave` | Music, sound effects, ambience, voices |
| `Tools/build_physis_conclave_map.py` | Pause-menu map art |

## Meshes

Generators are Python modules under `Tools/conclave_meshes/` that import `toolkit` and `palette` and
expose `MESHES` (builders returning a `toolkit.Part`), optional `VARIANTS` and `CONTRACT`. They must not
import bpy. `check.py <module>` must pass before a module is done.

- Units metres; x forward, y right, z up; faces wound so their front (numpy `cross(v1 - v0, v2 - v0)`)
  points out of the solid (the toolkit's primitives already do; `hexa()` orients faces for you).
- Pivot: things that stand on the ground start at z 0 (lowest point) with their footprint centred on
  the origin; things that float or hover (AL, items, the Spine) are centred on the origin. A mesh
  with a front (houses, people, gates, figures) faces **+x**.
- Prefixes: `SM_CD_` drum structure, `SM_CN_` structures and props, `SM_CP_` people and figures,
  `SM_CE_` AL enemies, `SM_CV_` vegetation and scatter. Budgets in `check.py`.
- Every declared slot must be used by at least one face (an unused slot imports as a stray
  WorldGridMaterial slot in Unreal).
- Realism: proportions and details of real things (mouldings, sills, frames, bevelled edges, tiles,
  rivets, seams, hinges), varied by seed so repeated meshes do not look stamped. Bevel structural
  edges (`bevel_box`), because a sharp-cornered box under PBR light reads as CG. Vertex colour can
  carry ambient occlusion and grime (darken toward the ground, in crevices), but colours stay in the
  palette: shade greys freely; keep shaded golds and reds bright enough to pass `allowed()`.

### Material slots (vertex colour is the albedo; the slot decides the surface)

Each slot maps to `MI_<slot>`, unless `MESH_LOOKS` (round 2, see Materials and rendering) gives that slot on the
meshes of one name prefix its own instance.

| Slot | Surface (Unreal material instance) | Typical vertex colours |
| --- | --- | --- |
| `CN_White` | Limestone dressings (quoins, sills, surrounds, mouldings, voussoirs, piers) and white stone, rock: rough 0.5 (`MI_CN_White`, the Limestone set). The Archive, the Shrine, the Orrery and the figures' white plates keep marble (`MI_CN_Marble`, the Stone set) | WHITE, IVORY, WHITE_COOL, ASH; dressings grey .62-.68 |
| `CN_Plaster` | Lime render (round 2): house and ruin walls, chimney stacks, parapet walls, the gate's spandrels and attic (`MI_CN_Plaster`, the Render set, damp toward the wall's foot) | WHITE_PURE (whitewash) |
| `CN_Black` | Black stone, slate, soot: rough 0.7 | BLACK, CHARCOAL, SLATE |
| `CN_Lacquer` | Glossy painted or lacquered: rough 0.15. The AL's and the figures' plates are satin enamel (`MI_CN_Enamel`, rough 0.3) | BLACK, RED, WHITE_PURE, BLUE |
| `CN_Metal` | Dark steel: metallic 0.9, rough 0.35. The Foundry's plant, the workshop, cranes, pipe racks and bridges, pylons, sluices, boards, the lift, the cradle and the freighter are painted, blackened iron with bright steel in its scratches (`MI_CN_Iron`) | CHARCOAL, SLATE, ASH |
| `CN_Gold` | Gold metal: metallic 1, rough 0.18 (polished) | GOLD, GOLD_PALE |
| `CN_Red` | Red paint, tile, terracotta-free red stone: rough 0.55 | RED, RED_DEEP, RED_BRIGHT |
| `CN_Blue` | Light-blue glazed tile, ceramic, paint: rough 0.3 | BLUE, BLUE_PALE |
| `CN_Cloth` | Fabric, rope, paper: rough 0.95 | any palette colour |
| `CN_Leaf` | Foliage, petals, grass: two-sided foliage shading; atlas cards (vertex alpha 0) and solid leaves (alpha 1). Trees, shrubs, hedges and vines use `MI_CN_LeafCrown` | GOLD_GRASS, GOLD_STRAW, RED_DEEP, RED_BRIGHT, WHITE_PURE, BLUE_PALE |
| `CN_Bark` | Tree bark, limbs and woody stems (since 2026-11-07; the Bark texture set) | CHARCOAL, IVORY, WHITE_PURE |
| `CN_Glow` | Light-emitting surfaces (windows lit from inside, lamps, Lightforms, AL eyes; the AL's glows are `MI_CN_ALGlow`) | LIGHT_WHITE, LIGHT_WARM, LIGHT_GOLD, LIGHT_BLUE, LIGHT_RED, GLOW_RED, GLOW_GOLD (brightness = vertex colour; see the glow rule) |
| `CN_Glass` | Glass, translucent; its look differs per mesh (`MESH_LOOKS`): light-blue glass (`MI_CN_Glass`), the drum's windows (`MI_CN_SpaceGlass`), window panes (`MI_CN_Pane`), crystal lit from within (`MI_CN_LightGlass`), the Orrery's basin water (`MI_CN_WaterBasin`), Iriel's and the Wisp's veils (`MI_CP_LightVeil`) | BLUE_PALE, WHITE_COOL |
| `CN_Ground` | Terrain only | see Terrain |
| `CN_Water` | Water only: the lake (`MI_CN_Water`); the Orrery, the Wellspring garden, channels and sluices (`MI_CN_WaterBasin`) | BLUE_ICE |

### Required meshes (names are the contract; sizes in metres are x by y by z)

Drum (`drum.py`):
`SM_CD_Terrain_<i>_<j>` (i 0-7 along x, j 0-1 along y; `CN_Ground`), `SM_CD_Water` (lake rectangle
x -70..150, y -60..100 at z 0), `SM_CD_Windows`, `SM_CD_UpperLandE` / `SM_CD_UpperLandW`,
`SM_CD_CapSouth` / `SM_CD_CapNorth` (vertical discs at x -800 / +800), `SM_CD_SpineDim` /
`SM_CD_SpineLit` (one third of the Spine: 533.3 long on x, radius 7, centred on the origin),
`SM_CD_ParapetW` / `SM_CD_ParapetE` (balustrades along y = -300 / +300 at terrain height, collision).

Architecture (`architecture.py`): `SM_CN_House0` (7 x 9 x <=11), `SM_CN_House1` (6 x 6 x <=13),
`SM_CN_House2` (8 x 12 x <=9), `SM_CN_House3` (8 x 8 x <=10), `SM_CN_Ruin0` (7 x 9 x <=8),
`SM_CN_Ruin1` (6 x 6 x <=7), `SM_CN_Archive` (round, radius 10, 30 tall with a gold dome; its open
arcade faces +x), `SM_CN_Orrery` (basin radius 6; gold rings to 9 tall), `SM_CN_Mendery` (8 x 10 x 6,
open toward +x), `SM_CN_Shrine` (radius 4, 5 tall), `SM_CN_Stall` (3 x 4 x 3.5), `SM_CN_Lamp`
(4.5 tall), `SM_CN_Bench` (0.6 x 2 x 0.9), `SM_CN_Planter` (1 x 2 x 1), `SM_CN_TerraceWall` (0.6 x 12 x
2.5, faces +x), `SM_CN_Stairs` (4.5 x 3 x 2.5, climbing along +x), `SM_CN_Gate` (the North Gate arch:
3 x 14 x 9, road through along x, 10 wide clear), `SM_CN_WellGarden` (ring of radius 9 around the
origin, a pool basin of radius 4 at its centre), `SM_CN_Banner` (6 tall).

Districts (`districts.py`): `SM_CN_HydroBed` (3 x 10 x 1), `SM_CN_Sluice` (1 x 3 x 3; a gold wheel at
the front), `SM_CN_Channel` (10 x 1.2 x 0.6 trough with water), `SM_CN_Board` (0.4 x 2 x 2.2),
`SM_CN_PipeBridge` (12 span on x, 4 tall), `SM_CN_Buoy` (radius 1.5; its top platform 1.2 above its
base), `SM_CN_Pier` (12 x 3 x 1), `SM_CN_Boat` (5 x 2 x 1.5), `SM_CN_Furnace` (6 x 8 x 10, glowing
mouth at +x), `SM_CN_Crane` (gantry: 4 x 22 x 14), `SM_CN_CraneBridge` (16 x 4 x 0.6 deck, pivot at the
deck's top centre, 'any' pivot), `SM_CN_CableLock` (1 x 1 x 1, centred), `SM_CN_Workshop` (10 x 14 x 8),
`SM_CN_PipeRack` (2 x 10 x 4), `SM_CN_Pylon` (5 x 5 x 18; crown crystal at the top),
`SM_CN_PylonBeam` (radius 2, 690 tall), `SM_CN_Spire` (base radius 24, 320 tall, tapering crystal),
`SM_CN_SpireGate` (2 x 10 x 9 arch), `SM_CN_LightPlatform` (hexagon radius 5, 0.8 thick, pivot at the
TOP centre: its walk surface is z 0), `SM_CN_LightRamp` (12 on x, 3 wide, rising 4; pivot at the low
end's top surface), `SM_CN_Lattice` (0.5 x 6 x 5; bars of light in a gold frame), `SM_CN_CrownDais`
(radius 9, 1 tall), `SM_CN_Cradle` (30 x 12 x 16), `SM_CN_Freighter` (60 x 18 x 16, wrecked),
`SM_CN_Crate` (2 x 2 x 2), `SM_CN_Lift` (8 x 8 x 20), `SM_CN_Barricade` (1 x 8 x 4: black emitters with
a red force sheet), `SM_CN_Current` (the portal: pool radius 3, gold ring frame 5 tall, pivot at the
pool surface), `SM_CN_StillPoint` (ring of white stones radius 3, light-blue glow), `SM_CN_LightCache`
(1 m light-blue crystal cluster, centred), `SM_CN_VaultDoor` (1 x 6 x 6, red sigil), `SM_CN_Kite`,
`SM_CN_MemoryCore`, `SM_CN_LedgerPage`, `SM_CN_SeedPod` (each under 1 m, centred),
`SM_CN_AugHealth`, `SM_CN_AugKatana`, `SM_CN_AugPistol`, `SM_CN_AugDefense`, `SM_CN_AugAgility`
(about 1 m, centred), `SM_CN_PickupHealth` (red), `SM_CN_PickupDivinity` (light blue),
`SM_CN_PickupAmmo` (gold) (each about 0.5 m, centred).

People (`people.py`): humans are the UE5 Mannequins (`/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple`
and `SKM_Manny_Simple`, 1.80 m) playing `MM_Idle`, with garments attached to bones (see People). Garment
meshes are modelled in actor space over the Mannequin's bind pose, facing +x (character's left is -y),
pivot at the feet (z 0): `SM_CP_G_<Name>`. Bind pose (cm, actor space, x forward, y right; Quinn /
Manny): pelvis z 98.7 / 95.9; spine_03 z 113.6 / 113.4; spine_05 (chest) z 139.5 / 141.1; neck z 151 /
153; head bone z 162.5 (top of the head ~180); shoulders (upperarm) y ±16 / ±19 at z 143; elbows y ±32 /
±35 at z 121; hands y ±45, x +14, z 105; hips y ±11 / ±10 at z 95; knees y ±13 at z 50; ankles y ±14 at
z 8. In MM_Idle the arms hang close to the body, so upper garments are sleeveless and snug (chest
half-width at most 0.155 m), and skirts and robes leave a hand's room at the hips.
The cast table (which body, scale, skin and garments each person in `PEOPLE` wears) is `CAST` in
`Content/Python/physis_conclave_cast.py`: a pure literal dict of strings and numbers, because the editor's
Python has no numpy and cannot import `people.py`. people.py imports it and checks every garment it names
exists; the scenario imports it in the editor.
Figures that are not human are static meshes standing on z 0 facing +x: `SM_CP_Robot` (Halden-7, 1.8
tall), `SM_CP_Courier` (Unit Quill, 1.2 tall, hovering body above a thin base), `SM_CP_Mechanoid`
(Forge-Mother Ilex, 2.6 tall, four arms), `SM_CP_Mecha` (Patience, seated, 7 tall), `SM_CP_Lightform`
(Iriel, 2.1 tall, a figure of light), `SM_CP_Wisp` (0.8 tall).

AL and vegetation (`al_flora.py`): `SM_CE_ALMite` (0.6), `SM_CE_ALLancer` (1.2), `SM_CE_ALBulwark` (2.0),
`SM_CE_EchoHunter` (1.6), `SM_CE_ALReaver` (2.4), `SM_CE_ALSiegeframe` (5), `SM_CE_ALShepherd` (7),
`SM_CE_Anchor` (1.2) — each centred, facing +x, black and white plated metal with red light (an eye
or core at +x that reads as the weak point); Echo Hunters add light-blue streaks. Vegetation (ground
pivot): `SM_CV_GrassGold` (a 1.8 m patch of tall grass clumps and low sward cards; see Foliage cards), `SM_CV_Wheat`
(1.1), `SM_CV_FlowersWhite`, `SM_CV_FlowersRed`, `SM_CV_FlowersBlue`, `SM_CV_Shrub` (1.2, white leaves), `SM_CV_Hedge`
(1 x 2 x 1.2, red leaves), `SM_CV_TreeWhite` (9, white bark and blossom), `SM_CV_TreeRed` (10, black bark, red canopy),
`SM_CV_TreeBlack` (12, black conifer), `SM_CV_FruitTree` (5, white leaves, gold fruit), `SM_CV_Vines` (hanging, 3),
`SM_CV_RockWhite`, `SM_CV_RockBlack` (1-3), `SM_CV_Reeds` (gold, 1.4), `SM_CV_Lily` (about 1.0 x 1.0 x 0.12, on water:
light-blue pads of 7-15 cm radius that never overlap, white flowers), and leaf litter under the trees,
`SM_CV_LitterWhite`, `SM_CV_LitterRed`, `SM_CV_LitterBlack` (round 2: 3 x 3 x at most 0.05, flat cards just above z 0
on `CN_Leaf` only, one colour family each, no collision). Trunks and stems use `CN_Bark`, `CN_Black` or `CN_White` and
collide; `CN_Leaf` never collides.

### Terrain (drum.py)

Height grid: x -800..800, y -350..350 m, cell 2 m (801 x 351), written to
`Art/Meshes/Conclave/height.bin` (little-endian float32, row-major: index = i * ny + j, i along x) and
`height.json` (`half_x`, `half_y`, `cell`, `nx`, `ny`, `water`, `regions`, `paths`). Shaping: the drum
circle plus gentle undulation; the Commons plaza flat within 45 m of the Orrery and terraced pads (2.5 m
steps, walkable ramps under 35 degrees) up both slopes; the Terraces stepped (3.5 m steps, ramps under
35 degrees) on the west slope; the lake bowl (ellipse `LAKE`, bed -4 m, island mound radius 16 m to +3 m
at `RESERVOIR_ISLAND`); the Foundry's pads, and a slag moat around `FOUNDRY_PYLON` (inner radius 18 m,
10 m wide, 6 m deep, unjumpable; the crane bridge crosses it toward the south-west); flat plazas at the
Spire (60 m) and the docks (arena radius 50 m); a berm beyond |y| 300 m too steep to walk; berms at the
end caps; roads flattened. Colours: golden grass lawns, white stone roads and plazas, black soil on
crop terraces, black slag and soot in the Foundry, grey metal deck in the docks, white shore sand, black
silt on the lake bed, white and grey rock on steep ground.
Keep clear of houses and scatter (radius m): Wellspring 30 at `WELL`; Orrery plaza 45; Archive 16 at
`ARCHIVE`; Mendery 12; Shrine 10; Patience 8; each pylon 22; the Spire 70; the docks arena 60; the North
Gate road (x -330..-280, |y| < 12); every road 6 either side.
Ground cover is the exception (round 2): `SM_CV_GrassGold`, `SM_CV_Flowers*` and `SM_CV_Litter*` grow from the road
edge + 0.6 m (smaller over the first 1.5 m of verge) and into the keep-clear circles, where short sward ramps in over
the outer 35% of each radius (flowers over the outer 20%); plazas, roads, decks and slag stay bare. `drum.audit()`
checks ground cover (`GROUND_COVER`) against every rule except the keep-clear circles; the audit must stay empty.

`Art/Meshes/Conclave/scatter.json`: `{mesh name: [[x_cm, y_cm, z_cm, pitch, yaw, roll, scale], ...]}`.
`SM_CV_*` rows become instanced foliage; `SM_CN_*` rows (houses, ruins, terrace walls, stairs, lamps,
benches, planters, banners, hedges are SM_CV) become individual mesh actors. drum.py lays out the town:
houses on the terraced pads facing the nearest road, terrace walls and stairs along pad edges, lamps
every ~30 m along roads, benches and planters in the plaza, ruins in the Old Quarter, orchards in rows on
the Orchard Rim; and (round 2) lilies in drifts with open water between them (none within 1.1 m of another), reeds in
belts at the waterline, vines on the corner piers of walls, and a litter mesh at the foot of every tree (white under
white and fruit trees, red under red, black under black; litter occupies nothing). Rows that collide (SM_CN_*, trees,
shrubs, hedges, rocks) must come out identical when ground cover changes, so every new layout step draws from its own
random generator and the shared one keeps its draws in order.

## Materials and rendering (physis_conclave_tools.py, physis_conclave_ground.py)

Folder `/Game/Conclave/Materials`. One master `M_CNSurface` (Default Lit): BaseColor = vertex colour x
Tint with world-space albedo variation and one macro octave (MacroScale, MacroVariation: each copy of a house takes
its own overall tone); roughness = base + noise; metallic, plus bare metal in a texture set's feature (MetalFeature); a
procedural micro-normal from world-space noise whose waves fade with their footprint on screen (no static
salt-and-pepper far away); optional marble veins and brushed streaks; a damp wall foot (Splash, SplashH: plaster only);
emissive by the glow rule below. Instances `MI_CN_<slot>` (`MI_CN_White`, `MI_CN_Plaster`, `MI_CN_Black`,
`MI_CN_Lacquer`, `MI_CN_Metal`, `MI_CN_Gold`, `MI_CN_Red`, `MI_CN_Blue`, `MI_CN_Cloth`, `MI_CN_Bark`, `MI_CN_Glow`) map
the slots of the same names; `MI_CN_Marble`, `MI_CN_Enamel`, `MI_CN_Iron` and `MI_CN_ALGlow` are per-mesh looks.
`M_CNFoliage` (two-sided foliage, masked atlas cards), `M_CNGlass` (translucent, forward-shaded reflections, `Glow` for
glass lit from within), `M_CNGround` and `M_CNWater` (see Ground and water), `M_CNSky` (black space, white stars, a
ringed gas giant banded in gold, white and light blue; the sky sphere wears its instance `MI_CNSky`), `M_CNSpineHalo`
(see Lights), `MI_CNRay_Puzzle` (gold), `MI_CNRay_Cache` (light blue), `MI_CNRay_Vault` (red) instances of the
Center's `M_DivinityRay`, `M_CNLightTrail` (Light Step's trail, light blue and white, additive), `M_CNFurnace` (the
furnace floors' grate: red and gold fire over black, never a dim maroon), `MI_CP_Porcelain` / `MI_CP_Obsidian`
(Mannequin skins from `M_Mannequin`: white and black).

**Per-mesh looks (round 2).** `MESH_LOOKS` rows are (mesh-name prefix, slot, instance); `apply_slots()` checks them
before the slot's own `MI_<slot>` and the first match wins, and the module refuses to load while a row names an
instance that `SURFACES` or `SLOT_MASTERS` does not define. One look cannot be the drum's windows onto black space, a
house's panes, the Spire's glowing crystal and Iriel's veil at once:
- `CN_Glass`: `MI_CN_SpaceGlass` on SM_CD_Windows (dark, so space reads black); `MI_CN_Pane` on houses, the Archive,
  the Mendery, the workshop, cranes, stalls and lamps (a grey film that mirrors the drum and shows the rooms behind);
  `MI_CN_LightGlass` on the Spire and its gate, light platforms and ramps, Light Caches, lattices and the Shrine (lit
  from within); `MI_CN_WaterBasin` on the Orrery's basin; `MI_CP_LightVeil` on the Lightform and the Wisp. All other
  glass, the pylon crystals included (a dark pylon must not glow), is the light-blue `MI_CN_Glass`.
- `CN_Water`: `MI_CN_WaterBasin` on the Orrery, the Wellspring garden, channels and sluices (clear grey water over
  their black beds, no foam); the lake's `MI_CN_Water` takes the master's defaults.
- `CN_Leaf`: `MI_CN_LeafCrown` on trees, the fruit tree, shrubs, hedges and vines (no ground normal, thinner cards).
- The AL (`SM_CE_`): `MI_CN_ALGlow` on `CN_Glow`, satin `MI_CN_Enamel` on `CN_Lacquer`; the Robot, the Courier, the
  Mechanoid and the Mecha take `MI_CN_Enamel` too.
- `CN_Metal`: `MI_CN_Iron` (painted, blackened iron, bright steel in the Steel set's scratches) on the furnace, the
  workshop, cranes and the crane bridge, pipe racks and bridges, pylons, sluices, boards, the lift, the cradle and the
  freighter.
- `CN_White`: `MI_CN_Marble` (the Stone set) on the Archive, the Shrine, the Orrery and the figures (`SM_CP_`); all
  other white stone is tooled limestone (`MI_CN_White`, the Limestone set).

**Glow rule (round 2).** M_CNSurface's emissive is GLOW_EMISSIVE: vertex colour x EmissiveStrength x k. A red glow (red
over four times green and blue, saturation 0.5 and more) keeps only its red channel, so exposure can no longer lift
its traces of green and blue into coral, peach or salmon, and takes k = RedScale; every other glow takes
k = lerp(1, ChromaScale, saturate(2 (saturation - 0.2))), so saturated gold and light-blue glows stop clipping to
white, and grey glows are unchanged. The defaults (RedScale 1, ChromaScale 1) change nothing; `MI_CN_Glow` has .8 and
.55, `MI_CN_ALGlow` (EmissiveStrength 24) .3 and .5. palette.py is not edited for glows: pure red is `GLOW_RED` =
(1, .005, .004), defined where it is used (physis_conclave_tools.py: MI_CNRay_Vault and M_CNFurnace's HotRed;
al_flora.py: the AL's lenses, emitters and nozzles), and the Mechanoid's furnace and visor are `GLOW_GOLD` =
(1, .70, .12) in people.py, at .55 of full strength; the Robot's and the Courier's light-blue eyes, lens and status
light run at .5, so they read light blue rather than white.

No post-process material. The post-process volume: auto exposure, bloom about 0.6, gentle vignette, no colour shift
outside the palette, and **Lumen** GI and reflections (author, 2026-11-07: AAA look, retry Lumen), hardware ray traced,
trace and scene distances 2 km, hit lighting for reflections. Lumen needs mesh distance fields for its surface cache
(without them the ground had none and shade went black), so `r.GenerateMeshDistanceFields=True` is on project-wide
since 2026-11-07 (author approved; `r.DistanceFieldAO=0` keeps the other levels' sky lights as they were; their GI and
reflections stay screen space). The editor for Conclave art runs WITHOUT -noraytracing; with it the volume's Lumen has
no hardware tracing. Nanite stays off (r.Nanite 0). Round 2 lifts and cools the shade, which was crushed to black and
brown: Lumen skylight leaking .15 with a white-blue tint, local exposure (shadow contrast .65, detail 1.1), shadow
saturation .4 (not under .35: it also greys Physis's deepest shadows), and the Spine's sun bounces 1.4 times (its
indirect lighting intensity). The volume's IndirectLightingColor stays unset: in 5.8.4 only precomputed lighting reads it.

**No ray tracing, no Nanite (author, 2026-11-15).** The project now runs with `r.RayTracing=False`,
`r.Lumen.HardwareRayTracing=False` and `r.Nanite=0` (Config/DefaultEngine.ini), so the level fits an 8 GB card: in the
editor at a town camera it took about 4.5 GB of video memory instead of about 5.8 to 6 GB. Lumen stays on and traces in
software against the mesh distance fields; side-by-side captures of the Wellspring, the Commons and the Reservoir showed
no visible change. The notes below about hardware tracing, `-noraytracing` and `RT_SKIP` describe the earlier setup;
`RT_SKIP` still keeps ground cover out of distance-field lighting. No launch flags are needed any more.

**Ray tracing and LODs (round 2).** Ground cover is out of the ray-tracing scene: scatter meshes whose names start with
`RT_SKIP` (SM_CV_GrassGold, SM_CV_Wheat, SM_CV_Flowers, SM_CV_Lily, SM_CV_Litter) have visible_in_ray_tracing and
affect_distance_field_lighting off (Lumen's surface-cache traces count every hit as opaque, so card grass roofed the
ground's bounce light; about 210k fewer instances also save VRAM). Trees, shrubs, hedges and reeds stay in, for the
lake's reflections, and shadows still come from everything. `r.Lumen.ScreenProbeGather.ShortRangeAO.FoliageOcclusionStrength=0.35`
(Config/DefaultEngine.ini, [SystemSettings]; Lumen only, read at editor start) softens the foliage's short-range AO.
LODs (`import_meshes()`): card plants get none (`NO_LOD`: grass, lilies, litter, shrubs, hedges, vines; reduction deletes
whole cards, so hedges turned into red sofas); trees `TREE_LODS` ((1, 1), (.7, .1), (.45, .03)); wheat, flowers and
reeds `PLANT_LODS`; houses, ruins, terrace walls, stairs, lamps, benches, the gate, the Archive, stalls and planters
`BUILDING_LODS` ((1, 1), (.5, .2), (.25, .08), (.12, .03)), complex collision on LOD0; rocks and the AL `LODS`.

**Texture detail (2026-11-07).** `Tools/conclave_textures/textures.py` (numpy) writes tileable 2048 px sets to
`Art/Textures/Conclave` (T_CN_<Set>_M: R albedo factor, G roughness factor, B cavity, A feature; T_CN_<Set>_N: tangent
normal; greyscale data only, so hue always comes from the palette) and `textures.json` (tile sizes). Sets: Stone
(MI_CN_Marble), Limestone (CN_White), Render (CN_Plaster), Basalt (CN_Black), Gold, Steel (CN_Metal, MI_CN_Iron),
Lacquer (CN_Lacquer, MI_CN_Enamel), Plaster (CN_Red), Tile (CN_Blue), Cloth, Bark (CN_Bark); ground: Flagstone,
GrassMat (turf), Soil, Sand, Rock, Deck, Setts (roads, laid in road space), Paving (plaza ashlar); water: Ripple
(M_CNWater's capillary normals). New sets go at the end of SETS: each set's seed is its index, so inserting one would
change every later set. `conclave:textures` imports them (BC7 masks, BC5 normals) to `/Game/Conclave/Textures`.
M_CNSurface samples its instance's set triplanar in object space (`DETAIL_SETS`, scalars DetailTile, AlbedoDetail,
RoughDetail, CavityAmount, FeatureAmount/Colour/FromBase/Rough, DetailNormalStrength); M_CNGround samples its ground sets
in world space by class (grass, paving, shore sand, steep rock, soil, the docks' deck; Setts on roads, Paving in the
plazas). The old procedural veins, brushing and flags are off where a set carries them.
`Tools/conclave_textures/scans.py` (headless Blender; `--list` runs in plain Python) turns Megascans surfaces unzipped
to `~/Downloads/Conclave/<listing name>/` into the same greyscale layout (a scan's hue is discarded) for Setts, Paving,
Sand, Soil, GrassMat and Rock, writes them over the procedural maps of those names and marks them
`'for': 'scan: <listing>'` in textures.json; textures.py then skips any set marked 'scan:' unless given `--force`.

**Ground and water (round 2).** `Content/Python/physis_conclave_ground.py` (editor Python, no numpy; it builds with
physis_conclave_tools' material helpers) makes `M_CNGround` and `M_CNWater`; `materials()` reloads it through
`ground_module()`, because the operation dispatcher reloads only the plan, the lore and the tools module. M_CNGround:
height-blended class edges a few centimetres wide (GROUND_W: Band, BlendHeight, BlendNoise) instead of a 2 m linear
smear; above z 500 m (the far side) top projection and noise in drum coordinates (DrumR, AxisZ); roads in road space
from `plan.road_segments()` (ROADS: Setts courses across the road, kerbs, a worn shoulder before the verge), Paving in
`plan.PLAZAS`, and the Orrery compass (rings of paving, gold inlays as metal: InlayColour, InlayStrength 0 turns them
off; a slate edge course); shore bands (swash, damp, a residue line), white sand toned down (SandBright) with ripples
parallel to the shore, DarkTint on soil, slag and silt, two-tap anti-tiling and a macro patchwork of gold and straw.
Its eight sets share wrap samplers (16 textures). M_CNWater (translucent, two-sided, refraction by pixel normal
offset): opacity from the water's depth below it plus Fresnel, its colour going from WaterColour over the shallows to
BodyColour, a lap line of foam at the shore, refraction toward IOR with depth, swells and waves faded by their
footprint, and capillaries from the Ripple set. Its parameters are the contract the instances use: scalars Ripple,
RippleSpeed, RippleDetail, Clarity, MaxOpacity, FresnelOpacity, TintDepth, Specular, Roughness, FoamWidth, FoamStrength,
IOR; vectors WaterColour, BodyColour, FoamColour. `MI_CN_Water` keeps the defaults (the lake); `MI_CN_WaterBasin` sets
TintDepth 0, Clarity 60, MaxOpacity .55, FoamStrength 0, Ripple .15 and WaterColour grey .5.

**Foliage cards (2026-11-07; round 2).** `Tools/conclave_textures/atlas.py` writes T_CN_LeafAtlas (M: R albedo factor,
G roughness, B stem mask, A opacity; greyscale data) as a 4 x 4 grid of 1024 px cells, 4096 px (`--size`, 4096 by
default). The cells, as (column, row), are the contract al_flora.py's `CELL_*` names follow: (0,0) broadleaf twig
CELL_LEAF, (1,0) blossom spray CELL_BLOSSOM, (2,0) grass clump CELL_GRASS, (3,0) conifer spray CELL_NEEDLE; (0,1)
sward strip CELL_SWARD, (1,1) seed heads CELL_SEED, (2,1) hedge mat CELL_HEDGE, (3,1) small-leaf branchlet
CELL_SMALLLEAF; (0,2) lily pad CELL_LILY, (1,2) reed stand CELL_REED, (2,2) leaf litter CELL_LITTER, (3,2) maple
branchlet CELL_MAPLE_A; (0,3) maple branchlet CELL_MAPLE_B, (1,3) blossom spray CELL_BLOSSOM2, (2,3) orchard branchlet
CELL_ORCHARD, (3,3) bare twigs CELL_TWIGS. It also writes `Art/Textures/Conclave/atlas.json` =
`{"grid": 4, "size": 4096, "cells": {"c,r": [[u, v] x 8]}}`: each cell's eight-sided hull (the k-DOP of its pixels with
alpha over .3, dilated 3 px), in cell-local uv (u right, v down), counter-clockwise. al_flora.py builds canopies,
shrubs, hedges, blossom, conifer sprays, sward, lilies, reeds and litter as atlas cards (`cards()`, `leaf_cards()`;
toolkit `Part.add(uv=...)` carries their UVs, image convention) with vertex-colour alpha 0 (CARD_ALPHA); solid leaf
geometry keeps alpha 1. Cards are cutouts: each is its cell's octagon (a 6-triangle fan; a quad where atlas.json or the
cell is missing), so its dead, shaded area is about halved, and its normals are the whole crown's (`cards(crown=...)`)
rather than one sphere per clump. M_CNFoliage is masked: cards take the atlas (stems in StemColour, not flipped on
their back faces), solid geometry its vertex colour; its subsurface opacity (LEAF_OPACITY) is CardSubsurfaceOpacity .2
on cards and SolidSubsurfaceOpacity .6 on solid leaves (`MI_CN_LeafCrown` .25), and light through a leaf keeps its hue
(TransmissionBright .55), so a backlit red leaf glows red instead of maroon. Canopy clumps have no dark filler ball
any more (it showed between the cards).

**Water and glass (2026-11-07; round 2).** `r.Lumen.TranslucencyReflections.FrontLayer.EnableForProject=True` (project
config; only levels with Lumen reflections use it) lets the translucent lake and glass take Lumen reflections. The
dark glass of 2026-11-07 blanked every house window, the Spire, the crystals, the Orrery's basin and Iriel's veil, so
glass looks are now per mesh (MESH_LOOKS): only the drum's windows keep it (`MI_CN_SpaceGlass`: tint grey .03, opacity
.06), and `MI_CN_Glass` is visible light-blue glass again (opacity .2; its hue is the BLUE_PALE vertex colour).
M_CNGlass keeps TLM_SURFACE_PER_PIXEL_LIGHTING, which in 5.8.4 is the Surface ForwardShading mode front-layer
reflections use. The fog is thin (density 0.0055, start 30 m), without directional inscattering (its lobe sat on a
fixed sun direction, a glow in the sky unrelated to the Spine), and FOG_BRIGHT is .9. M_CNSky's haze over the windows
is the engine fog's own line integral through both height-fog layers, times SkyHaze .6 (the drum's air scatters
forward, toward the Spine, and the windows are mostly seen away from it), so black space reads no brighter than black
ground at the same range; SkyHaze and HazeBright tune on `MI_CNSky` without a recompile (rebuild the sky material
after changing FOG).
Lights: the Spine's sun (directional, tag `SpineSun`, white, pitched -58 deg from yaw -60 so shadows read; intensity
grows with the pylons: the director's SunBase and SunStep), and since round 2 'Spine Fill E' and 'Spine Fill W' in
place of the one 'Spine Fill': directional, movable, white, no shadows, not the atmosphere's sun, tag `SpineSun` (the
director brightens them with the sun), on lighting channel 1 only. Each travels from the axis toward its upper land's
centre, raked 20 deg along x (pitch about 28, yaw 67.2 for E and -112.8 for W), so each land takes 0.81-0.94 of the
Spine's light across its width, and the east fill lights the north cap and the west fill the south cap. The upper
lands and both end caps take lighting channel 1 only (DRUM), and Lumen's surface cache honours lighting channels, so
the fills add neither light nor bounce on the floor. A sky light (light-blue-white), exponential height fog
(white-blue, two layers, gives the far end-cap haze), sphere reflection captures at the Commons, the Reservoir, the
Foundry, the Spire and the docks, gold point lights at lamps, red ones at AL nests, light blue at Lightform places.
**Spine halo (round 2).** `M_CNSpineHalo` (unlit, additive, after depth of field, arithmetic only) is the Gaussian
glow of the air around a lit third of the Spine (HALO_SIGMA 2500 cm, HALO_INTENSITY 30), integrated along the view ray
over that third's length. `spine_halos()` places 'Spine Halo 1..3' (engine cylinders along x, radius 90 m, 533.3 m
long, folder `Conclave/Spine`; no collision or shadow, out of ray tracing, reflection captures and distance-field
lighting), tagged `SpineLit1..3` and hidden in game, so BP_ConclaveDirector shows each halo with its lit third. The
dark thirds have none.
Tags placed by the level build: `SpineDim1..3`, `SpineLit1..3` (south, middle, north thirds of the
Spine; a lit third's halo carries its tag), `SpineSun` (the sun and both fills).
**Lighting without a rebuild (round 2).** `Tools/conclave/apply_look.py`, run with `conclave:exec:<absolute path>`,
re-places the lights, the haze, the look volume, the halos and the sky's material, and sets the ray-tracing flags
(RT_SKIP) and the lighting channels; recapture the sky light and save the level afterwards.

**Fab packs (2026-11-07).** `Content/Python/physis_conclave_fab.py` brings the author's free Fab packs in
(/Game/AncientTreasures, /Game/SICKA_MouldingSet, /Game/OldWest, /Game/GV_FreeShrubsPack, kept as Fab delivered them)
through two palette-locked masters: `M_CNFab` (opaque) and `M_CNFabLeaf` (masked two-sided foliage with wind) remap
every texel into one palette family by its hue, never a blend, set on the placed actors only. `place()` puts the
packs' meshes in the folder `Conclave/Fab` (labels `Fab ...`): treasure hoards in the three vaults, offerings at the
Shrine, urns and statues at the Archive, 6 m marble columns with gold urns at the plaza entrances and the North Gate,
shrubs round the Wellspring garden, the Commons plaza and the Archive, yucca, Joshua trees and juniper among the Old
Quarter's ruins. It reads the scenario's vault doors and Shrine, so it runs after `conclave:scenario`, and
`conclave:level` deletes its folder with every other Conclave actor. Its marble (`MI_CN_FabStone`) takes
`MI_CN_White`'s values with the Stone set, so retuning MI_CN_White also changes the Fab columns.

## People (BP_NPC) and Blueprints

Blueprint assets live in `/Game/Characters/Physis/Blueprints` (as the Center's do).

**BP_NPC** components: `Body` (SkeletalMeshComponent, relative yaw -90, single-node animation MM_Idle
looping when it has a mesh), `Lower`, `Upper`, `Head` (StaticMeshComponents: the garments, on Body's bones `pelvis`,
`spine_05`, `head`), `Shape` (StaticMeshComponent for figures that are not human). Round 2: the Blueprint attaches
Lower, Upper and Head to those bones keeping their relative transforms (KeepRelative) in its construction script and
again first in BeginPlay; the scenario sets each garment to the actor's transform while the body shows the bind pose
and attaches it keeping world, which stores the garment's transform relative to its bone. A compile re-runs
construction and used to put the Blueprint's own components back under the root, where those bone-relative transforms
laid every person's clothes on the ground (2026-11-07 review); KeepRelative re-reads them against the bone, so placed
people are repaired by the next compile. Never SnapToTarget: the garments are modelled in actor space.
Instance-editable variables: `Speaker` (string), `Key` (string), `Pages` (string, pages joined by `|`,
wrapped with `~` line breaks), `Asks` (string, topic labels joined by `|`), `Starts` (string, each
topic's first page index joined by `|`), `Greet` (int, greeting page count), `Show`, `Hide` (string
tokens), `Give` (string: one or more tokens), `Quest` (string), `RewardDivinity` (float), `RewardHeal`
(bool), `Note` (string), `Face` (bool, default true), `Bob` (float cm, idle float for figures that hover).
Runtime: `Talking` (bool), `Page`, `Stop`, `Mode` (0 reading, 1 choosing), `Row`, `OptCount` (int),
`Fresh`, `Rewarded` (bool), `PageText`, `Opt0`..`Opt3` (string), `HomeYaw` (float).
Functions: `TalkStart`, `TalkKey(Code)` (1 confirm/next, 2 up, 3 down, 4 leave), `TalkEnd`, `TalkShow`.
Voice: page k plays `BP_Physis.PhysisNarrate("Talk <Key> <k>")` (a BP_LogVoice with that title).
Talking pauses the game; `BP_Physis.Talking` mirrors it. A greeting's end gives Give once, sets Quest,
grants RewardDivinity / RewardHeal (heal after PhysisFidelity so a Health Augmentation heals to the new
maximum), and TalkEnd says Note once.

**BP_CutGrass, goldgrass** (author, 2026-11-15: no loose pickups in the Conclave; a grass her blade cuts drops them, and
it can be scanned). `Shape` is `SM_CV_Wheat` in `MI_CN_CutGrass` (a gold-tinted `MI_CN_Leaf`), no collision. Variables:
`Chance` (float, 0 means 0.5), `Regrow` (float, 0 means 120 s), `CutAt`, `Roll`, `Full` (BeginPlay stores Shape's relative
scale in it). `GrassCut` flattens Shape to 8% of `Full`'s height, plays `S_SwordSwing2`, starts the `GrassRegrow` timer, and
half the time (always while she has under 25 Divinity or under 30% health) drops one `BP_Pickup` 1.1 m up: health 40%,
Divinity 35%, ammo 25%, gone after 3 minutes. `GrassRegrow` puts Shape back to `Full`. `BP_Physis.PhysisStrikeNow` ends with
a loop that calls `GrassCut` on every tuft within 2.6 m in front of her. The scenario's `pickup()` now calls `grass()`: a
clump of five tufts (three, drawn in, on a piece in the air) at Shape scale `GRASS_SIZE`, the first carrying the
`GRASS_ENTRY` tag ('Items', 'Goldgrass'); its voice is `S_VO_Goldgrass`. The level holds 169 tufts in 35 clumps, folder
`Conclave/Grass`. The Blueprint is shared with the Center, which gives its tufts their own mesh and size. Enemy drops are
unchanged. The Blueprint and the strike loop were written with the 5.9 tools (see below), not by conclave_logic.py.

**Blueprint tools in 5.9 (2026-11-15).** The `BlueprintToolsets` plugin is enabled in Physis.uproject. Graphs are read and
written with `BlueprintToolsets.BlueprintDslToolset` (Read, Write, Edit, Schema, FindNodeReferences, Docs; a new dialect
with backtick names) and Blueprints are edited with `BlueprintToolsets.BlueprintToolset` (AddVariable, AddFunctionGraph,
CompileBlueprint...). `editor_toolset.toolsets.blueprint.BlueprintTools` and `editor_toolset.toolsets.actor` no longer
exist, so conclave_logic.py, center_overrides.py and the other Tools/blueprint_logic scripts cannot run until ported.

**BP_Current** (`Shape` = `SM_CN_Current`): `Need` (string), `Dest` (int: 1 to the Conclave, 2 to the
Center), `Radius` (float, 180). Visible only when Need is held; standing within Radius for 0.8 s
travels (`PhysisToConclave` / `PhysisConclaveHome`).

**BP_ConclaveDirector** (no mesh): first frame of a visit says the arrival message and narrates
`Arrival` once (`,conclave_seen,`); every 0.25 s shows the lit Spine thirds in the order the pylons' beams strike
them (the first pylon relit lights the middle third `SpineLit2`, the second the south `SpineLit1`, the third the
north `SpineLit3`; each `PylonBeamN` shows with its own pylon), raises `SpineSun` intensity by `SunStep` per pylon from
`SunBase`, and reskins any `BP_Pickup` into the palette meshes by Kind (drops are spawned at runtime with
station meshes). Its presence also marks the level for the shared graphs' Conclave branches.

**BP_LightTrail** (`Shape` engine cylinder, `M_CNLightTrail`): Light Step's streak; fades in 0.35 s.

**BP_Physis** additions: variables `Talking` (bool), `StepReady`, `StepEnd` (float), `StepDir` (vector);
functions `PhysisLightStep` (IA_LightStep: X, Gamepad_LeftShoulder), `PhysisLightStepEnd`,
`PhysisToConclave`, `PhysisConclaveHome`; `PhysisInteract` gains a first loop over BP_NPC (within 300 cm,
shown) that starts a conversation. Light Step: needs `,lightstep,` and not Cinematic/dead/talking; 0.9 s
between steps; no Divinity cost; calls `PhysisUsedAbility(",lightstep,")` first, then 0.1 s later
launches 4800 cm/s along the movement input (or facing), gravity off and SafeUntil +0.35 s during the
0.15 s step, then restores gravity and caps speed to 600 cm/s; spawns BP_LightTrail; plays S_LightStep.

**BP_PhysisHUD** (one batch per editor launch, conclave_hud.py): `DrawInteract` (adds a "E  Talk" icon
over a shown BP_NPC within 300 cm and calls `DrawTalk`), `DrawTalk(SizeX, SizeY)` (the talk panel and
key polling while `BP_Physis.Talking`), `PageMap` (a Conclave branch with `T_UI_MapConclave`, keyed on a
BP_ConclaveDirector being present, before the Center branch).

**Graphs a station rebuild rewrites** (Center session, 2026-11-06): rebuild2.sh runs scenario_bp.py (which
rebuilds `PhysisInteract`) and feat.py (which rewrites `DrawInteract`) before center_music.py runs
center_overrides.py. So the whole Conclave versions of `PhysisInteract` (the cinematic branch first, then
people, doors, switches, the fallback last) and `DrawInteract` live in center_overrides.py as part
`conclave`; conclave_logic.py and conclave_hud.py take their code from there. A station rebuild does not drop
input events (its only EventGraph write is feat2.py's EventTick, and write_graph_dsl keeps every other event root),
so `conclave_logic.py input` after a rebuild is only a safety net. rebuild2.sh runs part `conclave` through
center_music.py; center_overrides.py only compiles, so save BP_Physis afterwards (`aaa:save_asset:` its path).
Since 2026-11-09 (station session) combat.py's helper head skips every graph center_overrides.py owns (its
CENTER_OWNED set), so scenario_bp.py and feat.py no longer write `PhysisInteract` and `DrawInteract` over the
Conclave's, and conclave_hud.py is no longer needed after a station rebuild. Run it only when building the
Conclave itself (the first write of a fresh editor).

**center_overrides.py** Conclave branches (station and Center branches unchanged): `PhysisMusicPick`
(BP_ConclaveDirector present -> `/Game/Conclave/Audio/S_Music_Conclave`), `PhysisLoadGame` and
`MenuContinue` (`,at_conclave,` -> `L_Conclave`), `PhysisFidelity` (`,lightstep,` -> 3; `,settle,` or
`,conclave,` -> at least 2), `AUGMENTS` (adds `,aug_hp5,`, `,aug_hp6,`, `,aug_katana4,`, `,aug_pistol3,`,
`,aug_defense4,`, `,aug_agility4,`), part map's `PageMap` (same as conclave_hud.py). The level holds a
`BP_Awakening` with TestArrival off, which is how the shared graphs know an open-world level.

## Gameplay (physis_conclave_scenario.py)

Level `/Game/Levels/L_Conclave`; actors labelled `Scene <label>`, folders `Conclave/<folder>`.
Tokens: `,conclave,` `,at_conclave,` `,conclave_seen,` `,kairos,` `,sluice1-3,` `,pylon1,` (Terraces)
`,anchors,` `,pylon2,` (Reservoir) `,bridge,` `,pylon3,` (Foundry) `,spire,` `,lightstep,` `,crown,`
`,docksgate,` `,shepherd,` `,conclave_done,`, side requests `,orsolya,` `,seedpod,` `,petra,` `,page1-3,`
`,pages,` `,tamsin,` `,kite,` `,halden,` `,core,` `,wisp,`, augmentations as above, puzzles `,cn_*`.
Encounter rooms 301-399 (unique). Shared actors are reskinned into the palette: BP_SettleBarrier ->
`SM_CN_Barricade`, BP_AbilitySocket -> `SM_CN_Lattice` (or `SM_CN_VaultDoor`), BP_Hazard (furnace
floors) -> a red-gold glowing grate material, BP_Pickup -> the palette pickups, BP_Rise -> its own mesh,
BP_Relic -> the item or augmentation mesh, BP_Switch -> its prop (pylon foot, sluice, board, lever),
BP_DivinityRay -> `MI_CNRay_*`. Every person in `PEOPLE` gets a BP_NPC and one BP_LogVoice per page.
`place()`'s report lists under `people` (round 2) every Body that shows no Mannequin and every garment that is not
attached to its bone, hangs from a bone the body lacks, or has its world-bounds centre more than `GARMENT_REACH` (50 cm)
from that bone (a long skirt's sits 41 cm from the pelvis by design); the list must come out empty.

The Center's portal (`conclave:portal`, re-runnable, in L_CenterOfTheUniverse) is labelled `Conclave Current`,
`Conclave Current Tutorial` and `Conclave Current Tag` — never `Scene ...` (the Center scenario's clear()
deletes those) or `Cine ...` — and sets the placed `Scene Heartbloom Pedestal` actor's Done text to exactly:
"The Heartbloom opens in Physis's hands, and she understands how a wound is closed.~Mend learned: Z / |DL|.  Heals 6 health for 25 Divinity.~A Divinity current has opened in the sanctum.~Step into it to follow it to the Conclave, or explore the Center first."
(physis_center_scenario.py holds the same text). It saves the Center only with BP_Awakening TestArrival off.
No Conclave actor carries the tag `CineOnly` (BP_Awakening destroys those on every start).

## Audio

Voices (Kokoro, `Saved/AudioTools`, see memory kokoro-voice-workaround): Divinity's scans in `bf_emma`
with her effect, one wav per Logbook title (`physis_lore.voice_name(title)`); each person's pages in the
person's voice with an effect by kind (`human`, `robot`, `mechanoid`, `mecha`, `light`), file
`voice_name(person_key(key, page))`. Output `Art/Audio/Conclave/Voice/`, loudness -12 LUFS like Divinity.
Music `Art/Audio/Conclave/S_Music_Conclave.wav` (orchestral, warm; the Center's SoundFont pipeline).
Effects `S_LightStep`, `S_PylonWake`, `S_SpineWake`, `S_CurrentTravel`, `S_TalkOpen`, `S_LatticeOpen`;
ambience `S_Amb_Commons`, `S_Amb_Drum`, `S_Amb_Foundry`, `S_Amb_Water`. Imported to `/Game/Conclave/Audio`
(voices to `/Game/Conclave/Audio/Voice`). Music and ambience use the Center's `SC_CenterMusic` class and voices
`SC_CenterVoice`, so BP_Awakening's SyncMix carries the Music and Voice Volume settings to them.

**People's voices, Chatterbox (author, 2026-11-15: "make the voices of the NPCs more natural").** The 92 spoken pages of the
people (`S_VO_Talk*`) are no longer Kokoro's takes. Each is spoken by Chatterbox (Resemble AI, MIT licence; pip
`chatterbox-tts`, CPU, in `Saved/AudioTools/chatterbox_venv`), cloning its speaker's Kokoro voice from a dry 10 s
reference take, then put through that speaker's own chain, room and loudness from Tools/build_physis_voice.py
(`KINDS`), so robots, the Mechanoid, the Mecha and the Lightforms keep their sound. Divinity's narration is still
Kokoro. The scripts are copies kept in `Tools/conclave_voice/`; they run from `Saved/AudioTools/voice_test/` (paths are
relative to that folder): `make_refs.py <voices>` (Kokoro venv, with the bundled espeak variables), `batch.py`
(Chatterbox venv; about 40 s a page; each take is transcribed with faster-whisper and redone when under 90% of its
words match; `report.json` holds what was heard), `wet.py` (Kokoro venv), then copy `conclave_wet/*.wav` over
`Art/Audio/Conclave/Voice/` and import them. Do not run build_physis_voice.py `--conclave` without `--only` after
deleting any `S_VO_Talk*.wav`: it would remake that page with Kokoro. The previous files are in git history and in
`Saved/Backup_2026-11-15_voices`.

## Run order

1. `Tools/conclave_textures/textures.py` and `atlas.py --size 4096` (numpy, any time before the editor's
   `conclave:textures`; `--sheet` writes a preview to Saved/Conclave to look at); optionally, after textures.py and
   once the author's Megascans downloads are in ~/Downloads/Conclave, `Tools/conclave_textures/scans.py` in headless
   Blender (`... -b --python ~/PhysisProject/Tools/conclave_textures/scans.py -- --src ~/Downloads/Conclave`; look at
   Saved/Conclave/scan_sheet.png); then
   `flatpak run org.blender.Blender -b --python Tools/build_physis_conclave.py` (meshes, height, scatter; with mesh names
   after `--`, only those meshes, and height and scatter stay; through `flatpak-spawn --host` use the absolute
   ~/PhysisProject path), then
   `Tools/conclave/sim_scenario.py --prune` (venv numpy: drops the scatter rows the scenario's set pieces stand on,
   and checks the whole scenario offline; re-run it after any scatter.json rewrite), then
   `Tools/build_physis_conclave_map.py` (map art from height.bin, numpy)
2. Voices and audio (Kokoro venv; see the voice memory)
3. Editor (fresh, GPU, ray tracing on: no -noraytracing; `-ExecCmds="r.Nanite 0,..."`; it reads Config/DefaultEngine.ini
   only at start): `conclave:textures`, `conclave:materials` (its report lists the instances, the relinked meshes and
   anything SKIPPED; the Fab masters come from `physis_conclave_fab.materials()`, run once), `conclave:import`,
   `conclave:audio`, `conclave:map_art`, `conclave:blueprints`, `conclave:level` (map art before the HUD batch,
   whose PageMap names T_UI_MapConclave)
4. `python3 Tools/blueprint_logic/conclave_logic.py` (BP_NPC's construction script and BeginPlay attach the garments:
   read both graphs back); then `center_overrides.py music saves menu progress conclave`
   and save BP_Physis, BP_Switch, BP_MenuHUD and BP_Checkpoint (center_overrides.py only compiles; part saves
   rewrites BP_Checkpoint's EventGraph; part conclave makes BP_Switch.Reach, which PhysisInteract reads); then, in a
   FRESH editor as its first write, `conclave_hud.py` (PageMap, DrawInteract, DrawTalk in one batch; it refuses to
   start unless BP_NPC, the director and BP_Switch.Reach exist)
5. `conclave:scenario` (its report's `people` list must be empty), then the Fab placement through `conclave:exec` (a
   scratch script `import physis_conclave_fab as fab; RESULT = fab.place()`), `conclave:portal` (the Center's temple
   current, a targeted spawn). `conclave:level` destroys and re-places every Conclave-folder actor, scenario and
   `Conclave/Fab` included, so re-run `conclave:scenario` and then the Fab placement after any level rebuild; then the
   console's `BuildReflectionCaptures`, recapture the sky light, and save the level.
6. After a change to lighting only: `conclave:exec:<absolute path>/Tools/conclave/apply_look.py` (no level rebuild),
   then recapture the sky light and save the level; after a change to materials only, `conclave:materials`.
7. Test in Play (Tools/conclave has no PIE driver yet; the 2026-11-07 tests used EditorAppToolset StartPIE with
   `{"options": {...}}` and center:exec scripts calling BP functions on the PIE pawn). A test that saves creates
   Saved/SaveGames/Physis.sav: delete it afterwards if none existed before.

Status, 2026-11-07: built and saved; play-tested arrival, talk, Light Step, the pylons-to-Spire chain, the
arrival-by-current reload, and (by the Center session, starting from L_MainMenu so the GPU never holds both levels)
travel both ways, a death after returning, Continue, and Light Step opening a Center Light Lattice. The temple current
was then moved onto the sanctum ring floor (PORTAL 16 m north of the pedestal: the first place put a crystal inside
its reach) and no longer has a tutorial strip or scan tag in the Center (both showed before Mend). Not yet
play-tested: the Spire climb by hand, the fights and the Shepherd, a full playthrough; no package built.

AAA pass, 2026-11-07 (author: "as pretty as possible"): texture detail on every surface slot and the ground, bark,
atlas-card foliage and dense grass patches, Lumen GI and reflections with distance fields, thinner haze, dark glass,
clearer water; the same day, the author's Fab packs (physis_conclave_fab.py). Not done: the people's materials; ray
tracing's VRAM cost in the other levels and whether the shipped game should enable it only in the Conclave
(r.RayTracing.EnableOnDemand is 1).

AAA pass, round 2 (2026-11-07, after six specialist reviews): garments attached by BP_NPC itself; per-mesh glass,
water, leaf, iron, enamel and marble looks; glows that keep their hue (GLOW_RED, GLOW_GOLD); a lifted, cooler shade
and ground cover out of ray tracing; fills for the far side and both end caps; window haze matched to the engine fog;
Spine halos; height-blended ground, roads in road space with kerbs, plaza paving and the Orrery compass; depth-tinted
water with refraction and a lap line; turf, setts, paving, render, limestone and ripple sets and the Megascans
converter; a 4 x 4 cutout atlas with whole-crown normals, a real conifer, a sward, lilies at true scale, reed belts,
card hedges and shrubs, leaf litter; window rooms, lime plaster with limestone dressings, LODs that keep cards and
LODs for buildings and the AL; berm ramps and end-cap plating by band. Deferred: a lit-air shell around the Spine
(the halos give its glow), a separate dim and lit atmosphere, near-field volumetric fog (VRAM: measure what the
ray-tracing exclusion freed first), a baked far-side landscape, end-cap terraces and trusses, window frames and
glazing, the space backdrop (NASA star maps, Solar System Scope textures: next round), wind data in a second UV,
hand-built card LODs, groves (they would move colliding trees), hedge and garden beds in the architecture module,
house variants with interiors, the Orrery's and the Gate's gold geometry and scale (ask the author: both collide on
main walk lines), ruin and wreck damage (collision), a dedicated iron texture set, edge wear on the AL, faces and hair,
skinned garments, the people's skins, idle motion (Mixamo), mown stripes and a shingle band.

## Rules for anyone working on this (machine and project safety)

- Never launch Blender, Unreal or a full Kokoro run in parallel with another heavy job; the machine has
  8 GB of VRAM and has been OOM-killed. Offline checks (check.py, mocked harnesses) are fine.
- Only one editor may run (port 8000). Writes to the editor happen one client at a time.
- BP_PhysisHUD: at most one write batch per editor launch, first thing after launch, then save.
- In the Blueprint DSL: `Utilities|IsValid` only as a statement with both branches; a multi-exec node
  (a cast with :then/:CastFailed, IsValid with branches) ends the exec flow, so put follow-ups inside each
  continuation; bind gating values into variables before Set nodes run; `(return)` does not survive, use
  a flag; read every graph back after writing.
- No 3D text (TextRender) anywhere unless the author asks.
