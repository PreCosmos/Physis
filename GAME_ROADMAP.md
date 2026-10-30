# Physis — game design and development roadmap

Draft 2 · 30 October 2026 · Opening sequence and first ability revised by the author

## The game we are making

A single-player exploration adventure based on **Physis**, the story in *Fantasia*.
The player is Physis: a person born from the living substance of the universe,
learning how to heal its wounds and understand the beings who caused them.

The proposed blend is Zelda's spatial puzzles, memorable encounters, and ability
discovery with Metroid's interconnected routes, ability gates, and rewarding
returns to earlier areas. The game's distinct identity comes from three linked
systems: Physis perceives more as she develops, people respond to spoken
conversation, and worlds remember her actions.

The two main AI features are **English voice conversations with NPCs** and
**adaptive environmental puzzles within defined planetary terrains**.

Everything described as proposed below is a design direction for review, not an
implemented feature or a change to book canon.

## Confirmed requirements and current starting point

| Requirement | Planned result |
| --- | --- |
| Three main destinations | Earth, the First Ones' Planet, and the Center of the Universe |
| Opening tutorial | A human battle station fighting First Ones' ships and warriors; teach basic mechanics with no abilities |
| Birth and first ability | Travel to the Center after the station; Physis is born and learns to inspect the environment with a Scan Visor |
| Center art direction | Realistic cel shading |
| Different shading per destination | Each has its own material, lighting, color, and visual treatment |
| Graphics improve with abilities and levels | A persistent progression in visual richness and perception |
| Spoken AI NPC dialogue | Microphone input and spoken English responses; no typing required |
| Living terrains | Defined terrain identities with puzzles that react to player actions |
| MetaHuman characters | Use MetaHuman where appropriate for human characters, with animation support |

The current project is an Unreal Engine 5.8 first-person template. Its editor MCP
connection, editor tools, MetaHuman Generator, and Control Rig/Sequencer toolsets
have been connected. The game systems and a playable Physis level have not been
built. MetaHuman tool discovery is verified; finished character assembly and
speech-driven facial animation still need a practical test.

The editor currently needs a temporary NVIDIA rendering workaround. Stable
rendering is an early prerequisite for judging the intended art direction.
See [the connection notes](Tools/UNREAL_CONNECTION.md).

## Story adaptation

Source: *Fantasia*, “Physis,” printed pages 87–120, supplied by the author at
`/run/media/system/Games/Backup/General/Fantasia.pdf`. The document is story
reference; the author's requests define the game requirements.

| Book foundation | Game adaptation proposal |
| --- | --- |
| Divinity is the living substance permeating the universe | It connects perception, abilities, dialogue context, and world reactions |
| Physis is born at the absolute center and learns herself as she travels | Open with the human battle-station tutorial, then move to her birth at the Center and unlock the Scan Visor |
| Physis has technically absolute control of Divinity | Progress measures understanding, precision, and sustained attention; the game needs a consistent explanation for what she cannot yet do safely |
| Human factions: the Wise and the Just; First One factions: the Serene and the Vigil | Encounters reveal different perspectives and fears rather than a simple good/evil division |
| Kairos, Cassian, and Aeon are central figures | Preserve their roles and motivations; use them as major narrative anchors |
| Physis releases Divinity from weaponized configurations | Build major encounters around disarming, stabilizing, and healing |
| Integration, the holdouts, the Cosmoforms, and creation conclude the story | Preserve these as the late-game arc and epilogue, including Physis's uncertainty over her intervention in the holdouts |

The elder race and its homeworld are named **First Ones** and **First Ones' Planet**
throughout the game plan. Earth and the elder homeworld concentrate a story that also takes place
at stations, battlefronts, and installations across several systems. Retain those
places through vistas, memories, short set pieces, or travel sequences where
needed. Moving a scene to a planet should be a deliberate adaptation choice.

The Center is a cosmic destination in the book, rather than an ordinary planet.
Treating it as one of the three playable worlds preserves the requested structure
without requiring it to look or behave like Earth.

## Opening: the war, then the birth

The author has established this order: **human battle station → Center of the
Universe → Physis's birth → Scan Visor → wider exploration**. The battle station
is a prologue location in addition to the three main worlds.

### Prologue — human battle station

Begin inside a human battle station during an engagement with First Ones' ships
and warriors. Establish the war through the player's immediate surroundings:
crew activity, alarms, damage, views of the opposing ships, and encounters that
make the warriors a tangible presence. The exact battle choreography is still
to be designed.

This section teaches the basic controls through playable situations. Proposed
lessons are looking and moving, navigating obstacles, interacting with doors and
station equipment, following spatial and audio cues, and basic survival under
pressure. Teach jumping, crouching, evasion, or conventional combat only if those
actions belong in the agreed movement and combat model. Introduce spoken NPC
interaction in a brief crew encounter once the voice system is ready.

**No abilities are available in this section.** Do not introduce scanning,
resonance, healing, or Divinity manipulation before the birth. Use ordinary
observation and physical interactions for its teaching challenges. Stage the
tutorial consistently so players can learn before adaptive puzzles are added.

The opening should bring us into Physis's emerging mind without placing her
physically on the station before she is born. A proposed framing is that the
station sequence is the war impression reaching the consciousness forming in
Divinity. The exact playable viewpoint—human participant or an emerging
subjective experience—remains to be decided. This framing is a proposal, not an
additional claim about the book.

### Chapter one — Center of the Universe

After the station sequence, take the player to the Center and let Physis be born.
Contrast the pressure and confusion of war with the first experience of her own
awareness. The Center must already be visually compelling before any upgrade.

Use **realistic cel shading**: believable scale, proportions, material detail,
and coherent lighting expressed through deliberate bands of light and shadow.
Proposed supporting elements are cosmic depth, Divinity currents, and restrained
volumetric effects. Avoid letting bright effects obscure surfaces or scan clues.
This visual direction is established; exact palettes, outlines, and shading
thresholds still need an art test.

Physis receives her first ability here: **Scan Visor**, a working name for the
ability to inspect and understand her environment. The first lesson should move
from noticing something unfamiliar to scanning it, interpreting what it reveals,
and using that knowledge to choose a route or complete a simple interaction.

## First ability — Scan Visor

The Scan Visor expresses Physis learning to perceive Divinity. Its presentation
can resemble a visor without requiring a physical helmet; whether it is an
interface within her perception or a visible object remains an art decision.

Proposed initial behavior:

- Toggle scan mode and aim at a visible point of interest.
- Show which object is being examined and provide clear scan progress and completion feedback.
- Reveal a short, authored observation about the object's identity, condition,
  disturbance, or relationship to its surroundings.
- Make the result usable through visual feedback and spoken English narration;
  reading text is not required. Optional text can remain available.
- Remember completed discoveries so returning to the same object does not force
  the player to repeat the introductory explanation.

The first version reveals information. It does not repair, move, or reshape
objects; those belong to later abilities. A scan can supply the understanding
needed to operate an ordinary mechanism or recognize a route. Essential facts
come from authored object data, with any AI explanation constrained to those
facts. Players should not need to scan every decorative object to progress.

Proposed first teaching sequence: inspect a nearby formation, identify a
disturbance in a Divinity current, then recognize a safe route using that
information. Keep its solution fixed while the player learns the ability.
Exact objects and route layout will be designed in the Center blockout.

Acceptance criteria: scan mode is unavailable on the station; the unlock occurs
at the birth sequence; a new player can identify, scan, and act on a clue;
targets and results remain legible in the Center's cel shading; and scan unlocks
and discoveries persist through save/load. Later upgrades can expand what Physis
perceives without changing this first lesson.

## Core play loop

1. Explore a region and notice an inaccessible route or disturbance.
2. Read the environment and speak with its inhabitants.
3. Learn an ability or a new application of an existing one.
4. Resolve a traversal puzzle, hazardous installation, or confrontation.
5. See the planet react and Physis's perception deepen.
6. Return through a changed route and reach a previously inaccessible place.

Proposed camera: **third person**, so the player can see Physis's transformation
and read traversal clearly. Test this against the existing first-person setup
before committing. Target platforms, input devices, and minimum hardware remain
to be chosen; Linux editor use does not decide the shipping platform.

Proposed action model: movement, evasion, defensive resonance, and precision
disabling of hostile systems. A major encounter tests an ability and an
understanding of the opponent. Whether conventional weapons and lethal combat
belong in the game is a creative decision before the action prototype.

## The three worlds

The Center's realistic cel shading is established by the author. The terrain
vocabulary and the other worlds' shading directions remain proposals. The author's
existing terrain definitions should refine them before full environment production.

| World | Proposed terrain vocabulary | Shading identity | Puzzle language and narrative role |
| --- | --- | --- | --- |
| Earth | Reclaimed cities, forests, flooded research sites, damaged human infrastructure | Warm, painterly surfaces; soft shading; increasingly rich organic detail | Water, roots, energy distribution, and the consequences of the human war |
| First Ones' Planet | Ancient terraces, crystalline structures, suspended architecture, immense ruins | Cool palettes, sharp value bands, luminous edges, controlled reflections | Resonance, light, alignment, shifting architecture, and the legacy of control |
| Center of the Universe | Divinity currents, condensed matter islands, memory spaces, cosmic structures | Realistic cel shading: believable scale and materials, deliberate light/shadow bands, cosmic depth, and restrained volumetric effects | Physis's birth and first Scan Visor lesson; later return to combine abilities, connect memories, stabilize universal wounds, and prepare integration |

Opening route: human battle station (no abilities) → Center birth sequence and
Scan Visor unlock. Proposed continuation: Earth → First Ones' Planet → returns to
both worlds → expanded Center finale. Establish recognizable landmarks and
shortcuts so backtracking feels like discovery. Start with bounded, connected
regions; full planetary surfaces and spaceflight are outside the first scope.

## Progression and improving graphics

Make the visual improvement a visible expression of Physis learning to perceive
Divinity. Tie major visual stages to ability milestones, and smaller improvements
to earned levels. Keep hardware quality settings separate from story progression.

| Proposed stage | Ability example | Gameplay expansion | Visual growth |
| --- | --- | --- | --- |
| Prologue | No abilities | Learn basic movement, observation, and physical interaction on the battle station | Establish the human war setting; station art direction remains to be defined |
| Awakening / first perception | Scan Visor, unlocked at Physis's birth | Inspect environmental targets and use revealed information | Realistically cel-shaded Center; first visible layer of Divinity perception |
| Deeper perception | Later Scan Visor upgrades | Reveal additional traces, connections, and concealed paths | Richer color, material layers, and visible Divinity patterns |
| Connection | Resonance Link | Connect compatible nodes and redirect flows | Environmental motion, responsive surfaces, and deeper lighting detail |
| Transformation | Reweave | Restore or change designated structures | More complete geometry, surface detail, and ecological responses |
| Integration | Sustained combined abilities | Resolve complex wounds across connected spaces | Full planetary visual expression and cosmic layers |

The Scan Visor and its place as the first ability are established by the author;
its detailed controls and later ability names remain proposals. Teach one ability,
then combine it with earlier ones. Permanent traversal unlocks should come from
meaningful discoveries rather than repetitive grinding. Exploration, healing,
and understanding can contribute to levels; enemies need not be the main source.

Visual progression has two independent inputs: **Physis's mastery** and **local
world condition**. Revisiting Earth with greater mastery should reveal more even
in an unhealed area. Healing an area should also change its appearance. Essential
puzzle clues must remain readable at every visual stage and quality setting.
Budget the final, richest stage first so leveling up does not progressively ruin
performance. Prefer controlled reveals and authored variants over regenerating
all assets at every level.

## Spoken NPC conversations

The player approaches an NPC, starts a conversation, speaks English through a
microphone, and hears a spoken English reply. Proposed first interaction is
push-to-talk, with clear listening/thinking/speaking indicators and interruption
support. Natural turn detection can follow after the basic experience works.

The conversation pipeline needs audio capture, speech understanding, an NPC
dialogue model, voice output, and synchronized character animation. Evaluate
providers with the same sample scenes before selecting one. Keep service
credentials outside the shipped client and measure response time and cost per
conversation minute.

Each NPC needs an authored identity, voice, faction, knowledge limits, current
goals, and a small persistent memory of relevant interactions. Supply only the
story and world facts available at that moment. The game must validate any
proposed quest or world action before applying it. Spoken claims alone cannot
grant powers, invent objectives, or rewrite canon.

Critical exchanges need dependable authored beats inside flexible conversation.
Different phrasings should work; progression must not require guessing a hidden
sentence. NPCs can admit uncertainty, refuse, or disagree according to their
character. Understanding a viewpoint should matter more than finding flattering
words. Preserve Cassian's grief, Aeon's perspective, and Kairos's historical role.

No typed dialogue is required. Optional subtitles and replayable spoken hints
can provide accessibility without changing that requirement. Define the desired
non-microphone accessibility path during preproduction. On service failure, use
spoken recovery lines and preserve state; existing physical escape routes must
remain usable. Decide whether full offline dialogue is a release requirement
after measuring the online prototype.

MetaHumans suit human figures such as Kairos and potentially Physis's chosen
humanlike form. Robots, Mechas, Lightforms, and the First Ones need their own
designs. Test character assembly, hair/clothing, facial expression, lip sync, and
runtime performance separately; an editor connection does not implement them.

## Living terrain and adaptive puzzles

Keep each world's terrain identity and major landmarks authored. Build a limited
vocabulary of changes: roots form a bridge, water changes course, crystals rotate,
an energy current shifts, or a damaged structure stabilizes. Player actions alter
persistent regional state, which determines which changes are appropriate.

Proposed state includes ecological health, Divinity disturbance, local trust,
resolved story events, and unlocked abilities. Record concrete events such as
restoring a conduit or helping an inhabitant. Reactions should have a legible
cause; avoid a single hidden morality score.

The adaptive director selects or proposes a puzzle configuration from authored
modules. Begin with explicit rules so we can evaluate the experience. Then test
whether a model choosing among valid configurations adds worthwhile variety.
Model-generated geometry or executable gameplay logic is outside the first scope.

Every proposed change must pass game-owned checks:

- The objective is reachable with currently available abilities.
- Entrances, exits, checkpoints, and necessary clues remain accessible.
- New geometry does not trap, intersect, or displace the player unsafely.
- The player's current puzzle does not silently change halfway through solving it.
- Completed objectives and permanent traversal unlocks remain respected.
- The same saved world state restores the same accepted configuration.

If a proposal fails, use a known valid configuration. Apply major changes at
clear moments, with visible or audible feedback. Save the accepted result and
its seed or configuration ID rather than asking the model to recreate it on load.

Example: the player restores water flow in an Earth research grove. On returning,
new growth opens a root bridge and a water-routing puzzle uses a different valid
arrangement. A player who restored a power conduit first can encounter another
arrangement that uses the same learned ability. Both retain a valid exit and the
same essential story objective.

## Development milestones

These are completion gates, not calendar promises. Confirm team capacity, budget,
asset availability, platforms, and hardware before assigning dates. Build one
complete region before multiplying content across three worlds.

| Milestone | Deliverable | Completion gate |
| --- | --- | --- |
| 0. Creative and technical foundation | Agree camera, station viewpoint, action model, terrain references, target hardware, and visual progression; establish source control and backups | Opening order and no-ability rule recorded; stable editor and a packaged blank build run on the intended development target; full-quality rendering can be evaluated |
| 1. Opening prototype | Battle-station tutorial blockout, Center birth blockout, basic movement and interaction, first Scan Visor, checkpoint/save/load | A new player completes the station without abilities, transitions to the Center, unlocks scanning at birth, uses a scan clue, and resumes correctly after reloading |
| 2. Visual and character proofs | Prioritize the realistically cel-shaded Center and scan readability; station visual test; small Earth and First Ones' shading tests; one assembled MetaHuman with basic expression and speech animation | Each main world is distinct; the Center matches the agreed realistic cel shading; scanning and later visual stages preserve readability; richest stage meets the performance budget |
| 3. Voice and terrain proofs | One English-speaking NPC with bounded knowledge; one region with at least two action-dependent puzzle configurations | Natural paraphrases work; tested speech failures recover; both puzzle variants are solvable; accepted changes persist through save/load |
| 4. First playable opening | A proposed 15–20 minute station-to-Center experience combining the war tutorial, a brief voiced NPC encounter, Physis's birth, the Scan Visor lesson, and its first perception reveal | The opening works in a packaged build; station abilities remain locked; a first-time player understands scanning; checkpoints work across the transition; performance and voice latency/cost are measured |
| 5. Production systems and Earth integration slice | Reusable ability gates, NPC authoring, adaptive puzzle modules, regional state, planet transitions, save versioning, and debugging views; test them together in The Wounded Grove | Earth adds later ability use and action-dependent terrain without changing the established opening; revisits preserve abilities, scan discoveries, NPC memory, and terrain state |
| 6. Three-world campaign | Build the approved regions, major characters, installation encounters, faction arc, Center finale, and epilogue | The campaign is playable beginning to end with placeholder content allowed; all mandatory paths are covered by the progression graph |
| 7. Alpha and beta | Complete art/audio, balance action and puzzles, tune conversation, optimize characters and final visual stages, run external playtests | All required features are present; blockers are fixed; performance, save/load, accessibility, AI failure recovery, and service cost meet agreed targets |
| 8. Release preparation | Final builds, platform packaging, audio/input defaults, credits, account/service deployment, support and recovery plan | Fresh-install playthrough passes on supported hardware; builds and backend are reproducible; release checklist and operating budget are accepted |

Milestones 2 and 3 can overlap once the opening prototype establishes the
interaction model. The first playable opening uses the character and voice
proofs; adaptive terrain is proven separately before its Earth integration.
Do not scale up campaign content until both the opening and the Earth integration
slice demonstrate their intended experience.

## The first playable opening in detail

1. Enter the human battle station during its fight with First Ones' ships and warriors.
2. Learn looking, movement, navigation, and physical interaction through staged
   station situations. Introduce only the basic action mechanics approved for the game.
3. Include a short spoken crew interaction when the voice pipeline is ready.
4. Finish the war impression and transition into the consciousness forming at the Center.
5. Experience Physis's birth in the realistically cel-shaded environment.
6. Unlock the Scan Visor as the first ability and learn to examine a nearby target.
7. Use the revealed environmental information to recognize and follow a safe route.
8. Save and reload on both sides of the transition; confirm that abilities remain
   unavailable before birth and scan discoveries persist afterward.

Scope: a bounded station tutorial, a bounded Center birth area, one scan unlock,
a few authored scan targets, one short NPC exchange, and a transition between
locations. The first lessons use fixed arrangements. Adaptive terrain and later
manipulation abilities enter after this foundation.

## Later Earth integration slice

Working title: **The Wounded Grove**. This is an invented game location for review.

1. Arrive in a small Earth grove around a damaged research installation.
2. Explore two connected routes and encounter a barrier that is easy to remember.
3. Speak to one local NPC about the damaged system. Use a new supporting
   character unless relocating a book character is explicitly approved.
4. Discover Resonance Link, a proposed later ability following the Scan Visor,
   and gain the next visual stage.
5. Redirect a flow to stabilize the installation. Earlier actions determine which
   of two authored puzzle arrangements the player encounters.
6. Use the same ability under pressure to disable a defensive system.
7. See the grove respond, speak with the NPC again, and return via the new shortcut.
8. Save, quit, reload, and verify that the change and the NPC's relevant memory persist.

Scope: one bounded region, one meaningful ability unlock, one NPC, two puzzle
configurations, one confrontation, and one visible progression transition. This
follows the station and birth opening; it is not the first ability tutorial. Test
the other planetary shading identities in separate small scenes during this
stage. This later slice demonstrates the production approach without pretending that
the three-world campaign is already built.

## Architecture and production responsibilities

| System | Owns | Boundary |
| --- | --- | --- |
| Progression | Opening phase, abilities, levels, visual mastery, permanent unlocks | No abilities on the station; Scan Visor is the first unlock at birth; AI cannot award arbitrary upgrades |
| Scan system | Scan mode, target data, revealed facts, discovery history, visual/audio feedback | Reveals authored information; manipulation belongs to later abilities; discoveries persist in saves |
| Planet profiles | Shading identity, lighting, terrain modules, local rules | Planet identity remains recognizable across progression stages |
| Regional simulation | Persistent events, world condition, selected puzzle layouts | Changes are validated and applied at controlled times |
| Dialogue service | NPC context, conversation memory, speech requests and replies | Requests game actions through a narrow validated interface |
| Character presentation | Animation, expressions, lip sync, visual progression | Receives approved game/dialogue events; does not decide quest state |
| Save system | Progression, regional state, approved NPC memories, configuration IDs | Restores accepted outcomes without requiring a fresh AI response |
| Developer tooling | Event history, active gates, layout validity, AI timing and cost | Makes failures reproducible without exposing implementation details in normal play |

Use Unreal assets and Blueprints for authoring and iteration; add C++ where the
system's complexity or measured performance warrants it. Keep editor MCP tooling
separate from shipped runtime AI systems. Establish source control before changing
binary levels and character assets. Record asset sources and usage rights as
content enters production.

## Main uncertainties and how we resolve them

| Uncertainty | Earliest practical check | Decision it enables |
| --- | --- | --- |
| A powerful protagonist still needs satisfying limits | Ability prototype and narrative review | Agree mastery limits that fit the book |
| “Better graphics” could become visual noise or high cost | Same scene at every stage on target hardware | Set art rules and final-stage budgets |
| Spoken dialogue may feel slow or misunderstand players | Repeated conversations across accents and ordinary microphone conditions | Select pipeline, turn-taking, and recovery behavior |
| Adaptive puzzles could feel arbitrary or become unsolvable | Both layouts, varied action order, interruption, and reload tests | Approve the director's change vocabulary and validation rules |
| MetaHuman detail could overwhelm runtime budgets | One assembled character in the shading proof | Set character detail, animation, and crowd limits |
| Online AI creates recurring operating costs | Measure the slice's actual audio/model usage | Set session limits, service budget, and offline expectations |
| Editor rendering instability can hide art problems | Stable normal-rendering launch and packaged test | Separate driver workarounds from the final renderer choice |

## Decisions for the next review

1. Decide the battle-station viewpoint and its connection to Physis's emerging mind;
   confirm or change third-person exploration and the basic action model.
2. Supply the defined terrain references and visual references for the station
   and the Center's realistic cel shading; refine the other worlds' shading.
3. Refine Scan Visor presentation, controls, target types, and spoken feedback.
4. Approve how later mastery and leveling coexist with Physis's inherent power.
5. Set launch platforms, minimum hardware, team size, and available budget.
6. Decide online requirements, voice interaction style, and accessibility expectations.
7. Refine the station-to-Center opening scope and decide when to build The Wounded
   Grove as the later Earth integration slice.

After this review, start Milestone 0 and the opening prototype. This roadmap
does not authorize beginning full campaign production before the author's next
direction.
