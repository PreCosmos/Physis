"""Blueprint logic for level 3, the Conclave (Tools/conclave/README.md, "People (BP_NPC) and Blueprints"). Run from the
project folder, after `outfit_operation conclave:blueprints` has created the Blueprint assets and IA_LightStep:
    python3 Tools/blueprint_logic/conclave_logic.py [npc] [current] [director] [trail] [physis] [input] [--dry]

npc       BP_NPC: garments on their bones (the construction script, and again first in BeginPlay), people shown and
          hidden by tokens, the conversation (TalkStart, TalkKey, TalkShow, TalkTopic, TalkReward, TalkOpt, TalkEnd),
          facing Physis while talking, idle float for hovering figures
current   BP_Current: the Divinity current between the Center's temple and the Wellspring
director  BP_ConclaveDirector: the arrival, the Spine's thirds and sun per relit pylon, palette pickups
trail     BP_LightTrail: Light Step's streak
physis    BP_Physis: Talking, Light Step (PhysisLightStep, PhysisLightStepGo, PhysisLightStepEnd), PhysisToConclave,
          PhysisConclaveHome, and PhysisInteract with people first (center_overrides.py part conclave, run from here)
input     IA_LightStep (X, LB) wired to BP_Physis.PhysisLightStep
--dry     prints every call and every DSL graph instead of sending them (no editor needed)

Then center_overrides.py music saves menu progress conclave, then, in a FRESH editor as its first write,
conclave_hud.py (the HUD's talk panel, DrawInteract and the map; README "Run order", step 4). Every graph here is new
except PhysisInteract, a station graph the station's rebuild rewrites: its Conclave version lives in center_overrides.py
(part conclave), which this script runs once BP_NPC has its talk, as center_music.py does after a station rebuild.
Graphs naming an asset (MM_Idle, the palette pickups, the Conclave sounds) must be rewritten after that asset is
re-imported, or the node keeps a dead reference.

DSL rules applied (memory unreal-mcp-access): a cast with :then/:CastFailed ends the exec flow, so follow-ups sit
inside :then; no Utilities|IsValid; values a later Set would change are re-read from their variables, never bound;
no (return); pins are named as the generator scripts name them. Read every graph back after writing.
"""
import json
import pathlib
import struct
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
sys.path.insert(0, str(ROOT / 'Content/Python'))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import physis_conclave_lore as lore  # noqa: E402
import physis_conclave_plan as plan  # noqa: E402

DRY = '--dry' in sys.argv
ARGS = [a for a in sys.argv[1:] if a != '--dry']
if DRY:
    # center_overrides opens its editor connection on import; a stand-in client keeps a dry run offline.
    stub = types.ModuleType('unreal_mcp')

    class UnrealMCP:
        def __init__(self, timeout=30):
            self.timeout = timeout

        def initialize(self):
            return {}

        def call(self, name, arguments=None):
            raise RuntimeError('dry run: no editor calls')
    stub.UnrealMCP = UnrealMCP
    sys.modules['unreal_mcp'] = stub
import center_overrides as co  # noqa: E402

if DRY:
    co.call = lambda tool, args, quiet=False: call(tool, args, quiet)  # its graphs print with this script's
else:
    c = co.c  # one editor connection for both scripts
T = 'editor_toolset.toolsets.blueprint.BlueprintTools'
OBJ = 'editor_toolset.toolsets.object.ObjectTools'
OUTFIT = 'physis_character_tools.PhysisCharacterTools'
B = '/Game/Characters/Physis/Blueprints/'
P = B + 'BP_Physis.BP_Physis'
NPC = B + 'BP_NPC.BP_NPC'
CUR = B + 'BP_Current.BP_Current'
DIRECTOR = B + 'BP_ConclaveDirector.BP_ConclaveDirector'
TRAIL = B + 'BP_LightTrail.BP_LightTrail'
CA = '/Game/Conclave/Audio/'
CM = '/Game/Conclave/Meshes/'
MM_IDLE = '"/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle"'
FAILED = []
TOUCHED = []
BROKEN = set()  # Blueprints with a failed write: not saved, so a fresh editor does not keep a half-written graph


def call(tool, args, quiet=False, toolset=T):
    if DRY:
        if tool == 'write_graph_dsl':
            print('=== DSL %s' % args['graph']['refPath'])
            print(args['code'])
            print('=== END')
        else:
            print('--- %s %s' % (tool, json.dumps(args, ensure_ascii=False)))
        return '{"returnValue": null}'
    r = c.call('call_tool', {'toolset_name': toolset, 'tool_name': tool, 'arguments': args})
    text = r['content'][0]['text']
    if r.get('isError') and not quiet:
        print('ERR', tool, text[:700])
    return None if r.get('isError') else text


def var(bp, name, kind, edit=False):
    """Adds a member variable only if the Blueprint lacks it: add_variable on a name in use adds a numbered copy
    (Until_0, Until_1, ...), and set_variable_instance_editable marks the Blueprint changed on every call (review,
    2026-11-07). center_overrides.var() makes the check."""
    if DRY:
        call('add_variable', {'blueprint': {'refPath': bp}, 'name': name, 'type_name': kind}, True)
        if edit:
            call('set_variable_instance_editable', {'blueprint': {'refPath': bp}, 'variable_name': name, 'instance_editable': True}, True)
        return
    co.var(bp, name, kind, edit)


def shell(bp, name, params=()):
    if call('add_function_graph', {'blueprint': {'refPath': bp}, 'graph_name': name}, True) is None:
        return
    for pn, pt in params:
        call('add_function_param', {'graph': {'refPath': bp + ':' + name}, 'param_name': pn, 'param_type': pt, 'input_param': True})


def pruned(bp, graph):
    """After a successful write, the Center session's prune (center_overrides.prune: op center:prune) removes the dead
    nodes write_graph_dsl leaves on the entry's parameter pins (89% of all nodes by 2026-11-07). A prune that changes
    the graph's live DSL is a failure: the Blueprint is then not saved."""
    before = len(co.FAILED)
    co.prune(bp, graph)
    if any(item == 'prune ' + graph for item in co.FAILED[before:]):
        FAILED.append('prune ' + graph)
        BROKEN.add(bp)


def fn(bp, name, code):
    ok = call('write_graph_dsl', {'graph': {'refPath': bp + ':' + name}, 'code': code})
    print(name, 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        FAILED.append(name)
        BROKEN.add(bp)
    else:
        pruned(bp, name)


def events(bp, code, label):
    ok = call('write_graph_dsl', {'graph': {'refPath': bp + ':EventGraph'}, 'code': code})
    print(label, 'events ok' if ok else 'events FAILED', flush=True)
    if not ok:
        FAILED.append(label)
        BROKEN.add(bp)
    else:
        pruned(bp, 'EventGraph')


def comp(bp):
    call('compile_blueprint', {'blueprint': {'refPath': bp}})
    if bp not in TOUCHED:
        TOUCHED.append(bp)


def defaults(bp, values):
    """Class defaults (the DSL cannot set them): written on the generated class's default object, which keeps them
    through later compiles, as physis_aaa_tools does for initial_life_span."""
    found = call('get_default_object', {'blueprint': {'refPath': bp}})
    cdo = (json.loads(found).get('returnValue') or {}).get('refPath') if found else None
    if DRY:
        cdo = bp.rsplit('.', 1)[0] + '.Default__' + bp.rsplit('.', 1)[1] + '_C'
    ok = cdo and call('set_properties', {'instance': {'refPath': cdo}, 'values': json.dumps(values)}, toolset=OBJ)
    print('defaults', bp.rsplit('.', 1)[1], values, 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        FAILED.append('defaults ' + bp.rsplit('.', 1)[1])


def save(bp):
    """Saves one Blueprint (aaa:save_asset), so the HUD batch can run in a fresh editor without losing this run."""
    if bp in BROKEN:
        print('not saved', bp.rsplit('.', 1)[1], '(a write failed: fix it, then rerun this part)', flush=True)
        return
    ok = call('outfit_operation', {'operation': 'aaa:save_asset:' + bp.rsplit('.', 1)[0]}, toolset=OUTFIT)
    print('saved', bp.rsplit('.', 1)[1], 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        FAILED.append('save ' + bp.rsplit('.', 1)[1])


def lit(text):
    """A DSL string literal. The DSL has no escapes, so text holding a double quote or a line break cannot be written."""
    assert '"' not in text and '\n' not in text, text
    return '"%s"' % text


def snd(path, vol=1.0):
    name = path.split('/')[-1]
    return '(Audio|PlaySound2D :Sound "%s.%s" :VolumeMultiplier %s)' % (path, name, vol)


PHYSIS = '(bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))\n'
FLAGS = '(Class|BPPhysis|GetFlags :self physis)'
NOW = '(Utilities|Time|GetGameTimeinSeconds)'
REAL = '(Utilities|Time|GetRealTimeSeconds)'
EMPTY = lambda v: '(Utilities|String|EqualExactly(String) :A %s :B "")' % v
HAS = lambda flags, tok: '(Utilities|String|Contains :SearchIn %s :Substring %s)' % (flags, tok)
MAXP = '(select (> (Class|BPPhysis|GetMaxHealth :self physis) 0.0) (Class|BPPhysis|GetMaxHealth :self physis) 10.0)'
# A person's own token, given with their first reward. Rewarded alone lives only as long as the actor, so after a load
# Tamsin would pay her 60 Divinity again and Iriel would repeat her note; the token keeps "once" across saves.
MET = '(Utilities|String|Append :A ",met_" :B (Utilities|String|Append :A (Variables|Default|GetKey) :B ","))'


# ---------------------------------------------------------------- arrival points

def terrain_top(x, y, reach=3.0):
    """Highest point of the exported height grid (drum.py: Art/Meshes/Conclave/height.bin) within reach of (x, y)
    metres, or None before the Blender build has written it."""
    meta, grid = ROOT / 'Art/Meshes/Conclave/height.json', ROOT / 'Art/Meshes/Conclave/height.bin'
    if not (meta.exists() and grid.exists()):
        return None
    info = json.loads(meta.read_text())
    hx, hy, cell, nx, ny = info['half_x'], info['half_y'], info['cell'], int(info['nx']), int(info['ny'])
    data = grid.read_bytes()
    steps = int(reach / cell) + 1
    i0, j0 = int(round((x + hx) / cell)), int(round((y + hy) / cell))
    tops = [struct.unpack_from('<f', data, 4 * (i * ny + j))[0]
            for i in range(i0 - steps, i0 + steps + 1) for j in range(j0 - steps, j0 + steps + 1) if 0 <= i < nx and 0 <= j < ny]
    return max(tops) if tops else None


# Where a current lands her. The scenario places the real spots, TargetPoints tagged ConclaveArrival (on the Wellspring
# Still Point) and ConclaveReturn (in the Center's sanctum, by conclave:portal), on the placed ground; the travelling
# functions give ,trip, and BP_Current moves her onto the level's spot when it sees that token after the load. These
# points are the save's checkpoint until then, and where she stays in a level without the spot.
# The Conclave: a little north of the Wellspring's current pool (plan.WELL), clear of the current's 1.8 m pull. Her
# capsule centre goes 1.6 m above the highest ground within 3 m (the capsule's half height is 0.96 m, the rest is room
# for the garden's paving), so she settles with a short drop. Before the height grid exists the floor there is taken at
# 8 m, the top of its 6 to 8 m (plan.FLOOR is 6 m on the drum's centre line).
ARRIVE = (plan.WELL[0] + 7.0, plan.WELL[1])
_ground = terrain_top(*ARRIVE)
ARRIVE_CM = (ARRIVE[0] * 100.0, ARRIVE[1] * 100.0, round(((_ground if _ground is not None else plan.FLOOR + 2.0) + 1.6) * 100.0))
# The Center: the sanctum of the Temple of the First Light (physis_center_scenario TEMPLE (76000, 0) cm, sanctum floor
# TEMPLE_FLOOR + 600 = 4000 cm), 6 m south of the Heartbloom's pedestal, between it and the Sanctum Still Point
# (x 74400). BP_Current only carries her once she has been outside its radius since the level began (Armed), so an
# arrival this close to the temple's current can never bounce her straight back.
HOME_CM = (76000.0 - 600.0, 0.0, 4000.0 + 130.0)
# A direct start's quest (a current's arrival gets the Wellspring Still Point's); the lore owns all text, so its
# QUEST_ARRIVE is used once it has one.
QUEST_ARRIVE = getattr(lore, 'QUEST_ARRIVE', 'Find Kairos at the Archive in the Commons, north of the Wellspring')


# ---------------------------------------------------------------- BP_NPC

def npc():
    for n, k in (('Speaker', 'string'), ('Key', 'string'), ('Pages', 'string'), ('Asks', 'string'), ('Starts', 'string'),
                 ('Greet', 'int'), ('Show', 'string'), ('Hide', 'string'), ('Give', 'string'), ('Quest', 'string'),
                 ('RewardDivinity', 'float'), ('RewardHeal', 'bool'), ('Note', 'string'), ('Face', 'bool'), ('Bob', 'float')):
        var(NPC, n, k, True)
    # Contract runtime variables, then this script's own: Shown (the token test, read by PhysisInteract and the HUD),
    # NoteDue (the note waits for TalkEnd), ShapeHome (Shape's rest position for Bob), Reach and Top (talk range and
    # icon height from the person's size), Hold (frames left before her input comes back after a talk).
    for n, k in (('Talking', 'bool'), ('Page', 'int'), ('Stop', 'int'), ('Mode', 'int'), ('Row', 'int'), ('OptCount', 'int'),
                 ('Fresh', 'bool'), ('Rewarded', 'bool'), ('PageText', 'string'), ('Opt0', 'string'), ('Opt1', 'string'),
                 ('Opt2', 'string'), ('Opt3', 'string'), ('HomeYaw', 'float'), ('Shown', 'bool'), ('NoteDue', 'bool'),
                 ('ShapeHome', 'vector'), ('Reach', 'float'), ('Top', 'float'), ('Hold', 'int')):
        var(NPC, n, k)
    for name, params in (('TalkStart', ()), ('TalkKey', (('Code', 'int'),)), ('TalkEnd', ()), ('TalkShow', ()), ('TalkTopic', ()),
                         ('TalkReward', ()), ('TalkOpt', (('Slot', 'int'), ('Text', 'string')))):
        shell(NPC, name, params)

    fn(NPC, 'TalkOpt', """(fn TalkOpt (Slot Text)
  (if (== Slot 0)
    (Variables|Default|SetOpt0 Text))
  (if (== Slot 1)
    (Variables|Default|SetOpt1 Text))
  (if (== Slot 2)
    (Variables|Default|SetOpt2 Text))
  (if (== Slot 3)
    (Variables|Default|SetOpt3 Text)))""")

    # Page k of Pages (split on |) and its voice, BP_LogVoice "Talk <Key> <k>" (physis_conclave_lore.person_key).
    fn(NPC, 'TalkShow', """(fn TalkShow ()
  (bind pages (Utilities|String|ParseIntoArray :SourceString (Variables|Default|GetPages) :Delimiter "|" :CullEmptyStrings false))
  (if (< (Variables|Default|GetPage) (Utilities|Array|Length pages))
    (Variables|Default|SetPageText (Utilities|Array|Get(acopy) pages (Variables|Default|GetPage)))
    """ + PHYSIS + """      (:then
        (Class|BPPhysis|PhysisNarrate :self physis :Title (Utilities|String|Append :A "Talk " :B (Utilities|String|Append :A (Variables|Default|GetKey) :B (Utilities|String|Append :A " " :B (Utilities|String|ToString(Integer) (Variables|Default|GetPage)))))))
      (:CastFailed))))""")

    # Talking pauses the game, so this person (and Body's idle) ticks while paused to keep breathing and turn to her.
    # Fresh makes the HUD skip its keys on this first frame: the Interact press that started the talk is still "just
    # pressed" when the HUD draws. Options are the topics (Asks, at most three) and Leave. A message on the tutorial
    # panel is cleared: it shares the bottom of the screen with the talk panel, and its timer stops while paused.
    fn(NPC, 'TalkStart', """(fn TalkStart ()
  """ + PHYSIS + """    (:then
      (Variables|Default|SetTalking true)
      (Variables|Default|SetFresh true)
      (Variables|Default|SetMode 0)
      (Variables|Default|SetRow 0)
      (Variables|Default|SetPage 0)
      (if (< (Variables|Default|GetGreet) 1)
        (Variables|Default|SetGreet 1))
      (Variables|Default|SetStop (Variables|Default|GetGreet))
      (if """ + HAS(FLAGS, MET) + """
        (Variables|Default|SetRewarded true))
      (Variables|Default|SetOpt0 "")
      (Variables|Default|SetOpt1 "")
      (Variables|Default|SetOpt2 "")
      (Variables|Default|SetOpt3 "")
      (Variables|Default|SetOptCount 0)
      (for ask (Utilities|String|ParseIntoArray :SourceString (Variables|Default|GetAsks) :Delimiter "|" :CullEmptyStrings true)
        (if (< (Variables|Default|GetOptCount) 3)
          (CallFunction|TalkOpt :Slot (Variables|Default|GetOptCount) :Text ask)
          (Variables|Default|SetOptCount (+ (Variables|Default|GetOptCount) 1))))
      (CallFunction|TalkOpt :Slot (Variables|Default|GetOptCount) :Text "Leave")
      (Variables|Default|SetOptCount (+ (Variables|Default|GetOptCount) 1))
      (Class|BPPhysis|SetTalking :self physis :Talking true)
      (Class|BPPhysis|PhysisSay :self physis :Message "")
      (Actor|Tick|SetTickablewhenPaused :bTickableWhenPaused true)
      (Components|Tick|SetTickablewhenPaused :self (Variables|Default|GetBody) :bTickableWhenPaused true)
      (Game|SetGamePaused :bPaused true)
      """ + snd(CA + 'S_TalkOpen', .8) + """
      (if (and (Variables|Default|GetRewarded) (> (Variables|Default|GetOptCount) 1))
        (Variables|Default|SetMode 1)
        (else
          (CallFunction|TalkShow))))
    (:CastFailed)))""")

    # A topic answers from its first page (Starts) up to the next topic's first page, the last one to the end of Pages.
    fn(NPC, 'TalkTopic', """(fn TalkTopic ()
  (bind starts (Utilities|String|ParseIntoArray :SourceString (Variables|Default|GetStarts) :Delimiter "|" :CullEmptyStrings true))
  (if (< (Variables|Default|GetRow) (Utilities|Array|Length starts))
    (Variables|Default|SetPage (Utilities|String|StringToInteger :InString (Utilities|Array|Get(acopy) starts (Variables|Default|GetRow))))
    (Variables|Default|SetStop (Utilities|Array|Length (Utilities|String|ParseIntoArray :SourceString (Variables|Default|GetPages) :Delimiter "|" :CullEmptyStrings false)))
    (if (< (+ (Variables|Default|GetRow) 1) (Utilities|Array|Length starts))
      (Variables|Default|SetStop (Utilities|String|StringToInteger :InString (Utilities|Array|Get(acopy) starts (+ (Variables|Default|GetRow) 1)))))
    (if (< (Variables|Default|GetPage) (Variables|Default|GetStop))
      (Variables|Default|SetMode 0)
      (CallFunction|TalkShow))))""")

    # The greeting's end, once: Give, Quest, Divinity (capped at 100 like a relic's) and the heal, after PhysisFidelity
    # so a Health Augmentation in Give heals to the new maximum. The note waits for TalkEnd.
    gift = '(+ (Class|BPPhysis|GetDivinity :self physis) (Variables|Default|GetRewardDivinity))'
    fn(NPC, 'TalkReward', """(fn TalkReward ()
  (Variables|Default|SetRewarded true)
  """ + PHYSIS + """    (:then
      (Class|BPPhysis|PhysisGive :self physis :Token """ + MET + """)
      (if (and (not """ + EMPTY('(Variables|Default|GetGive)') + """) (not """ + HAS(FLAGS, '(Variables|Default|GetGive)') + """))
        (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive)))
      (if (not """ + EMPTY('(Variables|Default|GetQuest)') + """)
        (Class|BPPhysis|PhysisQuest :self physis :Goal (Variables|Default|GetQuest)))
      (if (> (Variables|Default|GetRewardDivinity) 0.0)
        (Class|BPPhysis|SetDivinity :self physis :Divinity (select (> """ + gift + """ 100.0) 100.0 """ + gift + """)))
      (if (Variables|Default|GetRewardHeal)
        (Class|BPPhysis|PhysisFidelity :self physis)
        (Class|BPPhysis|SetPhysisHealth :self physis :PhysisHealth """ + MAXP + """))
      (if (or (or (not """ + EMPTY('(Variables|Default|GetGive)') + """) (Variables|Default|GetRewardHeal)) (> (Variables|Default|GetRewardDivinity) 0.0))
        """ + snd('/Game/Center/Audio/S_Stillstone') + """)
      (Variables|Default|SetNoteDue (not """ + EMPTY('(Variables|Default|GetNote)') + """)))
    (:CastFailed)))""")

    # The game stays paused when the pause menu ended the talk (the HUD ends it when BP_Physis LogOpen is set).
    # Otherwise play resumes with the key that ended the talk still down (A or Space confirm, B leaves), and Enhanced
    # Input would start that key's action on the first unpaused frame: a jump, a dodge, or Interact opening the talk
    # again. So her input is off for three frames (Hold, counted by EventTick, which ticks on even if something pauses
    # the game meanwhile), long enough for that press to start and pass unheard. TalkEndAt also lets PhysisInteract
    # ignore Interact for 0.35 s.
    fn(NPC, 'TalkEnd', """(fn TalkEnd ()
  (Variables|Default|SetTalking false)
  (Variables|Default|SetMode 0)
  """ + PHYSIS + """    (:then
      (Class|BPPhysis|SetTalking :self physis :Talking false)
      (Class|BPPhysis|SetTalkEndAt :self physis :TalkEndAt """ + REAL + """)
      (Class|BPPhysis|PhysisVoiceStop :self physis)
      (if (Class|BPPhysis|GetLogOpen :self physis)
        (Actor|Tick|SetTickablewhenPaused :bTickableWhenPaused false)
        (Components|Tick|SetTickablewhenPaused :self (Variables|Default|GetBody) :bTickableWhenPaused false)
        (else
          (Input|DisableInput :self physis :PlayerController (Game|GetPlayerController 0))
          (Variables|Default|SetHold 3)))
      (Game|SetGamePaused :bPaused (Class|BPPhysis|GetLogOpen :self physis))
      (if (Variables|Default|GetNoteDue)
        (Variables|Default|SetNoteDue false)
        (Class|BPPhysis|PhysisSay :self physis :Message (Variables|Default|GetNote))))
    (:CastFailed)))""")

    # Code 1 confirm / next, 2 up, 3 down, 4 leave (the HUD's DrawTalk polls the keys). Reading (Mode 0) pages through
    # [Page, Stop); the greeting's last page rewards once, then the topics (Mode 1), or the end when there are none.
    fn(NPC, 'TalkKey', """(fn TalkKey (Code)
  (if (== Code 4)
    (CallFunction|TalkEnd)
    (elif (== (Variables|Default|GetMode) 1)
      (if (== Code 2)
        (Variables|Default|SetRow (select (> (Variables|Default|GetRow) 0) (- (Variables|Default|GetRow) 1) 0)))
      (if (== Code 3)
        (Variables|Default|SetRow (select (< (Variables|Default|GetRow) (- (Variables|Default|GetOptCount) 1)) (+ (Variables|Default|GetRow) 1) (Variables|Default|GetRow))))
      (if (== Code 1)
        (if (>= (Variables|Default|GetRow) (- (Variables|Default|GetOptCount) 1))
          (CallFunction|TalkEnd)
          (else
            (CallFunction|TalkTopic))))
      (else
        (if (== Code 1)
          (Variables|Default|SetPage (+ (Variables|Default|GetPage) 1))
          (if (< (Variables|Default|GetPage) (Variables|Default|GetStop))
            (CallFunction|TalkShow)
            (else
              (if (and (not (Variables|Default|GetRewarded)) (<= (Variables|Default|GetStop) (Variables|Default|GetGreet)))
                (CallFunction|TalkReward))
              (if (> (Variables|Default|GetOptCount) 1)
                (Variables|Default|SetMode 1)
                (else
                  (CallFunction|TalkEnd))))))))))""")

    # Shown: the Show token held (or none) and the Hide token not, and never hidden mid-talk (Iriel's greeting gives
    # her own Hide token). Hidden people lose collision too. A person's talk range is 3 m beyond their own footprint
    # (a human's bounds are inside 1 m, so 3 m; seated Patience is far wider), the talk icon sits over their bounds
    # (capped so a 7 m Mecha's stays on screen); a MetaHuman person is a child actor in Look (PEOPLE_DESIGN.md 3.1),
    # which the bounds count only when told to. Idles start at random points so a crowd does not breathe in step;
    # Bob floats Shape on real time, which runs on while a talk pauses the game. Hold gives her input back after a talk
    # (TalkEnd), then stops this person ticking while paused.
    yaw = '(Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw want)'
    # Garments ride their bones (2026-11-07 review: every person's clothes lay on the ground beside them). The scenario
    # attaches each garment to its bone keeping its world transform, but a compile re-runs construction and puts the
    # Blueprint's own components back under the root, where their stored bone-relative transforms land on the floor.
    # KeepRelative re-reads those transforms against the bone, so the construction script repairs placed people on the
    # next compile and BeginPlay again at play. (A figure's Body has no skeleton: its empty garments attach harmlessly.)
    attach = ''.join('\n  (Transformation|AttachComponentToComponent (Variables|Default|Get%s) (Variables|Default|GetBody) "%s" '
                     '"KeepRelative" "KeepRelative" "KeepRelative" false)' % (part, bone)
                     for part, bone in (('Lower', 'pelvis'), ('Upper', 'spine_05'), ('Head', 'head')))
    fn(NPC, 'UserConstructionScript', '(fn ConstructionScript ()' + attach + ')')
    events(NPC, """(event EventBeginPlay""" + attach + """
  (Variables|Default|SetHomeYaw (.yaw (Transformation|GetActorRotation)))
  (Variables|Default|SetShapeHome (Class|SceneComponent|GetRelativeLocation :self (Variables|Default|GetShape)))
  (bind (centre extent) (Collision|GetActorBounds :bOnlyCollidingComponents false :bIncludeFromChildActors true))
  (bind wide (select (> (.x extent) (.y extent)) (.x extent) (.y extent)))
  (bind rise (- (+ (.z centre) (.z extent)) (.z (Transformation|GetActorLocation))))
  (Variables|Default|SetReach (+ 300.0 (select (> wide 100.0) (- wide 100.0) 0.0)))
  (Variables|Default|SetTop (select (> rise 215.0) 240.0 (select (< rise 95.0) 120.0 (+ rise 25.0))))
  (Components|Animation|PlayAnimation :self (Variables|Default|GetBody) :NewAnimToPlay """ + MM_IDLE + """ :bLooping true)
  (Components|Animation|SetPosition :self (Variables|Default|GetBody) :InPos (Math|Random|RandomFloatinRange :Min 0.0 :Max 1.5) :bFireNotifies false))

(event EventTick (DeltaSeconds)
  """ + PHYSIS + """    (:then
      (if (> (Variables|Default|GetHold) 0)
        (Variables|Default|SetHold (- (Variables|Default|GetHold) 1))
        (if (== (Variables|Default|GetHold) 0)
          (Input|EnableInput :self physis :PlayerController (Game|GetPlayerController 0))
          (Actor|Tick|SetTickablewhenPaused :bTickableWhenPaused false)
          (Components|Tick|SetTickablewhenPaused :self (Variables|Default|GetBody) :bTickableWhenPaused false)))
      (bind flags """ + FLAGS + """)
      (Variables|Default|SetShown (or (Variables|Default|GetTalking) (and (or """ + EMPTY('(Variables|Default|GetShow)') + ' ' + HAS('flags', '(Variables|Default|GetShow)') + """) (or """ + EMPTY('(Variables|Default|GetHide)') + ' (not ' + HAS('flags', '(Variables|Default|GetHide)') + """)))))
      (Rendering|SetActorHiddenInGame :bNewHidden (not (Variables|Default|GetShown)))
      (Collision|SetActorEnableCollision :bNewActorEnableCollision (Variables|Default|GetShown))
      (if (> (Variables|Default|GetBob) 0.0)
        (bind home (Variables|Default|GetShapeHome))
        (Transformation|SetRelativeLocation :self (Variables|Default|GetShape) :NewLocation (Math|Vector|MakeVector :X (.x home) :Y (.y home) :Z (+ (.z home) (* (Variables|Default|GetBob) (Math|Trig|Sin(Radians) (+ (* """ + REAL + """ 1.7) (* (Variables|Default|GetHomeYaw) 0.05)))))) :bSweep false :bTeleport true))
      (if (Variables|Default|GetShown)
        (bind here (Transformation|GetActorLocation))
        (bind there (Transformation|GetActorLocation :self physis))
        (bind facing (Transformation|GetActorRotation))
        (bind want (select (and (Variables|Default|GetTalking) (Variables|Default|GetFace)) (Math|Trig|Atan2(Degrees) :Y (- (.y there) (.y here)) :X (- (.x there) (.x here))) (Variables|Default|GetHomeYaw)))
        (bind turn (.yaw (Math|Rotator|Delta(Rotator) :A """ + yaw + """ :B facing)))
        (if (> (select (< turn 0.0) (* turn -1.0) turn) 0.5)
          (Transformation|SetActorRotation :NewRotation (Math|Interpolation|RInterpTo :Current facing :Target """ + yaw + """ :DeltaTime (select (> DeltaSeconds 0.1) 0.1 DeltaSeconds) :InterpSpeed 5.0) :bTeleportPhysics false))))
    (:CastFailed)))""", 'npc')
    comp(NPC)
    defaults(NPC, {'Face': True})


# ---------------------------------------------------------------- BP_Current

def current():
    """Visible while Need is held; standing in it for 0.8 s travels (Dest 1 PhysisToConclave, 2 PhysisConclaveHome).
    The screen fades to the current's light over those 0.8 s and clears if she steps out. Armed: she must have been
    outside the current once since the level began, so arriving next to one never sends her straight back. Arrival:
    once the load has restored her flags with ,trip, (given by the travelling function), the current takes the token
    and moves her onto the scenario's spot for this level (TargetPoint ConclaveArrival in the Conclave, ConclaveReturn
    in the Center), which becomes her checkpoint; without one she stays where the save put her. The temple current (Dest
    1) also points the quest at itself once, when Mend has opened it and the Conclave is not yet visited
    (,cn_currenthint,): after the Heartbloom nothing else did (Center session's Play test, 2026-11-07)."""
    for n, k in (('Need', 'string'), ('Dest', 'int'), ('Radius', 'float')):
        var(CUR, n, k, True)
    for n, k in (('Stay', 'float'), ('Armed', 'bool'), ('Gone', 'bool')):
        var(CUR, n, k)
    light = '(Utilities|Struct|MakeLinearColor :R 0.85 :G 0.93 :B 1.0 :A 1.0)'
    land = ''.join("""
        (for %s (Actor|GetAllActorswithTag :Tag "%s")
          (Transformation|SetActorLocation :self physis :NewLocation (Transformation|GetActorLocation :self %s) :bSweep false :bTeleport true)
          (Class|BPPhysis|PhysisCheckpoint :self physis :X (.x (Transformation|GetActorLocation :self %s)) :Y (.y (Transformation|GetActorLocation :self %s)) :Z (.z (Transformation|GetActorLocation :self %s))))"""
                   % ((spot, tag) + (spot,) * 4) for spot, tag in (('spot', 'ConclaveArrival'), ('back', 'ConclaveReturn')))
    events(CUR, """(event EventTick (DeltaSeconds)
  """ + PHYSIS + """    (:then
      (if """ + HAS(FLAGS, '",trip,"') + """
        (Class|BPPhysis|SetFlags :self physis :Flags (Utilities|String|Replace :SourceString """ + FLAGS + """ :From ",trip," :To "" :SearchCase "CaseSensitive"))""" + land + """)
      (bind ready (or """ + EMPTY('(Variables|Default|GetNeed)') + ' ' + HAS(FLAGS, '(Variables|Default|GetNeed)') + """))
      (if (and (and ready (== (Variables|Default|GetDest) 1)) (and (not """ + HAS(FLAGS, '",conclave,"') + """) (not """ + HAS(FLAGS, '",cn_currenthint,"') + """)))
        (Class|BPPhysis|PhysisGive :self physis :Token ",cn_currenthint,")
        (Class|BPPhysis|PhysisQuest :self physis :Goal """ + lit(lore.QUEST_CURRENT) + """))
      (Rendering|SetActorHiddenInGame :bNewHidden (not ready))
      (Collision|SetActorEnableCollision :bNewActorEnableCollision ready)
      (bind reach (select (> (Variables|Default|GetRadius) 0.0) (Variables|Default|GetRadius) 180.0))
      (bind gap (Transformation|GetDistanceTo :OtherActor physis))
      (if (> gap (+ reach 150.0))
        (Variables|Default|SetArmed true))
      (if (and (and ready (Variables|Default|GetArmed)) (and (< gap reach) (and (not (Class|BPPhysis|GetCinematic :self physis)) (not (Class|BPPhysis|GetPhysisDead :self physis)))))
        (if (<= (Variables|Default|GetStay) 0.0)
          """ + snd(CA + 'S_CurrentTravel') + """)
        (Variables|Default|SetStay (+ (Variables|Default|GetStay) DeltaSeconds))
        (bind glow (/ (Variables|Default|GetStay) 0.8))
        (CameraFades|SetManualCameraFade :self (Game|GetPlayerCameraManager 0) :InFadeAmount (select (> glow 1.0) 1.0 glow) :Color """ + light + """ :bInFadeAudio false)
        (if (and (>= (Variables|Default|GetStay) 0.8) (not (Variables|Default|GetGone)))
          (Variables|Default|SetGone true)
          (if (== (Variables|Default|GetDest) 2)
            (Class|BPPhysis|PhysisConclaveHome :self physis)
            (elif (== (Variables|Default|GetDest) 1)
              (Class|BPPhysis|PhysisToConclave :self physis))))
        (else
          (if (> (Variables|Default|GetStay) 0.0)
            (Variables|Default|SetStay 0.0)
            (CameraFades|StopCameraFade :self (Game|GetPlayerCameraManager 0))))))
    (:CastFailed)))""", 'current')
    comp(CUR)
    defaults(CUR, {'Radius': 180.0})


# ---------------------------------------------------------------- BP_ConclaveDirector

def director():
    """Arrive (0.5 s in, after PhysisRestore and BP_Awakening's Begin at 0.25 s have set the flags): a direct start still
    gets ,conclave, ,at_conclave, (so its saves load here) and, with no objective and Kairos not yet met, a quest; the
    first visit says the arrival and narrates Divinity's Arrival line (,conclave_seen,). Spine (every 0.25 s): each
    relit pylon (,pylon1, Terraces = south third, ,pylon2, Reservoir = middle, ,pylon3, Foundry = north) shows SpineLitN
    and its own beam to the Spine (PylonBeamN, placed hidden by the scenario) and hides SpineDimN, with S_SpineWake
    when one wakes in play; SpineSun eases to SunBase + SunStep per pylon, or, with neither set on the placed director,
    from a quarter of the light's placed intensity to all of it. Every frame: BP_Pickup's BeginPlay (PickupSetup) puts
    the station's meshes on placed pickups and drops alike, so each gets its palette mesh by Kind (0 health, 1 Divinity,
    else ammo, as PickupSetup's own switch) before it is drawn."""
    for n in ('SunBase', 'SunStep'):
        var(DIRECTOR, n, 'float', True)
    for n, k in (('LitMask', 'int'), ('Lit', 'bool'), ('SunNow', 'float'), ('SunFull', 'float'), ('PickCount', 'int')):
        var(DIRECTOR, n, k)
    for name in ('Arrive', 'Spine', 'SpineThirds'):
        shell(DIRECTOR, name)
    pylon = lambda k: HAS('flags', '",pylon%d,"' % k)
    fn(DIRECTOR, 'Arrive', """(fn Arrive ()
  """ + PHYSIS + """    (:then
      (if (not """ + HAS(FLAGS, '",conclave,"') + """)
        (Class|BPPhysis|PhysisGive :self physis :Token ",conclave,"))
      (if (not """ + HAS(FLAGS, '",at_conclave,"') + """)
        (Class|BPPhysis|PhysisGive :self physis :Token ",at_conclave,"))
      (if (and """ + EMPTY('(Class|BPPhysis|GetObjective :self physis)') + ' (not ' + HAS(FLAGS, '",kairos,"') + """))
        (Class|BPPhysis|PhysisQuest :self physis :Goal """ + lit(QUEST_ARRIVE) + """))
      (if (not """ + HAS(FLAGS, '",conclave_seen,"') + """)
        (Class|BPPhysis|PhysisGive :self physis :Token ",conclave_seen,")
        (Class|BPPhysis|PhysisSay :self physis :Message """ + lit(lore.MESSAGES['arrive']) + """)
        (Class|BPPhysis|PhysisNarrate :self physis :Title """ + lit(lore.ARRIVAL_LINE[0]) + """)))
    (:CastFailed)))""")
    # The three pylons all stand along the middle third, and their beams lean across y only, so the thirds light in
    # the order the beams strike them: the first pylon relit (whichever) lights the middle third, the second the
    # south, the third the north. Each PylonBeamN shows with its own pylon. (Review, 2026-11-07.)
    need = {1: 2, 2: 1, 3: 3}
    thirds = ''.join("""
      (bind lit%d (>= relit %d))
      (for shown%d (Actor|GetAllActorswithTag :Tag "SpineLit%d")
        (Rendering|SetActorHiddenInGame :self shown%d :bNewHidden (not lit%d)))
      (for dimmed%d (Actor|GetAllActorswithTag :Tag "SpineDim%d")
        (Rendering|SetActorHiddenInGame :self dimmed%d :bNewHidden lit%d))
      (for beam%d (Actor|GetAllActorswithTag :Tag "PylonBeam%d")
        (Rendering|SetActorHiddenInGame :self beam%d :bNewHidden (not %s)))""" % ((k, need[k]) + (k,) * 11 + (pylon(k),)) for k in (1, 2, 3))
    relit = '(+ (select %s 1 0) (+ (select %s 1 0) (select %s 1 0)))' % (pylon(1), pylon(2), pylon(3))
    fn(DIRECTOR, 'SpineThirds', """(fn SpineThirds ()
  """ + PHYSIS + """    (:then
      (bind flags """ + FLAGS + """)
      (bind relit """ + relit + """)""" + thirds + """)
    (:CastFailed)))""")
    base, step, full, now = ('(Variables|Default|Get%s)' % n for n in ('SunBase', 'SunStep', 'SunFull', 'SunNow'))
    goal = '(select (> (+ %s %s) 0.0) (+ %s (* %s count)) (* %s (+ 0.25 (* 0.25 count))))' % (base, step, base, step, full)
    fn(DIRECTOR, 'Spine', """(fn Spine ()
  """ + PHYSIS + """    (:then
      (bind flags """ + FLAGS + """)
      (bind one """ + pylon(1) + """)
      (bind two """ + pylon(2) + """)
      (bind three """ + pylon(3) + """)
      (bind mask (+ (select one 1 0) (+ (select two 2 0) (select three 4 0))))
      (bind count (+ (select one 1.0 0.0) (+ (select two 1.0 0.0) (select three 1.0 0.0))))
      (if (or (not (Variables|Default|GetLit)) (not (== mask (Variables|Default|GetLitMask))))
        (if (and (Variables|Default|GetLit) (> mask (Variables|Default|GetLitMask)))
          """ + snd(CA + 'S_SpineWake') + """)
        (Variables|Default|SetLit true)
        (Variables|Default|SetLitMask mask)
        (CallFunction|SpineThirds))
      (Variables|Default|SetPickCount -1)
      (for sun (Actor|GetAllActorswithTag :Tag "SpineSun")
        (for part (Actor|GetComponentsByClass :self sun :ComponentClass "/Script/Engine.LightComponent")
          (bind light (Utilities|Casting|CastToLightComponent :Object part)
            (:then
              (if (<= """ + full + """ 0.0)
                (Variables|Default|SetSunFull (Class|LightComponentBase|GetIntensity :self light))))
            (:CastFailed))))
      (bind goal """ + goal + """)
      (if (> goal 0.0)
        (Variables|Default|SetSunNow (select (<= """ + now + """ 0.0) goal (+ """ + now + """ (* (- goal """ + now + """) 0.3))))
        (for lamp (Actor|GetAllActorswithTag :Tag "SpineSun")
          (for piece (Actor|GetComponentsByClass :self lamp :ComponentClass "/Script/Engine.LightComponent")
            (bind beam (Utilities|Casting|CastToLightComponent :Object piece)
              (:then
                (Rendering|Components|Light|SetIntensity :self beam :NewIntensity """ + now + """))
              (:CastFailed))))))
    (:CastFailed)))""")
    mesh = lambda name: '"%s%s.%s"' % (CM, name, name)
    events(DIRECTOR, """(event EventBeginPlay
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Arrive" :Time 0.5 :bLooping false)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Spine" :Time 0.25 :bLooping true))

(event EventTick (DeltaSeconds)
  (if (not (Variables|Default|GetLit))
    (CallFunction|Spine))
  (bind picks (Actor|GetAllActorsOfClass :ActorClass "%sBP_Pickup.BP_Pickup_C"))
  (if (not (== (Utilities|Array|Length picks) (Variables|Default|GetPickCount)))
    (Variables|Default|SetPickCount (Utilities|Array|Length picks))
    (for found picks
      (bind pick (Utilities|Casting|CastToBP_Pickup :Object found)
        (:then
          (bind kind (Class|BPPickup|GetKind :self pick))
          (if (== kind 0)
            (Components|StaticMesh|SetStaticMesh :self (Class|BPPickup|GetShape :self pick) :NewMesh %s))
          (if (== kind 1)
            (Components|StaticMesh|SetStaticMesh :self (Class|BPPickup|GetShape :self pick) :NewMesh %s))
          (if (or (< kind 0) (> kind 1))
            (Components|StaticMesh|SetStaticMesh :self (Class|BPPickup|GetShape :self pick) :NewMesh %s)))
        (:CastFailed)))))""" % (B, mesh('SM_CN_PickupHealth'), mesh('SM_CN_PickupDivinity'), mesh('SM_CN_PickupAmmo')), 'director')
    comp(DIRECTOR)


# ---------------------------------------------------------------- BP_LightTrail

def trail():
    """Light Step's streak: PhysisLightStepGo spawns it along the step (engine cylinder, local z along the step, scale z
    = length / 1 m). It fades over 0.35 s: CustomPrimitiveData 0 goes 1 to 0 for M_CNLightTrail (as M_SettleWave reads
    it), and the streak thins to nothing, which hides it even if the material ignores the data."""
    for n in ('Age', 'Width', 'Length'):
        var(TRAIL, n, 'float')
    events(TRAIL, """(event EventBeginPlay
  (bind placed (Transformation|GetActorTransform))
  (Variables|Default|SetWidth (.x (.scale placed)))
  (Variables|Default|SetLength (.z (.scale placed)))
  (Collision|SetCollisionEnabled :self (Variables|Default|GetShape) :NewType "NoCollision"))

(event EventTick (DeltaSeconds)
  (Variables|Default|SetAge (+ (Variables|Default|GetAge) DeltaSeconds))
  (bind fade (select (< (Variables|Default|GetAge) 0.35) (- 1.0 (/ (Variables|Default|GetAge) 0.35)) 0.0))
  (Rendering|Material|SetCustomPrimitiveDataFloat :self (Variables|Default|GetShape) :DataIndex 0 :Value fade)
  (Transformation|SetActorScale3D :NewScale3D (Math|Vector|MakeVector :X (* (Variables|Default|GetWidth) fade) :Y (* (Variables|Default|GetWidth) fade) :Z (Variables|Default|GetLength)))
  (if (>= (Variables|Default|GetAge) 0.35)
    (Actor|DestroyActor)))""", 'trail')
    comp(TRAIL)


# ---------------------------------------------------------------- BP_Physis

def physis_shells():
    """Variables and empty functions first: BP_NPC and BP_Current call them, and PhysisInteract calls BP_NPC's."""
    var(P, 'Talking', 'bool')
    for n in ('StepReady', 'StepEnd', 'StepGravity', 'TalkEndAt', 'TalkHudAt'):
        var(P, n, 'float')
    var(P, 'StepDir', 'vector')
    for name in ('PhysisLightStep', 'PhysisLightStepGo', 'PhysisLightStepEnd', 'PhysisToConclave', 'PhysisConclaveHome'):
        shell(P, name)
    comp(P)


def physis():
    has = lambda tok: HAS('(Variables|Default|GetFlags)', tok)
    # Light Step (X / LB): no Divinity cost, 0.9 s between steps. PhysisUsedAbility comes first and the launch 0.1 s
    # later, so a Light Lattice (BP_AbilitySocket) in reach has ticked open before she reaches it. She goes along her
    # movement input, or where she faces.
    fn(P, 'PhysisLightStep', """(fn PhysisLightStep ()
  (if (and (and (not (Variables|Default|GetCinematic)) (not (Variables|Default|GetPhysisDead))) (and (not (Variables|Default|GetTalking)) """ + has('",lightstep,"') + """))
    (if (> """ + NOW + """ (Variables|Default|GetStepReady))
      (Variables|Default|SetStepReady (+ """ + NOW + """ 0.9))
      (CallFunction|PhysisUsedAbility :Token ",lightstep,")
      (bind move (Pawn|Input|GetLastMovementInputVector))
      (bind ahead (Transformation|GetActorForwardVector))
      (bind w (select (> (Math|Vector|VectorLength (Math|Vector|MakeVector :X (.x move) :Y (.y move) :Z 0.0)) 0.1) 1.0 0.0))
      (Variables|Default|SetStepDir (Math|Vector|Normalize (Math|Vector|MakeVector :X (+ (* (.x move) w) (* (.x ahead) (- 1.0 w))) :Y (+ (* (.y move) w) (* (.y ahead) (- 1.0 w))) :Z 0.0)))
      (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisLightStepGo" :Time 0.1 :bLooping false))))""")
    # The step: 4800 cm/s for 0.15 s (about 7 m), gravity off, out of reach of hits for 0.35 s, and hidden: she is the
    # streak (BP_LightTrail, cut short where a trace meets a wall) for that moment.
    trace = ('(Collision|LineTraceByChannel :Start start :End (+ start (* dir 720.0)) :TraceChannel "Visibility" :bTraceComplex false '
             ':DrawDebugType "None" :bIgnoreSelf true)')
    streak = ('(Game|SpawnActorfromClass :Class "%sBP_LightTrail.BP_LightTrail_C" :SpawnTransform (Math|Transform|MakeTransform '
              ':Location (+ start (* dir (* reach 0.5))) :Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch -90.0 :Yaw (Math|Trig|Atan2(Degrees) :Y (.y dir) :X (.x dir))) '
              ':Scale (Math|Vector|MakeVector :X 0.32 :Y 0.32 :Z (/ reach 100.0))) :CollisionHandlingOverride "AlwaysSpawn")') % B
    safe = '(+ %s 0.35)' % NOW
    fn(P, 'PhysisLightStepGo', """(fn PhysisLightStepGo ()
  (if (and (not (Variables|Default|GetPhysisDead)) (and (not (Variables|Default|GetTalking)) (not (Variables|Default|GetCinematic))))
    (bind cmc (Variables|Character|GetCharacterMovement))
    (if (> (Class|CharacterMovementComponent|GetGravityScale :self cmc) 0.0)
      (Variables|Default|SetStepGravity (Class|CharacterMovementComponent|GetGravityScale :self cmc)))
    (bind start (Transformation|GetActorLocation))
    (bind dir (Variables|Default|GetStepDir))
    (bind (ray hit) """ + trace + """)
    (bind (blocking overlap time dist where impact) (Collision|BreakHitResult ray))
    (bind reach (select hit (select (> dist 60.0) dist 60.0) 720.0))
    """ + streak + """
    (Class|CharacterMovementComponent|SetGravityScale :self cmc :GravityScale 0.0)
    (Variables|Default|SetSafeUntil (select (> (Variables|Default|GetSafeUntil) """ + safe + """) (Variables|Default|GetSafeUntil) """ + safe + """))
    (Variables|Default|SetStepEnd (+ """ + NOW + """ 0.15))
    (Character|LaunchCharacter :LaunchVelocity (* dir 4800.0) :bXYOverride true :bZOverride true)
    (Rendering|SetActorHiddenInGame :bNewHidden true)
    """ + snd(CA + 'S_LightStep') + """
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisLightStepEnd" :Time 0.15 :bLooping false)))""")
    # StepEnd marks a step in flight, so the end runs once: her own gravity back (1.0 if none was read) and 600 cm/s at most.
    fn(P, 'PhysisLightStepEnd', """(fn PhysisLightStepEnd ()
  (if (> (Variables|Default|GetStepEnd) 0.0)
    (Variables|Default|SetStepEnd 0.0)
    (bind cmc (Variables|Character|GetCharacterMovement))
    (Class|CharacterMovementComponent|SetGravityScale :self cmc :GravityScale (select (> (Variables|Default|GetStepGravity) 0.0) (Variables|Default|GetStepGravity) 1.0))
    (Class|MovementComponent|SetVelocity :self cmc :Velocity (Math|Vector|ClampVectorSize :A (Class|MovementComponent|GetVelocity :self cmc) :Min 0.0 :Max 600.0))
    (Rendering|SetActorHiddenInGame :bNewHidden false)))""")
    # The temple's current (BP_Current Dest 1, Need ,mend,). No objective is set here: she lands on the Wellspring Still
    # Point, whose objective takes the Center's last one to Completed (one set here would be marked Completed at once);
    # return trips keep the quest in hand. ,trip, has BP_Current move her onto the scenario's arrival spot after the
    # load. The save makes the Conclave load at the Wellspring (PhysisLoadGame and MenuContinue pick L_Conclave by
    # ,at_conclave,); the options stay exactly "nocine,load".
    fn(P, 'PhysisToConclave', """(fn PhysisToConclave ()
  (if (not """ + has('",conclave,"') + """)
    (CallFunction|PhysisGive :Token ",conclave,"))
  (if (not """ + has('",at_conclave,"') + """)
    (CallFunction|PhysisGive :Token ",at_conclave,"))
  (CallFunction|PhysisGive :Token ",trip,")
  (CallFunction|PhysisCheckpoint :X %.1f :Y %.1f :Z %.1f)
  (CallFunction|PhysisSaveGame)
  (Game|OpenLevel(byName) :LevelName "L_Conclave" :Options "nocine,load"))""" % ARRIVE_CM)
    # The Wellspring's current (Dest 2): ,at_conclave, goes before the save, so saves now load the Center, in its sanctum.
    fn(P, 'PhysisConclaveHome', """(fn PhysisConclaveHome ()
  (Variables|Default|SetFlags (Utilities|String|Replace :SourceString (Variables|Default|GetFlags) :From ",at_conclave," :To "" :SearchCase "CaseSensitive"))
  (CallFunction|PhysisGive :Token ",trip,")
  (CallFunction|PhysisCheckpoint :X %.1f :Y %.1f :Z %.1f)
  (CallFunction|PhysisSaveGame)
  (Game|OpenLevel(byName) :LevelName "L_CenterOfTheUniverse" :Options "nocine,load"))""" % HOME_CM)
    # PhysisInteract with people first is a station graph the station's rebuild rewrites, so it is center_overrides.py
    # part conclave (one source); run here once BP_NPC has its talk, so this script alone leaves a working Interact.
    conclave_done = co.conclave()
    # Part conclave makes BP_Switch.Reach when it is missing, and PhysisInteract reads it: save BP_Switch before BP_Physis,
    # or a later launch would load an Interact that reads a variable its unsaved owner never kept (review, 2026-11-07).
    if co.SWITCH not in TOUCHED:
        TOUCHED.insert(TOUCHED.index(P) if P in TOUCHED else len(TOUCHED), co.SWITCH)
    if not conclave_done:
        FAILED.append('PhysisInteract (BP_NPC has no TalkStart: the npc part failed)')
    elif 'PhysisInteract' in co.FAILED:
        FAILED.append('PhysisInteract')
        BROKEN.add(P)
    comp(P)


# ---------------------------------------------------------------- input

def wire():
    """center_logic.wire(): IA_LightStep's Started event calls PhysisLightStep (IA_LightStep and its X / LB mappings
    come from conclave:blueprints)."""
    if DRY:
        print('--- wire IA_LightStep Started -> CallFunction|PhysisLightStep in %s:EventGraph (unless already wired)' % P)
        return
    G = {'refPath': P + ':EventGraph'}

    def j(tool, args):
        r = call(tool, args)
        return json.loads(r)['returnValue'] if r else None

    def pin(n, name, side):
        return next(p for p in j('get_node_infos', {'nodes': [n]})[0][side] if p['name'] == name)
    y = 9900
    for action, function in (('IA_LightStep', 'PhysisLightStep'),):
        found = j('find_nodes', {'graph': G, 'title': action}) or []
        if any('EnhancedInputAction' in json.dumps(n) for n in found):
            print(action, 'already wired')
            continue
        event = j('create_node', {'graph': G, 'type_id': 'Input|EnhancedActionEvents|' + action, 'pos': {'x': -400, 'y': y}})
        target = j('create_node', {'graph': G, 'type_id': 'CallFunction|' + function, 'pos': {'x': 0, 'y': y}})
        if not (event and target):
            print(action, 'FAILED: is', action, 'made (conclave:blueprints)?')
            FAILED.append('wire ' + action)
            continue
        call('connect_pins', {'output_pin': pin(event, 'Started', 'output_pins')['pin_id'], 'input_pin': pin(target, 'execute', 'input_pins')['pin_id']})
        print(action, 'wired')
        y += 250
    comp(P)


if __name__ == '__main__':
    parts = ARGS or ['npc', 'current', 'director', 'trail', 'physis', 'input']
    print('Conclave arrival %s cm (%s), Center arrival %s cm' % (ARRIVE_CM, 'height grid' if _ground is not None else 'no height grid yet: 8 m floor', HOME_CM))
    # BP_Physis's variables and empty functions first (BP_NPC sets Talking, BP_Current calls the travel functions),
    # BP_NPC before PhysisInteract (which calls TalkStart), BP_LightTrail before PhysisLightStepGo (which spawns it).
    if any(p in parts for p in ('npc', 'current', 'physis')):
        physis_shells()
    if 'npc' in parts:
        npc()
    if 'current' in parts:
        current()
    if 'director' in parts:
        director()
    if 'trail' in parts:
        trail()
    if 'physis' in parts:
        physis()
    if 'input' in parts:
        wire()
    for bp in TOUCHED:
        save(bp)
    print('FAILED:', FAILED or 'none')
