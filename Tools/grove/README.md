# Earth, the Wounded Grove (level 4): build contract

Design: GAME_ROADMAP.md, section "Level 4 — Earth: the Wounded Grove". This file is the contract every script of the
level follows: names, sizes, slots, variables and tokens. Change it before changing an interface.

## The level in one paragraph

Earth, days after Meridian. A valley whose trees are one organism, joined at the root. The Just built the Deeproot
Array into its oldest tree, the Heartwood, to drive Divinity through those roots as a weapon against ships in orbit.
It wounded the grove: where Divinity was forced, the roots came up as thornroot. The Array's automatic defence, the
Hedge, sealed the site when the fleets fell silent, and it is still forcing the roots. Physis arrives by a Divinity
current, learns **Resonance Link** from the grove's own graft (with Thessaly-4, the Just's field botanist), gives the
grove its water and its power back, crosses the Rift, stabilises the Array and stops the Warden.

## Author rules (2026-11-10)

1. **AAA quality assets, as realistic as possible.** Earth is rendered realistically: physically based materials on
   photo-scanned surfaces, scanned plants and rocks, real proportions and construction detail, Lumen, a real sky. No
   post-process stylisation (the "warm, painterly" look GAME_ROADMAP.md once proposed for Earth is withdrawn).
2. **Scans.** Free CC0 photo-scanned assets from Poly Haven and ambientCG may be downloaded (about 6-8 GB) into
   `Art/Scans/Grove`; every file's source and licence is recorded in `Art/Scans/Grove/manifest.json`.
3. **One MetaHuman.** The Array's director, Maren Voss, is heard over intercom posts and appears in person at the
   end, built like the Conclave's people (Tools/conclave/PEOPLE_DESIGN.md). Everyone else is a machine of the Just.
4. Standing rules from earlier levels: no 3D text unless the author asks; one editor at a time; High graphics from
   Settle on (the grove's own flag counts as stage 2 at least).

## Look

Natural colours, late-afternoon sun through a real atmosphere, volumetric light in the canopy, soft warm haze. Greens
are warm (yellow in them, never blue-green); the birches and the leaf litter are gold. Made things are forty years
weathered: stained concrete, rust, moss. Three lights tell three things apart: the Just's machines glow **amber**,
thornroot (forced Divinity) glows a sick **magenta**, and resonance, the grove's own linkage, glows **green-gold
turquoise**. The level's own meshes take their base colours from `Tools/grove_meshes/kit.py` and their surface detail
from scanned texture sets laid on by slot. No 3D text anywhere.

## Coordinates and the world plan

`Content/Python/physis_grove_plan.py` (pure Python) is the world plan: metres, Unreal axes (x north, y east, z up).
Height grid x -640..640, y -480..480, cell 2 m (641 x 481), 12 terrain tiles of 320 m. The walkable valley is the oval
`RIM` (566 x 404 m semi-axes); beyond it the land climbs into cliffs. The lake stands at z 0 (`WATER`), the only
swimmable water. Unreal placement is in centimetres. The pause-menu map shares the Center's frame (±920 m, north up).

## Files

| File | Contents |
| --- | --- |
| `Content/Python/physis_grove_plan.py` | The world plan |
| `Tools/grove_meshes/kit.py`, `check.py` | Mesh kit (slots, palette, helpers) on the Conclave's toolkit; validator and previewer |
| `Tools/grove_meshes/land.py` | Terrain (height grid, tiles, colours), water, the backdrop, scatter |
| `Tools/grove_meshes/flora.py` | Vegetation: trees, the great trees, the Heartwood, undergrowth, rocks, thornroot |
| `Tools/grove_meshes/structures.py` | The camp, the road, Old Town, the campus, the weir, the relay, the Array |
| `Tools/grove_meshes/machines.py` | The Hedge (enemies), the people, link nodes and gameplay props |
| `Tools/build_physis_grove.py` | Blender entry point: every module's meshes as FBX, height.bin, scatter.json |
| `Tools/build_physis_grove_map.py` | Pause-menu map art (`Art/UI/T_UI_MapGrove.png`) |
| `Tools/build_physis_grove_audio.py`, `Tools/build_physis_voice.py --grove` | Music, effects, ambience, voices |
| `Content/Python/physis_grove_lore.py` | All text: scans, people, enemies, tutorials, messages |
| `Content/Python/physis_grove_tools.py` | `grove:` operations: materials, import, audio, blueprints, level, map art |
| `Content/Python/physis_grove_scenario.py` | Gameplay placement, and the Center's current to Earth |
| `Tools/blueprint_logic/grove_logic.py` | Blueprint logic: Resonance Link, link nodes, beams and tethers, the director, travel |
| `Tools/blueprint_logic/grove_hud.py` | The one BP_PhysisHUD batch of a launch (the map page) |
| `Tools/blueprint_logic/center_overrides.py` | Grove branches in the shared graphs (music, saves, fidelity, augmentations, map) |

## Meshes

Generators are Python modules under `Tools/grove_meshes/` that `from kit import *` and expose `MESHES` (builders
returning a `Part`), optional `VARIANTS` and `CONTRACT`. They must not import bpy. `check.py <module>` must pass, and
`check.py <module> --preview` draws each mesh so it can be looked at.

- Units metres; x forward, y right, z up; faces wound counter-clockwise seen from outside. A mesh with a front
  faces **+x**.
- Pivot: what stands on the ground has its lowest point at z 0 and its footprint centred on the origin; what hovers
  or is picked up is centred on the origin; exceptions are named below.
- Prefixes: `SM_GT_` terrain and backdrop, `SM_GN_` structures and props, `SM_GV_` vegetation, `SM_GE_` the Hedge,
  `SM_GP_` people. Triangle budgets are in `check.py`.
- Slots are the Conclave's slot names under grove aliases (kit.py): LEAF, BARK, CONCRETE, ROCK, STEEL, PAINT, BRASS,
  RUST, TILE, CLOTH, MOSS, GLOW, GLASS, GROUND, WATER. Vertex colour is the albedo; the slot decides the surface. LEAF
  never collides; everything else does unless the mesh is listed as not colliding.
- Realism in a painterly key: true proportions, bevelled edges, weathering in vertex colour (darker toward the
  ground and in crevices, moss on tops and north sides, rust streaks under fixings), varied by seed.

### Vegetation (`flora.py`, all stand on z 0 unless noted)

| Mesh | Size | What |
| --- | --- | --- |
| `SM_GV_Oak` | 14 m tall | Broad oak: furrowed brown bark, spreading crown of warm green |
| `SM_GV_Beech` | 18 m | Tall smooth grey trunk, high crown, lighter yellow-green leaves |
| `SM_GV_Pine` | 20 m | Conifer: dark bark, layered whorls, deep green |
| `SM_GV_Birch` | 11 m | White bark with dark dashes, small golden leaves: the warm accent |
| `SM_GV_Snag` | 9 m | Dead tree: bare grey-black limbs, broken top (BARK only) |
| `SM_GV_Sapling` | 3 m | Young tree |
| `SM_GV_Bush` | 1.5 m | Dense shrub |
| `SM_GV_Fern` | 0.9 m | Fern clump, arching fronds (LEAF only, about 250 triangles) |
| `SM_GV_Grass` | 1.8 m wide patch | Meadow grass with dry tips (LEAF only, about 300 triangles) |
| `SM_GV_Flowers` | 1.2 m patch | Wildflowers, white, yellow and violet, on green stems (LEAF only) |
| `SM_GV_Rock0`, `SM_GV_Rock1` | 2.4 x 1.9 x 1.4; 3.5 x 2.2 x 1.2 | Boulder; slab outcrop. Grey, moss on top (ROCK, MOSS) |
| `SM_GV_Reeds` | 1.6 m | Reed stand (LEAF) |
| `SM_GV_Lily` | 1.0 x 1.0 x 0.12 | Lily pads and flowers lying on z 0 (LEAF, pivot any) |
| `SM_GV_Thorn` | 3 x 3 x 2.6 | Thornroot erupting from the ground: black-violet thorned arcs, magenta embers (BARK, GLOW) |
| `SM_GV_Ivy` | 2 wide, hangs from z 0 down to -3 | Hanging ivy curtain (LEAF, pivot any, top 0) |
| `SM_GV_Log` | 5 x 0.9 x 0.8 | Fallen mossy log along x (BARK, MOSS) |
| `SM_GV_Mushrooms` | 0.5 x 0.5 x 0.25 | Pale mushrooms with a faint resonance glow (MOSS, GLOW) |
| `SM_GV_GiantTree` | 46 m | A great tree: trunk radius 2.6 m at z 1.5, buttress roots to radius 5.5, first limbs at 22 m, crown radius about 16 m. Between z 8 and 24 the trunk stays within 2.9 m of the axis (platforms ring it there) |
| `SM_GV_Heartwood` | 88 m | The oldest tree: trunk radius 8.5 m at z 3 tapering to 5 m at z 40, buttress roots like walls reaching radius 17 m at the ground (nothing beyond 17.5 m below z 6), great limbs from z 38, crown radius about 40 m |

### Structures (`structures.py`)

| Mesh | Size (x by y by z) | What |
| --- | --- | --- |
| `SM_GN_Shelter` | 6 x 4.5 x 3.2 | Prefab field shelter: olive panels, ribbed roof with solar cells, door opening on +x, awning |
| `SM_GN_Greenhouse` | 9 x 6 x 4.2 | Steel ribs and glass, planting beds with saplings inside, door on +x |
| `SM_GN_Crate` | 1.2 x 0.95 x 1.0 | Field crate |
| `SM_GN_LampPost` | 0.6 x 0.6 x 4.2 | Field lamp on a pole, lantern at the top |
| `SM_GN_Planter` | 2.4 x 1.0 x 0.9 | Nursery bed of grafted saplings |
| `SM_GN_Overpass` | 26 x 10 x 8.5 | Collapsed highway overpass: the road runs under its standing span along x (8 m wide, 5 m clear); the other span has fallen, its raised edge 3.3 m above the point (x 4, y -3.5), where Burr braces it, with a clear space 3 x 3 m under that edge |
| `SM_GN_CarWreck` | 4.4 x 1.9 x 1.5 | Overgrown ground-car wreck |
| `SM_GN_RoadBarrier` | 3.0 x 0.6 x 0.85 | Concrete road barrier |
| `SM_GN_Ruin0` | 12 x 10 x 11 | Three-storey concrete shell, a doorway on +x (2.4 x 3 m) into an open ground floor |
| `SM_GN_Ruin1` | 9 x 9 x 7 | Two-storey corner ruin, stairs up to a first-floor slab at 3.4 m |
| `SM_GN_Ruin2` | 16 x 8 x 5 | Long low workshop ruin, a roller-door opening on +x |
| `SM_GN_WallChunk` | 5 x 0.6 x 2.6 | Broken wall piece |
| `SM_GN_Lab0` | 16 x 12 x 9 | Flooded research block: flat walkable roof at z 9.0 with a 0.9 m parapet (a 3 m gap on +x) |
| `SM_GN_Lab1` | 12 x 12 x 11 | Taller block: flat walkable roof at z 11.0, a stair-head hut and a mast |
| `SM_GN_Quay` | 1.4 x 12 x 6 | Retaining wall segment along y, facing +x (the water), its top walkable |
| `SM_GN_Walkway` | 8 x 2 x 1.4 | Steel catwalk span along x with railings; **pivot at the deck's top centre** (deck top z 0) |
| `SM_GN_Tank` | radius 4, 7 tall | Storage tank with a flat walkable roof at z 7.0 |
| `SM_GN_Hauler` | 9 x 3.2 x 3.4 | Wrecked cargo hauler, cab on +x |
| `SM_GN_Weir` | 8 x 56 x 17 | Concrete weir along y: a walkable deck 4 m wide with its top at z 12.0 and railings, three sluice bays with closed steel gates, two gate towers to z 17 at y ±14 (2 m of deck left free beside each); +x is upstream |
| `SM_GN_SluiceWheel` | 1.2 x 2.2 x 2.4 | A big hand-wheel and gear housing on a stand |
| `SM_GN_TreePlatform` | ring, inner radius 3.0, outer 6.0 | Timber deck round a great trunk with rope railing (2 m gaps at +x and -x), braces down to -2.5; **pivot at the deck's top (z 0)**, centred on the trunk |
| `SM_GN_RelayTower` | 9 x 9 x 30 | Lattice mast on a plinth with a walkable deck at z 6.0 (7 x 7 m, railings), dishes, insulators |
| `SM_GN_Capacitor` | 2.4 x 1.6 x 2.6 | Capacitor bank cabinet: ceramic insulators, copper bus bars |
| `SM_GN_Mast` | 3 x 3 x 16 | Ropeway gantry mast: A-frame, sheave wheel, cable stubs |
| `SM_GN_ArrayWall` | 1.6 x 12 x 9 | The Array's perimeter wall panel along y, facing +x: concrete base, steel ribs, a bone-white armoured band with the orange stripe |
| `SM_GN_ArrayGate` | 1.2 x 8 x 8.5 | The gate leaf: one armoured slab, orange chevrons, an amber lock light |
| `SM_GN_ArrayGateFrame` | 3 x 12 x 10.5 | The portal round the gate: opening 8 m wide and 8.5 m high, passage along x |
| `SM_GN_ArrayTower` | 4 x 4 x 15 | Emitter tower: tapering pylon, ring of emitter fins, amber crown |
| `SM_GN_Conduit` | 14 x 2.4 x 3 | Three heavy pipes on saddles, the +x end turning down into the ground, roots gripping them |
| `SM_GN_CoreDais` | radius 6, 1.2 tall | The Array's core coupling: a round dais, three radial bus bars, a socket ring |

### The Hedge, the people and gameplay props (`machines.py`)

The Hedge are the Just's forestry and garden machines turned sentries: bone-white enamel plates (PAINT), graphite
frames (STEEL), one signal-orange stripe, and an **amber** lens at the front (+x), the brightest light on the unit
(it reads as the weak point). They hover: pivot centre. Their silhouettes differ from the AL's (white, black and red).

| Mesh | Size | What |
| --- | --- | --- |
| `SM_GE_Wasp` | 0.7 | Small quick flier: tapered body, two rotor pods, a stinger emitter |
| `SM_GE_Lancet` | 1.3 | Ranged: a long lance barrel under a slim hull, stabiliser fins |
| `SM_GE_Burl` | 2.0 | Heavy: a round shell of overlapping plates, a small lens |
| `SM_GE_Palisade` | 1.9 | A tall front shield of staves, the body behind it, the lens in a slit |
| `SM_GE_Thresher` | 2.5 | Guard: two scythe arms and a rotor crown |
| `SM_GE_Harrow` | 5.0 | End-game: a wide harrow frame with rows of tines, heavy hull, three lenses |
| `SM_GE_Warden` | 7.5 | The boss: an armoured torso over a ring base, a front shield collar, two shield arms and two emitter arms, a crown of fins, a great amber eye at +x, and at its back (-x) an exposed coupling of copper and resonance-green light |
| `SM_GE_Emitter` | 1.2 | A fixed shield emitter (a target for the sidearm): a prism cluster on a gimbal, amber core |
| `SM_GP_Thessaly` | 1.78 tall | Robot botanist: slender, bone-white plates worn grey, a canvas field apron, a round head with two soft amber eyes, one arm a pruning multi-tool, moss on a shoulder. Stands on z 0 |
| `SM_GP_Burr` | 3.3 tall | Mechanoid loader, massive, one knee down, both arms raised over his head, palms flat at z 3.3; rust, moss and ferns on his shoulders, one amber eye |
| `SM_GP_Wick` | 1.5 tall | A small hovering courier: a lantern-like body floating at z 0.9-1.5 over a thin base disc on z 0 |
| `SM_GP_Intercom` | 0.5 x 0.5 x 2.3 | Intercom post: speaker grille, camera eye, amber call light under a rain hood |
| `SM_GN_LinkNode` | radius 0.5, 1.3 tall | A link anchor: a knot of root-wood holding a glowing seed (GLOW_LINK) at z 1.0 |
| `SM_GN_LinkSourceWater`, `...Power`, `...Surge` | radius 0.8, 1.8 tall | A flow source: a root-wood chalice with an open bright core in the flow's colour (GLOW_FLOW_WATER, GLOW_FLOW_POWER, GLOW_LINK) |
| `SM_GN_LinkReceiverWater`, `...Power`, `...Surge` | radius 0.7, 1.6 tall | A socket waiting for a flow: a cradle of root-wood and brass, its core dim (a quarter brightness) |
| `SM_GN_LinkRelayWater`, `...Power`, `...Surge` | radius 0.45, 1.4 tall | A relay: a standing knot with a lens of the flow's colour, dim |
| `SM_GN_RootBridge` | 20 x 4 x 3 | A bridge of living roots along x, a continuous walkable deck 3 m wide; **pivot at the deck's top centre** (z 0 at its ends, up to +0.5 mid-span) |
| `SM_GN_ThornWall` | 1.2 x 8 x 4.2 | Thornroot barrier along y (Settle dissolves it): a dense wall of black-violet thorn roots, magenta embers |
| `SM_GN_ThornCage` | 1.5 x 10 x 7 | A taller thorn wall section along y |
| `SM_GN_ThornKnot` | 1.0, centred | A knot of thornroot with an ember heart (the blade breaks it) |
| `SM_GN_VaultDoor` | 1 x 6 x 6 | A sealed Just vault door along y: a round armoured hatch in a square frame, a dim violet lock light |
| `SM_GN_SeedCache` | 0.9, centred | A woven root basket of glowing seeds |
| `SM_GN_Pin` | 0.8, centred | Burr's coupling pin: heavy steel, a brass collar and ring |
| `SM_GN_Canister` | 0.7, centred | A seed canister: glass and brass, seeds inside |
| `SM_GN_Breaker` | 0.6 x 1.0 x 1.8 | A knife-switch breaker panel on a post |
| `SM_GN_Board` | 0.4 x 1.8 x 2.0 | A weathered route board with pictograms (no text) |

No collision: `SM_GE_*`, `SM_GP_*`, the link meshes, `SM_GN_SeedCache`, `SM_GN_Pin`, `SM_GN_Canister`,
`SM_GV_Grass`, `SM_GV_Flowers`, `SM_GV_Fern`, `SM_GV_Reeds`, `SM_GV_Lily`, `SM_GV_Ivy`, `SM_GV_Mushrooms`.
Box collision: `SM_GN_ThornWall`, `SM_GN_ThornCage`, `SM_GN_VaultDoor`, `SM_GN_ArrayGate`.
