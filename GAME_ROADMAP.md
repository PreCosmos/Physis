# Physis — game design and development roadmap

Draft 3 · 30 October 2026 · Rebuilt as a Zelda/Metroid action-adventure; first map revised by the author

## The game we are making

A single-player third-person **action-adventure** based on **Physis**, the story in
*Fantasia*. The player is Physis: a person condensed from the living substance of
the universe, who fights her way through a war she was born to end and learns to
heal its wounds and understand the beings who caused them.

| Taken from | What we use |
| --- | --- |
| **Zelda** | Lock-on melee, a sword and a ranged tool that also solve puzzles, dungeons built around one new ability, memorable bosses, a settlement full of people worth talking to, secrets everywhere |
| **Metroid** | One interconnected map, ability gates remembered from hours earlier, shortcuts that loop back, isolation, environmental storytelling through scanning, health and resource expansions hidden off the main path |

Three things make the game its own: **Physis perceives more as she develops**
(graphics improve with abilities and levels), **people respond to spoken
conversation**, and **worlds remember her actions**.

The two main AI features are English voice conversations with NPCs and adaptive
environmental puzzles within defined terrains.

Status labels: **Author** means established by the author. **Proposed** means a
design direction for review. Nothing here changes book canon unless it says so.

## Confirmed requirements and current starting point

| Requirement (Author) | Planned result |
| --- | --- |
| Genre | Action/adventure mixing Zelda and Metroid |
| Three main destinations | Earth, the First Ones' Planet, and the Center of the Universe |
| First map | A battle station humanity uses to defend itself against the First Ones |
| First-map content | Basic movement and Divinity Sense; **no other abilities** |
| Physis fights | She wields a **sword** or a **gun**; both ways of fighting are introduced on the first map |
| Center art direction | Realistic cel shading |
| Different shading per destination | Each has its own material, lighting, color, and visual treatment |
| Graphics improve with abilities and levels | A persistent progression in visual richness and perception |
| Spoken AI NPC dialogue | Microphone input and spoken English responses; no typing required |
| Living terrains | Defined terrain identities with puzzles that react to player actions |
| MetaHuman characters | Use MetaHuman where appropriate for human characters, with animation support |

Current project: Unreal Engine 5.8, Blueprint-only (no `Source` folder), still
booting the template level `Lvl_IntroRoom`. The editor MCP connection works. Physis
exists as a MetaHuman (`MH_Physis`) with an outfit and a preview studio level. She
has no gameplay character, locomotion set, weapons, or combat animation. No game
systems or playable level exist yet.

The editor needed a temporary NVIDIA rendering workaround during setup. Stable
rendering is an early prerequisite for judging art direction. See
[the connection notes](Tools/UNREAL_CONNECTION.md).

## Story adaptation

Source: *Fantasia*, “Physis,” printed pages 87–120. The document is story reference;
the author's requests define the game requirements.

| Book foundation | Game adaptation |
| --- | --- |
| Divinity is the living substance permeating the universe | It connects perception, abilities, dialogue context, and world reactions |
| Physis is condensed at the absolute center; “learning herself as she moved” | Short birth opening, then straight to the first map; her power is real but unlearned |
| Her first act is at the Meridian Front, year 2312, eleven years into the war | The first map is set there: **Meridian Station** |
| Control “absolute in the technical sense,” yet uncertain “about almost everything specific” | Mastery means understanding, not raw power: see [Why Physis has limits](#why-physis-has-limits) |
| Humans: the Wise and the Just. First Ones: the Serene and the Vigil | Encounters show different fears rather than good against evil |
| Kairos, Cassian, and Aeon are central figures | Preserve their roles and motives. Book forms: Kairos is a human historian, Cassian a Robot, Aeon a First One |
| The dismantling: seventeen human installations, fewer and older First One ones | The dungeon structure of the game |
| Hardened facilities force her to enter the minds of those inside | The defining dungeon twist: Inner Installations |
| “She sat with it” — grief beneath ideology, not removed | Boss resolution mixes combat with a spoken final stage |
| The offer, the holdouts, integration, the Cosmoforms, creation | Late game and epilogue, including her uncertainty over the holdouts |

Canon notes:

- **Weapons.** In the book she never fights this way. Sword and gun are an author
  decision for the game. Proposed reconciliation: both are *ordinary* human weapons
  at first, and Physis fights to protect people until she learns a better way. The
  book's refusal to destroy then becomes something she grows into rather than
  something the action contradicts.
- **Dates.** The book says the war began “in the three hundred and first year after
  Divinity's discovery,” but also dates discovery to 2187 and the first engagement to
  2301. The game uses the calendar year 2301 and avoids the other phrase.
- **“Second hardest decision.”** The book calls the holdouts her second hardest
  decision and never names the hardest. Proposed: leave it unspoken until the ending,
  when she leaves her universe. The author should confirm.
- **Elder homeworld.** The First Ones' Planet is an adaptation; the book uses
  “sovereign space.” Earth and that planet concentrate events that span stations,
  fronts, and several star systems. The Center is a cosmic place, not a planet.

## Opening

Order, as proposed: **brief birth at the Center → Meridian Station (first map) →
Center hub → wider exploration.**

The author placed the station first and put Physis on it with Divinity Sense. She
has to exist by then, so this draft keeps her birth as a short non-interactive
opening, which also matches the book's order. It replaces the earlier order where
the station came first and birth followed it. Draft 2's rule of no abilities on the
station, and the framing of the station as a war impression, are withdrawn.

### Birth (about one minute, not playable)

Darkness, then the Center in full realistic cel shading. She opens her eyes “as a
convenience,” sees the universe, and feels everyone's wounds at once. One wound
burns brightest: the Meridian Front. She rises and moves. Cut to the station.

### Why she starts weak

She arrives condensed into a body for the first time, in a corridor, in a fight.
She knows what she is and almost nothing about how to do it. Reaching for Divinity
here feels like shouting in a room of people screaming. Perception is the one thing
that works, because perception is what she is. Everything else she does on this map,
she does with her hands.

## First map — Meridian Station

**Goal:** in 25–35 minutes, teach movement, scanning, sword, and gun, and prove the
Zelda/Metroid structure in miniature. Physis has **no abilities except Divinity
Sense**. Dodge, jump, and mantle are basic movement, not abilities.

The station is a defensive fortress of the human fleet: mixed crew of humans, Robots,
and Mechanoids, boarded by First One warriors and their AL forces, with Mechas among
the attackers. Art direction: grounded, heavy, worn after eleven years of war, with
the First Ones' ships filling every viewport. It is authored as a compact map that
loops back on itself, not a corridor.

| # | Space | Teaches | Beat |
| --- | --- | --- | --- |
| 1 | Breach Deck | Look, run, jump, mantle, crouch through wreckage | She arrives in the hull breach. Crew shout at a stranger in pale clothes and keep moving |
| 2 | Damage Control | **Divinity Sense** | A sealed door and a sparking panel. Scanning shows which conduit is live and which route is safe. Scan narration is spoken |
| 3 | Crew Ring | Dodge; scanning people | Injured crew; first brief voice exchange when the pipeline is ready. Scanning an enemy shows its weak point |
| 4 | Armory | **Gun** | She takes a fallen marine's sidearm. AL drones at range. A jammed door release across a gap can only be shot, so the gun is also a tool |
| 5 | Boarding Spine | **Sword** | A First One warrior's guard shrugs off gunfire. Station boarding blade on the wall. Melee, lock-on, block, and timed deflection |
| 6 | Reactor Gallery | Sword and gun together | Mixed fight: shielded warriors close in while drones hold the far side. Neither weapon alone is efficient |
| 7 | Service Loop | Shortcut | A hatch only openable from this side drops back to Damage Control. Past it: a Divinity-sealed door she cannot open yet, plainly marked on the map |
| 8 | Fleet Bridge Approach | Exam | **Mecha Breacher** boss. Scan finds the seam, gun opens it, sword exploits it |
| 9 | Observation Deck | Story climax | Canon scene: Divinity between the fleets settles without her meaning to. Weapons lose coherence. “I am not your enemy, and I am not your ally, and I need you to listen” |

**Divinity vault (Author, 2026-11-03).** The sealed door in Damage Control, whose
scan tells the player to remember it, is the map's payoff for paying attention.
Spending Divinity at the Reactor Gallery node raises the platforms, opens the Fleet
Bridge door and, with a line that the Service Loop and a sealed door far behind have
answered, unseals both: the empty Service Loop corridor and the vault door it leads to.
Behind that door is a small lit vault with the **Life Augmentation**: walking over it
permanently gives Physis a Health Tank (maximum health 10 → 20) and fully heals her.
It is optional, saved as the `,lifeaug,` progress flag, kept across respawns and
save/load, and shown on the HUD as a reserve tank icon under the health bar (see
Health Tanks).
It has its own Logbook entry, picture and narration like every item.

The involuntary settling at the end is not an unlock. She cannot repeat it, which
gives her a concrete goal: learn deliberately what just happened by accident. Then a
Divinity current pulls her back to the Center. It takes her as soon as the line has
been read (Author, 2026-11-07): the message stays 8 s, then the Center loads, with no
wait after it (it was 13 s).

**Station fights (Author, 2026-11-07).** A drone fights only while Physis is inside
its own room. From the next room, or through an open door, it stays where it is and
does not shoot, so drones no longer wreck themselves on the walls trying to reach her.
The moment she steps in, the room's drones warn and attack. Station drones fly level
and go around obstacles such as the reactor core, so only combat destroys them, or a
drone truly stuck inside the floor or a wall. The Mecha Breacher shows no
on-screen marker: the scan and its hit lines ("The front armor turns your attack...")
are how the player learns its weak point.

A fight room's door opens only when every drone of that room is destroyed, so no drone
may start inside a solid part (author's playtest, 2026-11-07: the Drone Hangar's door
never opened). One hangar drone was placed inside a pillar, rose out of it through the
ceiling and followed her out of sight and reach. It now starts between the pillars,
and the room generator keeps drones clear of them.

Acceptance criteria: a new player can finish the map using only movement, scan, sword,
and gun; each weapon is required at least once and useful in every later fight; no
ability beyond Divinity Sense is reachable; the player has seen one shortcut and one
unopenable door; the map works with both gamepad and keyboard; and progress survives
save and reload.

## Divinity Sense

Divinity Sense expresses Physis perceiving Divinity. The concept art deliberately has
no helmet or device, so it is presented as innate perception, not an object. It was
renamed from the working name “Scan Visor” (Author, 2026-11-07), a term strongly
associated with *Metroid Prime*. Internal names keep the old one (IA_ScanVisor,
ScanVisorOn, T_Ability_ScanVisor); players never see them. Saves made before the
rename have their Logbook text updated when they load.

- Hold to enter scan mode: over-the-shoulder view, color drops back, targets glow.
- Aim, hold on a target, and get progress and completion feedback.
- Every result is spoken; optional text remains available. Reading is not required.
- Works on environment, people, and enemies: identity, condition, disturbance, and
  weak points. Enemy scans give a real combat advantage, so it is never just lore.
- Scanning is usable during combat at a cost: time moves on and she is exposed.
- Discoveries persist and fill a Codex. Repeat scans skip the introduction.
- Essential facts come from authored data; AI may only rephrase them. Decorative
  objects are never required. Upgrades add what it can see, not new buttons.

## Fighting

Combat is third-person, lock-on, and readable: Zelda's clarity with a rhythm built
on switching between two weapons. Both are always available. The player chooses
freely, and encounters reward using both.

| | Sword | Gun |
| --- | --- | --- |
| Role | Close pressure, guard break | Range, weak points, crowd control |
| Risk | Close to danger | Heat builds; overheating locks it briefly |
| Defense | Timed deflection returns energy shots | None; relies on dodge and spacing |
| Exploration use | Cut cables and growths, strike switches | Hit distant switches, trigger mechanisms |
| Later growth | New techniques, and each ability adds a sword application | New firing modes, as Metroid's beam upgrades |

Rules:

- Basic attacks stay fun for the whole game; abilities extend them, not replace them.
- Every enemy has a health bar and a **Coherence** bar. Damage wears down health;
  scanned weak points, deflections, and well-chosen weapon swaps break Coherence for
  a big opening. On the first map this is plain stagger. Once she has learned to
  settle, breaking Coherence becomes the route to the non-destructive ending below.
- Sword and gun are also keys, so combat and exploration share a vocabulary.

**Lethality (Proposed, needs author decision).** AL are tools and can be destroyed.
Against living enemies she begins by fighting to stop them; after the first map,
defeated warriors are disarmed and withdraw rather than die on screen. This keeps
the action hard-hitting and stays true to “Destruction was not the right word.”

Enemy roster from the book's living ones: **AL** (drones and soldiers, no will,
first encounters), **First One warriors** (“native form” humans never captured, so an
art challenge rather than a monster), **Mechas** (ancient, proud, heavy elites),
**Robots and Mechanoids of the Just** (later human opposition), **Lightforms**
(shimmering, near instant, late hunters). AL that survive to the end face the book's
offer of choice, which gives every earlier fight a retroactive sting.

## Why Physis has limits

Her power is absolute; her understanding is not. The book supports this directly: she
is “uncertain about almost everything specific.” What she forces, she wounds, and
forcing Divinity is exactly what she came to stop. So:

- **Abilities are understood, not found.** Each one comes from a person, people, or
  event that taught her something, never from a chest. The map still treats it like a
  Metroid item, as a door that finally opens.
- **Levels are Understanding.** Earned through exploration, healing, and listening,
  with enemies as a minor source. They raise visual perception and small stats; they
  never replace ability gates, so grinding cannot skip anything.
- **Failure is diegetic.** Health is **Composure**: she feels everyone's wounds, and
  too much overwhelms her. At zero she scatters and re-condenses at the last **Still
  Point**, a pocket of peaceful Divinity that serves as save room. Composure Tanks
  (healed wounds) and Focus expansions are hidden off the main path.

## World structure

**The Center is the hub**, and the worlds interlock. Draft 2's line of Earth → First
Ones' Planet → returns made the Center a bookend; a Metroid needs the map to fold back
on itself. Divinity currents connect the Center to every destination, and each world
holds doors that only the other world's abilities open.

| Place | Terrain vocabulary | Shading identity | Role |
| --- | --- | --- | --- |
| Center of the Universe | Divinity currents, condensed-matter islands, memory spaces | **Author:** realistic cel shading with believable scale, deliberate light and shadow bands, restrained volumetrics | Hub, Still Point network, grows with each return, finale |
| Earth | Reclaimed cities, forests, flooded research sites, damaged infrastructure | Warm, painterly, soft shading, rich organic detail | Water, roots, energy; Just installations and their people |
| First Ones' Planet | Ancient terraces, crystal, suspended architecture, immense ruins | Cool palettes, sharp value bands, luminous edges | Resonance, light, alignment, shifting architecture; Vigil and Serene |

Smaller locations reachable from the hub:

- **Meridian Station:** first map, and revisited. New abilities open the sealed door
  from the first hour and change what the survivors say.
- **The Conclave:** the Wise's station. This is the game's Kakariko: the mixed
  community, Kairos, the silent old Mecha in the corner. It concentrates voiced NPCs
  in one bounded space, which is also the cheapest way to make voice AI feel rich.
- **The Threshold:** neutral space for the Reckoning and the Offer. Its Observatory is
  where Divinity was first detected.

All terrain and shading above except the Center remain proposals until the author's
terrain definitions refine them. Regions are bounded and connected; full planets and
spaceflight are out of scope.

### Installations are the dungeons

| Type | Count (Proposed) | Size | Purpose |
| --- | --- | --- | --- |
| Great Installation | 6: 3 Earth, 3 First Ones' Planet | 45–90 min dungeon | One new ability, one boss, one map-opening shortcut |
| Hardened Installation | 2 of the above | Adds an Inner Installation | See below |
| Minor node | Remaining human and First One sites | 5–10 min room, like a shrine | Optional-feeling puzzle, Composure or Focus reward; a threshold is required for the ending |

Together they keep the book's count: seventeen human sites, fewer First One sites,
all placed on the two worlds. The four star systems become four regions. This is a
deliberate adaptation choice for the author to approve.

**Inner Installations.** At a hardened facility, Physis cannot undo it from outside
and must enter the mind of someone inside. The mind-space is a dungeon built from that
person's memory, with its rooms made of what they lost. Its boss is the grief itself:
fight until it stops attacking, then **sit with it** through a spoken final stage.
Sword and gun will not finish it. The book's honesty stays: it “was not enough to
change all of them,” so some people are not reached, and the game says so.

## Abilities and progression

One ability each, taught alone, then combined. Each must work in **traversal,
combat, and puzzles**, which is what makes Metroid gates and Zelda dungeon items feel
earned.

| Order | Ability (working names) | Learned from | Traversal or gate | Combat | Puzzle | Visual stage |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | None; sword, gun | Meridian Station | Physical only | Base kit | Shoot, cut | Grounded station |
| 1 | **Divinity Sense** (Author) | Innate, first map | Reveals clues and routes | Weak points | Read the room | First perception layer |
| 2 | **Settle** | Learning what happened at Meridian | Dissolves weaponized barriers | Breaks Coherence; disarms without destroying | Calms hazards | Center fully realized |
| 3 | **Light Step** | Lightforms at the Conclave | Dash through gaps and grates | Dodge through attacks | Timed light routes | Depth and color |
| 4 | **Resonance Link** | The Wounded Grove, Earth | Pull along connected nodes | Tether enemies together | Redirect flows | Motion, responsive surfaces |
| 5 | **Trace Reading** (scan upgrade) | Kairos and the Wise | See the past of a room; hidden paths | Predict attack patterns | Past and present overlay, Zelda's dual worlds | Memory layers |
| 6 | **Dissonance** | Aeon; preparing the Reckoning | Hold open hostile zones | Field where enemy weapons falter | Sustained zones | Lighting depth |
| 7 | **Reweave** | First Ones' ruins | Restore bridges and structures | Rebuild cover, repair allies | Structural puzzles | Complete geometry, ecology |
| 8 | **Sit With** | First hardened facility | Opens Inner Installations | Ends grief bosses | Mind spaces | Interior worlds |
| 9 | **The Weight** | The holdouts | None. Story only, then never used again | None | One intimate act | Full expression |

Order after Settle can branch: the player chooses which world to pursue first, as in
Metroid's better non-linear entries, and the progression graph must keep every order
solvable. Sequence breaks are welcome where they do not skip story.

The Weight is the game's moral peak. The player must perform the book's “most intimate
violation” personally, slowly, with no reward and no fanfare, and the game does not
congratulate them. Refusing is not canon, so it is not an option; Physis's doubt
afterwards is not resolved.

### Improving graphics

Visual growth is an expression of perception. Major stages follow abilities; smaller
steps follow levels. It has two independent inputs: **Physis's mastery** and **local
world condition**, so returning with more mastery reveals more even in an unhealed
area, and healing an area changes it too. Hardware quality settings stay separate
from story progression. Essential clues and combat tells stay readable at every
stage. Budget the richest stage first, and prefer authored reveals over regenerating
assets per level.

#### Fidelity ladder (Author, 2026-11-03)

Physis starts the game at **LOD 2**. The next three upgrades each raise everything on
screen together, ending at **max graphics**:

| Stage | Name | Reached | Mesh detail | Texture detail | Detail and view distance |
| --- | --- | --- | --- | --- | --- |
| 0 | LOD 2 | New game, Meridian Station | Mesh LOD 2 (static and skeletal) | Mips biased down 2 | Low detail, 60% view distance |
| 1 | LOD 1 | Defeating the Mecha Breacher | Mesh LOD 1 | Mips biased down 1 | Medium detail, 80% view distance |
| 2 | Full detail | Learning Settle (Center of the Universe) | Full LODs | Full textures | Epic detail, full view distance |
| 3 | Max graphics | Third upgrade (to be placed) | Full LODs | Full textures | Epic detail, 140% view distance |

Meridian Station plays at stage 0 from the opening cinematic onward, and the boss
kill moves the rest of the level, including the Observation Deck ending, to stage 1.
The stage is derived from progress flags, so loading a save restores it. Leaving play
restores full detail, so the editor and menus are never left degraded: full detail
uses Epic detail mode, the editor's own level (Author, 2026-11-04). The Center of the
Universe is always at least stage 1, and learning Settle there reaches stage 2.
Stage 3 is wired but unassigned until its upgrade exists.

**Graphics Quality unlocks with the stages (Author, 2026-11-04).** The pause menu's
Graphics Quality offers only the levels the story has reached:

| Stage | Quality levels the player can choose |
| --- | --- |
| 0 | Low |
| 1 | Low, Medium |
| 2 and 3 | Low, Medium, High |

Trying to go above the unlocked levels shows "Higher quality unlocks as the story goes
on." When a new level unlocks, Quality switches up to it by itself, unless the player
chose a lower level, which is kept. The game always uses the lower of the player's
choice and the unlocked level, so loading an earlier save or a new game lowers it
again. Low, Medium and High are the engine's Medium, High and Epic scalability for
shadows, effects, post-processing and textures. Low and Medium also lower detail mode
the way the engine does (objects marked high or Epic detail are hidden), never above the stage's own
detail. Leaving play puts back the quality settings from before play, recorded when
the level started (in the editor, its own launch settings), so a test never leaves the
editor degraded or raised above them.

**High from Settle on (Author, 2026-11-06).** Once Physis learns Settle, the game plays
at High by default for the rest of the game: in the Center from that moment, and in
every later level. Each new level keeps the stage at 2 or above while `,settle,` is in
the flags, and its own level flag counts as at least stage 2 (the way `,center,` gives
the Center at least stage 1). The default choice stays High (`QualityWanted` 2), so
only the player's own lower pick in the menu lowers it.

Implementation: `PhysisFidelity` (the stage, in `center_overrides.py`) calls
`PhysisFidelityApply` on `BP_Physis` whenever the stage changes. That sets
`r.ForceLOD`, `r.SkeletalMeshLODBias`, `r.MipMapLODBias`, `r.ViewDistanceScale`, the
Quality cap, the `sg.*` quality groups and `r.DetailMode`. `PhysisFidelityReset` runs at
End Play. The player's choice is `QualityWanted`, saved in the settings slot; `Quality`
is the level in use, shown by the menu. These functions and the settings functions
(`PhysisSetting`, `PhysisSettingsApply`, `PhysisSettingsLoad`, `PhysisSettingsSave`)
are written by `Tools/blueprint_logic/quality.py`. The HUD checks the stage every frame
and applies it only when it changes.

### Loading screen (Author, 2026-11-07)

Every level load shows a loading screen: New Game, Continue and Load Game from the
menus, the Divinity currents between levels, and the reload after a death. The author
asked for "some form of loading bar ... until everything is loaded". It is deep navy
with the destination's name in gold (Meridian Station, Center of the Universe, The
Conclave; none for the main menu), a thin gold bar with a soft light running along it,
and LOADING under the bar.

The bar has two parts. While the map loads (about 80% of the bar) it is timed from how
long that map took to load last time on this machine, so it reaches the end about when
the load does. After the load the screen stays until the new level has settled: no
packages loading, no shaders compiling, no texture or mesh detail still streaming in.
That last part of the bar follows the work left. Then the screen fades out over half
a second. Meanwhile the world is paused and the player's input is held, so the opening
cinematic, timers and enemies start only once the player can see them, and a loaded
save has already put Physis in place. Typical times in the uncooked test build:
Meridian Station 4.4 s to load and 1.1 s to settle, the Center 4.5 s and 1.1 s.

Implementation: C++, `Source/Physis` `UPhysisLoadingScreenSubsystem` (a game instance
subsystem). The engine's MoviePlayer draws the screen during the blocking load, and
the same screen is a viewport overlay afterwards. Learned load times are kept in
GameUserSettings.ini, `[Physis.LoadingScreen]`. The console variable
`physis.LoadingScreen` is 1 by default (on in the game, off in Play-In-Editor, which
does not load maps the same way), 2 also shows it in Play-In-Editor after an
OpenLevel, and 0 turns it off. The Windows package must compile it with MSVC, like the
Steam Input code.

### Combat controls and defence (Author, 2026-11-03)

- Controller: **RB** light attack, **RT** heavy attack, **B** parry or dodge. B parries
  when an attack is about to land (a drone bolt within 650 units or a drone within 330)
  and dodges otherwise. Keyboard keeps Left Mouse, Middle Mouse or F, Right Mouse and
  Left Alt.
- **Divine Parry (an assist, Off by default):** when a hit lands that Physis did not
  parry herself, she parries it automatically if she has 5 Divinity, spending it. A
  manual parry costs nothing. It was on for everyone, which made fights far too easy,
  since drones drop Divinity and every parry ends in the cyclone counter (Author,
  2026-11-09). It is now the last option in Settings, "Assist: Divine Parry", and it
  starts Off, settings saved before included.
- Every parry is a dramatic beat: slow motion, a strong camera shake, sparks and a
  layered impact sound, then a fast cyclone counter that deals heavy damage.
- **Death:** when her health runs out she falls, and she rises at her last checkpoint
  as soon as she has landed (1.8 s, Author 2026-11-04), with full health and her
  progress kept. On the station that is the Breach Deck; in the Center it is the last
  Still Point she reached.
- In-game text names actions, not keys or buttons, because the player may be on a
  controller. Only tutorial prompts and the pause menu's controls list show inputs,
  and their controller glyphs come from Steam Input, so they match the pad in use
  (Xbox, PlayStation, Switch, Steam Deck). Without Steam, the Xbox glyphs are used.
  Every pad input has a glyph: face buttons, shoulders, triggers, both sticks and stick
  click, all four D-pad directions, Start (Menu) and Select (View). Prompts write them as
  tokens such as `|A|`, `|DR|`, `|Menu|` or `|View|` (HUD `DrawPadGlyph`).

### Health Tanks

Health is shown in tanks of 10. The main bar shows the current tank. Each reserve
tank is a small icon under it, lit while full and dark once spent. The Life
Augmentation in the Damage Control vault adds one tank. Further augmentations in
later levels add more, and the HUD supports up to nine reserve tanks.

### Augmentations and ability vaults (Author, 2026-11-04)

Augmentations are permanent upgrades, kept as progress flags so saves keep them:

| Kind | Effect per augmentation (tuning values) | In the Center |
| --- | --- | --- |
| Health | One more Health Tank (+10 health), fully heals | 4 |
| Katana damage | Sword hits +25% | 3 |
| Pistol damage | Gun hits +30%, the Divinity Shot too | 2 |
| Defense | 15% less damage from every hit | 3 |
| Agility | Perfect-parry window +0.1 s (base 0.3 s), parry reach grows with it | 3 |

Each one sits in an **ability vault**, a puzzle harder than the open-world puzzles
that needs abilities from every phase of the game: sword or gun, Divinity Sense
(the vault's stele explains it in full), Settle, and at least one ability from a
later level. So each vault is seen, and remembered, long before it opens, in the
Metroid way. Every ability reports its use to the vault locks:
`BP_Physis.PhysisUsedAbility` with its flag token (`,settle,` now; later
`,lightstep,`, `,resonance,`, `,trace,`, `,dissonance,`, `,reweave,`, `,sitwith,`).
Implementation: `Content/Python/physis_center_vaults.py` and
`Tools/blueprint_logic/center_overrides.py` (`AUGMENTS`).

### Finding things in the Center: drops, Still Points, Divinity Rays and the map (Author, 2026-11-05)

The author could not find health or any puzzles in the Center. Four changes:

- **Enemy drops.** A defeated enemy drops loot on the ground under it (they used to
  be buried under the terrain). Whether it drops anything at all is random (author,
  2026-11-09): 50% at level 1, 60% at level 2, 70% at level 3, 85% at level 4,
  always at level 5. A drop is a Divinity crystal and often health (50% at level 1,
  70% at level 2, always from level 3) and sometimes ammo (40%); the strongest drop
  up to three crystals and two health pickups. Drops last 3 minutes. A Static lock
  or prism always drops a crystal at Physis's feet. Station drones drop 60% of the
  time and the boss always. Every enemy drops while Physis has under 25 Divinity or
  under 30% health, so she can always pay a required node or a Mend.
- **Still Points heal.** Standing in a Still Point restores her health to full
  ("The Still Point restores you"), but only while no enemy is within 25 m, so a
  fight cannot be won by standing in one.
- **Divinity Rays.** A shaft of light rises from every open-world puzzle, Echo Cache
  and ability vault, 36 in all, and goes out once its puzzle is solved. Colours:
  gold for an open-world puzzle (three are sealed by thorns that need Settle), cyan
  for an Echo Cache (needs Settle), violet for an ability vault (needs abilities
  from later levels). Rays are 3 km tall, so each can be seen from anywhere in
  the Center; a ray fades when she is close to it.
- **Map.** The pause menu has a fifth tab, Map, which opens with **M** or **View**
  (the pad's Select). Pressing it again closes the menu, and opening the menu over a
  scan result closes the result first. It shows the Center from above, Physis and
  her facing, the Still Points (lit once reached), and every ray's site in its
  colour, greyed once solved. The Logbook moved to **L** on the
  keyboard; on a pad it is a pause-menu tab. Elsewhere the tab says there is no
  map yet; each later level needs its own map art (`Tools/build_physis_center_map.py`
  is the pattern).

Implementation: `physis_center_scenario.divinity_rays`, `physis_center_tools.material_ray`,
and the `drones`, `saves` (`still_points`) and `map` parts of `Tools/blueprint_logic/center_overrides.py`.

## Level 3 — The Conclave (Author, 2026-11-06)

Author decisions: the level after the Center is **the Conclave**; it is **large, about an hour**
like the Center; Physis reaches it through a **Divinity current that opens in the Temple of the
First Light once she has taken the Heartbloom (Mend)**, and the Center stays open to return to;
NPC conversations are **authored and voiced** (Kokoro), with microphone conversation left for later.
Everything below that is not one of those four decisions is Proposed.

### Premise

The Conclave is the Wise's station: a habitat drum 1.6 km long and 700 m in radius, turning slowly
in the lee of a ringed gas giant, far from both fleets. About two thousand people live in it:
humans who refused the war, Robots and Mechanoids who left the Just, a few First One listeners,
and the Lightforms, beings of light who came to study with the Wise. Kairos, a human historian,
keeps its Archive. In a corner of the Commons sits an old Mecha the people call **Patience**, who
has not spoken since the war began.

Nine days before Physis arrives, an **AL swarm** drifted in. It lost its fleet when the fleets fell
silent at Meridian, and AL have no will: they keep their last order, which was to hold what they
take. They took the north half of the drum and are draining the three **Spine Pylons** that feed the
**Spine**, the light that runs along the drum's axis, so the Conclave is going dark. Physis's first
act left something behind, and the current has brought her to it.

The drum is the level's image. The floor is one of three land strips; the land rises gently to
either side, gives way to long windows onto space and the gas giant, and continues overhead, where
fields and roofs hang upside down around the Spine. Physis only walks the floor strip (Unreal's
gravity stays straight down; buildings near the middle of the strip stand upright, and the steep
outer slopes end at the window parapets).

**Look (Author, 2026-11-06): realistic, in six colours.** The Conclave is not cel shaded. It is
rendered realistically (physically based materials, real light, fog, ambient occlusion and
reflections), and only six colours exist in it: **gold, light blue, red, green, black and white**
(the author added green on 2026-11-08), with greys as mixes of black and white. White stone and plaster, black stone, iron and soil, gold metal, gold grass
and wheat, red roofs, banners and AL light, light-blue water, glass, tiles and Lightform light. Plants,
the sky, effects and shared actors follow the same rule. The people are the UE5 Mannequins in
porcelain-white or black, dressed in garments in those colours; the robots, Mechanoids, Patience and
the Lightforms are their own figures. The Center and Meridian Station keep their own looks.

### Layout (x north along the drum, metres from its middle)

| # | Space | Where | What happens |
| --- | --- | --- | --- |
| 1 | The Wellspring | South end, x −760 | She steps out of the current into a garden the Wise built around a spring of Divinity. Still Point; the current home to the Center stays here |
| 2 | The Commons | x −620 to −300 | The settlement and hub: plaza, Orrery, market, terraced homes, canals, the Archive (Kairos), the Mendery (Robots), the listeners' shrine, Patience. No enemies. Most of the people to talk to |
| 3 | The Terraces | West slope, x −250 to +150 | Hydroponic terraces under AL control. Sluice puzzle (scan the irrigation board for the order), AL barricades (Settle), the **Terrace Pylon** |
| 4 | The Reservoir | Middle, x −150 to +250 | The drum's lake (swimming). Three AL anchors on buoys hold a lock over the island: shoot them, Settle the barricade, wake the **Reservoir Pylon** |
| 5 | The Foundry | East slope, x −200 to +250 | Mechanoid workshops: pulsing furnace floors (walk them dark or Settle them), cable locks (blade) that drop a crane bridge, the **Foundry Pylon** |
| 6 | The Lightform Spire | x +300 to +420 | A spire of hardened light, sealed until the three pylons are lit. **The Trial of Light**: Iriel, a Lightform, teaches **Light Step**, then a climb through lattices, timed light routes and fast Echo Hunters to the crown |
| 7 | The Old Quarter | North-east, x +350 to +600 | The first district the AL took: dark, overgrown, optional puzzles, Light Caches behind lattices, lore, a lost Lightform child |
| 8 | The Orchard Rim | North-west, x +150 to +600 | Orchards and the Serene listeners' terrace; optional puzzles and sealed vaults for later abilities |
| 9 | The Spindle Docks | North end, x +620 to +780 | The AL nest, behind a lattice wall (Light Step) and barricades (Settle). Boss: **the AL Shepherd** |

Critical path, about 35–45 minutes: Wellspring → Commons (talk to Kairos) → the three pylons in any
order → the Spire (learn Light Step, reach the crown) → the Spindle Docks (the Shepherd) → back to
Kairos. Everything else is optional, which with the side requests, puzzles and caches brings the
level to about an hour, more for completionists.

Progress tokens: `,conclave,` (arrived once), `,at_conclave,` (she is in the Conclave: saves load
here), `,kairos,`, `,pylon1,` `,pylon2,` `,pylon3,`, `,spire,`, `,lightstep,`, `,crown,`,
`,docksgate,`, `,shepherd,`, `,conclave_done,`.

When the Shepherd falls the swarm stops: without its orders the AL are only tools again. The Spine
burns white, people come back out, and their lines change. Patience speaks one sentence. Kairos
tells her the Wise can teach her to read what a room remembers when she comes back (Trace Reading
is a later ability; nothing here grants it).

### Light Step

| | |
| --- | --- |
| Input | **X** on the keyboard, **LB** on a pad (both were free in play) |
| Cost | None; 0.9 s between steps, so traversal can never be locked behind Divinity |
| Movement | She becomes light for a moment and crosses about 7 m in a fraction of a second, in the direction she is moving (or facing) |
| Combat | She cannot be hit while she steps, so it passes through volleys and through enemies |
| Traversal | **Light Lattices** (`BP_AbilitySocket`, ability `,lightstep,`) open as she steps; some open for good, timed ones only for a few seconds |
| Locks | It reports `,lightstep,` to `PhysisUsedAbility`, so the Center's vault lattices answer it now |
| Visual stage | Learning it reaches **stage 3, Max graphics** (140% view distance): "depth and color" |

The Center's "learned at the Conclave" lattices in its vaults can be passed from now on; those vaults
still need abilities from later levels to finish.

### People and conversations

Interact (E / X on a pad) near a person starts a conversation, which pauses play. The panel shows
the speaker's name and line; every line is voiced. After the greeting the player picks a topic with
up and down and confirms with Interact; a topic answers in one or more lines and returns to the
list, and Leave ends it. People face Physis while they speak, and what they say depends on progress
(before and after the pylons, after the Shepherd). Microphone conversation can be added later on the
same people, with this as the non-microphone path the GDD requires.

| Person | Kind | Role |
| --- | --- | --- |
| Kairos | Human historian | Quest giver; the Archive; the war's history; later, Trace Reading |
| Petra Lune | Human archivist | Side request: three lost ledger pages |
| Orsolya Fenn | Human gardener | Meets Physis at the Wellspring; side request: a seed pod from the Reservoir island |
| Tamsin | Human child | Side request: a kite caught on the upper Terraces |
| Halden-7 | Robot | The Mendery; side request: its lost memory core in the Foundry |
| Forge-Mother Ilex | Mechanoid | Trapped in the Foundry; tells her how the cable locks work |
| Iriel | Lightform | Teaches Light Step in the Spire |
| Patience | Mecha | Silent until the Shepherd falls |
| Commons folk (about ten) | Humans, Robots, Mechanoids, a First One listener | Rumours, hints, and the station's life |

### Enemies (AL: tools, so they are destroyed)

| Level | Enemy | Health | Notes |
| --- | --- | --- | --- |
| 1 | AL Mite | 5 | Small, quick, in swarms |
| 2 | AL Lancer | 9 | Longer volleys |
| 3 | AL Bulwark | 16 | Heavy; Settle stuns it |
| 4 | Echo Hunter | 20 | Lightform-fast hunters in the Spire; step through their volleys |
| 4 | AL Reaver | 26 | Guards the pylons and the docks |
| 5 | AL Siegeframe | 60 | End-game wanderers in the Old Quarter; avoidable |
| Boss | AL Shepherd | 90 | Scan finds its relay; parry, Settle and Light Step through its sweeps |

### Rewards

Six augmentations, from the side requests and the Spire crown: two Health (`,aug_hp5,`,
`,aug_hp6,`), one each of Katana (`,aug_katana4,`), Pistol (`,aug_pistol3,`), Defense
(`,aug_defense4,`) and Agility (`,aug_agility4,`). Plus Divinity crystals, capsules, Light
Caches, and Divinity Rays over every optional puzzle (gold), Light Cache (cyan) and vault (violet).
The Conclave has its own page on the pause-menu map.

### Implementation

`Tools/build_physis_conclave.py` (Blender: drum, terrain, buildings, people, AL, scatter),
`Content/Python/physis_conclave_lore.py` (all text and dialogue), `physis_conclave_tools.py`
(`conclave:` operations), `physis_conclave_scenario.py` (placement),
`Tools/blueprint_logic/conclave_logic.py` (Light Step, people, the current, the director), and
Conclave branches in `center_overrides.py` (music, saves, the Continue row, fidelity, map).
The level is `/Game/Levels/L_Conclave`, assets `/Game/Conclave`. It holds a `BP_Awakening`, which
is how the shared logic recognises an open-world level (Still Points, drops on the ground, enemy
hover, restoring a save), and a `BP_ConclaveDirector` for what is its own.

## Level 4 — Earth: the Wounded Grove (2026-11-10)

Author decisions: the author asked for "the next whole level" after the Conclave from this document, which makes it
the Earth slice, **the Wounded Grove**, where Physis learns **Resonance Link** (ability 4); its assets must be **AAA
quality and as realistic as possible** (so the "warm, painterly" Earth look proposed above is withdrawn: Earth is
rendered realistically, in natural colours); free **CC0 photo-scanned assets** (Poly Haven, ambientCG) may be
downloaded for it; and **one person appears as a MetaHuman**, the Array's director. Everything below that is not one
of those decisions is Proposed.

### Premise

Earth, a few days after Meridian. A wooded valley the Just call Site Verdance. Its trees are one organism: ten
thousand trunks on a single root system, older than any city. Forty years ago the Just built the **Deeproot Array**
into its oldest tree, the **Heartwood**, to drive Divinity through those roots: a ground-to-orbit defence that could
push a fleet out of the sky. It worked twice. It also wounded the grove. Where Divinity was forced through, the roots
came up as **thornroot**, black and barbed, and the ground split around the Heartwood (the **Rift**).

When the fleets fell silent at Meridian, no order to stand down ever reached Verdance. The Array's automatic defence,
the **Hedge** (machines without will, like the AL: the Just did not trust a mind with this job), sealed the site with
its last staff inside and went on forcing the roots. The grove is dying of it. Physis's first act left this behind
too, and a Divinity current brings her to it. Verdance is one of the book's seventeen human installations, and the
first she undoes.

It is a Great Installation in the sense of "Installations are the dungeons": one new ability, one boss, one
map-opening shortcut, 45 to 90 minutes. It is not hardened: nobody's mind has to be entered here.

**Look (Author, 2026-11-10): realistic.** Physically based materials built on photo-scanned surfaces, scanned plants
and rocks, late-afternoon sun through a real atmosphere, volumetric light in the canopy, Lumen global illumination
and reflections. Natural colours. Three lights tell three things apart: the Just's machines glow **amber**, thornroot
(forced Divinity) a sick **magenta**, and resonance, the grove's own linkage, **green-gold turquoise**. No
post-process stylisation, no 3D text.

### Layout (x north, y east, metres; the valley is about 1.1 km by 0.8 km, walled by cliffs)

| # | Space | Where | What happens |
| --- | --- | --- | --- |
| 1 | The Hollow | South end, x −500 | She steps out of the current into a mossy clearing. Still Point; the current home to the Center stays here |
| 2 | The Reclaimed Road | x −490 to −260 | An old highway under forty years of forest. First Hedge patrols, a thornroot wall (Settle). **Burr**, a Mechanoid loader, has been holding up a fallen overpass slab for nine years |
| 3 | Old Town | South-east, x −320, y +270 | Optional: overgrown ruins, a Harrow that can be avoided, a flow puzzle (after the link) for the Katana Augmentation, a sealed vault |
| 4 | The Field Camp | x −250 | The level's safe place: **Thessaly-4**, the Array's Robot botanist, shut out when the Hedge sealed the gates; **Wick**, the camp's courier; the first intercom post, where **Director Maren Voss** speaks from inside the Array |
| 5 | The Graft | x −160 | Thessaly's oldest graft, two trunks grown into one. Physis listens to it and understands **Resonance Link** |
| 6 | The Gully | x −112, across the whole valley | A dry gorge 16 m wide, its bridge long gone: crossed only by the link. The barrier she will remember |
| 7 | The Understory | Mid valley | Still Point where the trails part: west to the water, east to the power, north to the Rift |
| 8 | The Drowned Campus | West, around the lake | The Array's flooded research blocks. Swim, and link from roof to roof. Ends at **the Weir**: carry the river's flow to the sluice (`,water,`) |
| 9 | The High Canopy | East | Platforms in three great trees, linked upward to **the Relay** on its mesa: carry the charge to the mast (`,power,`) |
| 10 | The Rift and the Heartwood | North, x +330 | A ring gorge 16 m wide around the oldest tree. Water grows a root bridge across its west side; power wakes the link chain on the east side. The Array's gate opens only when both lifelines are back |
| 11 | The Deeproot Array | Inside the ring wall | The Root Court around the trunk: forced vents (Settle), the **core coupling** (redirect the surge into the Heartwood: `,stabilized,`), then **the Warden** |
| 12 | The Falls | North-west | Optional: a link course up the cliff beside the waterfall to a cache |

Critical path, about 40 to 50 minutes: Hollow → Road → Camp (Thessaly) → the Graft (Resonance Link) → across the
Gully → the Weir and the Relay in either order → the Rift → the Array's gate → the core coupling → the Warden →
Director Voss, in person → back to Thessaly. With the side requests, Old Town, the Falls, the caches and the sealed
vaults the level runs about an hour.

Progress tokens: `,grove,` (arrived once), `,at_grove,` (she is on Earth: saves load here), `,tess,`, `,resonance,`,
`,water,`, `,power,`, `,gr_first_w,` or `,gr_first_e,` (which lifeline came first), `,arraygate,`, `,stabilized,`,
`,warden,`, `,voss,`, `,grove_done,`; side requests `,burr,` `,pin,` `,wick,` `,can1,` `,can2,` `,can3,` `,cans,`;
puzzles and caches `,gr_*`.

**The living-terrain rule, for the first time (see "Living terrain and adaptive puzzles").** Whichever lifeline she
restores first chooses one of two authored arrangements of the core coupling's relays (`,gr_first_w,`: the relays stand
along the court's west side, among the water roots; `,gr_first_e,`: along the east side, among the cable runs). Both
have the same source, the same socket, the same exit and the same objective, both are solvable with the abilities
she must have by then, and the choice is a saved token, so a load restores the same arrangement. The map's skeleton
never changes.

When the Warden falls the Hedge stops. The Array stands open and Director Voss comes out of the control bunker.
The grove answers at once: the thornroot withdraws, the blight leaves the ground, the crown of the Heartwood
greens (the world remembers her actions). Root bridges grow across the Rift's south side and across the Gully, a
walking shortcut from the Heartwood to the camp. Thessaly tells her Verdance is one of seventeen.

### Resonance Link

| | |
| --- | --- |
| Input | **G** on the keyboard, **left stick click** on a pad |
| Cost | None; 0.6 s between uses, so traversal can never be locked behind Divinity |
| Aim | The link goes to what she looks at: the node nearest the centre of the view, within its range and in line of sight; with no node, the enemy nearest the centre of the view |
| Traversal | **Link anchors** (`BP_LinkNode`): she is pulled along the link to the anchor's perch, across gaps, up into the canopy, from the water to a roof. Chains of anchors are routes |
| Combat | **Tether**: the enemy she aims at is linked to its nearest neighbour for 8 s. What one suffers, the other suffers, whatever its armour: strike the soft one to hurt the shielded one. A lone enemy is held still for 2 s instead |
| Puzzle | **Flows**: link a source (water, power, surge) and she carries its flow on a beam of light, as far as the link reaches; link a relay to pass it on from there; link the matching socket to deliver it. Redirecting a flow is the level's key |
| Locks | It reports `,resonance,` to `PhysisUsedAbility`, so the Center's and the Conclave's resonance nodes answer it from now on |
| Visual stage | Motion: once she feels the grove's linkage the world answers her. Wind moves through leaves and grass, grass parts around her, water answers her steps. Before it, the valley holds its breath |

### People

| Person | Kind | Role |
| --- | --- | --- |
| Thessaly-4 | Robot, the Just's field botanist | Quest giver; forty years of measuring the roots; shows her the Graft; closes the level |
| Burr | Mechanoid loader | Holds the overpass slab up; side request: his coupling pin, in the wrecked hauler in the lake |
| Wick | Courier unit | The camp's scout and gossip; side request: three seed canisters (Old Town, a campus roof, the canopy) |
| Director Maren Voss | Human, the Array's director (MetaHuman) | A voice on the intercom posts, afraid of an open sky; in person once the Warden falls |

Voss carries the Just's fear rather than a villain's part: if the Array stops, nothing stands between Earth and the
First Ones' fleets. She is not argued out of it. She sees the grove answer, and says what the Array cost.
Conversations work as in the Conclave (authored, voiced, topics; microphone conversation later on the same people).

### Enemies: the Hedge (machines without will, so they are destroyed)

| Level | Enemy | Health | Notes |
| --- | --- | --- | --- |
| 1 | Hedge Wasp | 5 | Small, quick, in swarms; the best thing to tether a shielded machine to |
| 2 | Hedge Lancet | 9 | Long volleys from range |
| 3 | Hedge Burl | 16 | A shell of plates that turns light blows (tether it, strike heavy, or Settle it) |
| 4 | Hedge Palisade | 20 | Its face turns every blow: strike its back, or tether it |
| 4 | Hedge Thresher | 26 | Guards the Weir, the Relay and the Rift |
| 5 | Hedge Harrow | 60 | End-game wanderer in Old Town; avoidable |
| Boss | The Warden | 110 | Its face turns every blow, and its shield emitters on the wall answer only to the sidearm. Scan says how: tether it to its own Wasps, or get behind it |

Thornroot is not an enemy: walls of it dissolve to Settle, knots of it break to the blade.

### Rewards

Five augmentations: Health (`,aug_hp7,`, the Heartwood's gift once the Warden falls), Katana (`,aug_katana5,`, Old
Town's vault), Pistol (`,aug_pistol4,`, Voss), Defense (`,aug_defense5,`, Burr) and Agility (`,aug_agility5,`,
Wick). Plus Divinity crystals, capsules, seed caches, and Divinity Rays over every optional puzzle (gold), seed
cache (cyan) and sealed vault (violet). The grove has its own page on the pause-menu map.

### Implementation

`Tools/grove/README.md` is the build contract. `Content/Python/physis_grove_plan.py` (the world plan),
`Tools/grove_meshes/*.py` and `Tools/build_physis_grove.py` (terrain, the level's own meshes, scatter),
`Art/Scans/Grove` (the downloaded scans and their manifest), `Content/Python/physis_grove_lore.py` (all text),
`physis_grove_tools.py` (`grove:` operations), `physis_grove_scenario.py` (placement),
`Tools/blueprint_logic/grove_logic.py` (Resonance Link, link nodes, beams, tethers, the director, travel, and, as its
parts `shared`, `hud` and `relic`, the Grove branches in the graphs other levels own: music, saves, the Continue row,
fidelity, augmentations, the map page, the relics' scan tags). The level is
`/Game/Levels/L_Grove`, assets `/Game/Grove`. Like the Conclave it holds a `BP_Awakening` (an open-world level for
the shared logic) and its own `BP_GroveDirector`. A Divinity current in the Center's temple opens once the Shepherd
has fallen (`,shepherd,`) and carries her to the Hollow.

**Status (2026-11-15).** The level's land, look and gameplay are built and the critical path was tested in
Play-in-Editor (the link, the three flows, the gate, the core coupling, the tether, the people, travel, save and load).
What differs from this section is listed in `Tools/grove/DESIGN_NOTES.md`, "As built". Still open: Director Voss's
own MetaHuman (a Conclave person stands in), the Falls' link course and the sealed vaults for later abilities, and a
played balance pass of the fights.

## Level 5 — Arche: the City of the Descent (2026-11-16)

Author decisions: the level after the Wounded Grove is **the First Ones' Planet** (2026-11-15); Physis learns
**Reweave** there (ability 7; the table's order may branch after Settle); its look is **realistic, in a cool palette**;
**Aeon appears in person**, in a designed native First One form, with Serene keepers; it is **about an hour**, a Great
Installation; and the planet is to have a **name**. Everything below that is not one of those decisions is Proposed,
the name included.

### Premise

**Arche**, "the Beginning": the First Ones' homeworld (the book's "sovereign space", concentrated into one place as
Earth concentrates the human side). **Kathodos**, the city of the Descent, climbs a canyon basin in three tiers. It
is one of the First Ones' installations, fewer and older than humanity's seventeen: ages ago the Vigil raised the
**Sundering Lens** at its head, a defence that does not break what it strikes but makes it forget its shape. When
human engines first crossed Arche's sky the Vigil fed the Lens their own city. Every bridge and stair of Kathodos
was unwoven, so that no invader could ever walk it. The stones still hang in the air where they were unmade.

The Lens's keepers are AL, tools without will, the same the Vigil sent against Meridian; nothing ever told them to
stop. The **Serene**, who would neither leave nor fight, have lived cut off on the Lower Tier ever since. **Aeon**, the
eldest of them, has spent the time counting the stones. Physis's first act left this behind too, and a Divinity
current brings her to it.

It mirrors the Grove without repeating it: there a living thing was forced; here a made thing was unmade. The
Just's fear (Voss) was an open sky; the Vigil's (**Maruth**, the Lens-keeper) is a young species with a weapon. Neither
is argued out of it. Both watch what they kept apart come back together.

**Look (Author, 2026-11-16): realistic, cool.** Physically based materials on scanned surfaces graded to pale stone
and blue-black rock, silver alloy, deep blue glaze, ice-blue and violet crystal with luminous edges, a small cold
sun low in a deep sky, pale haze with mist in the Chasm. The First Ones built in large calm forms: battered walls,
tall pointed openings, long courses of pale stone with one thin line of electrum. Three lights tell three things
apart: the Serene's is **ice blue**, the Vigil's works glow a cold **violet**, and Reweave glows a warm **pearl gold**.
The AL keep their red. No post-process stylisation, no 3D text.

**The First Ones' native form (Proposed design).** Tall and slender, about 2.3 m: a body of pale layered mineral plates
over a dark core that shows at the joints; a long smooth head with no face in the human sense, only one vertical
seam of light; a crown of thin slivers floating a hand's width off the head; long four-fingered hands; a mantle and
a long skirt of heavy cloth. They stand very still. The Serene wear pearl and indigo; the Vigil violet over
night-blue enamel. Built figures, not MetaHumans.

### Layout (x north, y east, metres; the basin is about 1.1 km by 0.8 km, walled by cliffs; tiers of 12 m)

| # | Space | Where | What happens |
| --- | --- | --- | --- |
| 1 | The Landing | South end, x −500 | She steps out of the current. Still Point; the current home stays here |
| 2 | The Processional | x −490 to −300 | The road every First One walked once, between columns. First Ward patrols |
| 3 | The Hearthold | x −290 | The safe place: **Aeon**; the keepers **Ilun**, **Oreth** and **Sael** |
| 4 | The First Arch | x −215 | The one thing the unweaving did not take. Aeon shows her how stone remembers: **Reweave** |
| 5 | The Great Chasm | x −150, wall to wall | 26 m across; its bridge, **the Sundered Span**, hangs above it in pieces. Rewoven for good: the barrier she remembers, and the shortcut |
| 6 | The Concourse | x −70 | Still Point where the Lower Tier's ways part; bulwarks to reweave under fire |
| 7 | The Cisterns | West, on the Lower Tier | The city's water. A pier, then restless causeway (it holds nine seconds) to the island and the **western Mirror** |
| 8 | The First Stair | x +93 | Lower to Middle Tier: rewoven for good |
| 9 | The Crystal Garden | East, on the Middle Tier | Ten thousand years of grown crystal. A maker's **loom** holds two shapes of three: the stair and the causeway to the pinnacle and the **eastern Mirror** |
| 10 | The Second Stair | x +276 | Middle to Upper Tier: rewoven for good |
| 11 | The Galleries | North-east, on the Upper Tier | A mesa whose stair climbs two thirds of it; a knot of the grove's kind draws her the rest (Resonance Link) to the **northern Mirror** |
| 12 | The Lens Court | North, x +400 | A ring wall and, in its gate, **the Veil**: it falls only when all three Mirrors are turned on it. Inside: the Lens, and **the Sunderer** |
| 13 | The Ossuary of Names | South-east | Optional: three name-steles to reweave open a vault (Katana Augmentation); a Siegeframe that can be avoided |

Critical path, about 40 to 50 minutes: Landing → Processional → Hearthold (Aeon) → the First Arch (Reweave) → the Span
→ Concourse → the three Mirrors in any order (the Cisterns need only the Lower Tier; the Garden the First Stair; the
Galleries both Stairs) → the Veil → the Sunderer → Maruth, in person → back to Aeon. With the side requests, the
Ossuary, the caches and the sealed vaults the level runs about an hour.

Progress tokens: `,arche,` `,at_arche,` (saves load here), `,aeon,`, `,reweave,`, `,ar_span,`, `,ar_stair1,` `,ar_stair2,`,
`,ar_mirror_w,` `,ar_mirror_e,` `,ar_mirror_n,`, `,ar_veil,`, `,sunderer,`, `,maruth,`, `,arche_done,`; side requests
`,ilun,` `,chime,` `,oreth,` `,tab1,` `,tab2,` `,tab3,` `,tablets,` `,sael,` `,seedstone,`; the Ossuary `,ar_name1-3,`
`,ar_vault,`; guards, caches and seals `,ar_*`.

When the Sunderer falls the Lens goes dark and the world remembers: the stones that hang over Kathodos come down
(everything tagged for the unweaving goes), the Cisterns' causeway stands for good, and Sael's seedstone, if it was
brought, is growing at the Hearthold. Aeon tells her there are others, on both worlds.

**The Metroid rule.** The Span and the two Stairs are the map's skeleton: authored, rewoven once, saved by token,
never changed. Restless stone and looms act only inside a room. Two **sealed vaults** (Trace Reading, Dissonance)
are seen here and opened later; a few of the Grove's link knots stand in Kathodos, so Resonance Link opens doors on
this world as Reweave will on the others.

### Reweave

| | |
| --- | --- |
| Input | **B** on the keyboard, **right stick click** on a pad |
| Cost | None; 0.8 s between uses |
| Aim | What she looks at: the sundered thing whose mark (a ring of slivers turning round a pearl of light) is nearest the centre of the view, within its range and in plain sight; the mark swells when it would be taken |
| Traversal | **The city's bones** (the Span, the Stairs, the Mirrors' frames) knit together and stay, by token. **Restless stone** (near the Lens, or over water) holds a few seconds and lets go; reweaving it again holds it longer |
| Combat | **Bulwarks**: a broken wall rewoven stands 14 s between her and the Ward's fire |
| Puzzle | **Looms**: the weaves of one loom cannot all stand; one more, and the oldest lets go |
| Locks | It reports `,reweave,` to `PhysisUsedAbility`, so reweave sockets on the other worlds answer it |
| Visual stage | Complete geometry: what she reweaves is whole, and when the Lens goes dark the whole city is |

### People

| Person | Kind | Role |
| --- | --- | --- |
| Aeon | First One, eldest of the Serene | Quest giver; counts the stones; shows her the First Arch; closes the level |
| Ilun | Serene, keeper of the Cisterns | Side request: a wind chime, on the Garden's pinnacle (Defense Augmentation) |
| Oreth | Serene, of the record | Side request: three record tablets (the Ossuary, the Middle Tier, the Galleries) (Agility Augmentation) |
| Sael | Serene, the youngest | Side request: the last seedstone, on the Cisterns' island (Pistol Augmentation) |
| Maruth | First One, Lens-keeper of the Vigil | A voice in the speaking stone before the Veil; in person once the Sunderer falls |

The book's Aeon is a First One and a central figure; the game keeps that and adds nothing the book contradicts as
far as this document records it. Aeon's lines here are new writing for the author to review. The Vigil's leader is
still unnamed (decision 6 below): Maruth keeps one Lens and leads no one.

### Enemies: the Ward (AL: tools, so they are destroyed)

The Conclave's AL, at home: Ward Mite 5, Ward Lancer 9, Ward Bulwark 16 (turns light blows), Ward Hunter 20 (fast),
Ward Reaver 26 (guards the Mirrors and the Stairs), Ward Siegeframe 60 (the Ossuary road; avoidable), and the boss,
**the Sunderer**, 120: its face turns every blow, and she fights it among four bulwarks that she must keep reweaving.

### The Climb

Whoever falls into the Great Chasm walks out: a ramp of hung causeway slabs rises against the south wall from the
floor to the south rim beside the Span. It leads only to the south side, so the Span is still the way across.

### Enemies: the air-swimmers (living, so they scatter and gather again)

Arche has animals older than the city, and the Lens has maddened them. They hold the open ground between the places
the Ward guards: **Drift Mote** 4 (shoals, a darting bite), **Bell Medusa** 9 (turns and lashes with its tendrils),
**Shellback** 18 (its shell turns light blows; it rams shell first), **Sky Ray** 20 (fast; a tail whip), **Crest
Stalker** 28 (keeps a territory: three of the caches; rears and bites), and the **Leviathan**, 70, circling the
Ossuary (avoidable; a body slam). They fight only with their bodies, never with fire: each closes, calls and draws
back before it strikes, and the blow lands only if she is still in reach. Each is rigged: fins, tendrils, necks, jaws
and tails swim on their own and take part in the strike. None of them is destroyed: struck enough, one scatters like breath
on glass and gathers again somewhere quieter. They are the game's first organic enemies; the same kind of animal is
wanted on the earlier worlds too (Proposed: grove and basin fauna for levels 1 and 4).

### Rewards

Five augmentations: Health (`,aug_hp8,`, the Lens's Heart), Katana (`,aug_katana6,`, the Ossuary), Pistol
(`,aug_pistol5,`, Sael), Defense (`,aug_defense6,`, Ilun), Agility (`,aug_agility6,`, Oreth). Geode caches (blue rays),
the Ossuary's puzzle (gold), the sealed vaults (violet). Arche has its own page on the pause-menu map.

### Implementation

`Tools/arche/README.md` is the build contract. `Content/Python/physis_arche_plan.py` (the world plan),
`Tools/arche_meshes/*.py` and `Tools/build_physis_arche.py` (terrain, architecture, figures, scatter),
`Content/Python/physis_arche_lore.py` (all text), `physis_arche_tools.py` (`arche:` operations: materials on the
Grove's masters and scans, import), `physis_arche_level.py`, `physis_arche_scenario.py`, and
`Tools/blueprint_logic/arche_logic.py` with `arche_shared.py` (Reweave, `BP_Weave`, the director, travel, and the
Arche branches in the shared graphs). The level is `/Game/Levels/L_Arche`, assets `/Game/Arche`. A Divinity current
in the Center's temple opens once the Warden has fallen (`,warden,`) and carries her to the Landing.

**Status (2026-11-16).** Built: the land and look, the architecture and the First Ones as generated meshes, Reweave and
its Blueprints, the placement of the whole level, the map page, travel, saves. The critical path was tested by script
in Play-in-Editor (`Tools/arche/README.md`, "Gameplay pieces"). Nobody has played it by hand, and Aeon's and Maruth's
lines and the First Ones' design are new writing for the author to review.

## Core play loop

1. Explore, fight, and hit a door you cannot open. It goes on the map.
2. Read the environment and speak with the people around it.
3. Enter an installation and learn an ability or new application.
4. Beat the dungeon and its boss using it, then see the world react.
5. Check the map, remember the door, and take the shortcut home.
6. Find the secrets the new ability exposes on the way.

**Camera (decided, Proposed):** third person with lock-on, over-the-shoulder for scan
and aiming. It shows Physis's transformation, suits sword play, and uses the existing
character. The first-person template gets replaced.

Target platforms, input devices, and minimum hardware remain to be chosen.

## Spoken NPC conversations

The player approaches an NPC, speaks English through a microphone, and hears a spoken
reply. Start with push-to-talk and clear listening, thinking, and speaking indicators,
with interruption support. Natural turn detection can follow.

The pipeline needs audio capture, speech understanding, an NPC dialogue model, voice
output, and synchronized animation. Evaluate providers with the same sample scenes.
Keep service credentials out of the shipped client, and measure response time and
cost per conversation minute.

Each NPC has an authored identity, voice, faction, knowledge limits, current goals,
and a small persistent memory. Supply only facts available at that moment. The game
validates any proposed quest or world action before applying it. Spoken claims cannot
grant powers, invent objectives, or rewrite canon.

Critical exchanges use dependable authored beats inside flexible conversation.
Different phrasings work; progress never needs a hidden sentence. NPCs may refuse or
disagree in character. Preserve Cassian's grief, Aeon's perspective, and Kairos's
historical role.

Voice supplies depth, not pacing: action sequences never wait on an AI reply. In a
spoken boss stage, the fight is already won and the conversation has authored beats
that cannot fail. Every voiced step needs a non-microphone path defined in
preproduction. On service failure, use spoken recovery lines, preserve state, and keep
physical routes usable. Decide on offline dialogue after measuring the prototype.

MetaHumans suit human figures such as Kairos and Physis. Robots, Mechanoids, Mechas,
Lightforms, and the First Ones need their own designs, including Cassian. Test
assembly, expression, lip sync, and runtime performance separately.

## Living terrain and adaptive puzzles

Keep each world's terrain identity and major landmarks authored. Build a limited
vocabulary of changes: roots form a bridge, water changes course, crystals rotate, a
current shifts, a structure stabilizes. Player actions alter persistent regional
state: ecological health, Divinity disturbance, local trust, resolved events, unlocked
abilities. Reactions have a legible cause; avoid a single hidden morality score.

**The Metroid rule:** the map's skeleton is sacred. Ability gates, shortcuts, door
positions, Still Points, and room connections are authored and never change, because
players navigate by memory. Adaptive changes apply only inside a room or module, and
to optional routes. A player's remembered door is always where they remember it.

The adaptive director selects a configuration from authored modules. Begin with
explicit rules, then test whether a model choosing among valid options adds variety.
Model-generated geometry or executable logic is out of scope.

Every proposed change must pass game-owned checks:

- The objective is reachable with currently available abilities.
- Entrances, exits, checkpoints, and necessary clues remain accessible.
- New geometry does not trap, intersect, or displace the player unsafely.
- The current puzzle does not change while it is being solved.
- Completed objectives and permanent unlocks remain respected.
- The same saved world state restores the same accepted configuration.

If a proposal fails, use a known valid configuration. Apply major changes at clear
moments with visible or audible feedback. Save the configuration ID rather than asking
a model to recreate it on load.

Example: restoring water flow in an Earth grove opens a root bridge on return, and a
water-routing puzzle uses a different valid arrangement. Restoring a power conduit
first gives another arrangement of the same ability. Both keep the same exit and
objective.

## Campaign outline

| Act | Book chapters | Play |
| --- | --- | --- |
| Opening | V–VII | Birth, Meridian Station, the settling |
| 1. Learning herself | VI, VIII | Center hub, learn Settle, reach the Conclave, meet Kairos |
| 2. The two peoples | IX | Earth and First Ones' Planet open in either order; first Great Installations; Vigil, Serene, Aeon |
| 3. The Reckoning | X | Physis gathers both sides; a major story set piece at the Threshold, with no combat. Cassian's “Did it work?” |
| 4. The Dismantling | XI | Remaining installations, hardened facilities, Inner Installations; the map opens fully |
| 5. The Offer | XII–XIII | Eternity offered; holdouts refuse; The Weight |
| Finale and epilogue | XIV–XVI | Integration seen across all healed places, Cassian's memorial, Cosmoforms, creation as the last playable moment |

The book offers no final villain, and the game should not invent one to fight at the
Center. Proposed climax: the holdouts' last desperate attempt, a Vigil and Just remnant
acting together, as the final action sequence, followed by The Weight. The Vigil needs
a named leader for this; the book gives none, so the author should supply one.

Target length (Proposed): 10–14 hours, or 18–20 with everything found. Cutting order if
needed: fewer minor nodes first, then one Great Installation per world.

## Development milestones

These are completion gates, not calendar promises. Confirm team capacity, budget,
assets, platforms, and hardware before assigning dates. Build one complete region
before multiplying content.

| Milestone | Deliverable | Completion gate |
| --- | --- | --- |
| 0. Foundation | Stable rendering, source-control habits, packaged blank build, decisions below | Editor stable without workarounds or a known accepted alternative; full-quality rendering can be evaluated |
| 1. Action core | Third-person Physis, camera, movement, lock-on, sword, gun, one AL drone, one warrior, Divinity Sense, Composure, Still Point save, in a graybox room | Fighting feels good for ten minutes in gray boxes. **Do not advance until it does** |
| 2. Meridian Station graybox | All nine spaces, boss, shortcut loop, map screen, spoken scan lines | A new player finishes without help and can describe the sealed door later |
| 3. Visual and character proofs | Realistically cel-shaded Center; station art; Earth and First Ones' shading tests; Physis with weapons, expression, speech | Each destination is distinct; scan and combat tells stay readable; richest stage meets budget |
| 4. Voice and terrain proofs | One bounded voiced NPC; one region with two action-dependent configurations | Natural paraphrases work; speech failures recover; both variants solvable and persistent |
| 5. First playable | Birth, polished Meridian Station, voiced crew, the settling, arrival at the Center hub | Works in a packaged build; save and reload hold; voice latency and cost are measured |
| 6. Production systems, Earth slice | Ability gates, progression graph, map, Settle and Resonance Link, NPC authoring, adaptive modules, The Wounded Grove | Backtracking through the slice works with Station and Center connected; NPC memory and terrain state persist |
| 7. Three-world campaign | Conclave, regions, installations, Inner Installations, faction arc, finale, epilogue | Playable start to finish with placeholders; every mandatory path covered in every allowed order |
| 8. Alpha and beta | Final art and audio, balance, optimization, external playtests | Required features present; performance, accessibility, AI recovery, and cost hit targets |
| 9. Release preparation | Final builds, packaging, service deployment, support plan | Fresh-install playthrough passes on supported hardware; builds and backend are reproducible |

Milestones 3 and 4 can overlap. Do not scale campaign content until the Earth slice
demonstrates the intended experience.

## Later Earth slice: The Wounded Grove

An invented game location for review. A small grove around a damaged research site.
Explore two connected routes and meet a barrier that is easy to remember. Speak to one
new local NPC. Learn Resonance Link and gain a visual stage. Redirect a flow to
stabilize the site; earlier actions choose one of two authored arrangements. Beat a
defensive-system boss using sword, gun, and the link. See the grove respond, return by
shortcut, then save, reload, and verify the change and the NPC's memory persist.

## Architecture and production responsibilities

| System | Owns | Boundary |
| --- | --- | --- |
| Player character | Movement, camera, lock-on, input | Reads ability state; does not own it |
| Combat | Sword, gun, heat, Coherence, Composure, hit reactions, enemy data | Data-driven, so abilities add behavior without rewriting attacks |
| Progression | Abilities, Understanding levels, expansions, permanent unlocks | AI cannot award upgrades; first map allows only Divinity Sense |
| World map and gates | Region graph, gate requirements, map state, shortcuts, Still Points | Skeleton is authored and never touched by the adaptive director |
| Scan system | Targets, facts, Codex, feedback | Reveals authored information |
| Planet profiles | Shading identity, lighting, terrain modules | Identity stays recognizable across stages |
| Regional simulation | Persistent events, condition, puzzle layouts | Changes validated and applied at controlled times |
| Dialogue service | NPC context, memory, speech | Requests game actions through a narrow validated interface |
| Character presentation | Animation, expressions, lip sync, visual progression | Receives approved events; does not decide quest state |
| Save system | Progression, map, regions, approved memories, configuration IDs | Restores outcomes without a fresh AI response |
| Developer tooling | Event history, active gates, reachability checks, AI timing and cost | Makes failures reproducible |

Use Blueprints and data assets for authoring. Add C++ for the combat core and
anything performance-sensitive, which means converting this Blueprint-only project
early. Keep editor MCP tooling separate from shipped AI. Commit before changing binary
levels and character assets. Record asset sources and usage rights as content enters
production.

## Main uncertainties and how we resolve them

| Uncertainty | Earliest practical check | Decision it enables |
| --- | --- | --- |
| Combat may not feel good | Milestone 1 graybox | Whether the sword and gun model needs rework before any content |
| Weapons could clash with the book's nonviolence | Playtest and author review of the lethality rule | Final rule on living enemies |
| Interlocked worlds could soft-lock | Progression graph tested in every order | Allowed sequence breaks and branching |
| “Better graphics” could become noise or cost | Same scene at every stage on target hardware | Art rules and final budgets |
| Spoken dialogue may feel slow or mishear players | Repeat conversations across accents and microphones | Pipeline, turn-taking, recovery |
| Adaptive puzzles could feel arbitrary | Both layouts, varied order, interruption, reload | Director's vocabulary and rules |
| MetaHuman detail could overwhelm budgets | Physis in the shading proof with combat running | Character limits |
| Online AI has recurring costs | Measure real usage in the first playable | Session limits, budget, offline stance |
| Scope is large for the team size | Time actual effort on Meridian Station | Final count of installations and nodes |

## Decisions for the next review

1. Confirm the short birth opening before Meridian Station, or move birth elsewhere.
2. Decide the lethality rule against living enemies.
3. Decide where sword and gun come from long term: ordinary weapons, or condensed from
   Divinity. Update the concept art either way, since it shows her unarmed.
4. Approve the Center hub, the Conclave as settlement, and the installation counts.
5. Approve the ability list, especially Sit With and The Weight.
6. Name the Vigil's leader and confirm the “hardest decision” reading.
7. Supply terrain and station references; refine non-Center shading.
8. Set platforms, minimum hardware, team size, and budget.
9. Decide online requirements, voice style, and accessibility expectations.

After this review, start Milestones 0 and 1. This roadmap does not authorize full
campaign production before the author's next direction.
