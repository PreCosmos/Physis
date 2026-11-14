# The Wounded Grove: design notes for the build (working spec)

Companion to GAME_ROADMAP.md "Level 4" (what the level is) and Tools/grove/README.md (the contract). This file says
HOW each piece is meant to work, so reviews and scripts have one place to check. Positions are plan metres
(Content/Python/physis_grove_plan.py: x north, y east).

## What Physis has when she arrives

Sword and sidearm, Divinity Sense, Settle (10 Divinity; dissolves weaponised barriers within 17 m, stuns enemies 4 s,
closes hazards), Mend (25 Divinity, heals 6), Light Step (X / LB: about 7 m as light, no cost, 0.9 s between steps,
passes through attacks; a jump plus a step crosses 8-9 m), swimming (deep water only below z 0, a water jump of
about +2.5 m), walking speed about 6 m/s. Health 10 per tank; up to 7 tanks before this level. She cannot climb:
slopes over about 45 degrees stop her, and nothing in the game is an invisible wall.

## Resonance Link (BP_Physis.PhysisLink, input IA_Link: G / left stick click)

One press, 0.6 s between presses, no cost, needs `,resonance,`, not while cinematic, dead or talking. It calls
`PhysisUsedAbility(",resonance,")` first (the Center's and the Conclave's resonance sockets answer it).

Target choice, in this order:
1. A `BP_LinkNode` that is active (its Need token held or empty; not Hidden), within its Range of her (default 32 m,
   set per node), within 30 degrees of the camera's forward axis, and in line of sight from her head (a Visibility
   trace that stops at the node). Of those, the one nearest the view's centre.
2. Else an enemy (`BP_TrainingDrone`, not Static) within 24 m and 35 degrees of the view's centre: a tether.
3. Else nothing: a short "nothing answers" note, no cooldown.

`BP_LinkNode` (instance-editable): Kind (0 anchor, 1 source, 2 socket, 3 relay), Flow (string: 'water', 'power',
'surge'; anchors ''), Need, Hide (token that removes it), Give (token a fed socket or relay gives), Done (message when
fed), Range (cm), Reach (cm a flow can be carried from this node: sources and relays; default 30 m), Perch (vector,
cm: where she lands relative to the node, default 0,0,0: the node's origin is the landing spot and its visible seed
floats above it). Runtime: Fed (bool), Shown (bool), Aimed (bool: it is the node the next press would take; it
brightens and swells, which is the player's aim feedback).

- Anchor (Kind 0): she is pulled to the node's perch. `BP_LinkPull` (spawned) moves her along a straight line with a
  slight arc at 26 m/s (at least 0.25 s), gravity off, no sweep (line of sight was checked), untouchable while
  pulled (`SafeUntil`), then gives gravity back and leaves her standing (velocity zero) on the perch. A press
  during a pull is ignored. Pulls work from the ground, the air and the water.
- Source (Kind 1): she takes up its Flow. `LinkFlow` (BP_Physis string) holds the flow's name, `LinkFrom` the point
  it comes from and `LinkReach` how far it stretches. A `BP_LinkBeam` (spawned, mode carry) draws the beam from that
  point to her hand each frame and breaks the flow (clears LinkFlow, "The flow slips back") when she goes beyond
  LinkReach, loses line of sight for more than 1.5 s, dies or talks. Taking a second source replaces the first.
- Relay (Kind 3): while she carries its Flow, linking it feeds it (Fed, Give if set) and the flow now comes from the
  relay (LinkFrom = relay, LinkReach = its Reach), with a fixed beam left between the last point and the relay. A fed
  relay is also a source of its flow from then on. A relay is how a flow turns a corner or crosses a long gap.
- Socket (Kind 2): while she carries its Flow, linking it delivers: Fed, Give, Done, a fixed beam from the last
  point, the carry ends. Without the right flow it answers "It waits for <flow>".

Fed sockets and relays whose Give token is already held start Fed (after a load); fixed beams are not saved (they
are only drawn in the session that made them).

Tether (`BP_LinkTether`, spawned with the two enemies): lasts 8 s or until either dies. Each frame it reads both
healths; whatever one lost since the last frame is taken from the other too, directly (not through the other's
armour), and an enemy brought to zero that way is finished with its own TakeHit so it drops and counts normally. A
beam joins them. With no second enemy within 15 m of the first, the first is held still for 2 s (StunUntil) instead.
A second tether replaces the first. Static targets are never tethered.

Motion (the ability's visual stage): `MPC_Grove.Motion` is 0.12 before `,resonance,` and eases to 1 after; the
foliage's wind, the grass's parting round her (`MPC_Grove.Her`, her position) and the water's answer scale with it.
`MPC_Grove.Heal` is 0 until `,warden,`, then eases to 1 over 25 s: blight leaves the ground, the Heartwood's crown
greens. `BP_GroveDirector` drives all three, hides actors tagged `GroveBlight` and shows those tagged `GroveBloom`
once healed, shows actors tagged `GroveWater` / `GrovePower` when those tokens are held, and gives `,gr_first_w,` or
`,gr_first_e,` the first time it sees `,water,` or `,power,` alone.

## Gates, in order

| Gate | Where | Opens with | If she fails or falls |
| --- | --- | --- | --- |
| Thornroot wall on the Reclaimed Road | (-455, 72) | Settle (BP_SettleBarrier) | Nothing lost: Divinity crystals nearby |
| The Graft | (-162, 40) | Interact, after `,tess,` | "Thessaly, at the camp, knows this tree" |
| The Gully | x about -112, whole valley | The link: one anchor on each bank at y 42 | Its floor has a ramp out on the south side at y -300 only, so falling in costs a walk, never the level |
| Campus roofs | lake, (60, -260) | Link anchors from the water and from roof to roof; the quay wall is 4.6 m above the water (water jump reaches 2.5 m) | Swim back to the quay stairs |
| The Weir's deck | (196, -262), z 12 | Anchor chain from the last roof | Drop into the lake, swim round |
| `,water,` | weir deck | Carry 'water' from the headpond source (north end) through one relay (mid deck tower) to the sluice socket (south end): deck is 56 m, reach 30 m | The flow slips back; take it again |
| Great trees | (70, 225), (105, 262), (145, 298) | Anchors up from the Canopy Foot, tree to tree (ranges up to 60 m) | Falling costs nothing (no fall damage); climb again from the foot |
| The Relay mesa | (185, 335), z 62 | Anchor from the third tree | Jump down, or an anchor back |
| `,power,` | relay deck | Carry 'power' from the capacitor bank (ground, mesa's south edge) through a relay on the mast's plinth to the socket on the mast's deck (z 6) | As above |
| The Rift, west | (260, -127) | `,water,`: a root bridge rises (BP_Rise) | Rift floor has a ramp out at the south (outer side) only |
| The Rift, east | (282, 99) | `,power,` and the link: three anchors from the gantry mast across (their Need is `,power,`) | As above |
| The Array's gate | south of the ring wall, (258, -20) | `,water,` and `,power,` (BP_Requirement gives `,arraygate,`; the gate is a BP_Rise that sinks) | The Forecourt Still Point is right there |
| The core coupling | Root Court | `,arraygate,`; carry 'surge' from the emitter crown source to the heart socket through the two relays of the arrangement in force (west side if `,gr_first_w,`, east if `,gr_first_e,`), past forced vents (BP_Hazard, Settle closes them) and Hedge guards | Vents hurt, never kill outright; a Still Point inside the gate |
| The Warden's cage | Root Court, north | `,stabilized,`: the thorn cage (BP_Rise) sinks | |
| The Warden | arena (378, -20) | The fight: room 452 holds the Warden (kind 4, front immune, health 110), four Wasps, two Burls and three wall emitters (Static, sidearm only). The encounter gives `,warden,` when all are gone | Death returns her to the Root Court Still Point |

Sequence notes: `,resonance,` is needed for everything north of the Gully; the Gully cannot be walked round (it
meets the cliffs at both ends) or swum round (the lake lies wholly north of it). The lake's north and east shores
are quay walls, its west shore the cliff, its south shore a beach on the Understory side. Both lifelines are needed
for the gate, in either order; either one alone gets her across the Rift to the Forecourt, where the gate's scan
says what it still wants.

## Still Points (BP_Checkpoint, Until `,warden,`)

Hollow (-484, 46); Field Camp (-262, -14); Understory (-40, 4); Campus Quay (28, -146); Weir (at the deck's south
end, on the east bank, (212, -228)); Canopy Foot (45, 195); Relay (on the mesa, (176, 322)); Forecourt (268, -20);
Root Court (inside the gate, (282, -20)).

## Encounters and rooms (BP_Encounter Room 401-499, each once; loose packs are room 0)

401 Road ambush (2 Wasps, 1 Lancet) at the thornroot wall, gives `,gr_road,`; 402 Camp approach (optional);
411 Campus quay; 412 Lab roofs; 413 Weir deck guard (1 Thresher, 2 Lancets), gives `,gr_weir,` which the weir's
source needs (Need); 421 Canopy Foot; 422 Relay guard (1 Thresher, 2 Wasps, 1 Burl), gives `,gr_relay,` which the
capacitor source needs; 431 Rift west; 432 Rift east; 441 Forecourt (2 Palisades, 2 Wasps: the tether's lesson),
gives `,gr_forecourt,`; 451 Root Court guards; 452 the Warden. Old Town: 461 the Harrow (optional).

## People and what they give

- Thessaly-4 at the camp: `,tess,` and the quest to the Graft. After `,resonance,`: hints. After `,warden,`:
  the closing talk, `,grove_done,`, a full heal and 60 Divinity.
- The Graft (BP_Switch, Need `,tess,`): `,resonance,`; its Done text teaches the input.
- Burr at the overpass: `,burr,`; wants `,pin,` (BP_Relic in the hauler wreck in the lake's south-east shallows,
  reached by swimming after the Gully). With the pin: `,aug_defense5,`.
- Wick at the camp: `,wick,`; wants `,can1,` `,can2,` `,can3,` (BP_Requirement gives `,cans,`). With them: `,aug_agility5,`.
- Voss: intercom posts (BP_NPC with the post as Shape, her voice with a radio effect) at the camp, the Forecourt
  and the Root Court, each hidden by `,warden,`; in person (MetaHuman Look) at the control bunker door in the Root
  Court, shown by `,warden,`: `,voss,` and `,aug_pistol4,`.
- The Heartwood's gift: BP_Relic at the trunk's north foot, Need `,warden,`: `,aug_hp7,`, heals.
- Old Town's vault: a flow puzzle (carry 'power' from a live battery bank through two relays to a gate motor):
  `,gr_vault,` opens a BP_Rise door; inside, `,aug_katana5,`.

## After the Warden

`,warden,`: Heal eases to 1; `GroveBlight` actors go, `GroveBloom` actors show; root bridges (BP_Rise, Need
`,warden,`) rise across the Rift's south side (bearing 180) and across the Gully at y 42: the shortcut from the
Heartwood to the camp. Enemies elsewhere stay (the Hedge's patrols are not all ordered from here), except the
Root Court's.

## Travel and saves

`BP_GroveCurrent` (its own Blueprint, the Conclave's current mesh): in the Center's temple (Dest 1, Need
`,shepherd,`) and in the Hollow (Dest 2, always shown). `PhysisToGrove` gives `,grove,` `,at_grove,` `,trip_g,`, saves
and opens L_Grove with "nocine,load"; `PhysisGroveHome` takes `,at_grove,` away, gives `,trip_g,`, saves and opens the
Center. After the load the current sees `,trip_g,`, takes it and moves her to the TargetPoint tagged GroveArrival
(here) or GroveReturn (the Center). `PhysisLoadGame` and the menu's Continue open L_Grove for a save holding
`,at_grove,`. The save's exact spot uses world 4 (a BP_GroveDirector is present). A carried flow, a pull or a tether
is never saved: a load starts with LinkFlow empty.
