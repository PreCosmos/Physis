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
later levels add more. The HUD shows up to sixteen reserve tanks: it showed nine until 2026-11-19, when Hesper's
brought the total to eleven and two were held but never drawn (`Tools/blueprint_logic/augment_fix.py`).

### Augmentations and ability vaults (Author, 2026-11-04)

Augmentations are permanent upgrades, kept as progress flags so saves keep them:

| Kind | Effect per augmentation (tuning values) | In the Center |
| --- | --- | --- |
| Health | One more Health Tank (+10 health), fully heals | 4 |
| Katana damage | Sword hits +25% | 3 |
| Pistol damage | Gun hits +30%, the Divinity Shot too | 2 |
| Defense | 15% less damage from every hit, each on what the others leave (×0.85 each: eight leave 27%) | 3 |
| Agility | Perfect-parry window +0.1 s (base 0.3 s), parry reach grows with it | 3 |

Defense stacked by subtraction (1 − 0.15 per augmentation) until 2026-11-19. That reached zero at the seventh
(Halcyon's), and the hit code reads zero or less as "not set" and charges full damage, so the seventh brought full
damage back. It now multiplies (`Tools/blueprint_logic/augment_fix.py`). Each level since the Grove adds one of every
kind; levels after Hesper should not keep that pattern unchanged (parry window 1.1 s and about ×3 damage after Hesper).

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

### Reweave, seen

A sundered thing is not gone: it hangs where it stood as a slowly turning field of its own stone blocks. When she
reweaves it the blocks fly home in the order they were laid, so the Span builds outward across the Chasm, a stair
climbs, a wall closes. A restless thing lets go the same way. This holds for everything Reweave touches.

### The keepers

Besides Aeon and the Hearthold's four, nine Serene keepers stayed at their posts across the city, from the Landing
to the Upper Tier. Each says who they are, what they keep, and answers one question that helps with what lies ahead.


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

**The other worlds' animals (author, 2026-11-17: "organic enemies in all levels with physical attacks"; species, names
and text Proposed).** Each earlier world has three species of its own on the body plans of Arche's air-swimmers
(`Tools/arche_meshes/fauna.py`, `Content/Python/physis_fauna_lore.py`), added beside the machines, none replacing one
(`Content/Python/physis_fauna.py`): the station's **Breach Mite** 3, **Coolant Bell** 7 and **Hull Limpet** 12 (things
of the dark between ships, in through the breach after the reactor's Divinity; they joined the fight rooms until the
author had them all removed on 2026-11-18, so the station keeps only its machines and the Pyre Lion); the Center's
**Lantern Angel** 4, **Glass Ray** 16 and **Marsh Stalker** 22 (its own crystal life, strayed too near the wounds); the
Conclave's **Goldgrass Mote** 4, **Reservoir Bell** 9 and **Terrace Ray** 18 (the Wise's garden and reservoir stock,
driven wild by the swarm's signal); the Grove's **Blightfly** 4, **Burlback** 18 and **Canopy Stalker** 26 (the
valley's animals after forty years of the Array's discharges). They fight as Arche's do, with their bodies.

**Elements (author, 2026-11-17: "give elemental types and attacks to the already existing enemies"; the assignment is
Proposed).** Every enemy has an element: fire (a hit burns for three seconds), ice (slows her walk for 3.5 s), thunder
(a fast bolt; she cannot act for 0.6 s), wind (throws her back), dark (takes 15 Divinity) or light (a bolt no guard
stops). A blocked or parried hit carries none. Machines fire bolts of their element; living animals carry it on their
blow, and all but the small swarm animals now also spit a bolt of it from range (so "never with fire" above no longer
holds for them). Rules: `Tools/blueprint_logic/elements.py` (`BP_TrainingDrone.Element` and `Spits`, `BP_EnemyBolt`,
`BP_Physis.PhysisElement`). Who has which: `Content/Python/physis_elements.py`, whose `apply(world)` must be run again
after a level's scenario is re-placed. Seven new elemental monsters are designed but not made:
`Art/Monsters/DESIGN_BRIEFS.md`.

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

## Level 6 — Earth: Halcyon, the Drowned Harbour (2026-11-18)

Author decisions (2026-11-18): the level after Arche is **the second Earth Great Installation**, in which Physis
learns **Trace Reading** from **Kairos and the Wise** (ability 5 in the table; the Reckoning, Act 3, comes later); its
look is **realistic, in a neutral palette**. Everything below that is not one of those decisions is Proposed, the
name included.

### Premise

**Port Halcyon**, on Earth's coast, a few weeks after Meridian. In the war's first year a First One strike broke its
sea wall and the lower town drowned in one morning. It was the first blow to fall on Earth. The Just answered by
building their coastal command in the harbour mouth, **Bastion Halcyon**, and around it **the Undertow**, an engine
that forces Divinity through the sea so that the water stands back from the Bastion in walls: **the Held Sea**. The
Just swore their oath there, the **Halcyon Litany**, and the Bastion's Sea Gate still opens only to its three lines.

When the fleets fell silent at Meridian no order to stand down reached Halcyon. Its machines, the **Tide Guard**,
sealed the Bastion with its commander inside and went on holding the sea. One of the book's seventeen human
installations, the second she undoes.

**Kairos** and a small party of the Wise are camped above the town. They came for the record: the morning of the
strike is still written in the Divinity here, and Kairos means to read it before the Just and the First Ones ever
sit at one table. He teaches Physis **Trace Reading**, which is what the Wise have spent years learning to do and she
can do at once: to see what a place remembers.

It mirrors the Grove without repeating it: there the Just forced a living thing; here they forced the sea, and the
past is what she walks on. The Just's fear here is **Commodore Hollis Marr**'s: the sea came once without warning.
She is not argued out of it. She watches it lie down.

**Look (Author, 2026-11-18): realistic, neutral.** As realistic as the Grove and Arche (scanned surfaces, physically
based materials, real light) in a palette that belongs to neither: an overcast marine sky, a low pale sun, grey-white
limestone and render, slate roofs, weathered steel, grey-green sea, kelp and wrack on everything the tide reached.
Three lights tell three things apart: the Just's machines keep **amber**, forced Divinity (the Held Sea, the Undertow)
glows the Grove's sick **magenta**, and Trace Reading shows the past in pale **silver**. No post-process stylisation,
no 3D text.

### Layout (x north, y east, metres; the bay is about 1.1 km by 0.8 km, the town on a slope down to the sea)

| # | Space | Where | What happens |
| --- | --- | --- | --- |
| 1 | The Cliff Garden | South end, x −500, 40 m above the sea | She steps out of the current. Still Point; the current home stays here |
| 2 | The High Street | x −480 to −300 | The dry upper town, forty-year ruins and eleven-year ones. First Tide Guard patrols |
| 3 | The Signal House | x −290 | The safe place: **Kairos**, **Petra Lune** (the Conclave's archivist) and **Ledger**, the Wise's Robot scribe |
| 4 | The Clocktower | x −215 | Its clock stopped at the moment of the strike. Kairos shows her how a room remembers: **Trace Reading** |
| 5 | The Breach | x −150, wall to wall | Where the sea came through: a flooded cut 26 m wide. The **Harbour Bridge** stands only in the past. The barrier she remembers |
| 6 | The Market Steps | x −70 | Still Point where the town's ways part, down to the waterline |
| 7 | The Drowned Quarter | West, at sea level | Flooded streets around the old harbour. Past catwalks and rooftops; the **harbourmaster's echo** keeps the Litany's first line |
| 8 | The Cannery Yards | East | Sheds and cranes on the quays. A crane that moved only in the past; the **foreman's echo**, the second line |
| 9 | Lighthouse Point | North-east headland | The old lighthouse; its stair stands only in the past. The **keeper's echo** at the lamp, the third line |
| 10 | The Mole | x +250 to +380 | The breakwater out to the Bastion between the standing walls of the Held Sea. The **Sea Gate** opens to the three lines |
| 11 | Bastion Halcyon | North, x +420, in the sea | The Undertow's chamber and **the Keel**, the Tide Guard's command frame. Then Commodore Marr, in person |
| 12 | The Drowned Library | South-east | Optional: Petra's request; three shelves to read open a reading room (Katana Augmentation); a Harrow that can be avoided |

Critical path, about 40 to 50 minutes: Cliff Garden → High Street → Signal House (Kairos) → the Clocktower (Trace
Reading) → across the Breach → Market Steps → the three echoes in any order → the Mole and the Sea Gate → the Keel →
Commodore Marr → back to Kairos. With the side requests, the Library, the caches and the sealed vaults the level runs
about an hour.

Progress tokens: `,halcyon,` `,at_halcyon,` (saves load here), `,kairos_h,`, `,trace,`, `,ha_line1,` `,ha_line2,`
`,ha_line3,`, `,ha_gate,`, `,keel,`, `,marr,`, `,halcyon_done,`; side requests `,petra_h,` `,shelf1-3,` `,shelves,`
`,ledger,` `,logbook,`; guards, caches and seals `,ha_*`.

When the Keel falls the Undertow stops and the Held Sea lies down into the bay (everything tagged `HalcyonScar`
goes, `HalcyonBloom` shows): the walls of water and the magenta light go, the stained ground heals, and the town lays a
plank footbridge over the Breach (the shortcut home). Kairos
tells her what the record says, and that it will be needed when both peoples sit down together.

**The Metroid rule.** The Breach is the map's barrier: authored, crossed only by reading, never changed (the
footbridge after the Keel is a second way, not a change to it). Whoever falls in walks out up a slipway on its south
side, which leads only back south. Traces stand only while she reads; they never save. Two
**sealed vaults** (Reweave, Dissonance) are seen here: Reweave, from Arche, opens one already.

### Trace Reading

| | |
| --- | --- |
| Input | **T** on the keyboard; **hold D-pad down** on a pad (a tap is still Reload) |
| Cost | None; a reading lasts 10 s, 1 s between readings; reading again while one lasts renews it |
| Range | Every trace within 40 m of her when she reads, and any she comes within 40 m of while it lasts |
| Traversal | **Traces**: what stood here once (a bridge, a stair, a catwalk, a roof) shows in pale silver and bears her weight while she reads. They fade over the last 2 s |
| Echoes | People the place remembers stand where they stood and say one thing, once: the Litany's lines, the town's record |
| Combat | Not in the first build (Proposed: the next blow of the machine she locks on to shows a beat early) |
| Locks | It reports `,trace,` to `PhysisUsedAbility`, so the trace sockets on Arche and elsewhere answer it |
| Visual stage | Memory layers: the past shows over the present |

### People

| Person | Kind | Role |
| --- | --- | --- |
| Kairos | Human historian, the Wise | Quest giver; teaches Trace Reading; reads the record; closes the level |
| Petra Lune | Human archivist | Side request: three shelves in the Drowned Library (Pistol Augmentation) |
| Ledger | Robot scribe of the Wise | Side request: its field logbook, left on Lighthouse Point (Defense Augmentation) |
| Commodore Hollis Marr | Human, the Bastion's commander (MetaHuman) | A voice on the Sea Gate's speaker; in person once the Keel falls |

### Enemies: the Tide Guard (machines without will, so they are destroyed)

The Hedge's machines in the Just's coastal service (the Grove's meshes): Tide Wasp 5, Tide Lancet 9, Tide Burl 16,
Tide Palisade 20, Tide Thresher 26 (guards the echoes and the Mole), Tide Harrow 60 (the Library; avoidable), and the
boss, **the Keel**, 130: a command frame fed by the Undertow. Its shield answers to four pumps round the chamber:
break them with the sidearm, then fight it. Living animals: the Grove's three
species stand in for the coast's own until those are made.

### Rewards

Five augmentations: Health (`,aug_hp9,`, the Undertow's Heart), Katana (`,aug_katana7,`, the Library's reading room),
Pistol (`,aug_pistol6,`, Petra), Defense (`,aug_defense7,`, Ledger), Agility (`,aug_agility7,`, Kairos, once the
record is read). Tide caches (cyan rays), sealed vaults (violet). Halcyon has its own page on the pause-menu map.

### Implementation

`Tools/halcyon/README.md` is the build contract; the pipeline is Arche's, cloned (`Tools/halcyon_meshes`,
`Tools/build_physis_halcyon.py`, `Content/Python/physis_halcyon_*.py`, `Tools/blueprint_logic/halcyon_logic.py`). The
level is `/Game/Levels/L_Halcyon`, assets `/Game/Halcyon`. A Divinity current in the Center's temple opens once the
Sunderer has fallen (`,sunderer,`) and carries her to the Cliff Garden.

**Status (2026-11-18).** Built in one pass: the land and look, the town and its landmarks as generated meshes (no
downloads; the Grove's scans and Hedge machines are reused), Trace Reading and its Blueprints (`BP_Trace`, the director,
the current, BP_Physis), the whole level's placement (449 actors, 78 machines, 35 traces), the map page, travel both
ways, saves (world 6), the cook lists. Tested by script in Play-in-Editor: arrival; the Clocktower refusing without
Kairos and teaching Trace Reading with him; reading the Harbour Bridge and standing on it, and falling into the
Breach when the reading ends; standing on every past stair (the office, the crane, the lighthouse) and the roofs
they reach; the three echoes' lines; the Sea Gate opening; the Keel's room ending the level (the Held Sea gone, the
footbridge and Commodore Marr shown); save and load on Halcyon; the current home and back. Not done or not played by
hand: any fight, walking the routes with the controls, the slipway, the side requests' rewards, the Library; Trace
Reading's combat use; Halcyon's own sound effects (Trace Reading, the echoes and the current borrow Arche's and the
Grove's; its music, *the Litany*, and its three ambience beds are its own, `Tools/build_physis_halcyon_audio.py`); the
coast's own animals. Kairos's, Petra's, Ledger's and Marr's lines, the echoes and the town's story are new writing for
the author to review.

**People (2026-11-19).** Kairos and Petra are the Conclave's MetaHumans of them; Ledger is the Conclave's robot
figure. Commodore Marr, who wore Rhea Sato's MetaHuman until then, has her own (`Content/Python/physis_earth_people.py`,
Proposed look: about fifty-seven, deep brown skin, cropped greying hair, the Just's black officer's coat with brass
buttons and a white collar). Checked in L_Halcyon where she stands after the Keel.

## Level 7 — Arche: Hesper, the City of One Voice (2026-11-18)

Author decisions (2026-11-18): the level after Halcyon is **the second First Ones' Great Installation, on Arche**, in
which Physis learns **Dissonance** from **Aeon**, as preparation for the Reckoning (ability 6 in the table); its look
is **realistic, a warm dusk**. Everything below that is not one of those decisions is Proposed, the name included.

### Premise

**Hesper**, "the Evening", is the Vigil's seat on Arche: a city on a high plateau on the line between Arche's day and
its night, where the sun has stood on the horizon for as long as there have been First Ones to watch it. Its people
argued under that sun for ten thousand years. When the war came the Vigil decided they could not afford to: they
raised **the Concord**, an engine that sounds one tone through every thread of Divinity in the city, so that inside
Hesper every voice agrees with the Vigil's. Where the tone is strongest it stands in the air as **Unison**: walls and
veils of trembling amber light that nothing out of tune can pass. The Concord's AL, **the Choir**, keep it sounding;
nothing ever told them to stop.

The **Serene** of Hesper did not leave. They stopped speaking, because in the Concord's field every word they said came
out as the Vigil's. **Aeon** has come from Kathodos to them, and brings Physis, because of what comes next: the Reckoning
needs both peoples at one table, and the Vigil cannot sit at it while an engine speaks for them. Aeon teaches her
**Dissonance**: to hold a note of her own inside someone else's, so that for a while the field around her is free to
disagree.

It mirrors Kathodos without repeating it: there the Vigil unmade their own city so no stranger could walk it; here they
unmade their own disagreement so no doubt could weaken them. The Vigil's fear here is **Vaelun**'s, the Precentor who
keeps the Concord: a divided people loses. She is not argued out of it. She hears the city argue again, and stays.

**Look (Author, 2026-11-18): realistic, warm dusk.** As realistic as Arche and Halcyon (scanned surfaces, physically
based materials, real light), under a sun that sits on the horizon: long raking light, long violet shadows, an
amber-rose sky going to deep blue overhead, warm haze in the low ground. The First Ones' pale stone takes the light as
honey and rose; the rock is red-brown and violet. Four lights tell four things apart: **Unison** (the Concord's tone)
glows **amber gold**, the Serene's lamps keep **ice blue**, the Vigil's works their cold **violet**, and **Dissonance**
shows as a clear **blue-white** ring. The Choir keep the AL's red. No post-process stylisation, no 3D text.

### Layout (x north, y east, metres; the plateau is about 1.1 km by 0.8 km, ringed by cliffs; the ground climbs north to the Concord)

| # | Space | Where | What happens |
| --- | --- | --- | --- |
| 1 | The Sunward Stair | South end, x −500 | She steps out of the current. Still Point; the current home stays here |
| 2 | The Long Terrace | x −480 to −300 | The road into the city along the cliff edge, the sun on the left. First Choir patrols |
| 3 | The House of Listeners | x −290 | The safe place: **Aeon**, and the Serene of Hesper: **Liss**, **Tavor**, **Anwe** |
| 4 | The Tuning Court | x −215 | A small Unison veil round a fallen bell. Aeon shows her how to hold a note of her own: **Dissonance** |
| 5 | **The Choir Wall** | x −150, cliff to cliff | A standing wall of Unison 6 m thick across the whole plateau. The barrier she remembers: crossed only inside Dissonance |
| 6 | The Bell Market | x −70 | Still Point where the ways part |
| 7 | The Reed Terraces | West | Stepped pools and reed beds; Unison veils across the causeways. **The Low Bell**, silenced in a shell of Unison |
| 8 | The Amber Galleries | East | Long colonnades; Unison closes the cross-walks into a maze. **The Middle Bell** |
| 9 | The Watch Spire | North-east | A tower on a rock terrace, its ramp barred by Unison gates one after another. **The High Bell** at its foot |
| 10 | The Nave | x +250 to +380 | The processional way to the Concord under arches, Unison across it again and again; break each with a fresh note |
| 11 | The Concord | North, x +420 | **The Choir Gate** opens when the three bells ring. Inside: the Concord's horn, its four tuning pylons, and **the Cantor**. Then Vaelun, in person |
| 12 | The Hall of Withheld Votes | South-east | Optional: Liss's request; three speaking stones sealed in Unison open the hall (Katana Augmentation); a Siegeframe that can be avoided |

Critical path, about 40 to 50 minutes: Sunward Stair → Long Terrace → House of Listeners (Aeon) → the Tuning Court
(Dissonance) → through the Choir Wall → Bell Market → the three bells in any order → the Nave → the Choir Gate → the
Cantor → Vaelun → back to Aeon. With the side requests, the Hall, the caches and the sealed vaults the level runs about
an hour.

Progress tokens: `,hesper,` `,at_hesper,` (saves load here), `,aeon_h,`, `,dissonance,`, `,hs_bell1,` `,hs_bell2,`
`,hs_bell3,`, `,hs_gate,`, `,cantor,`, `,vaelun,`, `,hesper_done,`; side requests `,liss,` `,hs_stone1-3,` `,hs_stones,`
`,tavor,` `,tuningfork,` `,anwe,` `,reedflute,`; guards, caches and seals `,hs_*`.

When the Cantor falls the Concord stops. Every Unison in the city (tag `HesperScar`) goes, the amber in the air goes
with it, and the city's own bells, rung by nobody, ring once each (`HesperBloom`). Vaelun hears the Serene speak for the
first time in eleven years. Aeon tells Physis that both peoples can now be asked to the table, and that asking is the
hard part.

**The Metroid rule.** The Choir Wall is the map's barrier: authored, crossed only inside Dissonance, never changed until
the Concord stops, and the Concord stopping is the level's end, so it never strands a player. Unison walls only open and
close around her; nothing moves. Two **sealed vaults** (Trace Reading, Reweave) are seen here, and both open already.
The Center's and the Conclave's Dissonance vaults (`physis_center_vaults.py`, the Conclave's Vault of Discord) now open
too.

### Dissonance

| | |
| --- | --- |
| Input | **C** on the keyboard; **hold D-pad up** on a pad (a tap still switches weapons) |
| Cost | None; a note lasts 8 s; another can be held 2 s after it ends |
| Reach | A ring 9 m round her, which moves with her |
| Traversal | **Unison** (walls, veils, gates, steps) inside the ring thins and lets her through. It never closes on her: a panel she stands in waits until she is out |
| Locks | **Shells** of Unison round a thing (the bells, the speaking stones, the Cantor's pylons) break for good once she holds the ring on them for 3 s |
| Combat | The Choir's bolts falter inside the ring and go out (`BP_EnemyBolt`) |
| Sockets | It reports `,dissonance,` to `PhysisUsedAbility`, so every Dissonance vault on the other worlds answers it |
| Visual stage | Lighting depth: the ring shows the dusk without the Concord's amber in it |

### People

| Person | Kind | Role |
| --- | --- | --- |
| Aeon | First One, eldest of the Serene | Quest giver; teaches Dissonance; closes the level |
| Liss | Serene, a singer who stopped singing | Side request: three speaking stones in the Hall of Withheld Votes (Agility Augmentation) |
| Tavor | Serene, the bell-wright | Side request: his tuning fork, left at the foot of the Watch Spire (Defense Augmentation) |
| Anwe | Serene, the youngest | Side request: a reed flute from the Reed Terraces' far pool (Pistol Augmentation) |
| Vaelun | First One, Precentor of the Vigil | A voice in the Concord's speaking stone at the Choir Gate; in person once the Cantor falls |

The book names none of these but Aeon; their lines are new writing for the author to review. Vaelun keeps one engine
and leads no one: the Vigil's leader is still unnamed (decision 6 below).

### Enemies: the Choir (AL: tools, so they are destroyed), and Hesper's animals

The Conclave's AL, in the Concord's service (the Ward's meshes): Choir Mite 5, Choir Lancer 9, Choir Bulwark 16,
Choir Hunter 20, Choir Reaver 26 (guards the bells and the Nave), Choir Siegeframe 60 (the Hall; avoidable), and the
boss, **the Cantor**, 140: a floating ring of pipes round a masked core, the Concord's own voice. Its shield answers to
four tuning pylons round the court, each sealed in a Unison shell: break a shell with Dissonance, then stop the pylon
with the sidearm. Arche's own animals, maddened by the tone, hold the open ground between (the air-swimmers of
Kathodos, as there: they scatter and gather again).

### Rewards

Five augmentations: Health (`,aug_hp10,`, the Concord's Heart), Katana (`,aug_katana8,`, the Hall of Withheld Votes),
Pistol (`,aug_pistol7,`, Anwe), Defense (`,aug_defense8,`, Tavor), Agility (`,aug_agility8,`, Liss). Dusk caches
(gold rays), sealed vaults (violet). Hesper has its own page on the pause-menu map.

### Implementation

`Tools/hesper/README.md` is the build contract; the pipeline is Halcyon's and Arche's, cloned (`Tools/hesper_meshes`,
`Tools/build_physis_hesper.py`, `Content/Python/physis_hesper_*.py`, `Tools/blueprint_logic/hesper_logic.py`). Hesper is
on Arche, so it reuses Kathodos's architecture, its First Ones, its animals and the Ward's AL, regraded for the dusk.
The level is `/Game/Levels/L_Hesper`, assets `/Game/Hesper`. A Divinity current in the Center's sanctum, north-east of
the Heartbloom, opens once the Keel has fallen (`,keel,`) and carries her to the Sunward Stair.

**Status (2026-11-19).** Built in one pass: the plateau, its western drop and the dusk look; Hesper's own meshes
(Unison panel and shell, the bells, the Concord, its pylons, the Watch Spire, the parapet, the Cantor) as generated
meshes, with Kathodos's architecture, First Ones, animals and the Ward's AL regraded warm; Dissonance and its
Blueprints (`BP_Unison`, `BP_Dissonance`, the director, the current, BP_Physis, `BP_EnemyBolt`'s faltering bolts);
the whole level's placement (646 actors, 78 enemies, 92 pieces of Unison of which 64 are the Choir Wall); 88 voiced
pages and scans (Kokoro); the map page; travel both ways; saves (world 7); the cook lists; the music, *One Voice*
(A Aeolian: a chant in unison that breaks into harmony), and three ambience beds (wind, the Concord, the reeds), all
imported and placed (`Tools/build_physis_hesper_audio.py`). Tested in Play-in-Editor by script
(`Saved/Hesper/run/pie_hesper.py`, at low quality): arrival (tokens, quest, Hesper's own music and beds); the Tuning
Court refusing without Aeon and teaching Dissonance with him; the Fallen Bell Shell thinning under the note and
breaking after 2 s; the Choir Wall stopping her without the note, letting her through with it and closing behind her
once she is clear; the three bell shells breaking after 3 s each and the Choir Gate sinking (she walks through);
a drone's bolt hitting her without the note and bursting into sparks inside it; a pylon shell breaking, and an intact
one stopping a shot at its pylon; the Cantor's ending (`,cantor,` given: all 27 scarred pieces hidden, the bloom
shown, every piece of Unison gone, the wall open); save and load on Hesper (world 7, the exact spot); the current to
the Center and back. The Choir Gate opens the moment the third bell rings, wherever she is; the director keeps the
objective "Follow the Nave north to the Choir Gate" until she is 25 m short of the gate (or past it), then gives
"Silence the Cantor", never after the Cantor (tested).
Not done or not played by hand: any fight (the Cantor's shield and its pylons, the Choir), walking the routes with the
controls and the pad's D-pad hold, the Hall of Withheld Votes, the side requests' rewards, the music and beds by ear,
Play-in-Editor at Epic quality (8 GB is tight with the desktop's 3 GB). Aeon's, the Serene's and Vaelun's lines, the
bells and the city's story are new writing for the author to review.

## Level 8 — Earth: Morrow, the Valley Before Morning (2026-11-19)

Author decisions (2026-11-19): the level after Hesper is **the third Earth Great Installation**, and the **first
hardened** one: Physis cannot undo it from outside and must enter the mind of someone inside (an Inner Installation).
She learns **Sit With** there (ability 8 in the table). Its look is **realistic, a cold dawn**. Everything below that
is not one of those decisions is Proposed, the name included.

### Premise

**Morrow** is a reservoir town of the Just high in Earth's northern mountains. Its dam powered the Meridian Front, and
the Front's mountain depot, **the Hold**, is built into the dam. Its Warden is **Maren Holt**. Her son **Tam**, a
pilot, fell at Meridian in the last week of the fighting, days before Physis came. The news reached Morrow at dawn,
over the telegraph, and was carried up to the dam in a letter. Maren read it on the crest as the sun came over the
eastern ridge. Then she turned the Hold's cold engine, **the Lull**, on her own valley.

The Lull forces Divinity through every drop of water in Morrow so that nothing goes on from that hour. The reservoir
froze. Frost stands on everything, mist lies in the low ground, and for forty days the sun has stood just under the
eastern ridge. Where it is strongest the forcing stands up as **Rime**: walls and crusts of hoarfrost with the forced
magenta deep in them. Whoever in the town was grieving that morning was caught in it: **the Stilled**, frosted where
they stood when they heard, alive, not moving. The Hold's machines, **the Frost Guard**, keep the dam. The Hold is
**hardened**: the Lull is bound to Maren's own mind, and Settle cannot touch it. It is the first time Physis's power
is refused.

**Edda Holt**, Maren's mother and Tam's grandmother, is not Stilled. She lost her husband twenty years ago and learned
then what she teaches Physis: **Sit With**. Not mending, not settling. Staying, while someone cannot bear it, until
they can.

It mirrors the Grove and Halcyon without repeating them: there the Just forced a living thing and the sea; here a
grieving mother has forced time, and kept one morning from ending. The Just's fear here is Maren's: if the morning
ends, he is gone. She is not argued out of it, and Physis does not fight her. She is sat with, and the sun comes up.

**Look (Author, 2026-11-19): realistic, cold dawn.** As realistic as Halcyon and Hesper (scanned surfaces, physically
based materials, real light) in the blue hour before sunrise: the sun 2 degrees under the eastern ridge, the sky
pale gold low in the east going to steel blue overhead, the western peaks' snow catching the first pink, the valley
in cold blue shadow, mist in the low ground and on the ice, frost on every roof and branch, long soft shadows. Three
lights tell three things apart: the Just's machines keep **amber**; the Rime (forced Divinity) shows **magenta** deep
in white frost; **Sit With** is a small warm **ember rose**, the one warm light in the valley. When the Lull stops
the sun clears the ridge: the level's one change of light, from cold dawn to morning. No post-process stylisation,
no 3D text.

### Layout (x north, y east, metres; the valley is about 1.1 km by 0.8 km, walled by peaks; it climbs north to the dam)

| # | Space | Where | What happens |
| --- | --- | --- | --- |
| 1 | The Pass Chapel | South end, x −500 | She steps out of the current. Still Point; the current home stays here |
| 2 | The Orchard Road | x −480 to −300 | Frozen orchards in the mist. First Frost Guard |
| 3 | The Mill House | x −290 | The safe place: **Edda Holt**, **Corin Vell** (the dam engineer who walked out of the Hold the first night), and **Pilgrim**, the Hold's courier Mechanoid, which carried the letter |
| 4 | Edda's Bench | By the Mill House | On the frozen millpond's bank. The miller is Stilled at his wheel. Edda shows Physis how to sit: **Sit With** |
| 5 | **The Gorge** | x −150, wall to wall | The river's gorge, 26 m across, frozen. The **Ferry Bridge** is buried in a mound of Rime, its keeper Stilled at its head. The barrier she remembers: opened only by sitting with him |
| 6 | Chapel Square | x −70 | Still Point where the ways part |
| 7 | The Schoolhouse | West | Rime walls ring the school yard. Tam's teacher, **Ada Lowe**, Stilled at its door |
| 8 | The Glider Field | East, on a bench above the town | Where Tam learned to fly. His friend **Jory Pike**, Stilled by the hangar with the glider they built |
| 9 | The Telegraph House | North-east rock | Up a frosted path. **Ines Okon**, the operator who took the message down, Stilled at her key |
| 10 | The Dam Stair | x +250 to +380 | The long stair up the dam's face beside the frozen spillway; the Frost Guard's heaviest |
| 11 | The Crest and the Hold | North, x +420, on the dam | Maren, Stilled herself on the crest with the letter in her hand. Settle is refused. With the three memories, Physis sits with her and goes in |
| 12 | **Inner Installation: The Morning** | In Maren's mind | Rooms made of what she lost: the Kitchen (the letter on the table), the Long Hall (his door at every age), the Field (the glider in the mist), and the Crest as she remembers it, where **the Unrisen** waits |
| 13 | The Ice House | South-east | Optional: Corin's request; his night shift, three Stilled in the Hold's old ice house (Katana Augmentation); a Frost Harrow that can be avoided |

Critical path, about 45 to 55 minutes: Pass Chapel → Orchard Road → Mill House (Edda) → Edda's Bench (Sit With) → the
Ferry Bridge → Chapel Square → the three Stilled in any order → the Dam Stair → the Crest → the Morning (four rooms
and the Unrisen) → Maren → back to Edda. With the side requests, the Ice House, the caches and the sealed vaults the
level runs about an hour.

Progress tokens: `,morrow,` `,at_morrow,` (saves load here), `,edda,`, `,sitwith,`, `,mw_bridge,`, `,mw_mem1,`
`,mw_mem2,` `,mw_mem3,` (the three memories), `,mw_inner,` (inside), `,mw_room1-3,`, `,mw_still,` (the Unrisen stops),
`,unrisen,`, `,maren,`, `,morrow_done,`; side requests `,corin,` `,mw_crew1-3,` `,mw_crew,` `,pilgrim,` `,satchel,`;
guards, caches and seals `,mw_*`.

The three Stilled each wake with something of Tam that Maren has stopped letting herself know (what he was like at
eight, what he said before his first flight alone, the last line he sent): the three memories. Without them Maren
does not let her in.

When the Unrisen is sat with, the Lull stops. Every Rime in the valley (tag `MorrowScar`) goes, the Stilled all wake,
the reservoir's ice breaks, and **the sun clears the eastern ridge** (`MorrowBloom`, and the director raises the sun
over 40 s). Maren comes down from the crest with Edda. Edda tells Physis that the morning was always going to end, and
that it was never her job to end it, only not to leave.

**The Metroid rule.** The Gorge is the map's barrier: authored, opened once by Sit With, never changed after. Whoever
falls in walks out up a ramp on its south side, which leads only back south. Rime walls only thaw while she sits by
the person they hold; nothing moves. The Inner Installation is entered only from the crest and left only at its end
or by its Still Point's way back to the crest; dying inside respawns at its Still Point. Two **sealed vaults** (Trace
Reading, Dissonance) are seen here, and both open already.

### Sit With

| | |
| --- | --- |
| Input | **H** on the keyboard; **hold D-pad left** on a pad (a tap is still Mend) |
| Cost | None. She kneels where she is; she stays until she presses again, moves, or is struck |
| Reach | Whoever is within 3 m of her |
| Traversal and locks | **The Stilled**: sitting with one for 4 s wakes them. They say what they were holding, give their token, and whatever their Rime held opens (the bridge, a yard wall, a door) |
| Inner Installations | Sitting with someone at a hardened place, once she understands enough of them (here the three memories), takes her into their mind |
| Combat | Grief bosses: fight until it stops attacking, then sit with it. The spoken final stage plays while she sits and pauses if she stands; it cannot fail. While she sits her Composure comes back slowly (Proposed) |
| Sockets | It reports `,sitwith,` to `PhysisUsedAbility`, so later Inner Installations and vaults answer it |
| Visual stage | Interior worlds: the mind-spaces, and the one warm light in a cold place |

### People

| Person | Kind | Role |
| --- | --- | --- |
| Edda Holt | Human, Maren's mother (MetaHuman) | Quest giver; teaches Sit With; closes the level |
| Corin Vell | Human, the dam's engineer, the Just (MetaHuman) | Side request: his three Stilled crew in the Ice House (Katana, then Pistol Augmentation) |
| Pilgrim | Mechanoid courier of the Just | Side request: its satchel, left at the Telegraph House (Defense Augmentation) |
| Warden Maren Holt | Human, the Hold's commander, the Just (MetaHuman) | Stilled on the crest; met in her mind; in person once the Unrisen is sat with |
| The Stilled | Humans of Morrow | The miller, the bridge keeper, Ada Lowe, Jory Pike, Ines Okon, Corin's crew |

The book names none of these. Their lines, Tam, and the town's story are new writing for the author to review.

### Enemies: the Frost Guard (machines without will, so they are destroyed), and the Rime-shapes

The Hedge's machines in the Hold's service (the Grove's meshes, frosted): Frost Wasp 5, Frost Lancet 9, Frost Burl
16, Frost Palisade 20, Frost Thresher 26 (guards the Stilled and the Dam Stair), Frost Harrow 60 (the Ice House;
avoidable). In the Morning, **Rime-shapes**: Maren's grief, frost given form. They are not machines and not destroyed:
struck enough, one scatters and gathers again (the rule for the living). The boss, **the Unrisen**, 150: a kneeling
figure of Rime as tall as the house, holding the morning down in its arms. Fight it until it stops attacking; then
sit with it.

### Rewards

Five augmentations: Health (`,aug_hp11,`, the Lull's Heart), Katana (`,aug_katana9,`, the Ice House), Pistol
(`,aug_pistol8,`, Corin), Defense (`,aug_defense9,`, Pilgrim), Agility (`,aug_agility9,`, Edda, afterwards). Frost
caches (cyan rays), sealed vaults (violet). Morrow has its own page on the pause-menu map.

### Implementation

`Tools/morrow/README.md` is the build contract; the pipeline is Halcyon's, cloned (`Tools/morrow_meshes`,
`Tools/build_physis_morrow.py`, `Content/Python/physis_morrow_*.py`, `Tools/blueprint_logic/morrow_logic.py`). Morrow is
on Earth, so it reuses the Grove's ground, scans and Hedge machines and Halcyon's houses, frosted. The level is
`/Game/Levels/L_Morrow`, assets `/Game/Morrow`; the Morning is built in the same level, an island in the mist 1.6 km
north of the dam. A Divinity current in the Center's sanctum, south-east of the Heartbloom, opens once the Cantor has
fallen (`,cantor,`) and carries her to the Pass Chapel.

**Status (2026-11-19).** Built in one pass: the valley, the dam and its reservoir, the cold-dawn look (frost on every
upward face through Morrow's copies of the Grove's masters, `M_MW_*`; snow on the peaks; the sun under the eastern
ridge), Morrow's own meshes (52: the Rime, chapel, mill and wheel, Edda's bench, the Ferry Bridge, school, hangar and
glider, telegraph, the dam's crest and stair, the Hold, the ice house, the eight Stilled, the Rime-shapes, the Unrisen
fighting and kneeling, and the Morning's kitchen, hall, islands and walks) with Halcyon's houses and the Grove's trees,
scans and Hedge machines frosted; Sit With and its Blueprints (`BP_Stilled`, `BP_SitWith`, the director, the current,
BP_Physis); the whole level's placement (502 actors, 79 enemies, 13 Stilled and memories); 89 voiced lines (Kokoro:
Divinity, the people, the Stilled's words and Maren's stage lines); the map page; travel both ways; saves (world 8);
the cook lists; the music, *The Valley Before Morning* (D minor, the lullaby, turning to D major in its morning
section), three beds (the valley, the Lull, the Morning) and three effects (Sit With, the waking, the way in). Tested
in Play-in-Editor by script (`Saved/Morrow/run/pie_morrow.py`, at low quality): arrival (tokens, objective, Morrow's own
music); Edda's bench refusing without Edda and teaching Sit With with her; kneeling (the get-up clip held at its
half-kneel, weapons hidden), the glow, standing by pressing again and by moving; the miller, the bridge keeper (the
Ferry Bridge blocked by its Rime, then crossed), Ada, Jory and Ines waking after 4 s each and the three memories
giving `,mw_mems,`; Maren taking her into the Morning; the chair, his door and the glider opening the Rime doors and
the way; falling out of the Morning and coming back in the kitchen; the Unrisen hit to nothing and the encounter
giving `,mw_still,` and the kneeling Unrisen; the spoken stage (13 lines at 6.5 s, paused while she stands, resumed)
ending in `,unrisen,`, her return to the crest, the Rime gone, the reservoir thawed, Maren in person; the sunrise
(pitch -5 to -26 and 5.5 to 15 lux over 40 s); save and load on Morrow (world 8, the exact spot, the sun already up);
the current to the Center and back.
Not done or not played by hand: any fight (the Frost Guard, the Rime-shapes, the Unrisen with the sword and gun), the
routes walked with the controls and the pad's D-pad hold (Mend fires as the hold begins, as Reload and the weapon
switch do for the other holds), the Ice House and Corin's crew, Pilgrim's satchel, the side requests' rewards, the
music and beds by ear, Play-in-Editor at Epic quality. The Unrisen bursts as a machine does when it stops (the living
"scatter and gather again" is still only words); the kneeling Unrisen then takes its place. The story, Tam, the Stilled's and Maren's lines are new
writing for the author to review.

**People (2026-11-19).** Edda, Corin and Maren, who wore the Conclave's MetaHumans until then (Wen, Marek, Ama), are
their own (`Content/Python/physis_earth_people.py`; looks Proposed): Edda, seventy-four, white hair braided up, a deep
red knitted shawl over a cream blouse and a slate skirt; Corin, about forty-four, a short dark beard and an ochre
oilskin; Maren, in her forties, her mother's face drawn leaner, in the Just's olive field greatcoat and an officer's
peaked cap as her Stilled figure wears them (`SM_OP_Stilled7`). Play-tested: Edda and Corin show in the valley and
Edda's conversation opens and closes; Maren checked on the crest in the editor. Pilgrim is the Conclave's robot figure.

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
