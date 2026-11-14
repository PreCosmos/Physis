"""Center overrides of Blueprint graphs shared with the Battle Station. Run from the project folder, after
every other logic script (the station's rebuild runs it last, through center_music.py):
    python3 Tools/blueprint_logic/center_overrides.py

Each graph here is written whole. Station branches keep the station's own logic; Center branches are
chosen by whether the level holds a BP_Awakening actor (L_CenterOfTheUniverse does, and so does L_Conclave,
which the shared graphs treat as an open-world level like the Center). Conclave branches come first where
the Conclave differs (music, map) and are chosen by a BP_ConclaveDirector, which only L_Conclave holds; saves
pick L_Conclave by the ,at_conclave, flag (Tools/conclave/README.md). Counting actors is the test, because a
bare Utilities|IsValid inside an expression compiles as the branching macro and silently drops the rest of
the graph. Conclave branches and part conclave are only written once the Conclave's Blueprints exist (built()):
this file runs in every station and Center rebuild, and a graph naming a class or asset that is not there yet
can fail its whole write. Read every graph back after changing it.

The Conclave (Tools/conclave/README.md, "Run order", step 4): conclave_logic.py, which runs part conclave itself
once BP_NPC has its talk; then the parts music saves menu progress conclave; then, in a FRESH editor as its first
write, conclave_hud.py: the one HUD batch of that launch, PageMap and DrawInteract from here (map_page_code,
draw_interact_code) with DrawTalk and its helpers, so part map does not run in that launch. Since 2026-11-09 a
station rebuild (rebuild2.sh) no longer writes PhysisInteract (scenario_bp.py) or DrawInteract (feat.py) over the
Conclave's, nor any other graph this file owns: combat.py's helper head skips every graph in its CENTER_OWNED list.

Ownership: CENTER_OWNED in Tools/blueprint_logic/combat.py (kept by the station session, identical to its scratchpad
copy) must list every graph this file writes. When a part takes over another graph, add it there or tell the
station session.

BP_Physis
  PhysisMusic / PhysisMusicPick / PhysisMusicStop  the level's own score: S_Music_Conclave in the Conclave, the
      Center's orchestral piece in the Center
  PhysisCinemaStart / PhysisCenterStart / PhysisCenterPrepare  first frame of a level; the Center lets
      BP_Awakening.Prepare set it up (it must never run PhysisCinemaCleanup, which destroys the CineOnly
      stand-in); a station save made in the hand-off window is carried on to the Center
  PhysisRestart      death in the Center returns to the last Still Point, not the station's Breach Deck
  PhysisScanShow     a scan finishing while she is dead no longer pauses the game (a soft-lock)
  PhysisSaveGame     no save in the 8 s between the station's final terminal and the Center; a save keeps her exact
      spot, facing and camera (BP_PhysisSave SpotWorld/SpotX/Y/Z/SpotYaw/ViewYaw/ViewPitch) when it is safe
  PhysisRestore      a Center load keeps cleared encounters cleared and only visited Still Points used; a load
      puts her at the save's spot when SpotWorld is this level (else, and after a death, the checkpoint)
  PhysisClearRoom    removes an encounter's enemies (used by PhysisRestore)
  PhysisFinish       the station's last quest is recorded as completed; 8 s later PhysisToCenter (Swift at 4 s)
  PhysisLoadGame     a save holding ,at_conclave, loads into the Conclave, else one holding ,center, into the Center
  PhysisFidelity     stage 1 after the boss, stage 2 after Settle or in the Conclave, stage 3 after Light Step
BP_Checkpoint EventTick (part saves)  in the Center each Still Point records itself in the flags (,sp_<x>_<y>,) when
      reached, and restores her health whenever she stands in it with no enemy within 25 m. A first visit sets the
      Still Point's objective only while Flags lack its Until token: Center ,mend, (the Sanctum's ,sanctum,), Conclave
      ,shepherd,, station none. In an open-world level a Still Point she has used moves her checkpoint whenever she
      stands in it again.
BP_Encounter EventTick   a won fight with no next goal leaves the current quest alone (it used to blank it); FightLine
      shows "<Goal>: N left" as the objective inside an encounter's Radius (Goal '' does nothing)
BP_ScanTarget VisorMeasure  a target is in view if its tag or the creature carrying it is, with a 0.3 s grace
BP_ScanTarget VisorApply / TagSetup, BP_Physis PhysisAddLog / PhysisScanKnown / PhysisScanCount / PhysisVisorToggle
      (part scans, the station's since 2026-11-08): exact '^Title^' Logbook keys, a finished scan greys every tag of
      its kind, SCANS X / Y counts kinds; runtime tags set themselves up with TagSetup
BP_Pickup PickupSetup / EventGraph (part items, the station's since 2026-11-08)  every pickup carries its own tag
BP_PhysisHUD DrawVisor (part visor, explicit only: a HUD write)  the station's (hudfont.py) with the kind counter
BP_TrainingDrone DroneThink (the station's dronefix.py since 2026-11-08)  EnemyKind 1-4 (tank, ward, fast, front
      immune); unseen enemies stop at their band; in open levels the band is flat and the height band is gone; every
      move, turn and timer steps at most 0.05 s a frame, so a long frame slows drones instead of sinking them
BP_TrainingDrone DroneStuckCheck / DroneHover / DroneArena  in the Center an enemy's crystal is its collider against
      the ground: it is held above the terrain and the water instead of being destroyed by the station's stuck rules;
      arena enemies (ArenaOut > 0, the temple's) are kept in their ring and sent home when stuck
BP_TrainingDrone DroneSeparate / DroneSeparateAll / DroneSeparateCenter  the station's separation, run 5 times a
      second and only near her in the Center, never moving Static locks and prisms there; bumps cost no health
BP_TrainingDrone TakeHit / DroneArmour / DroneDrop / DroneDropOne  the station's death drop at z 125 in the station;
      in the Center the loot rests on the ground under the enemy and grows with its level; each kind's armour; since
      2026-11-09 whether an enemy drops anything is a roll (station 60%; Center L1 50% up to L5 always)
BP_Switch UseSwitch (part switches, the station's scenario_bp.py's since 2026-11-09)  an optional second requirement,
      NeedB, refused with DeniedB: the Heartbloom pedestal also needs ,settle,
PhysisHurt (Time pin only)  she respawns as soon as her death fall lands, 1.8 s instead of 3.5 s
BP_MenuHUD DrawMenu / MenuContinue  a Continue row on the main menu when a save exists (into the save's level)
Augmentations (part augments; tokens in AUGMENTS, the Center's vaults and the Conclave's people and crown,
values set every frame by PhysisFidelity):
  PhysisStrikeNow    katana damage x KatanaPower        PhysisShotHit     gun damage x PistolPower
      (both tell the enemy the blow's raw strength, HitPower; the sword reaches tall open-level enemies by bounds)
  PhysisHurt         a hit costs HurtTaken, not 1.0     PhysisBlock       the perfect-parry window is ParryTime
      (a Perfect Parry staggers every enemy kind within 4.2 m)
  PhysisThreatCheck  B parries from as far as the longer window allows
BP_Physis PhysisMenu (part map)  pause.py's menu toggle; a scan result showing when the menu opens is closed first
BP_PhysisHUD DrawPauseMenu / PageMap / MapMark (part map)  the pause menu, ported whole from the station's pause.py with a
      fifth tab, Map (page 4): the level's map (the Conclave's or the Center's, same frame), Physis, the Still Points
      and every Divinity Ray's site; M or View (IA_Map -> BP_Physis.PhysisMap, center_logic.py) opens it. Station edits
      to DrawPauseMenu belong here now.
BP_Physis PhysisInteract (part conclave)  the station's Interact (the cinematic first, then doors, switches and the
      fallback) with the Conclave's people before the doors: a shown BP_NPC in talk range starts a conversation, and
      nothing else runs on that press. A switch is in reach within its BP_Switch Reach (made by this part; the
      Heartbloom pedestal's 450), else 260.
BP_PhysisHUD DrawInteract (draw_interact_code, written by conclave_hud.py)  feat.py's "E  Use" icons and scan hint, plus
      "E  Talk" over a person in talk range, and DrawTalk last. Switch icons use the same reach as PhysisInteract.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
sys.path.insert(0, str(ROOT / 'Content/Python'))
import physis_conclave_plan as conclave_plan  # noqa: E402
from unreal_mcp import UnrealMCP  # noqa: E402

c = UnrealMCP(timeout=600)
c.initialize()
T = 'editor_toolset.toolsets.blueprint.BlueprintTools'
B = '/Game/Characters/Physis/Blueprints/'
P = B + 'BP_Physis.BP_Physis'
CK = B + 'BP_Checkpoint.BP_Checkpoint'
ST = B + 'BP_ScanTarget.BP_ScanTarget'
EN = B + 'BP_Encounter.BP_Encounter'
DR = B + 'BP_TrainingDrone.BP_TrainingDrone'
MENU = B + 'BP_MenuHUD.BP_MenuHUD'
AWAKENING = '"%sBP_Awakening.BP_Awakening_C"' % B
CONCLAVE = '"%sBP_ConclaveDirector.BP_ConclaveDirector_C"' % B
DIRECTOR = B + 'BP_ConclaveDirector.BP_ConclaveDirector'
SWITCH = B + 'BP_Switch.BP_Switch'
NPC = B + 'BP_NPC.BP_NPC'
NPC_CLASS = '"%sBP_NPC.BP_NPC_C"' % B
DRONE = '"%sBP_TrainingDrone.BP_TrainingDrone_C"' % B
SAVE_CLASS = '"%sBP_PhysisSave.BP_PhysisSave_C"' % B
SAVE_BP = B + 'BP_PhysisSave.BP_PhysisSave'
PLATFORM = '"%sBP_Platform.BP_Platform_C"' % B
BARRIER = '"%sBP_SettleBarrier.BP_SettleBarrier_C"' % B
TARGETS = '"%sBP_ScanTarget.BP_ScanTarget_C"' % B
PICK = B + 'BP_Pickup.BP_Pickup'
FAILED = []
# Which level a save's spot belongs to: 3 the Conclave (its director), 2 the Center (its BP_Awakening; the Conclave
# holds one too, so the director is tested first), 1 the station. 0 in a save means no spot (an old save, or one made
# mid-air or near a moving platform).
WORLD = ('(select (> (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass %s)) 0) 3 (select (> (Utilities|Array|Length '
         '(Actor|GetAllActorsOfClass :ActorClass %s)) 0) 2 1))' % (CONCLAVE, AWAKENING))


def log_key(title):
    """LogData holds 'Category^Title^Body@' per entry, so '^Title^' matches one entry's title and nothing else. A bare
    title also matched inside longer titles and texts, so 'Shardling' never logged after 'Shardling Matriarch', and tags
    turned grey after a load without being scanned (review, 2026-11-08)."""
    return '(Utilities|String|Append :A "^" :B (Utilities|String|Append :A %s :B "^"))' % title


def wrap_text(text, width=62):
    """physis_aaa_tools.wrap_text (that module needs the editor): HUD lines joined with ~."""
    lines, line, count = [], [], 0
    for word in text.split(' '):
        size = 3 if word.startswith('|') and word.endswith('|') else len(word)
        if count and count + 1 + size > width:
            lines.append(' '.join(line))
            line, count = [], 0
        line.append(word)
        count += size + (1 if count else 0)
    lines.append(' '.join(line))
    return '~'.join(lines)


def literal(text):
    """A DSL string literal (the parser reads \\" and \\\\)."""
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"')

# Saved game fields, as the station's pause.py saves and restores them.
FIELDS = ('Flags', 'Objective', 'LogData', 'QuestDone', 'Fuses', 'SkillLevel', 'SeqStep', 'PhysisHealth', 'Divinity',
          'GunAmmo', 'GunReserve', 'CheckX', 'CheckY', 'CheckZ', 'LevelTime')
PUT = '\n          '.join('(Class|BPPhysisSave|Set%s :self saved :%s (Variables|Default|Get%s))' % (n, n, n) for n in FIELDS)
GET = '\n      '.join('(Variables|Default|Set%s (Class|BPPhysisSave|Get%s :self saved))' % (n, n) for n in FIELDS)
OPTIONS = '(Class|GameModeBase|GetOptionsString (Game|GetGameMode))'


def still_key(where):
    """A Center Still Point's flag token, ,sp_<x>_<y>, in whole metres of its location. Its object name would
    change whenever the scenario re-spawns the Still Points, which would orphan every saved token."""
    metres = lambda axis: '(Utilities|String|ToString(Integer) (Math|Float|Truncate (/ (.%s %s) 100.0)))' % (axis, where)
    return '(Utilities|String|Append :A ",sp_" :B (Utilities|String|Append :A %s :B (Utilities|String|Append :A "_" :B (Utilities|String|Append :A %s :B ","))))' % (metres('x'), metres('y'))


def call(tool, args, quiet=False):
    r = c.call('call_tool', {'toolset_name': T, 'tool_name': tool, 'arguments': args})
    text = r['content'][0]['text']
    if r.get('isError'):
        if not quiet:
            print('ERR', tool, text[:700])
        return None
    return text


def graph(bp, name, params=()):
    call('add_function_graph', {'blueprint': {'refPath': bp}, 'graph_name': name}, True)
    for pname, ptype in params:
        call('add_function_param', {'graph': {'refPath': bp + ':' + name}, 'param_name': pname, 'param_type': ptype, 'input_param': True}, True)


def var(bp, name, kind, edit=False):
    """Adds a member variable unless the Blueprint already has it, and returns whether it did. add_variable on a name in
    use adds a numbered copy (Until_0, Until_1, ...: FindUniqueKismetName), which is how BP_Physis gathered hundreds of
    unused copies (review, 2026-11-07). set_variable_instance_editable marks the Blueprint changed on every call, so it
    runs only for a new variable. edit makes it instance editable, so a scenario can set it on placed actors."""
    have = call('list_variables', {'blueprint': {'refPath': bp}}, True)
    names = (json.loads(have).get('returnValue') or []) if have else []
    if name in names:
        return False
    call('add_variable', {'blueprint': {'refPath': bp}, 'name': name, 'type_name': kind}, True)
    if edit:
        call('set_variable_instance_editable', {'blueprint': {'refPath': bp}, 'variable_name': name, 'instance_editable': True}, True)
    return True


def fn(bp, name, code):
    ok = call('write_graph_dsl', {'graph': {'refPath': bp + ':' + name}, 'code': code})
    print(name, 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        FAILED.append(name)
    else:
        prune(bp, name)


def prune(bp, graph_name):
    """After a write: remove the dead nodes write_graph_dsl leaves behind (Content/Python/physis_graph_prune.py, op
    center:prune). Otherwise every rewrite keeps the previous version alive through the entry's parameter pins (89% of
    all nodes on 2026-11-07, when BP_PhysisHUD was 129 MB instead of 12). A changed live DSL is a failure: do not
    save then. A dry run (stand-in client) only notes it. conclave_hud.py and part conclave write through here;
    conclave_logic.py's own fn()/events(), center_logic.py's and the station's combat.py need the same step."""
    try:
        r = c.call('call_tool', {'toolset_name': 'physis_character_tools.PhysisCharacterTools', 'tool_name': 'outfit_operation',
                                 'arguments': {'operation': 'center:prune:%s:%s' % (bp, graph_name)}})
    except Exception as error:  # noqa: BLE001  (dry runs: the stand-in client has no editor)
        print('--- prune %s:%s (%s)' % (bp.split('.')[-1], graph_name, str(error)[:60]), flush=True)
        return
    text = r['content'][0]['text'] if r.get('content') else ''
    try:
        row = json.loads(json.loads(text)['returnValue'])
    except (ValueError, KeyError, TypeError):
        row = None
    if r.get('isError') or not row or not row.get('same'):
        print(graph_name, 'PRUNE FAILED', text[:300], flush=True)
        FAILED.append('prune ' + graph_name)
    elif row.get('removed'):
        print(graph_name, 'pruned', row['removed'], 'dead nodes', flush=True)


def comp(bp):
    call('compile_blueprint', {'blueprint': {'refPath': bp}})


BUILT = {}


def built(bp, member=None):
    """Whether a Conclave Blueprint exists (with the function member, when one is named). Conclave branches only name
    the Conclave's classes and assets once conclave:blueprints (after conclave:audio and conclave:map_art) and
    conclave_logic.py have made them: center_music.py runs every part in the station's and the Center's rebuilds, and
    a graph naming a class or asset that is not there yet can fail its whole write. A dry run counts as built."""
    if bp not in BUILT:
        found = call('list_functions', {'blueprint': {'refPath': bp}}, True)
        names = json.loads(found).get('returnValue') if found else None
        BUILT[bp] = (found is not None, None if names is None else {n.get('name') if isinstance(n, dict) else n for n in names})
    exists, names = BUILT[bp]
    return exists and (member is None or names is None or member in names)


def timer_seconds(graph_name, function, seconds):
    """Sets the Time pin of the Set Timer by Function Name node in graph_name that calls function."""
    found = call('find_nodes', {'graph': {'refPath': P + ':' + graph_name}, 'title': 'Set Timer by Function Name'})
    nodes = json.loads(found)['returnValue'] if found else []
    infos = json.loads(call('get_node_infos', {'nodes': nodes}))['returnValue'] if nodes else []
    done = 0
    for info in infos:
        pins = {pin['name']: pin for pin in info['input_pins']}
        if pins.get('FunctionName', {}).get('value') == function and 'Time' in pins:
            done += call('set_pin_value', {'pin': pins['Time']['pin_id'], 'value': '%g' % seconds}) is not None
    print('%s timer for %s' % (graph_name, function), '%g s' % seconds if done else 'FAILED', flush=True)
    if not done:
        FAILED.append(graph_name + ' timer')


# ---------------------------------------------------------------- music

def music():
    graph(P, 'PhysisMusicPick')
    graph(P, 'PhysisMusicStop')
    # The awakening cinematic has its own score: BP_Awakening silences the level music while it plays.
    fn(P, 'PhysisMusicStop', """(fn PhysisMusicStop ()
  (Utilities|IsValid (Variables|Default|GetMusicComp)
    (:"Is Valid"
      (Audio|Components|Audio|Stop (Variables|Default|GetMusicComp)))))""")
    # The Center's and the station's score, chosen by BP_Awakening as before the Conclave.
    center = """(Utilities|IsValid (Actor|GetActorOfClass %s)
    (:"Is Valid"
      (Variables|Default|SetMusicComp (Audio|SpawnSound2D "/Game/Center/Audio/S_Music_Center.S_Music_Center" (* 0.1 (Variables|Default|GetMusicVol)))))
    (:"Is Not Valid"
      (Variables|Default|SetMusicComp (Audio|SpawnSound2D "/Game/Audio/S_Music_Combat.S_Music_Combat" (* 0.1 (Variables|Default|GetMusicVol))))))""" % AWAKENING
    if built(DIRECTOR):
        # The Conclave first: it holds a BP_Awakening too.
        fn(P, 'PhysisMusicPick', """(fn PhysisMusicPick ()
  (bind conclave (Actor|GetAllActorsOfClass :ActorClass %s))
  (if (> (Utilities|Array|Length conclave) 0)
    (Variables|Default|SetMusicComp (Audio|SpawnSound2D "/Game/Conclave/Audio/S_Music_Conclave.S_Music_Conclave" (* 0.1 (Variables|Default|GetMusicVol))))
    (else
      %s)))""" % (CONCLAVE, center.replace('\n', '\n    ')))
    else:
        fn(P, 'PhysisMusicPick', '(fn PhysisMusicPick ()\n  %s)' % center)
    # Called on every level start (PhysisCinemaCleanup) and by BP_Awakening.
    fn(P, 'PhysisMusic', """(fn PhysisMusic ()
  (Utilities|IsValid (Variables|Default|GetMusicComp)
    (:"Is Valid"
      (Audio|Components|Audio|Stop (Variables|Default|GetMusicComp))
      (CallFunction|PhysisMusicPick))
    (:"Is Not Valid"
      (CallFunction|PhysisMusicPick))))""")


# ---------------------------------------------------------------- level start

def start():
    graph(P, 'PhysisCenterStart')
    graph(P, 'PhysisCenterPrepare')
    fn(P, 'PhysisCenterPrepare', """(fn PhysisCenterPrepare ()
  (for director (Actor|GetAllActorsOfClass %s)
    (Class|BPAwakening|Prepare director)))""" % AWAKENING)
    # The Center's first frame: the director re-attaches enemy scan tags (BP_Awakening AttachTags), a save is
    # restored if the level was opened with "load", then the director prepares that frame (station clock off;
    # black hold and cinema HUD on an arrival, else no stand-in).
    fn(P, 'PhysisCenterStart', """(fn PhysisCenterStart ()
  (for director (Actor|GetAllActorsOfClass %s)
    (Class|BPAwakening|AttachTags director))
  (if (Utilities|String|Contains %s "load")
    (CallFunction|PhysisRestore)
    (CallFunction|PhysisCenterPrepare)
    (else
      (CallFunction|PhysisCenterPrepare))))""" % (AWAKENING, OPTIONS))
    # The station's opening (Theme music, the first level sequence it finds, a 40 s lockout) is for the
    # station only. A station save that holds ,end, but not ,center, was made in the hand-off window
    # (PhysisSaveGame now refuses that); loading one finishes the hand-off.
    fn(P, 'PhysisCinemaStart', """(fn PhysisCinemaStart ()
  (bind _returnvalue (Game|GetPlayerController 0))
  (CallFunction|PhysisSettingsLoad)
  (bind directors (Actor|GetAllActorsOfClass %s))
  (if (> (Utilities|Array|Length directors) 0)
    (CallFunction|PhysisCenterStart)
    (else
      (if (Utilities|String|Contains %s "nocine")
        (CallFunction|PhysisCinemaCleanup)
        (if (Utilities|String|Contains %s "load")
          (CallFunction|PhysisRestore)
          (if (and (Utilities|String|Contains (Variables|Default|GetFlags) ",end,") (not (Utilities|String|Contains (Variables|Default|GetFlags) ",center,")))
            (CallFunction|PhysisToCenter)))
        (else
          (Variables|Default|SetCinematic true)
          (Variables|Default|SetCinemaStartedAt (Utilities|Time|GetGameTimeInSeconds))
          (Input|SetIgnoreMoveInput _returnvalue true)
          (Input|SetIgnoreLookInput _returnvalue true)
          (bind _returnvalue_1 (Audio|SpawnSound2D "/Game/Audio/S_Music_Theme.S_Music_Theme" (* 0.075 (Variables|Default|GetMusicVol))))
          (Variables|Default|SetMusicComp _returnvalue_1)
          (bind _returnvalue_2 (Actor|GetActorOfClass "/Script/LevelSequence.LevelSequenceActor"))
          (Sequencer|Player|Play (Class|LevelSequenceActor|GetSequencePlayer _returnvalue_2))
          (Utilities|Time|SetTimerbyFunctionName self "PhysisCinemaEnd" 40.0))))))""" % (AWAKENING, OPTIONS, OPTIONS))


# ---------------------------------------------------------------- death

def death():
    # Death: back to the last checkpoint. The station's is the Breach Deck; in the Center it is the last
    # Still Point she reached (CheckX/Y/Z: the wake spot until then). The Center does not re-arm its
    # Still Points, which would replay their objectives. A held scan or lock is released (PhysisScanRelease
    # also drops the lock target), so neither carries on after she rises.
    fn(P, 'PhysisRestart', """(fn PhysisRestart ()
  (bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))
  (Animation|Montage|MontageStop :self anim :InBlendOutTime 0.2)
  (Utilities|Time|SetGlobalTimeDilation :TimeDilation 1.0)
  (Variables|Default|SetPhysisDead false)
  (Variables|Default|SetPhysisHealth (select (> (Variables|Default|GetMaxHealth) 0.0) (Variables|Default|GetMaxHealth) 10.0))
  (Variables|Default|SetSafeUntil (+ (Utilities|Time|GetGameTimeinSeconds) 2.0))
  (CallFunction|PhysisScanRelease)
  (bind directors (Actor|GetAllActorsOfClass :ActorClass %s))
  (if (> (Utilities|Array|Length directors) 0)
    (Transformation|SetActorLocation :NewLocation (Math|Vector|MakeVector :X (Variables|Default|GetCheckX) :Y (Variables|Default|GetCheckY) :Z (Variables|Default|GetCheckZ)) :bSweep false :bTeleport true)
    (Input|EnableInput :PlayerController (Game|GetPlayerController 0))
    (CallFunction|PhysisSay :Message "Your strength gave out. Divinity carried you back to the last Still Point.~Your progress is kept.")
    (else
      (Transformation|SetActorLocation :NewLocation (Math|Vector|MakeVector :X 300.0 :Y 0.0 :Z 110.0) :bSweep false :bTeleport true)
      (CallFunction|PhysisCheckpoint :X 300.0 :Y 0.0 :Z 110.0)
      (CallFunction|PhysisResetChecks)
      (Input|EnableInput :PlayerController (Game|GetPlayerController 0))
      (CallFunction|PhysisSay :Message "Your strength gave out. Divinity carried you back to the Life Checkpoint~at the Breach Deck. Your progress is kept."))))""" % AWAKENING)
    # A scan that completes during the 3.5 s before PhysisRestart used to pause the game while input was
    # disabled, so PhysisRestart never ran. Now its result panel is closed instead (only PhysisScan, from the
    # paused state, would close it otherwise).
    # She respawns as soon as she has fallen: AM_Physis_Dead (2.67 s) lands her on the ground at 1.7 s, and
    # the station waited 3.5 s. PhysisHurt is the station's combat graph, so only its timer's Time pin changes.
    timer_seconds('PhysisHurt', 'PhysisRestart', 1.8)
    fn(P, 'PhysisScanShow', """(fn PhysisScanShow ()
  (if (not (Variables|Default|GetPhysisDead))
    (Variables|Default|SetScanPaused true)
    (Game|SetGamePaused :bPaused true)
    (else
      (CallFunction|PhysisScanHide))))""")


# ---------------------------------------------------------------- saving and loading

# Where she stood when the game was saved (author, 2026-11-08: "Physis needs to respawn exactly where she saved when
# loading back"). Old saves lack these fields: SpotWorld then loads as 0 and the load keeps the checkpoint.
SPOT_FIELDS = (('SpotWorld', 'int'), ('SpotX', 'float'), ('SpotY', 'float'), ('SpotZ', 'float'), ('SpotYaw', 'float'),
               ('ViewYaw', 'float'), ('ViewPitch', 'float'))


# Logbook bodies from before a rewording, as a save's LogData holds them: a scan stores the tag's ScanText, wrapped at 62
# (wrap_text). PhysisRestore swaps each for the current text of the same entry, read from its lore module, so a later
# rewording needs only its old text added here. 2026-11-09: the Lantern Stele (lanterns moved and renamed), and the
# station session's AL Drone and Divinity Crystal (no automatic parry by default; drops are random).
OLD_STELE = ('A First One stele, its glyphs re-cut by human hands into survey numbers. It names the lanterns in the order of '
             'the dead they guided home: first the Rose lantern beneath the willows, then the Cyan lantern on the reed isle, '
             'last the Gold lantern under the great arch. Interact with each to light it, in that order.')
OLD_LOG_BODIES = (
    ('physis_center_lore', 'The Lantern Stele', OLD_STELE),
    ('physis_lore', 'AL Drone', 'A First One AL unit. It strafes around you, holds its range and fires a slow red plasma bolt. '
     'Before each attack it sparks and whooshes: that is your cue. Parry just before the hit lands to counter, or dodge clear. '
     'With Divinity to spare, Physis parries on her own. Six health. It drops Divinity when destroyed.'),
    ('physis_lore', 'Divinity Crystal', 'A shard of Divinity grown solid. Walk over it to add to the Divinity you carry, shown '
     'in the HUD. Spend Divinity at nodes to calm plasma or wake machines, or on a Divinity Shot with the sidearm. Destroyed '
     'drones release it too.'))


def lore_body(module, title):
    """The current text of a lore entry by title: physis_lore.all_entries() or physis_center_lore.center_entries()."""
    import importlib  # noqa: PLC0415
    mod = importlib.import_module(module)
    rows = mod.all_entries() if hasattr(mod, 'all_entries') else mod.center_entries()
    return next(row[2] for row in rows if row[1] == title)


def stele_fix():
    """PhysisRestore lines for saves made before a rewording (2026-11-09). Each old Logbook body in OLD_LOG_BODIES gets
    its entry's current text, and ,stones12, (Stillstone Pair's token) is added silently when the save already holds
    Stillstone Three or both of the others, so the Pair's line cannot play late or falsely."""
    has = lambda token: '(Utilities|String|Contains :SearchIn (Variables|Default|GetFlags) :Substring "%s")' % token
    lines = []
    for module, title, old in OLD_LOG_BODIES:
        new = wrap_text(lore_body(module, title).replace('~', ' '))
        old = wrap_text(old)
        if old != new:
            lines.append('(Variables|Default|SetLogData (Utilities|String|Replace :SourceString (Variables|Default|GetLogData) '
                         ':From "%s" :To "%s" :SearchCase "IgnoreCase"))' % (old, new))
    lines.append('(if (and (not %s) (or %s (and %s %s)))\n'
                 '        (Variables|Default|SetFlags (Utilities|String|Append :A (Variables|Default|GetFlags) :B ",stones12,")))'
                 % (has(',stones12,'), has(',stone3,'), has(',stone1,'), has(',stone2,')))
    return '\n      '.join(lines)


def saves():
    # BP_PhysisSave's spot fields first (its Set/Get nodes need the compiled class). The list, not a generator, makes
    # any() add every missing field instead of stopping at the first new one.
    if any([var(SAVE_BP, name, kind) for name, kind in SPOT_FIELDS]):
        comp(SAVE_BP)
    var(P, 'SpotSafe', 'bool')
    # PhysisSaveGame reads the encounters' count state (part encounters makes and writes the rest).
    if any([var(EN, name, kind, edit) for name, kind, edit in (('Goal', 'string', True), ('Before', 'string', False), ('Showing', 'bool', False))]):
        comp(EN)
    # Between the station's final terminal (LevelDone) and PhysisToCenter (which gives ,center, and saves)
    # a save would hold a station that is already finished.
    # The spot: her location, facing and camera, with SpotWorld naming the level, but only when a load can put her back
    # there safely: not in the air (jumps, Light Step), not dead, and not on or beside a moving platform (6.5 m covers
    # the station's 3.4 m platforms, the Center's 6 m hexagons and the Conclave lift), since platforms restart at home,
    # nor within 6.5 m (and 2.5 m in height) of a BP_Rise that has moved (stairs, stepping stones, the Temple Door; not
    # a lantern's flame overhead): every load starts each one at home and raises it again over seconds, so she would
    # stand in the air or inside it; nor within 3 m of an open station gate, which starts closed after a load.
    # A fight count on the objective line is saved as the objective it stands in for (FightLine's Before), since the
    # encounter's own state is not saved.
    # SpotSafe is a variable because a bound pure check would be read again later. The travel functions save in the
    # level she is leaving, so their SpotWorld never matches the level they open and the arrival spot stands.
    fn(P, 'PhysisSaveGame', """(fn PhysisSaveGame ()
  (if (and (Variables|Default|GetLevelDone) (not (Utilities|String|Contains :SearchIn (Variables|Default|GetFlags) :Substring ",center,")))
    (Variables|Default|SetMenuNote "Divinity is carrying Physis onward. Save again when she arrives.")
    (else
      (Variables|Default|SetSpotSafe (and (not (Movement|IsFalling :self (Variables|Character|GetCharacterMovement))) (not (Variables|Default|GetPhysisDead))))
      (for plat (Actor|GetAllActorsOfClass :ActorClass %s)
        (if (< (Transformation|GetDistanceTo :OtherActor plat) 650.0)
          (Variables|Default|SetSpotSafe false)))
      (for found (Actor|GetAllActorsOfClass :ActorClass "%sBP_Rise.BP_Rise_C")
        (bind rise (Utilities|Casting|CastToBP_Rise :Object found)
          (:then
            (bind dz (- (.z (Transformation|GetActorLocation :self rise)) (.z (Transformation|GetActorLocation))))
            (if (and (and (> (Class|BPRise|GetMoved :self rise) 0.0) (< (Transformation|GetDistanceTo :OtherActor rise) 650.0)) (< (select (> dz 0.0) dz (neg dz)) 250.0))
              (Variables|Default|SetSpotSafe false)))
          (:CastFailed)))
      (for found (Actor|GetAllActorsOfClass :ActorClass "%sBP_Gate.BP_Gate_C")
        (bind gate (Utilities|Casting|CastToBP_Gate :Object found)
          (:then
            (if (and (Class|BPGate|GetOpened :self gate) (< (Transformation|GetDistanceTo :OtherActor gate) 300.0))
              (Variables|Default|SetSpotSafe false)))
          (:CastFailed)))
      (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object (SaveGame|CreateSaveGameObject :SaveGameClass %s))
        (:then
          %s
          (Class|BPPhysisSave|SetSpotWorld :self saved :SpotWorld (select (Variables|Default|GetSpotSafe) %s 0))
          (Class|BPPhysisSave|SetSpotX :self saved :SpotX (.x (Transformation|GetActorLocation)))
          (Class|BPPhysisSave|SetSpotY :self saved :SpotY (.y (Transformation|GetActorLocation)))
          (Class|BPPhysisSave|SetSpotZ :self saved :SpotZ (.z (Transformation|GetActorLocation)))
          (Class|BPPhysisSave|SetSpotYaw :self saved :SpotYaw (.yaw (Transformation|GetActorRotation)))
          (Class|BPPhysisSave|SetViewYaw :self saved :ViewYaw (.yaw (Pawn|GetControlRotation :self (Game|GetPlayerController 0))))
          (Class|BPPhysisSave|SetViewPitch :self saved :ViewPitch (.pitch (Pawn|GetControlRotation :self (Game|GetPlayerController 0))))
          (for found (Actor|GetAllActorsOfClass :ActorClass "%sBP_Encounter.BP_Encounter_C")
            (bind fight (Utilities|Casting|CastToBP_Encounter :Object found)
              (:then
                (if (Class|BPEncounter|GetShowing :self fight)
                  (Class|BPPhysisSave|SetObjective :self saved :Objective (select (Utilities|String|EqualExactly(String) :A (Class|BPEncounter|GetBefore :self fight) :B "") (Class|BPEncounter|GetGoal :self fight) (Class|BPEncounter|GetBefore :self fight)))))
              (:CastFailed)))
          (SaveGame|SaveGametoSlot :SaveGameObject saved :SlotName "Physis" :UserIndex 0)
          (Variables|Default|SetMenuNote (select (Variables|Default|GetSpotSafe) "Game saved." "Game saved. Loading returns Physis to her last checkpoint.")))
        (:CastFailed)))))""" % (PLATFORM, B, B, SAVE_CLASS, PUT, WORLD, B))
    graph(P, 'PhysisClearRoom', [('Room', 'int')])
    fn(P, 'PhysisClearRoom', """(fn PhysisClearRoom (Room)
  (for found (Actor|GetAllActorsOfClass :ActorClass %s)
    (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found)
      (:then
        (if (== (Class|BPTrainingDrone|GetRoomId :self drone) Room)
          (for tag (Actor|GetAttachedActors :self drone)
            (Actor|DestroyActor :self tag))
          (Actor|DestroyActor :self drone)))
      (:CastFailed))))""" % DRONE)
    # The station's rules, plus two for the Center: an encounter whose token is held has its enemies
    # removed (the station's drone rule only knows its own rooms), and a Still Point counts as used only
    # if she reached it (its ,sp_<x>_<y>, token), not by its X as along the station's line of rooms.
    # The Scan Visor became Divinity Sense (author, 2026-11-07, via the station session). LogData keeps each scan's
    # full text, so a save made before the rename has its wording rewritten on load: "the Scan Visor", then "Scan
    # Visor", become "Divinity Sense", in any case. This runs before the scan targets below match their titles
    # against LogData.
    # Exact spot (author, 2026-11-08): when the save's SpotWorld is this level, she wakes where she saved, facing and
    # looking the same way, after the checkpoint teleport (CheckX/Y/Z are still restored, so death keeps using the
    # checkpoint). PhysisRestore runs only for a load (options "load"), at BeginPlay before any actor ticks. A save made
    # mid-fight wakes beside enemies at full health, hence 2 s of SafeUntil. Settle barriers stand again after every
    # load (they are not saved), so near a standing one she gets enough Divinity for one Settle (10) and cannot be sealed
    # inside a vault corridor or a Conclave ring (only once she has Settle: without it the Divinity could not open them).
    # Scan tags match LogData by the exact '^Title^' key (log_key).
    fn(P, 'PhysisRestore', ("""(fn PhysisRestore ()
  (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object (SaveGame|LoadGamefromSlot :SlotName "Physis" :UserIndex 0))
    (:then
      %s
      (Variables|Default|SetLogData (Utilities|String|Replace :SourceString (Utilities|String|Replace :SourceString (Variables|Default|GetLogData) :From "the Scan Visor" :To "Divinity Sense" :SearchCase "IgnoreCase") :From "Scan Visor" :To "Divinity Sense" :SearchCase "IgnoreCase"))
      """ + stele_fix() + """
      (Transformation|SetActorLocation :NewLocation (Math|Vector|MakeVector :X (Variables|Default|GetCheckX) :Y (Variables|Default|GetCheckY) :Z (Variables|Default|GetCheckZ)) :bSweep false :bTeleport true)
      (if (and (> (Class|BPPhysisSave|GetSpotWorld :self saved) 0) (== (Class|BPPhysisSave|GetSpotWorld :self saved) """ + WORLD.replace('%', '%%') + """))
        (Transformation|SetActorLocation :NewLocation (Math|Vector|MakeVector :X (Class|BPPhysisSave|GetSpotX :self saved) :Y (Class|BPPhysisSave|GetSpotY :self saved) :Z (Class|BPPhysisSave|GetSpotZ :self saved)) :bSweep false :bTeleport true)
        (Transformation|SetActorRotation :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Class|BPPhysisSave|GetSpotYaw :self saved)) :bTeleportPhysics true)
        (Pawn|SetControlRotation :self (Game|GetPlayerController 0) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch (Class|BPPhysisSave|GetViewPitch :self saved) :Yaw (Class|BPPhysisSave|GetViewYaw :self saved)))
        (Variables|Default|SetSafeUntil (+ (Utilities|Time|GetGameTimeinSeconds) 2.0))
        (if (and (< (Variables|Default|GetDivinity) 10.0) (Utilities|String|Contains :SearchIn (Variables|Default|GetFlags) :Substring ",settle,"))
          (for thorn (Actor|GetAllActorsOfClass :ActorClass """ + BARRIER + """)
            (if (< (Transformation|GetDistanceTo :OtherActor thorn) 10000.0)
              (Variables|Default|SetDivinity 10.0)))))
      (bind flags (Variables|Default|GetFlags))
      (bind directors (Actor|GetAllActorsOfClass :ActorClass %s))
      (bind center (> (Utilities|Array|Length directors) 0))
      (for found1 (Actor|GetAllActorsOfClass :ActorClass %s)
        (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found1)
          (:then
            (bind room (Class|BPTrainingDrone|GetRoomId :self drone))
            (if (or (and (== room 1) (Utilities|String|Contains :SearchIn flags :Substring ",room1,")) (or (and (== room 2) (Utilities|String|Contains :SearchIn flags :Substring ",room2,")) (or (and (== room 3) (Utilities|String|Contains :SearchIn flags :Substring ",boss,")) (and (> room 100) (Utilities|String|Contains :SearchIn flags :Substring (Utilities|String|Append :A ",w" :B (Utilities|String|Append :A (Utilities|String|ToString(Integer) (- room 101)) :B ",")))))))
              (for tag (Actor|GetAttachedActors :self drone)
                (Actor|DestroyActor :self tag))
              (Actor|DestroyActor :self drone)))
          (:CastFailed)))
      (for found2 (Actor|GetAllActorsOfClass :ActorClass "%sBP_ScanTarget.BP_ScanTarget_C")
        (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found2)
          (:then
            (if (and (not (Utilities|String|EqualExactly(String) :A (Class|BPScanTarget|GetScanTitle :self item) :B "")) (Utilities|String|Contains :SearchIn (Variables|Default|GetLogData) :Substring """ + log_key('(Class|BPScanTarget|GetScanTitle :self item)') + """))
              (Class|BPScanTarget|SetScanDone :self item :ScanDone true)))
          (:CastFailed)))
      (for found3 (Actor|GetAllActorsOfClass :ActorClass "%sBP_Pickup.BP_Pickup_C")
        (bind pick (Utilities|Casting|CastToBP_Pickup :Object found3)
          (:then
            (if (and (not (Utilities|String|EqualExactly(String) :A (Class|BPPickup|GetToken :self pick) :B "")) (Utilities|String|Contains :SearchIn flags :Substring (Class|BPPickup|GetToken :self pick)))
              (Actor|DestroyActor :self pick)))
          (:CastFailed)))
      (for found4 (Actor|GetAllActorsOfClass :ActorClass "%sBP_Switch.BP_Switch_C")
        (bind lever (Utilities|Casting|CastToBP_Switch :Object found4)
          (:then
            (if (and (== (Class|BPSwitch|GetSeq :self lever) 0) (and (not (Utilities|String|EqualExactly(String) :A (Class|BPSwitch|GetGive :self lever) :B "")) (Utilities|String|Contains :SearchIn flags :Substring (Class|BPSwitch|GetGive :self lever))))
              (Class|BPSwitch|SetUsed :self lever :Used true)))
          (:CastFailed)))
      (for found5 (Actor|GetAllActorsOfClass :ActorClass "%sBP_Encounter.BP_Encounter_C")
        (bind fight (Utilities|Casting|CastToBP_Encounter :Object found5)
          (:then
            (if (Utilities|String|Contains :SearchIn flags :Substring (Class|BPEncounter|GetGive :self fight))
              (Class|BPEncounter|SetDone :self fight :Done true)
              (if (and center (and (> (Class|BPEncounter|GetRoom :self fight) 0) (not (Utilities|String|EqualExactly(String) :A (Class|BPEncounter|GetGive :self fight) :B ""))))
                (CallFunction|PhysisClearRoom :Room (Class|BPEncounter|GetRoom :self fight)))))
          (:CastFailed)))
      (for found6 (Actor|GetAllActorsOfClass :ActorClass "%sBP_Checkpoint.BP_Checkpoint_C")
        (bind mark (Utilities|Casting|CastToBP_Checkpoint :Object found6)
          (:then
            (if center
              (if (Utilities|String|Contains :SearchIn flags :Substring %s)
                (Class|BPCheckpoint|SetUsed :self mark :Used true))
              (else
                (if (<= (.x (Transformation|GetActorLocation :self mark)) (+ (Variables|Default|GetCheckX) 1.0))
                  (Class|BPCheckpoint|SetUsed :self mark :Used true)))))
          (:CastFailed))))
    (:CastFailed)))""") % (GET, AWAKENING, DRONE, B, B, B, B, B, still_key('(Transformation|GetActorLocation :self mark)')))
    # ,at_conclave, (given by PhysisToConclave, taken by PhysisConclaveHome) before ,center,, which a Conclave save holds too.
    fn(P, 'PhysisLoadGame', """(fn PhysisLoadGame ()
  (if (SaveGame|DoesSaveGameExist :SlotName "Physis" :UserIndex 0)
    (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object (SaveGame|LoadGamefromSlot :SlotName "Physis" :UserIndex 0))
      (:then
        (if (Utilities|String|Contains :SearchIn (Class|BPPhysisSave|GetFlags :self saved) :Substring ",at_conclave,")
          (Game|OpenLevel(byName) :LevelName "L_Conclave" :Options "nocine,load")
          (elif (Utilities|String|Contains :SearchIn (Class|BPPhysisSave|GetFlags :self saved) :Substring ",center,")
            (Game|OpenLevel(byName) :LevelName "L_CenterOfTheUniverse" :Options "nocine,load")
            (else
              (Game|OpenLevel(byName) :LevelName "L_BattleStation" :Options "nocine,load")))))
      (:CastFailed))
    (else
      (Variables|Default|SetMenuNote "No saved game yet."))))""")
    still_points()


def still_points():
    # A Center Still Point records itself when reached, so a load can tell which ones she has used. The
    # station re-arms its checkpoints after every death and keeps its own rule, so they record nothing.
    # In the Center a Still Point is also a place of rest: standing in one restores her health (author, 2026-11-04:
    # "I'm struggling to find health"), but only while no enemy (Static locks aside) is within 25 m of her, or a
    # fight inside its radius could never be lost (review, 2026-11-05: the Sanctum fight that gates Mend). Warned
    # keeps the "enemies are near" note to once per stay.
    # The first visit sets the checkpoint, gives the ,sp_ token (open-world levels only) and sets the Still Point's
    # objective. The objective is skipped once Flags hold Until, an instance-editable token. The Center's Still Points
    # have Until ,mend,: after Mend their old objectives would replace the current quest and file it as Completed
    # (Play test, 2026-11-07: coming home from the Conclave, an unused Center Still Point filed the Kairos quest).
    # An empty Until keeps the station's and the Conclave's rule. It is tested for "" first, because Contains with
    # an empty substring is true. In an open-world level (a BP_Awakening is present), standing in a Still Point she has
    # used before also moves the checkpoint there, with no token and no quest. So deaths and Continue follow the last
    # Still Point she stood in, not a current's arrival spot or an older Still Point (Conclave session's suggestion,
    # 2026-11-07). The station re-arms its checkpoints instead.
    maxp = '(select (> (Class|BPPhysis|GetMaxHealth :self physis) 0.0) (Class|BPPhysis|GetMaxHealth :self physis) 10.0)'
    var(CK, 'Calm', 'bool')
    var(CK, 'Warned', 'bool')
    var(CK, 'Until', 'string', True)
    fn(CK, 'EventGraph', """(event EventTick (DeltaSeconds)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (if (and (not (Variables|Default|GetUsed)) (< (Transformation|GetDistanceTo :OtherActor physis) (Variables|Default|GetRadius)))
        (Variables|Default|SetUsed true)
        (bind here (Transformation|GetActorLocation))
        (Class|BPPhysis|PhysisCheckpoint :self physis :X (.x here) :Y (.y here) :Z (.z here))
        (bind directors (Actor|GetAllActorsOfClass :ActorClass %s))
        (if (> (Utilities|Array|Length directors) 0)
          (Class|BPPhysis|PhysisGive :self physis :Token %s))
        (if (or (Utilities|String|EqualExactly(String) :A (Variables|Default|GetUntil) :B "") (not (Utilities|String|Contains :SearchIn (Class|BPPhysis|GetFlags :self physis) :Substring (Variables|Default|GetUntil))))
          (Class|BPPhysis|PhysisQuest :self physis :Goal (Variables|Default|GetObjective))))
      (if (and (Variables|Default|GetUsed) (< (Transformation|GetDistanceTo :OtherActor physis) (Variables|Default|GetRadius)))
        (bind worlds (Actor|GetAllActorsOfClass :ActorClass %s))
        (if (> (Utilities|Array|Length worlds) 0)
          (bind spot (Transformation|GetActorLocation))
          (Class|BPPhysis|PhysisCheckpoint :self physis :X (.x spot) :Y (.y spot) :Z (.z spot))))
      (if (and (< (Transformation|GetDistanceTo :OtherActor physis) (Variables|Default|GetRadius)) (< (Class|BPPhysis|GetPhysisHealth :self physis) %s))
        (bind rest (Actor|GetAllActorsOfClass :ActorClass %s))
        (if (and (> (Utilities|Array|Length rest) 0) (not (Class|BPPhysis|GetPhysisDead :self physis)))
          (Variables|Default|SetCalm true)
          (for foe (Actor|GetAllActorsOfClass :ActorClass %s)
            (bind enemy (Utilities|Casting|CastToBP_TrainingDrone :Object foe)
              (:then
                (if (and (not (Class|BPTrainingDrone|GetStatic :self enemy)) (< (Transformation|GetDistanceTo :self enemy :OtherActor physis) 2500.0))
                  (Variables|Default|SetCalm false)))
              (:CastFailed)))
          (if (Variables|Default|GetCalm)
            (Class|BPPhysis|SetPhysisHealth :self physis :PhysisHealth %s)
            (Audio|PlaySound2D :Sound "/Game/Audio/S_PickupHealth.S_PickupHealth")
            (Class|BPPhysis|PhysisNote :self physis :Message "The Still Point restores you")
            (Variables|Default|SetWarned false)
            (elif (not (Variables|Default|GetWarned))
              (Variables|Default|SetWarned true)
              (Class|BPPhysis|PhysisNote :self physis :Message "Enemies are near. The Still Point cannot restore you yet."))))
        (else
          (Variables|Default|SetWarned false))))
    (:CastFailed)))""" % (AWAKENING, still_key('here'), AWAKENING, maxp, AWAKENING, DRONE, maxp))
    comp(CK)


# ---------------------------------------------------------------- the station's end and the Center's progress

# Augmentations (Author, 2026-11-04): permanent upgrades from the Center's ability vaults, kept as flag tokens
# so every save keeps them. Health: the station's Life Augmentation and four vault tanks, 10 health each.
# Katana: +25% sword damage each. Pistol: +30% gun damage each. Defense: 15% less damage taken each.
# Agility: +0.1 s on the 0.3 s perfect-parry window each.
# The Conclave adds six (GAME_ROADMAP.md, "Rewards"): two Health tanks, and one each of the other four, from its side
# requests and the Spire's crown (physis_conclave_lore PEOPLE gifts).
AUGMENTS = {'Health': (',lifeaug,', ',aug_hp1,', ',aug_hp2,', ',aug_hp3,', ',aug_hp4,', ',aug_hp5,', ',aug_hp6,'),
            'Katana': (',aug_katana1,', ',aug_katana2,', ',aug_katana3,', ',aug_katana4,'),
            'Pistol': (',aug_pistol1,', ',aug_pistol2,', ',aug_pistol3,'),
            'Defense': (',aug_defense1,', ',aug_defense2,', ',aug_defense3,', ',aug_defense4,'),
            'Agility': (',aug_agility1,', ',aug_agility2,', ',aug_agility3,', ',aug_agility4,')}


def held(kind):
    """How many of an augmentation kind's tokens the flags hold, as a float."""
    terms = ['(select (Utilities|String|Contains :SearchIn (Variables|Default|GetFlags) :Substring "%s") 1.0 0.0)' % t for t in AUGMENTS[kind]]
    out = terms[-1]
    for term in reversed(terms[:-1]):
        out = '(+ %s %s)' % (term, out)
    return out


AUGMENT_VALUES = '\n'.join((
    '  (Variables|Default|SetMaxHealth (* 10.0 (+ 1.0 %s)))' % held('Health'),
    '  (Variables|Default|SetKatanaPower (+ 1.0 (* 0.25 %s)))' % held('Katana'),
    '  (Variables|Default|SetPistolPower (+ 1.0 (* 0.3 %s)))' % held('Pistol'),
    '  (Variables|Default|SetHurtTaken (- 1.0 (* 0.15 %s)))' % held('Defense'),
    '  (Variables|Default|SetParryTime (+ 0.3 (* 0.1 %s)))' % held('Agility')))
KATANA = '(select (> (Variables|Default|GetKatanaPower) 0.0) (Variables|Default|GetKatanaPower) 1.0)'
PISTOL = '(select (> (Variables|Default|GetPistolPower) 0.0) (Variables|Default|GetPistolPower) 1.0)'
HURT = '(select (> (Variables|Default|GetHurtTaken) 0.0) (Variables|Default|GetHurtTaken) 1.0)'
PARRY_TIME = '(select (> (Variables|Default|GetParryTime) 0.0) (Variables|Default|GetParryTime) 0.3)'


def progress():
    # The station's final terminal: its last quest goes to Completed, the fleets fall quiet, and 8 s later, when
    # ShowTutorial's 8 s message has been read, a Divinity current carries her to the Center (PhysisToCenter,
    # center_logic.py). Swift unlocks at 4 s, so each achievement gets its own frame and a toast of at least 4 s
    # before the level changes (station session, 2026-11-07; it was 13 s and 6.5 s).
    fn(P, 'PhysisFinish', """(fn PhysisFinish ()
  (CallFunction|PhysisQuest :Goal "")
  (Variables|Default|SetLevelDone true)
  (if (not (Variables|Default|GetAchStation))
    (Variables|Default|SetAchStation true)
    (CallFunction|PhysisAchieve :Id "ACH_PHYSIS_STATION" :Name "Meridian Holds"))
  (if (and (< (Variables|Default|GetLevelTime) 600.0) (not (Variables|Default|GetAchSwift)))
    (Variables|Default|SetAchSwift true)
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisSwiftUnlock" :Time 4.0 :bLooping false))
  (CallFunction|PhysisSay :Message "Divinity settles between the fleets. Their weapons fall silent.   I am not your enemy,~and I am not your ally, and I need you to listen.")
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisToCenter" :Time 8.0 :bLooping false))""")
    # Fidelity ladder (PhysisFidelityApply): stage 0 is LOD 2, stage 1 LOD 1 once the boss falls, stage 2 full
    # detail (LOD 0) once she learns Settle, the Center's GDD ability, and stage 3, Max (140% view distance), once
    # she learns Light Step in the Conclave. The Center is always at least LOD 1, even when started without the
    # station's flags; the Conclave (,conclave,) at least stage 2, so a direct start plays at High (author,
    # 2026-11-06: High from Settle on, for the rest of the game).
    # The HUD runs PhysisFidelity every frame, so it also keeps the augmentation values current.
    for n in ('KatanaPower', 'PistolPower', 'HurtTaken', 'ParryTime'):
        var(P, n, 'float')
    has = lambda token: '(Utilities|String|Contains :SearchIn (Variables|Default|GetFlags) :Substring "%s")' % token
    fn(P, 'PhysisFidelity', """(fn PhysisFidelity ()
""" + AUGMENT_VALUES + """
  (bind want (select %s 3 (select (or %s %s) 2 (select (or %s %s) 1 0))))""" % (has(',lightstep,'), has(',settle,'), has(',conclave,'), has(',boss,'), has(',center,')) + """
  (if (not (== (+ want 1) (Variables|Default|GetFidelityApplied)))
    (Variables|Default|SetFidelityApplied (+ want 1))
    (CallFunction|PhysisFidelityApply :Stage want)))""")


# ---------------------------------------------------------------- main menu

def menu():
    for name, kind in (('HasSave', 'bool'), ('Checked', 'bool')):
        var(MENU, name, kind)
    graph(MENU, 'MenuContinue')
    fn(MENU, 'MenuContinue', """(fn MenuContinue ()
  (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object (SaveGame|LoadGamefromSlot :SlotName "Physis" :UserIndex 0))
    (:then
      (if (Utilities|String|Contains :SearchIn (Class|BPPhysisSave|GetFlags :self saved) :Substring ",at_conclave,")
        (Game|OpenLevel(byName) :LevelName "L_Conclave" :Options "nocine,load")
        (elif (Utilities|String|Contains :SearchIn (Class|BPPhysisSave|GetFlags :self saved) :Substring ",center,")
          (Game|OpenLevel(byName) :LevelName "L_CenterOfTheUniverse" :Options "nocine,load")
          (else
            (Game|OpenLevel(byName) :LevelName "L_BattleStation" :Options "nocine,load")))))
    (:CastFailed)))""")
    # The live menu, with a Continue row above New Game when a save exists (rows 0 Continue, 1 New Game,
    # 2 Exit Game). The save is looked up once, on the first frame drawn. Pins are named, as in the menu's
    # own generator (menu.py): the positional form read back from the graph does not write back.
    on = lambda i: '(== (Variables|Default|GetSelected) %d)' % i
    lit = lambda i: '(Utilities|Struct|MakeLinearColor :R (select %s 1.0 0.62) :G (select %s 0.82 0.66) :B (select %s 0.42 0.72) :A 1.0)' % (on(i), on(i), on(i))
    plate = lambda i: '(Utilities|Struct|MakeLinearColor :R 1.0 :G 0.8 :B 0.4 :A (select %s 0.14 0.0))' % on(i)
    scale = '(* (* u 2.2) 0.35)'
    font = '"/Game/UI/F_Physis.F_Physis"'

    def row(label, i, half, y):
        x = '(- (/ SizeX 2.0) (* u %s))' % half
        top = '(* u (+ %s 8.0))' % y
        return """(HUD|DrawRect :RectColor %s :ScreenX (- (/ SizeX 2.0) (* u 300.0)) :ScreenY (* u %s) :ScreenW (* u 600.0) :ScreenH (* u 72.0))
  (CallFunction|MenuTextPlate :Text "%s" :X %s :Y %s :Scale %s)
  (HUD|DrawText :Text "%s" :TextColor %s :ScreenX %s :ScreenY %s :Font %s :Scale %s)""" % (plate(i), y, label, x, top, scale, label, lit(i), x, top, font, scale)

    def keys(*names):
        out = '(Game|Player|WasInputKeyJustPressed :self pc :Key "%s")' % names[0]
        for name in names[1:]:
            out = '(or %s (Game|Player|WasInputKeyJustPressed :self pc :Key "%s"))' % (out, name)
        return out
    sky = '(select (> SizeX (* SizeY 2.0)) SizeX (* SizeY 2.0))'
    fn(MENU, 'DrawMenu', """(fn DrawMenu (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind pc (Game|GetPlayerController 0))
  (if (not (Variables|Default|GetChecked))
    (Variables|Default|SetChecked true)
    (Variables|Default|SetHasSave (SaveGame|DoesSaveGameExist :SlotName "Physis" :UserIndex 0))
    (Variables|Default|SetSelected (select (Variables|Default|GetHasSave) 0 1)))
  (HUD|DrawTexture :Texture "/Game/Cinematics/T_Sky_Space.T_Sky_Space" :ScreenX (- (/ SizeX 2.0) (/ %s 2.0)) :ScreenY (- (/ SizeY 2.0) (/ %s 4.0)) :ScreenW %s :ScreenH (/ %s 2.0) :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor "(R=0.75,G=0.75,B=0.8,A=1.0)")
  (HUD|DrawRect :RectColor "(R=0.0,G=0.01,B=0.03,A=0.45)" :ScreenX 0.0 :ScreenY 0.0 :ScreenW SizeX :ScreenH SizeY)
  (HUD|DrawTexture :Texture "/Game/UI/T_UI_Title.T_UI_Title" :ScreenX (- (/ SizeX 2.0) (/ (* u 880.0) 2.0)) :ScreenY (* u 90.0) :ScreenW (* u 880.0) :ScreenH (* (* u 880.0) 0.625) :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor "(R=1.0,G=1.0,B=1.0,A=1.0)")
  (if (Variables|Default|GetHasSave)
    %s)
  %s
  %s
  (if %s
    (Variables|Default|SetSelected (select (> (Variables|Default|GetSelected) (select (Variables|Default|GetHasSave) 0 1)) (- (Variables|Default|GetSelected) 1) (Variables|Default|GetSelected))))
  (if %s
    (Variables|Default|SetSelected (select (< (Variables|Default|GetSelected) 2) (+ (Variables|Default|GetSelected) 1) (Variables|Default|GetSelected))))
  (if %s
    (if (== (Variables|Default|GetSelected) 0)
      (CallFunction|MenuContinue)
      (elif (== (Variables|Default|GetSelected) 1)
        (Game|OpenLevel(byName) :LevelName "L_BattleStation")
        (else
          (Game|QuitGame))))))""" % (
        sky, sky, sky, sky,
        row('Continue', 0, '73.6', '660.0').replace('\n  ', '\n    '),
        row('New Game', 1, '73.6', '(select (Variables|Default|GetHasSave) 760.0 680.0)'),
        row('Exit Game', 2, '82.8', '(select (Variables|Default|GetHasSave) 860.0 790.0)'),
        keys('Up', 'W', 'Gamepad_DPad_Up', 'Gamepad_LeftStick_Up'),
        keys('Down', 'S', 'Gamepad_DPad_Down', 'Gamepad_LeftStick_Down'),
        keys('E', 'Enter', 'SpaceBar', 'Gamepad_FaceButton_Bottom')))
    comp(MENU)


# ---------------------------------------------------------------- scanning

def scans():
    # Line of sight for the visor. A tag attached to an enemy sits inside its body, which blocks a test to
    # the tag, so the enemy itself is tested too. Ground animals (stags, foxes) have no collision, but their
    # origin is snapped onto the terrain every tick, so a test to the animal ends exactly on the ground and
    # flickers; their tag, at the middle of the body, is tested instead. Either one seen counts
    # (LineOfSightTo of no actor is simply false). VisorApply resets a scan on any frame its target is out
    # of view, so a target stays in view for 0.3 s after it was last seen.
    var(ST, 'SeenAt', 'float')
    fn(ST, 'VisorMeasure', """(fn VisorMeasure (Eye Look)
  (bind gap (- (Transformation|GetActorLocation) Eye))
  (bind facing (Math|Vector|DotProduct Look (Math|Vector|Normalize gap)))
  (Variables|Default|SetScanAimDot -1.0)
  (Variables|Default|SetScanInView false)
  (if (and (< (Math|Vector|VectorLength gap) 2500.0) (> facing 0.3))
    (if (or (Controller|LineOfSightTo :self (Game|GetPlayerController 0) :Other self) (Controller|LineOfSightTo :self (Game|GetPlayerController 0) :Other (Actor|GetAttachParentActor)))
      (Variables|Default|SetSeenAt (Utilities|Time|GetGameTimeinSeconds)))
    (if (< (- (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetSeenAt)) 0.3)
      (Variables|Default|SetScanInView true)
      (Variables|Default|SetScanAimDot facing))))""")
    # Tags made at runtime (BP_Pickup part items, BP_Relic in center_logic.py) set themselves up here: texts, hidden in
    # game with no collision (as the scenario's game.hide_scan does), and already grey when the Logbook holds the kind.
    graph(ST, 'TagSetup', [('Category', 'string'), ('Title', 'string'), ('Body', 'string'), ('Important', 'bool')])
    fn(ST, 'TagSetup', """(fn TagSetup (Category Title Body Important)
  (Variables|Default|SetScanCategory Category)
  (Variables|Default|SetScanTitle Title)
  (Variables|Default|SetScanText Body)
  (Variables|Default|SetScanImportant Important)
  (Variables|Default|SetScanProgress 0.0)
  (Rendering|SetActorHiddenInGame :bNewHidden true)
  (Collision|SetActorEnableCollision :bNewActorEnableCollision false)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (Variables|Default|SetScanDone (Utilities|String|Contains :SearchIn (Class|BPPhysis|GetLogData :self physis) :Substring """ + log_key('Title') + """)))
    (:CastFailed)))""")
    comp(ST)
    # The Logbook and the scan counter (author, 2026-11-08: "scanning any particular object should make the scan
    # rectangle on all other objects of the same kind go grey", "we need only the unique scans to count"). A kind is a
    # ScanTitle. Titles match LogData by the exact '^Title^' key. PhysisAddLog was the station's (scenario_bp.py),
    # PhysisVisorToggle quiet.py's and VisorApply feat.py's; all three live here since 2026-11-08 (station session's OK).
    for name, kind in (('ScanKinds', 'string'), ('ScanKindCount', 'int'), ('ScanKindDone', 'int')):
        var(P, name, kind)
    graph(P, 'PhysisAddLog', [('Category', 'string'), ('Title', 'string'), ('Body', 'string')])
    graph(P, 'PhysisScanKnown', [('Title', 'string')])
    graph(P, 'PhysisScanCount')
    fn(P, 'PhysisAddLog', """(fn PhysisAddLog (Category Title Body)
  (if (not (Utilities|String|Contains :SearchIn (Variables|Default|GetLogData) :Substring """ + log_key('Title') + """))
    (Variables|Default|SetLogData (Utilities|String|Append :A (Variables|Default|GetLogData) :B (Utilities|String|Append :A (Utilities|String|Append :A Category :B "^") :B (Utilities|String|Append :A (Utilities|String|Append :A Title :B "^") :B (Utilities|String|Append :A Body :B "@")))))))""")
    # A finished scan greys every tag of the same kind (DrawVisor tints ScanDone tags grey and drops their bar).
    fn(P, 'PhysisScanKnown', """(fn PhysisScanKnown (Title)
  (for found (Actor|GetAllActorsOfClass :ActorClass %s)
    (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
      (:then
        (if (Utilities|String|EqualExactly(String) :A (Class|BPScanTarget|GetScanTitle :self item) :B Title)
          (Class|BPScanTarget|SetScanDone :self item :ScanDone true)))
      (:CastFailed))))""" % TARGETS)
    # SCANS X / Y: Y is the number of different kinds whose tags this visit of the level has shown (ScanKinds, a
    # '^Title^' set that only grows, so a kill or a taken item never lowers it), X how many of them the Logbook holds.
    # Counted when Divinity Sense opens and after each finished scan, not every frame.
    fn(P, 'PhysisScanCount', """(fn PhysisScanCount ()
  (for found (Actor|GetAllActorsOfClass :ActorClass %s)
    (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
      (:then
        (bind title (Class|BPScanTarget|GetScanTitle :self item))
        (if (and (not (Utilities|String|EqualExactly(String) :A title :B "")) (not (Utilities|String|Contains :SearchIn (Variables|Default|GetScanKinds) :Substring %s)))
          (Variables|Default|SetScanKinds (Utilities|String|Append :A (Variables|Default|GetScanKinds) :B %s))))
      (:CastFailed)))
  (Variables|Default|SetScanKindCount 0)
  (Variables|Default|SetScanKindDone 0)
  (for kind (Utilities|String|ParseIntoArray :SourceString (Variables|Default|GetScanKinds) :Delimiter "^" :CullEmptyStrings true)
    (Variables|Default|SetScanKindCount (+ (Variables|Default|GetScanKindCount) 1))
    (if (Utilities|String|Contains :SearchIn (Variables|Default|GetLogData) :Substring %s)
      (Variables|Default|SetScanKindDone (+ (Variables|Default|GetScanKindDone) 1)))))""" % (TARGETS, log_key('title'), log_key('title'), log_key('kind')))
    fn(P, 'PhysisVisorToggle', """(fn PhysisVisorToggle ()
  (if (not (Variables|Default|GetCinematic))
    (Variables|Default|SetScanVisorOn (not (Variables|Default|GetScanVisorOn)))
    (Variables|Default|SetScanHeld false)
    (Variables|Default|SetLockHeld false)
    (CallFunction|PhysisVoiceStop)
    (CallFunction|PhysisLockClear)
    (if (Variables|Default|GetScanVisorOn)
      (CallFunction|PhysisScanCount))
    (for found (Actor|GetAllActorsOfClass :ActorClass %s)
      (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
        (:then (Class|BPScanTarget|VisorClear :self item))
        (:CastFailed)))))""" % TARGETS)
    comp(P)
    # feat.py's VisorApply (narration the first time a kind is scanned, the result shown with the game paused) with
    # the exact key, and the same-kind grey and the recount before the paused frame shows them.
    fn(ST, 'VisorApply', """(fn VisorApply (Best Held Seconds)
  (bind aimed (and (Variables|Default|GetScanInView) (and (> Best (select Held 0.86 0.97)) (>= (Variables|Default|GetScanAimDot) Best))))
  (Variables|Default|SetScanAimed aimed)
  (if (and aimed Held)
    (bind screen (Utilities|Casting|CastToBP_PhysisHUD :Object (HUD|GetHUD (Game|GetPlayerController 0)))
      (:then
        (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
          (:then
            (bind player (Game|GetPlayerController 0))
            (Pawn|SetControlRotation :self player :NewRotation (Math|Interpolation|RInterpTo :Current (Pawn|GetControlRotation :self player) :Target (Math|Rotator|FindLookatRotation :Start (Camera|GetCameraLocation :self (Game|GetPlayerCameraManager 0)) :Target (Transformation|GetActorLocation)) :DeltaTime Seconds :InterpSpeed 10.0))
            (if (Variables|Default|GetScanDone)
              (Class|BPPhysis|SetScanHeld :self physis :ScanHeld false)
              (Class|BPPhysisHUD|ShowScanResult :self screen :Message (Variables|Default|GetScanText))
              (Class|BPPhysis|PhysisScanShow :self physis)
              (else
                (Variables|Default|SetScanProgress (+ (Variables|Default|GetScanProgress) (/ Seconds (select (Variables|Default|GetScanImportant) 2.0 1.2))))
                (if (>= (Variables|Default|GetScanProgress) 1.0)
                  (Variables|Default|SetScanDone true)
                  (Class|BPPhysis|SetScanHeld :self physis :ScanHeld false)
                  (if (not (Utilities|String|Contains :SearchIn (Class|BPPhysis|GetLogData :self physis) :Substring """ + log_key('(Variables|Default|GetScanTitle)') + """))
                    (Class|BPPhysis|PhysisNarrate :self physis :Title (Variables|Default|GetScanTitle)))
                  (Class|BPPhysis|PhysisAddLog :self physis :Category (Variables|Default|GetScanCategory) :Title (Variables|Default|GetScanTitle) :Body (Variables|Default|GetScanText))
                  (Class|BPPhysis|PhysisScanKnown :self physis :Title (Variables|Default|GetScanTitle))
                  (Class|BPPhysis|PhysisScanCount :self physis)
                  (Class|BPPhysisHUD|ShowScanResult :self screen :Message (Variables|Default|GetScanText))
                  (Class|BPPhysis|PhysisScanShow :self physis)))))
          (:CastFailed)))
      (:CastFailed))
    (else
      (Variables|Default|SetScanProgress 0.0))))""")
    comp(ST)


# ---------------------------------------------------------------- items (author, 2026-11-08: "All augmentations and
# items need to be scannable")

ITEM_TITLES = ('Health Capsule', 'Divinity Crystal', 'Ammo Cell', 'Reactor Fuse', 'Life Augmentation')  # by BP_Pickup Kind 0-4


def item_texts():
    """The station's entries for the five pickup kinds (physis_lore STORY_SCANS), as the scan shows them. The texts stay
    the station's, because Divinity's voice line for each title reads them."""
    import physis_lore  # noqa: PLC0415  (Content/Python is on sys.path)
    rows = {row[1]: row for row in physis_lore.STORY_SCANS}
    return [(rows[title][0], title, wrap_text(rows[title][2])) for title in ITEM_TITLES]


def items():
    # Every BP_Pickup, placed or dropped, carries its own tag: PickupSetup attaches one (in the level's first second, a
    # placed pickup adopts a same-title tag within 2 m, such as the station's first-of-a-kind tags, so it goes with the
    # item; drops come later and always make their own) and sets it to the kind.
    # Drops call PickupSetup twice (BeginPlay with Kind 0, then the drop's kind), which only re-labels the tag.
    # EventEndPlay destroys attached actors, however the pickup goes (collected, restored as taken, or its life span).
    # PickupSetup was the station's (combat.py) and the EventGraph pause.py's; both live here since 2026-11-08.
    rows = item_texts()
    pick = lambda field: ' '.join('(select (== Value %d) %s' % (k, literal(row[field])) for k, row in enumerate(rows[:4])) + ' ' + literal(rows[4][field]) + ')' * 4
    made = spawn('BP_ScanTarget', '(Transformation|GetActorLocation)')
    graph(PICK, 'PickupSetup', [('Value', 'int')])
    fn(PICK, 'PickupSetup', """(fn PickupSetup (Value)
  (Variables|Default|SetKind Value)
  (if (and (>= Value 0) (<= Value 4))
    (if (and (== (Utilities|Array|Length (Actor|GetAttachedActors)) 0) (< (Utilities|Time|GetGameTimeinSeconds) 1.0))
      (for found (Actor|GetAllActorsOfClass :ActorClass %s)
        (bind free (Utilities|Casting|CastToBP_ScanTarget :Object found)
          (:then
            (if (and (Utilities|String|EqualExactly(String) :A (Class|BPScanTarget|GetScanTitle :self free) :B %s) (< (Transformation|GetDistanceTo :self free :OtherActor self) 200.0))
              (Transformation|SetActorLocation :self free :NewLocation (Math|Vector|MakeVector :X (.x (Transformation|GetActorLocation)) :Y (.y (Transformation|GetActorLocation)) :Z (.z (Transformation|GetActorLocation :self free))) :bSweep false :bTeleport true)
              (Transformation|AttachActorToActor :self free :ParentActor self :LocationRule "KeepWorld" :RotationRule "KeepWorld" :ScaleRule "KeepWorld")))
          (:CastFailed))))
    (if (== (Utilities|Array|Length (Actor|GetAttachedActors)) 0)
      (bind made %s)
      (Transformation|AttachActorToActor :self made :ParentActor self :LocationRule "KeepWorld" :RotationRule "KeepWorld" :ScaleRule "KeepWorld"))
    (for kid (Actor|GetAttachedActors)
      (bind tag (Utilities|Casting|CastToBP_ScanTarget :Object kid)
        (:then
          (Class|BPScanTarget|TagSetup :self tag :Category %s :Title %s :Body %s :Important (>= Value 3)))
        (:CastFailed))))
  (switch int Value
    (:0 (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh "/Game/Gameplay/SM_Pickup_Health.SM_Pickup_Health"))
    (:1 (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh "/Game/Gameplay/SM_Pickup_Divinity.SM_Pickup_Divinity"))
    (:Default (Components|StaticMesh|SetStaticMesh :self (Variables|Default|GetShape) :NewMesh "/Game/Gameplay/SM_Pickup_Ammo.SM_Pickup_Ammo"))))""" % (
        TARGETS, pick(1), made, pick(0), pick(1), pick(2)))
    fn(PICK, 'EventGraph', """(event EventBeginPlay
  (CallFunction|PickupSetup :Value (Variables|Default|GetKind)))

(event EventTick (DeltaSeconds)
  (Transformation|AddActorWorldRotation :DeltaRotation (Math|Rotator|MakeRotator :Yaw (* DeltaSeconds 80.0)) :bSweep false :bTeleport false)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (if (< (Transformation|GetDistanceTo :OtherActor physis) 130.0)
        (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetToken))
        (Class|BPPhysis|PhysisCollect :self physis :Kind (Variables|Default|GetKind))
        (Actor|DestroyActor)))
    (:CastFailed)))

(event EventEndPlay (EndPlayReason)
  (for kid (Actor|GetAttachedActors)
    (Actor|DestroyActor :self kid)))""")
    comp(PICK)


# ---------------------------------------------------------------- enemy drones
# Enemy kinds (author, 2026-11-08: "We need more enemy variety... tanks (enemies with 20 health and great defense),
# enemies with shields, fast enemies etc. ... Perhaps there's an enemy that takes damage only from the sides or from
# behind"). BP_TrainingDrone EnemyKind, instance-editable, set by the Center scenario (physis_center_scenario foe()):
#   0  today's drone (the station, the Conclave and every Center enemy placed before 2026-11-08)
#   1  Bastion: light blows (raw hit power under 3) do half damage, carried; heavy finishers, the parry counter,
#      Divine and charged shots and any blow while it is stunned do full damage. Slow, close, long melee reach.
#   2  Aegis Shard: its Ward (a plate on its front) turns every blow from the front until a heavy blow breaks it for
#      4 s; its sides and back always take damage; Perfect Parry and Settle open it too.
#   3  Ember Skitter: fast and fragile, keeps far, dashes in just before each attack.
#   4  Onyx Ward: its front (its Ward face plate) takes no damage at all; it turns toward her at only 100 deg/s and
#      strikes only what is in front of it, so she circles it or Settles it and walks behind.
# Blocked blows spark at its front with S_Block and a short note, at most every 4 s per enemy. A Perfect Parry stuns
# every kind within 4.2 m (parry_beat). The Ward is a StaticMeshComponent made by physis_center_tools op
# center:drone_ward; the scenario gives it a mesh on kinds 2 and 4 only.
KIND = '(Variables|Default|GetEnemyKind)'
NOW_D = '(Utilities|Time|GetGameTimeinSeconds)'
BOLT = lambda yaw: ('(Game|SpawnActorfromClass :Class "%sBP_EnemyBolt.BP_EnemyBolt_C" :SpawnTransform (Math|Transform|MakeTransform :Location (+ (Transformation|GetActorLocation) (* (Transformation|GetActorForwardVector) 100.0)) :Rotation (Math|Rotator|CombineRotators :A (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw %s) :B (Transformation|GetActorRotation)) :Scale (Math|Vector|MakeVector :X 1.5 :Y 0.07 :Z 0.07)) :CollisionHandlingOverride "AlwaysSpawn")' % (B, yaw))
READY = '(and (Variables|Default|GetInRoom) (not (or (Variables|Default|GetStatic) (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil)))))'


def drone_think():
    """DroneThink, the station's (dronefix.py, written by apply_dronethink.py until 2026-11-08; the station session
    handed it over that day so one script writes it). For EnemyKind 0 in a station room every number is the station's,
    with one change for everyone: an unseen drone stops at the edge of its band instead of flying on into her centre
    (author, 2026-11-08: "many enemies go right where she is"; the station's own hangar test saw the pile-up too).
    In an open level (a BP_Awakening: the Center, the Conclave) the band is measured flat, the station's absolute
    height band (115-165 cm, meaningless on terrain 0-70 m high, which pressed every seen enemy down) is gone, moves are
    level (DroneHover holds the height above the ground, both ways), and a blocked drone inside its band slides away
    from her, not toward her. A drone holding at its band out of sight sets Holding, so the station's no-travel rule
    (which assumed every free drone keeps moving) does not destroy it. So does one in sight inside its band
    (2026-11-08): there it only weaves sideways, reversing every 2.86 s in step with every kind-0 drone, so a 2.5 s
    window can end where it began. A Play test caught all three Reactor Gallery drones destroyed together that way,
    52 cm from their window's start, with Physis standing among them and nothing hurting them. The Aegis Shard (2) turns at 220 deg/s and the
    Onyx Ward (4) at 100 deg/s, so a dodge round them reaches their side; the others face her at once, as before. The
    boss keeps the station's unseen approach.
    Time step (station session's trace, 2026-11-08): every move, turn, timer and push of a drone uses dt, the frame's
    DeltaSeconds clamped to 0.05 s, and DroneThink hands dt to DroneSeparate and DroneStuckCheck (so DroneHover,
    DroneArena and DroneSeparateAll get it too). Unclamped, one long frame moved a station drone by its whole rate:
    above its 165 cm band it drops at up to 516 cm/s, so a 0.33 s frame (Play in the background, ~3 fps) took it from
    194 to 64 in one step (another, lifted ~75 cm by two such frames of its bob, met the overhang above it and counted
    as sunk), and a single hitch of 0.25 s or more mid-fight (a first shader compile, a GC spike) could
    sink one below the z 40 kill line, so to the player it died on its own. At 0.05 s the largest vertical step is
    about 26 cm and the fastest step (a dashing Ember Skitter, about 72 cm) stays inside the 120 cm wall trace. Below
    20 fps drones run slower instead of jumping; above it nothing changes. Far Center drones that Budget ticks every
    0.25 s (over 50 m from her) run at a fifth of their pace, out of reach of any move rule (gap < 18 m)."""
    look = '(Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation) :Target (+ (Transformation|GetActorLocation :self physis) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 30.0)))'
    turn = '(.yaw (Math|Rotator|Delta(Rotator) :A %s :B (Transformation|GetActorRotation)))' % look
    limit = '(* dt (select (== kind 2) 220.0 100.0))'
    slow_yaw = '(+ (.yaw (Transformation|GetActorRotation)) (select (> %s %s) %s (select (< %s (neg %s)) (neg %s) %s)))' % (turn, limit, limit, turn, limit, limit, turn)
    zband = '(select (> (.z (Transformation|GetActorLocation)) (select boss 260.0 165.0)) -0.9 (select (< (.z (Transformation|GetActorLocation)) (select boss 200.0 115.0)) 0.9 0.0))'
    return """(fn DroneThink (DeltaSeconds)
  (bind dt (select (> DeltaSeconds 0.05) 0.05 DeltaSeconds))
  (if (not (Variables|Default|GetHomeSet))
    (Variables|Default|SetHomeSet true)
    (Variables|Default|SetHome (Transformation|GetActorLocation))
    (Variables|Default|SetOpenWorld (> (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass """ + AWAKENING + """)) 0))
    (if (!= """ + KIND + """ 0)
      (Variables|Default|SetPhase (Math|Random|RandomFloatinRange :Min 0.0 :Max 6.28))))
  (CallFunction|DroneSeparate :DeltaSeconds dt)
  (CallFunction|DroneStuckCheck :DeltaSeconds dt)
  (Variables|Default|SetCooldown (- (Variables|Default|GetCooldown) dt))
  (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) dt))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (bind herspot (Transformation|GetActorLocation :self physis))
      (Variables|Default|SetInRoom (or (<= (.x (Variables|Default|GetRoomMax)) (.x (Variables|Default|GetRoomMin))) (and (and (> (.x herspot) (.x (Variables|Default|GetRoomMin))) (< (.x herspot) (.x (Variables|Default|GetRoomMax)))) (and (> (.y herspot) (.y (Variables|Default|GetRoomMin))) (< (.y herspot) (.y (Variables|Default|GetRoomMax)))))))
      (Variables|Default|SetBlocked false)
      (Variables|Default|SetHolding false)
      (bind boxed (> (.x (Variables|Default|GetRoomMax)) (.x (Variables|Default|GetRoomMin))))
      (bind open (Variables|Default|GetOpenWorld))
      (if (and (not (Variables|Default|GetInRoom)) (< (Variables|Default|GetCooldown) 1.2))
        (Variables|Default|SetCooldown 1.2))
      (bind gap (Transformation|GetDistanceTo :OtherActor physis))
      (bind boss (Variables|Default|GetBoss))
      (bind seen (Controller|LineOfSightTo :self (Game|GetPlayerController 0) :Other self))
      (bind kind """ + KIND + """)
      (bind pace (select (== kind 3) 1.9 (select (== kind 1) 0.6 (select (== kind 4) 0.75 1.0))))
      (bind near (select boss 300.0 (select (== kind 3) 450.0 (select (== kind 1) 260.0 (select (== kind 4) 300.0 340.0)))))
      (bind far (select boss 500.0 (select (== kind 3) 800.0 (select (== kind 1) 420.0 (select (== kind 4) 480.0 560.0)))))
      (bind flatgap (Math|Vector|VectorLength (Math|Vector|MakeVector :X (- (.x herspot) (.x (Transformation|GetActorLocation))) :Y (- (.y herspot) (.y (Transformation|GetActorLocation))) :Z 0.0)))
      (bind band (select open flatgap gap))
      (bind dash (and (== kind 3) (and (< (Variables|Default|GetCooldown) 0.35) (< gap 900.0))))
      (if (and boss (and (> (.x (Transformation|GetActorLocation :self physis)) 13480.0) (< (.x (Transformation|GetActorLocation :self physis)) 16400.0)))
        (Class|BPPhysis|SetBossShown :self physis :BossShown (/ (Math|Conversions|ToFloat(Integer) (Variables|Default|GetHealth)) 30.0))
        (elif boss
          (Class|BPPhysis|SetBossShown :self physis :BossShown 0.0)))
      (if (and (and (< gap 1800.0) seen) """ + READY + """)
        (if (or (== kind 4) (== kind 2))
          (Transformation|SetActorRotation :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw """ + slow_yaw + """) :bTeleportPhysics false)
          (else
            (Transformation|SetActorRotation :NewRotation """ + look + """ :bTeleportPhysics false)))
        (bind fwd (select (or (== kind 4) (== kind 2)) (Math|Vector|Normalize (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation))) (Transformation|GetActorForwardVector)))
        (bind ahead (select (or boxed open) (Math|Vector|Normalize (Math|Vector|MakeVector :X (.x fwd) :Y (.y fwd) :Z 0.0)) fwd))
        (bind step (* (+ (+ (* ahead (select dash 1.6 (select (> band far) 1.0 (select (< band near) -1.0 0.0)))) (* (Transformation|GetActorRightVector) (select (> (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 1.1)) 0.0) 0.75 -0.75))) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (+ (* 0.3 (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 3.0))) (select open 0.0 """ + zband + """)))) (* dt (* 430.0 pace))))
        (if (and (not dash) (and (>= band near) (<= band far)))
          (Variables|Default|SetHolding true))
        (bind (wallhit blocked) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* (Math|Vector|Normalize step) (select boss 240.0 120.0))) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (if (not blocked)
          (Transformation|AddActorWorldOffset :DeltaLocation step :bSweep false :bTeleport false)
          (else
            (Variables|Default|SetBlocked true)
            (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) 2.86))
            (bind flat (Math|Vector|Normalize (Math|Vector|MakeVector :X (.x step) :Y (.y step) :Z 0.0)))
            (bind across (Math|Vector|MakeVector :X (neg (.y flat)) :Y (.x flat) :Z 0.0))
            (bind nearer (> (Math|Vector|DotProduct across (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation))) 0.0))
            (bind side (* across (select (or (not open) (> band far)) (select nearer 1.0 -1.0) (select nearer -1.0 1.0))))
            (bind (sidehit sideblocked) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* side (select boss 240.0 120.0))) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
            (if (not sideblocked)
              (Transformation|AddActorWorldOffset :DeltaLocation (* side (Math|Vector|VectorLength step)) :bSweep false :bTeleport false)
              (else
                (Transformation|AddActorWorldOffset :DeltaLocation (* side (* -1.0 (Math|Vector|VectorLength step))) :bSweep false :bTeleport false))))))
      (if (and (and (and (< gap 1800.0) (not seen)) (or boss (> band near))) """ + READY + """)
        (bind toward0 (* (Math|Vector|Normalize (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation))) (* dt (* 300.0 pace))))
        (bind toward (select (or boxed open) (Math|Vector|MakeVector :X (.x toward0) :Y (.y toward0) :Z 0.0) toward0))
        (bind (wallhit2 blocked2) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* (Math|Vector|Normalize toward) 120.0)) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (if (not blocked2)
          (Transformation|AddActorWorldOffset :DeltaLocation toward :bSweep false :bTeleport false)
          (else
            (Variables|Default|SetBlocked true)
            (bind flat2 (Math|Vector|Normalize (Math|Vector|MakeVector :X (.x toward) :Y (.y toward) :Z 0.0)))
            (bind side2 (* (Math|Vector|MakeVector :X (neg (.y flat2)) :Y (.x flat2) :Z 0.0) (select (> (Math|Trig|Sin(Radians) (* (Variables|Default|GetPhase) 0.7)) 0.0) 1.0 -1.0)))
            (bind (sidehit2 sideblocked2) (Collision|LineTraceByChannel :Start (Transformation|GetActorLocation) :End (+ (Transformation|GetActorLocation) (* side2 120.0)) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
            (if (not sideblocked2)
              (Transformation|AddActorWorldOffset :DeltaLocation (* side2 (* dt (* 300.0 pace))) :bSweep false :bTeleport false)
              (else
                (Variables|Default|SetPhase (+ (Variables|Default|GetPhase) 4.49))
                (Transformation|AddActorWorldOffset :DeltaLocation (* side2 (* dt (* -300.0 pace))) :bSweep false :bTeleport false))))))
      (if (and (and (and (< gap 1800.0) (not seen)) (and (not boss) (<= band near))) """ + READY + """)
        (Variables|Default|SetHolding true))
      (if (and (and (< (Variables|Default|GetCooldown) 0.6) """ + READY + """) (and (not (Variables|Default|GetWarned)) (and (< gap 1500.0) seen)))
        (Variables|Default|SetWarned true)
        """ + sound_at('S_SwordHeavy', '(Transformation|GetActorLocation)', .9) + """
        """ + spawn('BP_Spark', '(Transformation|GetActorLocation)') + """)
      (if (and (<= (Variables|Default|GetCooldown) 0.0) """ + READY + """)
        (if (== kind 3)
          (Variables|Default|SetCooldown (Math|Random|RandomFloatinRange :Min 1.4 :Max 2.4))
          (else
            (Variables|Default|SetCooldown (select boss (Math|Random|RandomFloatinRange :Min 1.7 :Max 2.6) (Math|Random|RandomFloatinRange :Min 2.8 :Max 4.6)))))
        (Variables|Default|SetWarned false)
        (if (< gap (select boss 340.0 (select (== kind 1) 300.0 240.0)))
          (if (or (!= kind 4) (> (Math|Vector|DotProduct (Transformation|GetActorForwardVector) (Math|Vector|Normalize (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation)))) 0.3))
            (Class|BPPhysis|PhysisHurt :self physis :FromAhead (> (Transformation|GetDotProductTo :self physis :OtherActor self) 0.0)))
          (elif (and (< gap 1500.0) seen)
            """ + sound_at('S_Laser1', '(Transformation|GetActorLocation)') + """
            """ + BOLT('0.0') + """
            (if boss
              """ + BOLT('18.0') + """
              """ + BOLT('-18.0') + """)))))
    (:CastFailed)))"""


def ward_ready():
    """The Ward component, which DroneStuckCheck reads, through the idempotent op center:drone_ward (physis_center_tools):
    it adds the component if missing and saves BP_TrainingDrone. Without it the DroneStuckCheck write would fail while
    the other drone graphs were written, leaving a mix (2026-11-08 review). A dry run counts as ready."""
    try:
        r = c.call('call_tool', {'toolset_name': 'physis_character_tools.PhysisCharacterTools', 'tool_name': 'outfit_operation',
                                 'arguments': {'operation': 'center:drone_ward'}})
    except Exception as error:  # noqa: BLE001  (dry runs: the stand-in client has no editor)
        print('--- drone_ward (%s)' % str(error)[:60], flush=True)
        return True
    text = r['content'][0]['text'] if r.get('content') else ''
    if r.get('isError') or 'Ward' not in text:
        print('drones: center:drone_ward did not confirm the Ward component, so no drone graph was written:', text[:300], flush=True)
        FAILED.append('drones (no Ward)')
        return False
    return True


def drones():
    if not ward_ready():
        return
    # Every variable these graphs name is made here (var() skips existing names), so no write names a missing one.
    # EnemyKind and the arena are instance-editable: the scenario sets them on placed enemies.
    for name, kind, edit in (('InRoom', 'bool', False), ('Blocked', 'bool', False), ('BlockedSeen', 'bool', False),
                             ('EnemyKind', 'int', True), ('ArenaAt', 'vector', True), ('ArenaIn', 'float', True),
                             ('ArenaOut', 'float', True), ('Dealt', 'int', False), ('ArmorCarry', 'float', False),
                             ('ShieldDownUntil', 'float', False), ('NoteAt', 'float', False), ('HitPower', 'int', False),
                             ('Home', 'vector', False), ('HomeSet', 'bool', False), ('OpenWorld', 'bool', False),
                             ('ArenaR', 'float', False), ('ArenaK', 'float', False), ('PairNear', 'bool', False),
                             ('PairFor', 'float', False), ('Holding', 'bool', False), ('SunkOnce', 'bool', False)):
        var(DR, name, kind, edit)
    # The station's drone is a 47 cm sphere; the Center reskins drones as crystals up to 5.5 m tall whose
    # centre sits up to 3.9 m above their lowest point. They move without sweeping and have no collider of
    # their own, so they sank into the terrain, and the station's stuck rules (a surface within 70 cm above
    # the centre, a height under 40 cm, 0.75 s without moving) then destroyed them. In the Center the crystal's
    # bounds are its collider instead: its lowest point is held 20 cm above the ground below its centre, more
    # on a slope for its width, and never below the water line (z 0), and nothing destroys it.
    # An arena drone (ArenaOut > 0: the temple guardians, on a flat floor) is never let below the height it was placed
    # at instead: the downward trace from its centre could land on a crystal tip, the pedestal or the gate ring and
    # throw it metres up into the temple (2026-11-08 review of "some enemies got stuck in the temple itself").
    # It also comes down again (2026-11-08 review): the station's height band used to press every open-level enemy
    # down, and without it a drone lifted by a rise, a rock or its own bob kept that height when the ground fell away,
    # out of the sword's reach. A body more than 60 cm over its floor (arena: 60 cm over home) sinks at up to 300 cm/s.
    graph(DR, 'DroneHover', [('DeltaSeconds', 'float')])
    fn(DR, 'DroneHover', """(fn DroneHover (DeltaSeconds)
  (if (and (> (Variables|Default|GetArenaOut) 0.0) (Variables|Default|GetHomeSet))
    (if (< (.z (Transformation|GetActorLocation)) (.z (Variables|Default|GetHome)))
      (Transformation|AddActorWorldOffset :DeltaLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (- (.z (Variables|Default|GetHome)) (.z (Transformation|GetActorLocation)))) :bSweep false :bTeleport false)
      (elif (> (.z (Transformation|GetActorLocation)) (+ (.z (Variables|Default|GetHome)) 60.0))
        (Transformation|AddActorWorldOffset :DeltaLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (* DeltaSeconds -300.0)) :bSweep false :bTeleport false)))
    (else
      (bind (centre extent) (Collision|GetActorBounds :bOnlyCollidingComponents false))
      (bind (below hit) (Collision|LineTraceByChannel :Start centre :End (- centre (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (+ (.z extent) 4000.0))) :TraceChannel "Visibility" :bTraceComplex true :DrawDebugType "None" :bIgnoreSelf true))
      (bind (blocking overlap time dist where impact normal) (Collision|BreakHitResult below))
      (bind ground (select hit (select (> (.z impact) 0.0) (.z impact) 0.0) 0.0))
      (bind half (* 0.8 (select (> (.x extent) (.y extent)) (.x extent) (.y extent))))
      (bind slope (/ (Math|Vector|VectorLength (Math|Vector|MakeVector :X (.x normal) :Y (.y normal) :Z 0.0)) (select (> (.z normal) 0.3) (.z normal) 0.3)))
      (bind floor (+ (+ ground 20.0) (select hit (* half slope) 0.0)))
      (bind lowest (- (.z centre) (.z extent)))
      (if (< lowest floor)
        (Transformation|AddActorWorldOffset :DeltaLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (- floor lowest)) :bSweep false :bTeleport false)
        (elif (> lowest (+ floor 60.0))
          (Transformation|AddActorWorldOffset :DeltaLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (neg (select (> (- lowest floor) (* DeltaSeconds 300.0)) (* DeltaSeconds 300.0) (- lowest floor)))) :bSweep false :bTeleport false))))))""")
    # The temple arena (Center only, inert while ArenaOut is 0). Its guardians are kept between ArenaIn and ArenaOut
    # (flat distance from ArenaAt: clear of the crystal ring and of the colonnade), and one that is engaged and blocked
    # and has moved under 60 cm in 2.5 s is put back where it was placed (Home, recorded by DroneThink's first tick).
    # Being held by the ring is not being stuck: the clamp restarts the window (2026-11-08 review: a guardian pressing
    # in toward her at the pedestal was otherwise sent home every few seconds), and so is waiting out of sight. Nothing destroys a Center enemy (author, 2026-11-04). StuckFor, LastSpot and BlockedSeen are the
    # station branch's, unused in the Center otherwise. ArenaR/ArenaK are variables because a bound pure value would be
    # read again after the move.
    graph(DR, 'DroneArena', [('DeltaSeconds', 'float')])
    fn(DR, 'DroneArena', """(fn DroneArena (DeltaSeconds)
  (if (and (> (Variables|Default|GetArenaOut) 0.0) (Variables|Default|GetHomeSet))
    (Variables|Default|SetArenaR (Math|Vector|VectorLength (Math|Vector|MakeVector :X (- (.x (Transformation|GetActorLocation)) (.x (Variables|Default|GetArenaAt))) :Y (- (.y (Transformation|GetActorLocation)) (.y (Variables|Default|GetArenaAt))) :Z 0.0)))
    (Variables|Default|SetArenaK (/ (select (> (Variables|Default|GetArenaR) (Variables|Default|GetArenaOut)) (Variables|Default|GetArenaOut) (select (< (Variables|Default|GetArenaR) (Variables|Default|GetArenaIn)) (Variables|Default|GetArenaIn) (Variables|Default|GetArenaR))) (select (> (Variables|Default|GetArenaR) 1.0) (Variables|Default|GetArenaR) 1.0)))
    (if (or (> (Variables|Default|GetArenaK) 1.001) (< (Variables|Default|GetArenaK) 0.999))
      (Transformation|SetActorLocation :NewLocation (Math|Vector|MakeVector :X (+ (.x (Variables|Default|GetArenaAt)) (* (- (.x (Transformation|GetActorLocation)) (.x (Variables|Default|GetArenaAt))) (Variables|Default|GetArenaK))) :Y (+ (.y (Variables|Default|GetArenaAt)) (* (- (.y (Transformation|GetActorLocation)) (.y (Variables|Default|GetArenaAt))) (Variables|Default|GetArenaK))) :Z (.z (Transformation|GetActorLocation))) :bSweep false :bTeleport true)
      (Variables|Default|SetStuckFor 0.0)
      (Variables|Default|SetBlockedSeen false)
      (Variables|Default|SetLastSpot (Transformation|GetActorLocation)))
    (Variables|Default|SetStuckFor (+ (Variables|Default|GetStuckFor) DeltaSeconds))
    (if (Variables|Default|GetBlocked)
      (Variables|Default|SetBlockedSeen true))
    (if (>= (Variables|Default|GetStuckFor) 2.5)
      (if (and (and (< (Transformation|GetDistanceTo :OtherActor (Game|GetPlayerPawn 0)) 1800.0) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil))) (and (Variables|Default|GetBlockedSeen) (< (Math|Vector|Distance(Vector) :V1 (Transformation|GetActorLocation) :V2 (Variables|Default|GetLastSpot)) 60.0)))
        (Transformation|SetActorLocation :NewLocation (Variables|Default|GetHome) :bSweep false :bTeleport true))
      (Variables|Default|SetBlockedSeen false)
      (Variables|Default|SetStuckFor 0.0)
      (Variables|Default|SetLastSpot (Transformation|GetActorLocation)))))""")
    # The station branch is the station's own DroneStuckCheck (its dronefix.py). One change since (station session,
    # 2026-11-07): a drone counts as active only while InRoom. DroneThink sets InRoom from the drone's RoomMin/RoomMax
    # box, and true when no box is set, as for every Center and Conclave drone. Otherwise idle drones in the next room
    # would count as stuck and be destroyed.
    # Reactor Gallery fix (author: "Yes, fix it", via the station session, 2026-11-07). The station's drones steered into
    # the reactor core and stood still, and the 0.75 s no-travel rule killed all three within about 4 s. Now:
    # - Sunk or z below 40 kills when it holds on two ticks in a row (SunkOnce; station session, 2026-11-08), so one
    #   odd frame does not. The grace counts ticks, not time: between the two checks the floor push below lifts a
    #   dipped drone by 600 cm/s x dt, 30 cm at 20 fps or slower but about 10 cm at 60 fps. Sunk means a surface within
    #   20 cm above the drone's centre, found by a downward trace from 20 cm above it. It was 70 cm, which read the
    #   underside of 'Scene Climb 1', 51-61 cm above the gallery's drones, as sunk and killed all three (station
    #   session's watch probe). Station drones hover 115-165 cm over floors at about 0, so z below 40 still catches one
    #   sinking into the floor. DeltaSeconds here is DroneThink's dt (at most 0.05 s), so the floor push lifts at most
    #   30 cm a tick, well inside its 80 cm roof check.
    # - No travel kills only after 2.5 s, and never when DroneThink set Blocked (its forward trace hit something it now
    #   slides along) or Holding (waiting at its band, in sight or not; 2026-11-08) at any time in that window. BlockedSeen latches it, so a drone sliding along a wall cannot be
    #   caught between two blocked frames.
    # Station session, 2026-11-08 (the Drone Hangar): two drones closer than 45 cm both die only after 1.5 s together
    # while active (PairFor), not the moment they cross; and the floor push (a surface within 60 cm under it lifts it)
    # never lifts a drone above 3 m or into anything within 80 cm overhead, since the hangar's drone that started in a
    # 4.5 m pillar was pushed up through the 4.7 m ceiling and out of reach.
    # The Aegis Shard's Ward plate shows only while its ward is up: not broken (ShieldDownUntil past) and not stunned
    # (Settle, a parry), since a stunned Aegis takes blows from the front too (DroneArmour), in every level.
    fn(DR, 'DroneStuckCheck', """(fn DroneStuckCheck (DeltaSeconds)
  (if (== """ + KIND + """ 2)
    (Rendering|SetVisibility :self (Variables|Default|GetWard) :bNewVisibility (and (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetShieldDownUntil)) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil)))))
  (if (not (or (Variables|Default|GetBoss) (Variables|Default|GetStatic)))
    (bind directors (Actor|GetAllActorsOfClass :ActorClass %s))
    (if (> (Utilities|Array|Length directors) 0)
      (CallFunction|DroneArena :DeltaSeconds DeltaSeconds)
      (CallFunction|DroneHover :DeltaSeconds DeltaSeconds)
      (else
        (bind here (Transformation|GetActorLocation))
        (bind active (and (and (< (Transformation|GetDistanceTo :OtherActor (Game|GetPlayerPawn 0)) 1800.0) (Variables|Default|GetInRoom)) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil))))
        (Variables|Default|SetStuckFor (+ (Variables|Default|GetStuckFor) DeltaSeconds))
        (if (not active)
          (Variables|Default|SetSpotActive false))
        (Variables|Default|SetPairNear false)
        (for other (Actor|GetAllActorsOfClass :ActorClass %s)
          (if (and active (and (> (Transformation|GetDistanceTo :OtherActor other) 1.0) (< (Transformation|GetDistanceTo :OtherActor other) 45.0)))
            (Variables|Default|SetPairNear true)))
        (Variables|Default|SetPairFor (select (Variables|Default|GetPairNear) (+ (Variables|Default|GetPairFor) DeltaSeconds) 0.0))
        (if (>= (Variables|Default|GetPairFor) 1.5)
          (CallFunction|TakeHit :Amount 99))
        (bind (sunkhit sunk) (Collision|LineTraceByChannel :Start (+ here (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 20.0)) :End here :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (if (and active (or sunk (< (.z here) 40.0)))
          (if (Variables|Default|GetSunkOnce)
            (CallFunction|TakeHit :Amount 99)
            (else
              (Variables|Default|SetSunkOnce true)))
          (else
            (Variables|Default|SetSunkOnce false)))
        (if (or (Variables|Default|GetBlocked) (Variables|Default|GetHolding))
          (Variables|Default|SetBlockedSeen true))
        (if (>= (Variables|Default|GetStuckFor) 2.5)
          (if (and (and active (Variables|Default|GetSpotActive)) (and (not (Variables|Default|GetBlockedSeen)) (< (Math|Vector|Distance(Vector) :V1 here :V2 (Variables|Default|GetLastSpot)) 60.0)))
            (CallFunction|TakeHit :Amount 99))
          (Variables|Default|SetSpotActive active)
          (Variables|Default|SetBlockedSeen false)
          (Variables|Default|SetStuckFor 0.0)
          (Variables|Default|SetLastSpot (Transformation|GetActorLocation)))
        (bind (floorhit low) (Collision|LineTraceByChannel :Start here :End (- here (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 60.0)) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (bind (roofhit roof) (Collision|LineTraceByChannel :Start here :End (+ here (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 80.0)) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
        (if (and low (and (not roof) (< (.z here) 300.0)))
          (Transformation|AddActorWorldOffset :DeltaLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (* DeltaSeconds 600.0)) :bSweep false :bTeleport false))))))""" % (AWAKENING, DRONE))
    # Separation: the station checks every drone against every other drone each frame, which at the Center's
    # numbers (hundreds) cost most of a frame. The station's logic is kept as DroneSeparateAll; in the Center
    # it runs five times a second, with the time since the last run, and only for drones within 50 m of her
    # (BP_Awakening Budget also slows far drones' ticks). Bumps no longer cost health (station session, 2026-11-08:
    # hangar drones piling on her killed each other); the push and the spark stay.
    var(DR, 'SepWait', 'float')
    graph(DR, 'DroneSeparateAll', [('DeltaSeconds', 'float')])
    graph(DR, 'DroneSeparateCenter', [('DeltaSeconds', 'float')])
    spark = ('(Game|SpawnActorfromClass :Class "%sBP_Spark.BP_Spark_C" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation)'
             ' :Rotation (Math|Rotator|MakeRotator :Yaw 0.0) :Scale (Math|Vector|MakeVector :X 1.0 :Y 1.0 :Z 1.0)) :CollisionHandlingOverride "AlwaysSpawn")' % B)
    fn(DR, 'DroneSeparateAll', """(fn DroneSeparateAll (DeltaSeconds)
  (Variables|Default|SetBumpCool (- (Variables|Default|GetBumpCool) DeltaSeconds))
  (for other (Actor|GetAllActorsOfClass :ActorClass %s)
    (bind apart (Transformation|GetDistanceTo :OtherActor other))
    (if (and (> apart 1.0) (< apart (select (Variables|Default|GetBoss) 300.0 150.0)))
      (bind away (Math|Vector|Normalize (- (Transformation|GetActorLocation) (Transformation|GetActorLocation :self other))))
      (Transformation|AddActorWorldOffset :DeltaLocation (* (Math|Vector|MakeVector :X (.x away) :Y (.y away) :Z 0.0) (* DeltaSeconds 600.0)) :bSweep false :bTeleport false)
      (if (and (<= (Variables|Default|GetBumpCool) 0.0) (not (Variables|Default|GetBoss)))
        (Variables|Default|SetBumpCool 1.0)
        %s))))""" % (DRONE, spark))
    fn(DR, 'DroneSeparateCenter', """(fn DroneSeparateCenter (DeltaSeconds)
  (Variables|Default|SetSepWait (+ (Variables|Default|GetSepWait) DeltaSeconds))
  (if (>= (Variables|Default|GetSepWait) 0.2)
    (if (and (not (Variables|Default|GetStatic)) (< (Transformation|GetDistanceTo :OtherActor (Game|GetPlayerPawn 0)) 5000.0))
      (CallFunction|DroneSeparateAll :DeltaSeconds (select (> (Variables|Default|GetSepWait) 0.25) 0.25 (Variables|Default|GetSepWait))))
    (Variables|Default|SetSepWait 0.0)))""")
    fn(DR, 'DroneSeparate', """(fn DroneSeparate (DeltaSeconds)
  (bind directors (Actor|GetAllActorsOfClass :ActorClass %s))
  (if (> (Utilities|Array|Length directors) 0)
    (CallFunction|DroneSeparateCenter :DeltaSeconds DeltaSeconds)
    (else
      (CallFunction|DroneSeparateAll :DeltaSeconds DeltaSeconds))))""" % AWAKENING)
    # Drops. The station's TakeHit (its dronefix.py) puts an enemy's crystal and its capsule or ammo cell at z 125,
    # the station's floor height; the Center's ground is 0 to 70 m high, so nearly every drop there spawned inside
    # the terrain, out of reach (author, 2026-11-04: "I'm struggling to find health"). TakeHit is written whole here:
    # the station branch is the station's code unchanged; the Center branch calls DroneDrop, which rests the loot
    # 1.2 m above the first surface under the enemy (40 cm above the water) and scales the drop with the enemy's
    # level (StartHealth): L1 a crystal and a 50% capsule, L2 70%, L3 always, L4 and L5 more, 40% ammo; crystal
    # locks and prisms (Static) give one crystal, at her feet. Dropped stops a second TakeHit dropping twice.
    for name, kind in (('StartHealth', 'int'), ('Dropped', 'bool'), ('LootAt', 'vector')):
        var(DR, name, kind)
    graph(DR, 'DroneDrop')
    graph(DR, 'DroneDropOne', [('Kind', 'int'), ('DX', 'float'), ('DY', 'float')])
    graph(DR, 'DroneArmour', [('Amount', 'int')])
    code = drops_code()
    fn(DR, 'DroneDropOne', code['DroneDropOne'])
    fn(DR, 'DroneDrop', code['DroneDrop'])
    fn(DR, 'DroneArmour', code['DroneArmour'])
    fn(DR, 'TakeHit', code['TakeHit'])
    graph(DR, 'DroneThink', [('DeltaSeconds', 'float')])
    fn(DR, 'DroneThink', drone_think())
    comp(DR)


def drops_code():
    out = {}
    roll = '(Math|Random|RandomFloatinRange :Min 0.0 :Max 1.0)'
    # A drop that is never collected goes after three minutes (BP_Pickup ticks; placed pickups keep no life span).
    out['DroneDropOne'] = """(fn DroneDropOne (Kind DX DY)
  (bind drop """ + spawn('BP_Pickup', '(+ (Variables|Default|GetLootAt) (Math|Vector|MakeVector :X DX :Y DY :Z 0.0))') + """)
  (Class|BPPickup|PickupSetup :self drop :Value Kind)
  (Actor|SetLifeSpan :self drop :InLifespan 180.0))"""
    # LootAt: 1.2 m above the first surface under the enemy (40 cm above the water line where that is water); at her
    # own position (so it is taken at once) for a Static target, when nothing is under the enemy, or when the loot
    # would float more than 130 cm (BP_Pickup's reach) above her centre (rock, wall and pillar tops she cannot
    # collect from below; review, 2026-11-05) or 8 m below her (mesa edges).
    # Level tiers come from StartHealth (ENEMY_ENTRIES health 5, 9, 16, 26, 60; locks 6 or 8; prisms 1).
    # Whether an enemy drops anything at all is a roll (author, 2026-11-09: "Enemies don't need to leave loot
    # necessarily. Make it random if they drop loot or not."): L1 half the time, L2 60%, L3 70%, L4 85%, L5 always.
    # When it drops, the table below is unchanged. Static locks and prisms still always give their crystal: they are
    # puzzle pieces, not enemies. Every kill drops while she is short (needy: under 25 Divinity, the dearest single
    # cost, Mend's, or under 30% health): crystals come mostly from enemies, so a run of failed rolls could otherwise
    # leave her unable to pay a required node (the station's Reactor Lift costs 20; review, 2026-11-09).
    chance = '(select (>= level 60) 1.0 (select (>= level 26) 0.85 (select (>= level 16) 0.7 (select (>= level 9) 0.6 0.5))))'
    needy = ('(or (< (Class|BPPhysis|GetDivinity :self physis) 25.0) (< (Class|BPPhysis|GetPhysisHealth :self physis) '
             '(* 0.3 (Class|BPPhysis|GetMaxHealth :self physis))))')
    out['DroneDrop'] = """(fn DroneDrop ()
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (bind here (Transformation|GetActorLocation))
      (bind her (Transformation|GetActorLocation :self physis))
      (bind (below hit) (Collision|LineTraceByChannel :Start here :End (- here (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 8000.0)) :TraceChannel "Visibility" :bTraceComplex true :DrawDebugType "None" :bIgnoreSelf true))
      (bind (blocking overlap time dist where impact normal) (Collision|BreakHitResult below))
      (Variables|Default|SetLootAt (Math|Vector|MakeVector :X (.x here) :Y (.y here) :Z (select (> (.z impact) 0.0) (+ (.z impact) 120.0) 40.0)))
      (if (or (or (Variables|Default|GetStatic) (not hit)) (or (> (- (.z (Variables|Default|GetLootAt)) (.z her)) 130.0) (< (- (.z (Variables|Default|GetLootAt)) (.z her)) -800.0)))
        (Variables|Default|SetLootAt (+ her (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 30.0))))
      (bind level (Variables|Default|GetStartHealth))
      (if (or (or (Variables|Default|GetStatic) """ + needy + """) (< """ + roll + ' ' + chance + """))
        (CallFunction|DroneDropOne :Kind 1 :DX 0.0 :DY 0.0)
        (if (>= level 26)
          (CallFunction|DroneDropOne :Kind 1 :DX -60.0 :DY 55.0))
        (if (>= level 60)
          (CallFunction|DroneDropOne :Kind 1 :DX 55.0 :DY -60.0))
        (if (not (Variables|Default|GetStatic))
          (if (or (>= level 16) (< """ + roll + """ (select (>= level 9) 0.7 0.5)))
            (CallFunction|DroneDropOne :Kind 0 :DX 70.0 :DY 40.0))
          (if (or (>= level 60) (and (>= level 26) (< """ + roll + """ 0.5)))
            (CallFunction|DroneDropOne :Kind 0 :DX -70.0 :DY -40.0))
          (if (< """ + roll + """ 0.4)
            (CallFunction|DroneDropOne :Kind 2 :DX 10.0 :DY -80.0)))))
    (:CastFailed)))"""
    # How each kind turns a blow (the kind notes at the top of this section). It sets Dealt, the damage TakeHit then
    # takes. HitPower is the blow's raw strength before augmentations (PhysisStrikeNow: 1-2 light, 2-3 heavy
    # finishers, 4 the parry counter; PhysisShotHit: 1 a tap, 4 the Divine Shot, 5 charged); 3 or more is heavy. It is
    # 0 for anything else (Settle's 1), and then Amount stands for it. front is the flat facing toward her.
    face = '(+ (Transformation|GetActorLocation) (* flat 90.0))'
    turned = lambda message: ('(Variables|Default|SetDealt 0)\n        ' + spawn('BP_Spark', face) + '\n        ' + sound_at('S_Block', face, .9) +
                              '\n        (if (> now (Variables|Default|GetNoteAt))\n          (Variables|Default|SetNoteAt (+ now 4.0))\n          '
                              '(Class|BPPhysis|PhysisNote :self physis :Message "%s"))' % message)
    out['DroneArmour'] = """(fn DroneArmour (Amount)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (bind now """ + NOW_D + """)
      (bind kind """ + KIND + """)
      (bind flat (Math|Vector|Normalize (Math|Vector|MakeVector :X (.x (Transformation|GetActorForwardVector)) :Y (.y (Transformation|GetActorForwardVector)) :Z 0.0)))
      (bind toher (Math|Vector|Normalize (Math|Vector|MakeVector :X (- (.x (Transformation|GetActorLocation :self physis)) (.x (Transformation|GetActorLocation))) :Y (- (.y (Transformation|GetActorLocation :self physis)) (.y (Transformation|GetActorLocation))) :Z 0.0)))
      (bind front (Math|Vector|DotProduct flat toher))
      (bind heavy (>= (select (> (Variables|Default|GetHitPower) 0) (Variables|Default|GetHitPower) Amount) 3))
      (bind stunned (< now (Variables|Default|GetStunUntil)))
      (if (== kind 1)
        (Variables|Default|SetArmorCarry (+ (Variables|Default|GetArmorCarry) (* (Math|Conversions|ToFloat(Integer) Amount) (select (or heavy stunned) 1.0 0.5))))
        (Variables|Default|SetDealt (Math|Float|Truncate (Variables|Default|GetArmorCarry)))
        (Variables|Default|SetArmorCarry (- (Variables|Default|GetArmorCarry) (Math|Conversions|ToFloat(Integer) (Variables|Default|GetDealt))))
        (if (not (or heavy stunned))
          """ + sound_at('S_Block', face, .6) + """
          (if (> now (Variables|Default|GetNoteAt))
            (Variables|Default|SetNoteAt (+ now 4.0))
            (Class|BPPhysis|PhysisNote :self physis :Message "Its plating turns light blows: strike heavy, parry or Settle it"))))
      (if (and (== kind 2) (and (> front 0.35) (and (not stunned) (>= now (Variables|Default|GetShieldDownUntil)))))
        (if heavy
          (Variables|Default|SetDealt 0)
          """ + spawn('BP_Spark', face) + """
          (Variables|Default|SetShieldDownUntil (+ now 4.0))
          (Variables|Default|SetStunUntil (+ now 1.2))
          """ + sound_at('S_DroneExplosion', face, .5) + """
          (Class|BPPhysis|PhysisNote :self physis :Message "Ward broken")
          (else
            """ + turned('Its ward turns the blow: strike its side or back, or break it with a heavy blow') + """)))
      (if (and (== kind 4) (> front 0.35))
        """ + turned('Its face turns every blow: strike its sides or back') + """))
    (:CastFailed)))"""
    # TakeHit, written whole. The station branch is the station's TakeHit (its dronefix.py) except for the loot roll below; StartHealth is
    # recorded on the first hit (no effect on the station). Dropped keeps a second TakeHit of the same dying enemy from
    # dropping twice in the Center. A kind's armour decides the damage (DroneArmour sets Dealt); Kind 0 takes Amount, as
    # before, and so does every kind for the stuck rules' 99. Since 2026-11-09 a station drone drops its crystal and
    # capsule or ammo only 60% of the time (the author's random loot); the boss and Static targets always drop, and so
    # does every drone while she is short (needy, above).
    station_loot = """(bind loot (Math|Vector|MakeVector :X (.x (Transformation|GetActorLocation)) :Y (.y (Transformation|GetActorLocation)) :Z 125.0))
                (bind crystal """ + spawn('BP_Pickup', 'loot') + """)
                (Class|BPPickup|PickupSetup :self crystal :Value 1)
                (bind extra """ + spawn('BP_Pickup', '(+ loot (Math|Vector|MakeVector :X 70.0 :Y 40.0 :Z 0.0))') + """)
                (Class|BPPickup|PickupSetup :self extra :Value (select (> (Math|Random|RandomFloatinRange :Min 0.0 :Max 1.0) 0.5) 0 2))"""
    out['TakeHit'] = """(fn TakeHit (Amount)
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (bind there (Math|Vector|Normalize (- (Transformation|GetActorLocation :self physis) (Transformation|GetActorLocation))))
      (bind facing (Math|Vector|DotProduct (Transformation|GetActorForwardVector) there))
      (if (and (Variables|Default|GetBoss) (> facing -0.35))
        (if (and (> facing 0.35) (> (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetStunUntil)))
          (Variables|Default|SetEyeHits (+ (Variables|Default|GetEyeHits) 1))
          """ + spawn('BP_Spark', '(+ (Transformation|GetActorLocation) (* (Transformation|GetActorForwardVector) 110.0))') + """
          (if (>= (Variables|Default|GetEyeHits) 3)
            (Variables|Default|SetEyeHits 0)
            (Variables|Default|SetStunUntil (+ (Utilities|Time|GetGameTimeinSeconds) 5.0))
            """ + sound_at('S_DroneExplosion', '(Transformation|GetActorLocation)', .6) + """
            (Class|BPPhysis|PhysisSlow :self physis :Rate 0.25 :Seconds 0.4)
            (Class|BPPhysis|PhysisSay :self physis :Message "The Mecha Breacher is paralysed!~Get behind it and strike its back.")
            (else
              (Class|BPPhysis|PhysisSay :self physis :Message "The red eye flickers. Strike it again.")))
          (else
            (Class|BPPhysis|PhysisSay :self physis :Message "The front armor turns your attack.~Its back is the weak point.")))
        (else
          (Variables|Default|SetDealt Amount)
          (if (and (!= """ + KIND + """ 0) (< Amount 99))
            (CallFunction|DroneArmour :Amount Amount))
          (Variables|Default|SetHitPower 0)
          (if (== (Variables|Default|GetStartHealth) 0)
            (Variables|Default|SetStartHealth (Variables|Default|GetHealth)))
          (Variables|Default|SetHealth (- (Variables|Default|GetHealth) (Variables|Default|GetDealt)))
          (if (<= (Variables|Default|GetHealth) 0)
            """ + sound_at('S_DroneExplosion', '(Transformation|GetActorLocation)') + """
            """ + spawn('BP_DroneBurst', '(Transformation|GetActorLocation)') + """
            (bind directors (Actor|GetAllActorsOfClass :ActorClass """ + AWAKENING + """))
            (if (> (Utilities|Array|Length directors) 0)
              (if (not (Variables|Default|GetDropped))
                (Variables|Default|SetDropped true)
                (CallFunction|DroneDrop))
              (else
                (if (or (or (or (Variables|Default|GetBoss) (Variables|Default|GetStatic)) """ + needy + """) (< """ + roll + """ 0.6))
                  """ + station_loot + """)))
            (Class|BPPhysis|PhysisSlow :self physis :Rate 0.22 :Seconds 0.55)
            (Class|BPPhysis|SetBossShown :self physis :BossShown 0.0)
            (for tag (Actor|GetAttachedActors)
              (Actor|DestroyActor :self tag))
            (Actor|DestroyActor)))))
    (:CastFailed)))"""
    return out


# ---------------------------------------------------------------- encounters

def encounters():
    # How many are left (author, 2026-11-08: "when I got to the Light temple I couldn't tell how many enemies I
    # needed to defeat"). An encounter with a Goal (instance-editable; '' keeps today's behaviour, as in the station
    # and the Conclave) shows "<Goal>: N left" as the objective while she is within its Radius and enemies remain, and
    # puts back the objective it replaced when she leaves or the fight is won. It writes Objective directly, because
    # PhysisQuest would file every count in the Completed list. Shown is the count on screen, so the text changes
    # only when the count does. Whatever else sets the objective during the fight (a Still Point's first visit) becomes
    # the one put back afterwards, and the count is shown again. A save never holds a count: PhysisSaveGame stores the
    # objective it stands in for. (An encounter out of range used to reset a count line to its plain Goal, which let two
    # fights with the same Goal text undo each other in Play, 2026-11-08; it is gone.)
    for name, kind, edit in (('Goal', 'string', True), ('Radius', 'float', True), ('Before', 'string', False),
                             ('Showing', 'bool', False), ('Shown', 'int', False)):
        var(EN, name, kind, edit)
    graph(EN, 'FightLine')
    mine = '(Utilities|String|StartsWith :SourceString (Class|BPPhysis|GetObjective :self physis) :InPrefix (Utilities|String|Append :A (Variables|Default|GetGoal) :B ": "))'
    fn(EN, 'FightLine', """(fn FightLine ()
  (if (not (Utilities|String|EqualExactly(String) :A (Variables|Default|GetGoal) :B ""))
    (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
      (:then
        (if (and (> (Variables|Default|GetLeft) 0) (< (Transformation|GetDistanceTo :OtherActor physis) (Variables|Default|GetRadius)))
          (if (or (not """ + mine + """) (!= (Variables|Default|GetLeft) (Variables|Default|GetShown)))
            (if (not """ + mine + """)
              (Variables|Default|SetBefore (Class|BPPhysis|GetObjective :self physis)))
            (Variables|Default|SetShowing true)
            (Variables|Default|SetShown (Variables|Default|GetLeft))
            (Class|BPPhysis|SetObjective :self physis :Objective (Utilities|String|Append :A (Variables|Default|GetGoal) :B (Utilities|String|Append :A ": " :B (Utilities|String|Append :A (Utilities|String|ToString(Integer) (Variables|Default|GetLeft)) :B " left")))))
          (elif (Variables|Default|GetShowing)
            (Variables|Default|SetShowing false)
            (Class|BPPhysis|SetObjective :self physis :Objective (select (Utilities|String|EqualExactly(String) :A (Variables|Default|GetBefore) :B "") (Variables|Default|GetGoal) (Variables|Default|GetBefore))))))
      (:CastFailed))))""")
    comp(EN)
    # A won fight gives its token, may set the next quest, and shows its message. Optional Center fights
    # (Glade Edge, the prisms, Thornveil, the Sentinels) have no next goal, and PhysisQuest "" moved the
    # current objective to Completed and left the Main Quest empty. Every station fight has one.
    fn(EN, 'EventGraph', """(event EventTick (DeltaSeconds)
  (if (not (Variables|Default|GetDone))
    (Variables|Default|SetLeft 0)
    (for found (Actor|GetAllActorsOfClass :ActorClass %s)
      (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found)
        (:then
          (if (== (Class|BPTrainingDrone|GetRoomId :self drone) (Variables|Default|GetRoom))
            (Variables|Default|SetLeft (+ (Variables|Default|GetLeft) 1))))
        (:CastFailed)))
    (CallFunction|FightLine)
    (if (== (Variables|Default|GetLeft) 0)
      (Variables|Default|SetDone true)
      (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
        (:then
          (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive))
          (if (not (Utilities|String|EqualExactly(String) :A (Variables|Default|GetNextGoal) :B ""))
            (Class|BPPhysis|PhysisQuest :self physis :Goal (Variables|Default|GetNextGoal)))
          (Class|BPPhysis|PhysisLearnN :self physis :Count (Variables|Default|GetLearn) :Message (Variables|Default|GetMessage)))
        (:CastFailed)))))""" % DRONE)
    comp(EN)


# ---------------------------------------------------------------- augmentations in combat
# Copies of the station's graphs (scenario_bp.py and feel.py PhysisStrikeNow, combat.py PhysisShotHit,
# parry2.py PhysisHurt and PhysisThreatCheck, feat.py PhysisBlock) with the augmentation values applied.

AUDIO = '/Game/Audio/'
MONTAGES = '/Game/Characters/Physis/Animations/Katana/Montages/'
NOW = '(Utilities|Time|GetGameTimeinSeconds)'
ANIM = '(bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))'


def sound(name, volume=1.0, pitch=1.0):
    return '(Audio|PlaySound2D :Sound "%s%s.%s" :VolumeMultiplier %s :PitchMultiplier %s)' % (AUDIO, name, name, volume, pitch)


def sound_at(name, where, volume=1.0):
    return '(Audio|PlaySoundatLocation :Sound "%s%s.%s" :Location %s :VolumeMultiplier %s)' % (AUDIO, name, name, where, volume)


def spawn(bp, where, rot='(Math|Rotator|MakeRotator :Yaw 0.0)'):
    return ('(Game|SpawnActorfromClass :Class "%s%s.%s_C" :SpawnTransform (Math|Transform|MakeTransform :Location %s :Rotation %s '
            ':Scale (Math|Vector|MakeVector :X 1.0 :Y 1.0 :Z 1.0)) :CollisionHandlingOverride "AlwaysSpawn")') % (B, bp, bp, where, rot)


def play(name, rate):
    return '(Animation|Montage|MontagePlay :self anim :MontageToPlay "%sAM_Physis_%s.AM_Physis_%s" :InPlayRate %s)' % (MONTAGES, name, name, rate)


def parry_beat(stun=False):
    """parry2.py's parry: freeze-frame, steel and boom, sparks around her, a hard shake, a cyclone counter. A Perfect
    Parry (stun) also staggers every enemy kind within 4.2 m for 2.5 s and drops an Aegis Shard's ward for 4 s, so the
    counter lands (2026-11-08); Kind 0 enemies are left as they were, and so is Divine Parry (the Settings assist, Off
    by default since 2026-11-09, PhysisHurt)."""
    spark = lambda offset: spawn('BP_Spark', '(+ (Transformation|GetActorLocation) %s)' % offset)
    stagger = ('(for found (Actor|GetAllActorsOfClass :ActorClass %s) (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found) '
               '(:then (if (and (!= (Class|BPTrainingDrone|GetEnemyKind :self drone) 0) (< (Transformation|GetDistanceTo :OtherActor drone) 420.0)) '
               '(Class|BPTrainingDrone|SetStunUntil :self drone :StunUntil (select (> (+ now 2.5) (Class|BPTrainingDrone|GetStunUntil :self drone)) (+ now 2.5) (Class|BPTrainingDrone|GetStunUntil :self drone))) (Class|BPTrainingDrone|SetShieldDownUntil :self drone :ShieldDownUntil (+ now 4.0)))) '
               '(:CastFailed)))' % DRONE)
    lines = ([stagger] if stun else []) + [sound('S_Parry', 1.0), sound('S_SwordHeavy', 0.9, 0.7), sound('S_DroneExplosion', 0.35, 1.3),
             spark('(+ (* (Transformation|GetActorForwardVector) 60.0) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 120.0))'),
             spark('(+ (* (Transformation|GetActorRightVector) 45.0) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 150.0))'),
             spark('(+ (* (Transformation|GetActorRightVector) -45.0) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 95.0))'),
             '(Variables|Default|SetShakeAmount 12.0)', '(Variables|Default|SetSafeUntil (+ now 1.4))',
             '(CallFunction|PhysisSlow :Rate 0.04 :Seconds 0.55)', '(CallFunction|PhysisSwung :Length (* %s 0.6) :Damage 4)' % play('F_Cyclone', 1.6)]
    return ''.join('\n        ' + line for line in lines)


def dealt(amount, power, carry):
    """TakeHit takes whole damage, so a multiplied hit keeps its fraction in a carry for the next hit: over a
    fight +25% really is +25% (a 1-damage light swing deals 2 on every fourth hit). DamageNow stores the sum
    first, because a bound pure node would be re-read after the carry changes."""
    return '''(Variables|Default|SetDamageNow (+ (* %s %s) (Variables|Default|Get%s)))
          (Variables|Default|Set%s (- (Variables|Default|GetDamageNow) (Math|Conversions|ToFloat(Integer) (Math|Float|Truncate (Variables|Default|GetDamageNow)))))''' % (amount, power, carry, carry)


def augments():
    for n in ('KatanaPower', 'PistolPower', 'HurtTaken', 'ParryTime', 'DamageNow', 'KatanaCarry', 'PistolCarry'):
        var(P, n, 'float')
    var(P, 'WaterJumped', 'bool')  # center_logic.py part jump's; made here too, as PhysisStrikeNow reads it
    var(DR, 'ShotOnly', 'bool', True)  # instance-editable: a scenario marks targets that only a shot may break
    up = '(+ (Transformation|GetActorLocation) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z %s))'
    slash = spawn('BP_SlashFX', up % '100.0', '(Math|Rotator|CombineRotators :A (Math|Rotator|MakeRotator :Roll (Math|Random|RandomFloatinRange :Min -38.0 :Max 38.0) :Pitch 0.0 :Yaw 0.0) :B (Transformation|GetActorRotation))')
    # Reach (2026-11-08): the station's test is 3 m between origins. A Center or Conclave crystal's origin hangs up to
    # 3.9 m above its lowest point, so the sword never reached Prism Wraiths or Wardens standing on the ground. In an
    # open level a non-boss enemy is also in reach when the flat distance to its bounds' centre, less 60% of their
    # narrower half-width, is under 3 m, she is level with the body (1.5 m under its bottom to 0.5 m over its top),
    # and it is ahead of her on the flat. HitPower tells the enemy's armour how strong the swing was before the
    # augmentations (TakeHit resets it). During a water hop (WaterJumped, falling) the blade does not touch Static
    # targets, and a Static target marked ShotOnly never takes it: the Conclave's Reservoir anchors are meant to be shot,
    # and the higher water jump (2026-11-08) can put her on a buoy deck beside them (the Conclave scenario sets ShotOnly).
    reach = ('(and world (and (not (Class|BPTrainingDrone|GetBoss :self drone)) (and (< (- (Math|Vector|VectorLength flat) (* 0.6 (select (> (.x half) (.y half)) (.y half) (.x half)))) 300.0) '
             '(and (> (.z (Transformation|GetActorLocation)) (- (- (.z box) (.z half)) 150.0)) (and (< (.z (Transformation|GetActorLocation)) (+ (+ (.z box) (.z half)) 50.0)) '
             '(> (Math|Vector|DotProduct (Math|Vector|Normalize flat) (Math|Vector|Normalize (Math|Vector|MakeVector :X (.x (Transformation|GetActorForwardVector)) :Y (.y (Transformation|GetActorForwardVector)) :Z 0.0))) 0.2))))))')
    fn(P, 'PhysisStrikeNow', """(fn PhysisStrikeNow ()
  (bind amount (Variables|Default|GetPendingDamage))
  (Variables|Default|SetGunHit false)
  """ + slash + """
  (bind world (> (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass """ + AWAKENING + """)) 0))
  (for found (Actor|GetAllActorsOfClass :ActorClass """ + DRONE + """)
    (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found)
      (:then
        (bind (box half) (Collision|GetActorBounds :self drone :bOnlyCollidingComponents false))
        (bind flat (Math|Vector|MakeVector :X (- (.x box) (.x (Transformation|GetActorLocation))) :Y (- (.y box) (.y (Transformation|GetActorLocation))) :Z 0.0))
        (if (and (or (and (< (Transformation|GetDistanceTo :OtherActor drone) (select (Class|BPTrainingDrone|GetBoss :self drone) 560.0 300.0)) (> (Transformation|GetDotProductTo :OtherActor drone) 0.2)) """ + reach + """) (not (and (Class|BPTrainingDrone|GetStatic :self drone) (or (Class|BPTrainingDrone|GetShotOnly :self drone) (and (Variables|Default|GetWaterJumped) (Movement|IsFalling :self (Variables|Character|GetCharacterMovement)))))))
          """ + sound_at('S_SwordHit1', '(Transformation|GetActorLocation :self drone)') + """
          """ + spawn('BP_Spark', '(Transformation|GetActorLocation :self drone)') + """
          (Variables|Default|SetShakeAmount (+ 2.5 (* amount 1.5)))
          (CallFunction|PhysisSlow :Rate 0.08 :Seconds (+ 0.05 (* amount 0.025)))
          """ + dealt('amount', KATANA, 'KatanaCarry') + """
          (Class|BPTrainingDrone|SetHitPower :self drone :HitPower amount)
          (Class|BPTrainingDrone|TakeHit :self drone :Amount (Math|Float|Truncate (Variables|Default|GetDamageNow)))))
      (:CastFailed))))""")
    fn(P, 'PhysisShotHit', """(fn PhysisShotHit (Damage Muzzle Far)
  (bind target (Variables|Default|GetShotTarget))
  (Utilities|IsValid target
    (:"Is Valid"
      (bind spot (Transformation|GetActorLocation :self target))
      (CallFunction|PhysisTracer :From Muzzle :To spot)
      (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object target)
        (:then
          """ + dealt('Damage', PISTOL, 'PistolCarry') + """
          (Class|BPTrainingDrone|SetHitPower :self drone :HitPower Damage)
          (Class|BPTrainingDrone|TakeHit :self drone :Amount (Math|Float|Truncate (Variables|Default|GetDamageNow))))
        (:CastFailed)))
    (:"Is Not Valid" (CallFunction|PhysisTracer :From Muzzle :To Far))))""")
    fn(P, 'PhysisBlock', """(fn PhysisBlock ()
  (if (or (Variables|Default|GetScanVisorOn) (Variables|Default|GetScanPaused))
    (CallFunction|PhysisScan)
    (else
      """ + ANIM + """
      (if (and (and (not (Variables|Default|GetPhysisDead)) (not (Variables|Default|GetCinematic))) (> """ + NOW + """ (Variables|Default|GetBlockUntil)))
        (Variables|Default|SetChainOpenAt 0.0)
        """ + play('Block', 1.2) + """
        (Variables|Default|SetBlockUntil (+ """ + NOW + """ 0.7))
        (Variables|Default|SetParryUntil (+ """ + NOW + ' ' + PARRY_TIME + """))))))""")
    # A longer window lets B parry an attack from further away: the bolt reach scales with it, drones half as much.
    fn(P, 'PhysisThreatCheck', """(fn PhysisThreatCheck ()
  (Variables|Default|SetThreatNear false)
  (bind reach (/ """ + PARRY_TIME + """ 0.3))
  (for bolt (Actor|GetAllActorsOfClass :ActorClass \"""" + B + """BP_EnemyBolt.BP_EnemyBolt_C")
    (if (< (Transformation|GetDistanceTo :OtherActor bolt) (* 650.0 reach))
      (Variables|Default|SetThreatNear true)))
  (for drone (Actor|GetAllActorsOfClass :ActorClass """ + DRONE + """)
    (if (< (Transformation|GetDistanceTo :OtherActor drone) (* 330.0 (+ 0.5 (* 0.5 reach))))
      (Variables|Default|SetThreatNear true))))""")
    beat = parry_beat()
    # Divine Parry (a hit she does not parry is parried for her, for 5 Divinity) is a Settings assist since 2026-11-09,
    # Off by default (author, via the station session: "Please remove the automatic parrying from being the default. It
    # makes the fighting extremely easy."). The station's quality.py adds AutoParry to BP_Physis and BP_PhysisSave and
    # loads it; var() here only keeps this write from naming a missing variable.
    var(P, 'AutoParry', 'bool')
    fn(P, 'PhysisHurt', """(fn PhysisHurt (FromAhead)
  """ + ANIM + """
  (bind now """ + NOW + """)
  (if (and (and (not (Variables|Default|GetPhysisDead)) (not (Variables|Default|GetCinematic))) (> now (Variables|Default|GetSafeUntil)))
    (Variables|Default|SetChainOpenAt 0.0)
    (if (and (and FromAhead (< now (Variables|Default|GetBlockUntil))) (< now (Variables|Default|GetParryUntil)))
      (CallFunction|PhysisNote :Message "Perfect Parry")""" + parry_beat(True) + """
      (elif (and (Variables|Default|GetAutoParry) (>= (Variables|Default|GetDivinity) 5.0))
        (Variables|Default|SetDivinity (- (Variables|Default|GetDivinity) 5.0))
        (CallFunction|PhysisNote :Message "Divine Parry")""" + beat + """
        (elif (and FromAhead (< now (Variables|Default|GetBlockUntil)))
          """ + sound('S_Block', 0.8) + """
          """ + play('Impact', 1.4) + """
          (Variables|Default|SetShakeAmount 3.0)
          (Variables|Default|SetSafeUntil (+ now 0.8))
          (else
            (Variables|Default|SetPhysisHealth (- (Variables|Default|GetPhysisHealth) """ + HURT + """))
            (Variables|Default|SetShakeAmount 5.0)
            (Variables|Default|SetSafeUntil (+ now 1.0))
            (if (<= (Variables|Default|GetPhysisHealth) 0.0)
              (Variables|Default|SetPhysisDead true)
              """ + play('Dead', 1.0) + """
              (Input|DisableInput :self self :PlayerController (Game|GetPlayerController 0))
              (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisRestart" :Time 1.8 :bLooping false)
              (elif FromAhead
                """ + play('Hit_Front_Big1', 1.4) + """
                (else
                  """ + play('Hit_Back_Small', 1.4) + """)))))))))""")
    comp(P)


# ---------------------------------------------------------------- level map (pause menu page 4)
# The pause menu (the station's pause.py DrawPauseMenu, ported whole below) gains a fifth tab, Map, page 4.
# M or the gamepad's View/Select button (IA_Map) opens the menu straight on it and closes it again
# (BP_Physis PhysisMap). The art, /Game/UI/T_UI_MapCenter, is square and shows x and y in [-MAP_HALF, MAP_HALF] cm
# (the map art's EXTENT_CM), north (+X) at the top and east (+Y) at the right: U = (y + E) / 2E, V = (E - x) / 2E.

H = B + 'BP_PhysisHUD.BP_PhysisHUD'
FONT = '/Game/UI/F_Physis.F_Physis'
GOLD = '"(R=1.0,G=0.82,B=0.42,A=1.0)"'
DIM = '"(R=0.62,G=0.68,B=0.74,A=1.0)"'
CREAM = '"(R=1.0,G=0.92,B=0.78,A=1.0)"'
TEAL = '"(R=0.5,G=1.0,B=0.88,A=1.0)"'
MAP_PAGE = 4
MAP_HALF = 92000.0                                   # cm from the map's centre to each edge: EXTENT_CM of the map art
MAP_LEFT, MAP_TOP, MAP_SIDE = 110.0, 146.0, 800.0    # u (SizeY / 1080); the menu frame's inside is 118u .. SizeY - 96u
# Puzzle, Echo Cache and vault sites come from the level at runtime: every BP_DivinityRay (physis_center_scenario
# divinity_rays) is marked in its ray's colour by Kind (0 puzzle gold, 1 vault violet, 2 Echo Cache cyan), and greys
# out once its DoneToken (the site's reward) is in the flags, so the map can never drift from the placed scenario.
# The Conclave's rays keep its five colours (MI_CNRay_*: 0 puzzle gold, 1 vault red, 2 Light Cache light blue).
RAY_CLASS = '"%sBP_DivinityRay.BP_DivinityRay_C"' % B
# name, world x, world y, lift above the hub in u (negative: below it). Each is the nearest spot whose text box
# clears every Still Point and ray mark by 2u (checked against the placed level, 2026-11-05).
REGION_LABELS = (('The Still Glade', -70000, 0, -44), ('Lantern Marsh', -36000, -44000, 42), ('The Concourse', 0, 0, 28),
                 ('Choir Hollow', -15000, 56000, 28), ('Thornveil', 38000, 40000, 32), ('Glass Highlands', 40000, -48000, 32),
                 ('Temple of the First Light', 76000, 0, 28))
# The Conclave's regions (physis_conclave_plan.REGIONS, metres) at their centres, lifted 24u (about 55 m) so the
# region's own Still Point or pylon ray under its centre stays readable. Like the Center's, the lifts are to be checked
# against the placed level (/Game/UI/T_UI_MapConclave, Tools/build_physis_conclave_map.py, the same frame).
CONCLAVE_LABELS = tuple((name, x * 100.0, y * 100.0, 24) for name, (x, y, _radius, _blend) in conclave_plan.REGIONS.items())


def tex(name, x, y, w, h, tint='"(R=1.0,G=1.0,B=1.0,A=1.0)"', extra=''):
    """combat.py's tex(): a /Game/UI texture."""
    return ('(HUD|DrawTexture :Texture "/Game/UI/%s.%s" :ScreenX %s :ScreenY %s :ScreenW %s :ScreenH %s '
            ':TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor %s%s)') % (name, name, x, y, w, h, tint, extra)


def text(t, x, y, scale, colour='"(R=1.0,G=0.9,B=0.7,A=1.0)"'):
    """hudfont.py's text(): every HUD text sits on its dark plate; F_Physis is cached at 40 pt, so scales are x0.35."""
    scale = '(* %s 0.35)' % scale
    return ('(CallFunction|DrawTextPlate :Text %s :X %s :Y %s :Scale %s)\n    '
            '(HUD|DrawText :Text %s :TextColor %s :ScreenX %s :ScreenY %s :Scale %s :Font "%s")') % (t, x, y, scale, t, colour, x, y, scale, FONT)


def press(*names):
    """pause.py's press(): any of these keys went down this frame (polled, so it works while paused)."""
    out = '(Game|Player|WasInputKeyJustPressed :self pc :Key "%s")' % names[0]
    for name in names[1:]:
        out = '(or %s (Game|Player|WasInputKeyJustPressed :self pc :Key "%s"))' % (out, name)
    return out


def map_x(y):
    """Screen X of world Y (east), inside PageMap (binds left, side). A number is folded to a float fraction here."""
    if isinstance(y, (int, float)):
        return '(+ left (* %.5f side))' % ((y + MAP_HALF) / (2 * MAP_HALF))
    return '(+ left (* (/ (+ %s %s) %s) side))' % (y, MAP_HALF, 2 * MAP_HALF)


def map_y(x):
    """Screen Y of world X (north is up), inside PageMap (binds top, side)."""
    if isinstance(x, (int, float)):
        return '(+ top (* %.5f side))' % ((MAP_HALF - x) / (2 * MAP_HALF))
    return '(+ top (* (/ (- %s %s) %s) side))' % (MAP_HALF, x, 2 * MAP_HALF)


def pause_menu_code(map_tab=True):
    """The station's DrawPauseMenu (pause.py), generated the same way; map_tab adds the Map tab (page 4)."""
    UP = press('Up', 'W', 'Gamepad_DPad_Up', 'Gamepad_LeftStick_Up')
    DN = press('Down', 'S', 'Gamepad_DPad_Down', 'Gamepad_LeftStick_Down')
    LF = press('Left', 'A', 'Gamepad_DPad_Left', 'Gamepad_LeftStick_Left')
    RT = press('Right', 'D', 'Gamepad_DPad_Right', 'Gamepad_LeftStick_Right')
    TL = press('Q', 'Gamepad_LeftShoulder')
    TR = press('Tab', 'Gamepad_RightShoulder')
    OK = press('E', 'Enter', 'SpaceBar', 'Gamepad_FaceButton_Bottom')
    last = MAP_PAGE if map_tab else 3
    rows = (('Save Game', '""'), ('Load Game', '""'),
            ('Graphics: Quality', '(select (== (Class|BPPhysis|GetQuality :self physis) 0) "Low" (select (== (Class|BPPhysis|GetQuality :self physis) 1) "Medium" "High"))'),
            ('Audio: Music Volume', '(Utilities|String|Append :A (Utilities|String|ToString(Integer) (Math|Float|TruncatetoInteger64 (* 10.0 (Class|BPPhysis|GetMusicVol :self physis)))) :B "%")'),
            ('Audio: Voice Volume', '(Utilities|String|Append :A (Utilities|String|ToString(Integer) (Math|Float|TruncatetoInteger64 (* 10.0 (Class|BPPhysis|GetVoiceVol :self physis)))) :B "%")'),
            ('Gameplay: Camera Shake', '(select (Class|BPPhysis|GetShakeOn :self physis) "On" "Off")'),
            ('Gameplay: Hit Slow-Motion', '(select (Class|BPPhysis|GetSlowOn :self physis) "On" "Off")'),
            ('Controls: Look Sensitivity', '(Utilities|String|ToString(Float) (Class|BPPhysis|GetLookSens :self physis))'),
            ('Controls: Invert Look', '(select (Class|BPPhysis|GetInvertLook :self physis) "On" "Off")'),
            ('Assist: Divine Parry', '(select (Class|BPPhysis|GetAutoParry :self physis) "On" "Off")'), ('Exit Game', '""'))
    # Row 9 is the Divine Parry assist (station session's PhysisSetting row 9, 2026-11-09), so Exit Game is row 10 and
    # the note under the rows moved from 720u to 776u: row 10 sits at 146 + 56 x 10 = 706u.
    rowdraw = ''.join('\n          (CallFunction|MenuRowDraw :Label "%s" :Value %s :Index %d :Row row :SizeY SizeY)' % (l, v, i) for i, (l, v) in enumerate(rows))
    bind = ['Light attack: Left Mouse / RB', 'Heavy attack: Middle Mouse, F / RT', 'Parry, or scan with Divinity Sense: Right Mouse / B, LT',
            'Lock on: Left Shift / LT', 'Divinity Sense: Q / Y', 'Jump: Space / A', 'Dodge: Left Alt / B (parries if a hit is coming)',
            'Interact: E / X', 'Sidearm: Tab / D-pad Up', 'Reload: R / D-pad Down', 'Logbook: L / View', 'Pause Menu: Esc / Menu']
    if map_tab:
        # View moved from the Logbook to the map (IA_Map); the Center's abilities were never listed.
        bind[bind.index('Logbook: L / View')] = 'Logbook: L, or its tab in this menu'
        bind[-1:-1] = ['Map: M / View']
    binddraw = ''.join('\n          ' + text('"%s"' % b, '(* u 960.0)', '(* u %d)' % (150 + i * 46), '(* u 1.05)', TEAL) for i, b in enumerate(bind))
    tabs = ['Logbook', 'Abilities', 'Quests', 'Settings'] + (['Map'] if map_tab else [])
    tabdraw = '\n      '.join('(CallFunction|MenuTab :Label "%s" :Index %d :Page shown :SizeY SizeY)' % (t, i) for i, t in enumerate(tabs))
    footer = ('"Q, Tab / LB, RB: pages     E / A: select     M / View: map     Esc / Menu: resume"' if map_tab
              else '"Q, Tab / LB, RB: pages     E / A: select     Esc / Menu: resume"')
    mappage = ('\n      (if (== shown %d)\n        (CallFunction|PageMap :SizeX SizeX :SizeY SizeY))' % MAP_PAGE) if map_tab else ''
    return """(fn DrawPauseMenu (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind pc (Game|GetPlayerController 0))
  (bind sky (select (> SizeX (* SizeY 2.0)) SizeX (* SizeY 2.0)))
  (HUD|DrawTexture :Texture "/Game/Cinematics/T_Sky_Space.T_Sky_Space" :ScreenX (- (/ SizeX 2.0) (/ sky 2.0)) :ScreenY (- (/ SizeY 2.0) (/ sky 4.0)) :ScreenW sky :ScreenH (/ sky 2.0) :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor "(R=0.6,G=0.6,B=0.68,A=1.0)")
  (HUD|DrawRect :RectColor "(R=0.0,G=0.012,B=0.03,A=0.72)" :ScreenX 0.0 :ScreenY 0.0 :ScreenW SizeX :ScreenH SizeY)
  (HUD|DrawRect :RectColor "(R=0.0,G=0.03,B=0.06,A=0.62)" :ScreenX (* u 64.0) :ScreenY (* u 118.0) :ScreenW (- SizeX (* u 128.0)) :ScreenH (- SizeY (* u 214.0)))
  (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX (* u 64.0) :ScreenY (- SizeY (* u 96.0)) :ScreenW (- SizeX (* u 128.0)) :ScreenH (* u 2.0))
  (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX (* u 64.0) :ScreenY (* u 118.0) :ScreenW (* u 2.0) :ScreenH (- SizeY (* u 214.0)))
  (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX (- SizeX (* u 66.0)) :ScreenY (* u 118.0) :ScreenW (* u 2.0) :ScreenH (- SizeY (* u 214.0)))
  """ + tex('T_UI_LogoMark', '(- SizeX (* u 150.0))', '(* u 12.0)', '(* u 104.0)', '(* u 104.0)') + """
  (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.55)" :ScreenX (* u 64.0) :ScreenY (* u 100.0) :ScreenW (- SizeX (* u 240.0)) :ScreenH (* u 2.0))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (bind page (Class|BPPhysis|GetMenuPage :self physis))
      (if (or """ + TL + """ (and (not (== page 3)) """ + LF + """))
        (Class|BPPhysis|SetMenuPage :self physis :MenuPage (select (> page 0) (- page 1) %d))
        (Class|BPPhysis|SetMenuRow :self physis :MenuRow 0)
        (Class|BPPhysis|SetMenuTitle :self physis :MenuTitle "")
        (Class|BPPhysis|PhysisVoiceStop :self physis))
      (if (or """ % last + TR + """ (and (not (== page 3)) """ + RT + """))
        (Class|BPPhysis|SetMenuPage :self physis :MenuPage (select (< page %d) (+ page 1) 0))
        (Class|BPPhysis|SetMenuRow :self physis :MenuRow 0)
        (Class|BPPhysis|SetMenuTitle :self physis :MenuTitle "")
        (Class|BPPhysis|PhysisVoiceStop :self physis))
      (bind shown (Class|BPPhysis|GetMenuPage :self physis))
      """ % last + tabdraw + """
      """ + text(footer, '(* u 80.0)', '(- SizeY (* u 62.0))', '(* u 1.1)', TEAL) + """
      (if (== shown 0)
        (CallFunction|PageLogbook :SizeX SizeX :SizeY SizeY :Data (Class|BPPhysis|GetLogData :self physis)))
      (if (== shown 1)
        (CallFunction|PageAbilities :SizeX SizeX :SizeY SizeY :Skill (Class|BPPhysis|GetSkillLevel :self physis)))
      (if (== shown 2)
        """ + text('"Main Quest"', '(* u 110.0)', '(* u 150.0)', '(* u 1.5)', GOLD) + """
        (CallFunction|DrawLines :Message (Class|BPPhysis|GetObjective :self physis) :X (* u 110.0) :Y (* u 196.0) :Scale (* u 1.2) :Step (* u 36.0) :Red 1.0 :Green 0.92 :Blue 0.78)
        (Variables|Default|SetLineY (+ (Variables|Default|GetLineY) (* u 30.0)))
        """ + text('"Completed"', '(* u 110.0)', '(Variables|Default|GetLineY)', '(* u 1.2)', DIM) + """
        (Variables|Default|SetLineY (+ (Variables|Default|GetLineY) (* u 44.0)))
        """ + text('"Achievements"', '(* u 900.0)', '(* u 150.0)', '(* u 1.5)', GOLD) + """
        """ + text('(select (Class|BPPhysis|GetAchStation :self physis) "Unlocked:  Meridian Holds" "Locked:  Meridian Holds")', '(* u 900.0)', '(* u 200.0)', '(* u 1.1)', '(Utilities|Struct|MakeLinearColor :R 1.0 :G (select (Class|BPPhysis|GetAchStation :self physis) 0.85 0.6) :B (select (Class|BPPhysis|GetAchStation :self physis) 0.45 0.62) :A 1.0)') + """
        """ + text('"Finish Meridian Station."', '(* u 920.0)', '(* u 234.0)', '(* u 0.9)', DIM) + """
        """ + text('(select (Class|BPPhysis|GetAchSwift :self physis) "Unlocked:  Swift as Light" "Locked:  Swift as Light")', '(* u 900.0)', '(* u 280.0)', '(* u 1.1)', '(Utilities|Struct|MakeLinearColor :R 1.0 :G (select (Class|BPPhysis|GetAchSwift :self physis) 0.85 0.6) :B (select (Class|BPPhysis|GetAchSwift :self physis) 0.45 0.62) :A 1.0)') + """
        """ + text('"Finish Meridian Station in under 10 minutes."', '(* u 920.0)', '(* u 314.0)', '(* u 0.9)', DIM) + """
        (for finished (Utilities|String|ParseIntoArray :SourceString (Class|BPPhysis|GetQuestDone :self physis) :Delimiter "@" :CullEmptyStrings true)
          (if (< (Variables|Default|GetLineY) (- SizeY (* u 130.0)))
            (bind start (Variables|Default|GetLineY))
            (CallFunction|DrawLines :Message finished :X (* u 110.0) :Y start :Scale (* u 0.95) :Step (* u 28.0) :Red 0.62 :Green 0.68 :Blue 0.74))))
      (if (== shown 3)
        (bind row (Class|BPPhysis|GetMenuRow :self physis))
        (if """ + UP + """
          (Class|BPPhysis|SetMenuRow :self physis :MenuRow (select (> row 0) (- row 1) 0)))
        (if """ + DN + """
          (Class|BPPhysis|SetMenuRow :self physis :MenuRow (select (< row 10) (+ row 1) 10)))
        (if """ + LF + """
          (Class|BPPhysis|PhysisSetting :self physis :Row row :Delta -1.0))
        (if """ + RT + """
          (Class|BPPhysis|PhysisSetting :self physis :Row row :Delta 1.0))
        (if (and (== row 0) """ + OK + """)
          (Class|BPPhysis|PhysisSaveGame :self physis))
        (if (and (== row 1) """ + OK + """)
          (Class|BPPhysis|PhysisLoadGame :self physis))
        (if (and (== row 10) """ + OK + """)
          (Game|QuitGame))""" + rowdraw + binddraw + """
        """ + text('(Class|BPPhysis|GetMenuNote :self physis)', '(* u 84.0)', '(* u 776.0)', '(* u 1.2)', GOLD) + """)""" + mappage + """)
    (:CastFailed)))"""


def map_page_code(conclave=True):
    """PageMap: the level's map, Physis, the Still Points and the puzzle, cache and vault sites; elsewhere a note. The
    Conclave's map when a BP_ConclaveDirector is present (L_Conclave also holds a BP_Awakening, so it is tested first),
    else the Center's when a BP_Awakening is. Both share the frame (MAP_HALF, so MapMark serves both), the legend and the
    marks; only the art, region labels, title and the vault and cache colours differ, each a small branch in the
    Center's own drawing order. The marks are written once, not per map, because a large PageMap write has run the
    editor out of memory. With conclave False (the Conclave not built yet) it is the Center's page as it was before."""
    def labels(table, tag):
        out = []
        for k, (name, x, y, lift) in enumerate(table):
            out.append('(bind (%sw%d %sh%d) (HUD|GetTextSize :Text "%s" :Font "%s" :Scale (* (* u 0.85) 0.35)))' % (tag, k, tag, k, name, FONT))
            out.append(text('"%s"' % name, '(- %s (/ %sw%d 2.0))' % (map_x(y), tag, k), '(- %s (+ (/ %sh%d 2.0) (* u %.1f)))' % (map_y(x), tag, k, lift), '(* u 0.85)', CREAM))
        return '\n    '.join(out)
    key = lambda y, r, g, b, label: ('(HUD|DrawRect :RectColor "(R=%s,G=%s,B=%s,A=1.0)" :ScreenX (* u 962.0) :ScreenY (* u %s) :ScreenW (* u 16.0) :ScreenH (* u 16.0))\n    ' % (r, g, b, y + 6)
                                     + text('"%s"' % label, '(* u 994.0)', '(* u %s)' % y, '(* u 1.05)', CREAM))

    def branch(here, there):
        """The Conclave's statements in L_Conclave, else the Center's; the Center's alone before the Conclave exists."""
        if not conclave:
            return '\n    '.join(there)
        return '(if conclave\n      %s\n      (else\n        %s))' % ('\n      '.join(here), '\n        '.join(there))
    art = branch([tex('T_UI_MapConclave', 'left', 'top', 'side', 'side')], [tex('T_UI_MapCenter', 'left', 'top', 'side', 'side')])
    names = branch([labels(CONCLAVE_LABELS, 'c')], [labels(REGION_LABELS, 'l')])
    legend = [branch([text('"THE CONCLAVE"', '(* u 960.0)', '(* u 150.0)', '(* u 1.5)', GOLD)],
                     [text('"THE CENTER OF THE UNIVERSE"', '(* u 960.0)', '(* u 150.0)', '(* u 1.5)', GOLD)]),
              text('"Physis"', '(* u 994.0)', '(* u 206.0)', '(* u 1.05)', TEAL),
              key(250.0, 1.0, 1.0, 1.0, 'Still Point, reached'), key(294.0, 0.45, 0.5, 0.55, 'Still Point, not yet reached'),
              key(338.0, 1.0, 0.8, 0.45, 'Puzzle (gold ray)'),
              branch([key(382.0, 0.92, 0.16, 0.12, 'Sealed vault (red ray)'), key(426.0, 0.55, 0.8, 1.0, 'Light Cache (light blue ray)')],
                     [key(382.0, 0.78, 0.45, 1.0, 'Ability vault (violet ray)'), key(426.0, 0.5, 0.92, 1.0, 'Echo Cache (cyan ray)')]),
              key(470.0, 0.35, 0.35, 0.38, 'Solved: its ray has gone out'),
              text('"A Divinity Ray rises over every puzzle until it is solved."', '(* u 960.0)', '(* u 530.0)', '(* u 1.0)', DIM)]
    # Ray marks by Kind: 0 puzzle gold, 1 vault (Center violet, Conclave red), 2 cache (Center cyan, Conclave light blue).
    hue = lambda solved, vault, cache, puzzle: '(select solved %s (select (== kind 1) %s (select (== kind 2) %s %s)))' % (solved, vault, cache, puzzle)
    pick = (lambda here, there: '(select conclave %s %s)' % (here, there)) if conclave else (lambda here, there: there)
    head = ('(bind conclaves (Actor|GetAllActorsOfClass :ActorClass %s))\n  ' % CONCLAVE) if conclave else ''
    found = ('\n  (bind conclave (> (Utilities|Array|Length conclaves) 0))\n  (if (or conclave (> (Utilities|Array|Length directors) 0))' if conclave
             else '\n  (if (> (Utilities|Array|Length directors) 0)')
    red, green, blue = hue('0.35', pick('0.92', '0.78'), pick('0.55', '0.5'), '1.0'), hue('0.35', pick('0.16', '0.45'), pick('0.8', '0.92'), '0.8'), hue('0.38', pick('0.12', '1.0'), '1.0', '0.45')
    white = '"(R=1.0,G=1.0,B=1.0,A=1.0)"'
    line = lambda ax, ay, bx, by: '(HUD|DrawLine :StartScreenX %s :StartScreenY %s :EndScreenX %s :EndScreenY %s :LineColor %s :LineThickness (* u 3.0))' % (ax, ay, bx, by, white)
    return """(fn PageMap (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  """ + head + """(bind directors (Actor|GetAllActorsOfClass :ActorClass %s))""" % AWAKENING + found + """
    (bind left (* u %s))
    (bind top (* u %s))
    (bind side (* u %s))
    """ % (MAP_LEFT, MAP_TOP, MAP_SIDE) + art + """
    (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX left :ScreenY (- top (* u 2.0)) :ScreenW side :ScreenH (* u 2.0))
    (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX left :ScreenY (+ top side) :ScreenW side :ScreenH (* u 2.0))
    (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX (- left (* u 2.0)) :ScreenY top :ScreenW (* u 2.0) :ScreenH side)
    (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX (+ left side) :ScreenY top :ScreenW (* u 2.0) :ScreenH side)
    """ + text('"N"', '(- (+ left (/ side 2.0)) (* u 8.0))', '(+ top (* u 6.0))', '(* u 1.2)', GOLD) + """
    """ + names + """
    """ + tex('T_UI_Reticle', '(* u 958.0)', '(* u 198.0)', '(* u 26.0)', '(* u 26.0)') + """
    """ + '\n    '.join(legend) + """
    (for found (Actor|GetAllActorsOfClass :ActorClass "%sBP_Checkpoint.BP_Checkpoint_C")
      (bind mark (Utilities|Casting|CastToBP_Checkpoint :Object found)
        (:then
          (bind spot (Transformation|GetActorLocation :self mark))
          (bind reached (Class|BPCheckpoint|GetUsed :self mark))
          (CallFunction|MapMark :X (.x spot) :Y (.y spot) :Size (* u 18.0) :Red (select reached 1.0 0.45) :Green (select reached 1.0 0.5) :Blue (select reached 1.0 0.55) :Left left :Top top :Side side))
        (:CastFailed)))
    (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
      (:then
        (bind flags (Class|BPPhysis|GetFlags :self physis))
        """ % B + '''(for found (Actor|GetAllActorsOfClass :ActorClass ''' + RAY_CLASS + ''')
          (bind ray (Utilities|Casting|CastToBP_DivinityRay :Object found)
            (:then
              (bind spot (Transformation|GetActorLocation :self ray))
              (bind kind (Class|BPDivinityRay|GetKind :self ray))
              (bind token (Class|BPDivinityRay|GetDoneToken :self ray))
              (bind solved (and (not (Utilities|String|EqualExactly(String) :A token :B "")) (Utilities|String|Contains :SearchIn flags :Substring token)))
              (CallFunction|MapMark :X (.x spot) :Y (.y spot) :Size (* u (select (== kind 1) 20.0 (select (== kind 2) 13.0 16.0))) :Red ''' + red + ''' :Green ''' + green + ''' :Blue ''' + blue + ''' :Left left :Top top :Side side))
            (:CastFailed)))''' + """
        (bind me (Transformation|GetActorLocation :self physis))
        (bind ahead (Transformation|GetActorForwardVector :self physis))
        (bind px """ + map_x('(.y me)') + """)
        (bind py """ + map_y('(.x me)') + """)
        (bind reach (* u 20.0))
        (bind tipx (+ px (* (.y ahead) reach)))
        (bind tipy (- py (* (.x ahead) reach)))
        (bind backx (- px (* (.y ahead) (* reach 0.6))))
        (bind backy (+ py (* (.x ahead) (* reach 0.6))))
        (bind wingx (* (.x ahead) (* reach 0.6)))
        (bind wingy (* (.y ahead) (* reach 0.6)))
        """ + tex('T_UI_Reticle', '(- px (* u 26.0))', '(- py (* u 26.0))', '(* u 52.0)', '(* u 52.0)') + """
        """ + line('tipx', 'tipy', '(+ backx wingx)', '(+ backy wingy)') + """
        """ + line('tipx', 'tipy', '(- backx wingx)', '(- backy wingy)') + """
        """ + line('(+ backx wingx)', '(+ backy wingy)', '(- backx wingx)', '(- backy wingy)') + """)
      (:CastFailed))
    (else
      """ + text('"There is no map of this place yet."', '(* u 110.0)', '(* u 160.0)', '(* u 1.3)', DIM) + """)))"""


# pause.py's PhysisMenu (Esc, P, Menu, L, M and View all come here) with one change: a scan result showing when the
# menu opens is closed first (as PhysisScan's continue does; the text is already in the Logbook). Before, closing the
# menu unpaused the world while ScanPaused was still set (review, 2026-11-05).
PHYSIS_MENU = """(fn PhysisMenu (Page)
  (if (not (Variables|Default|GetCinematic))
    (if (Variables|Default|GetScanPaused)
      (Variables|Default|SetScanPaused false)
      (CallFunction|PhysisScanHide))
    (Variables|Default|SetLogOpen (not (Variables|Default|GetLogOpen)))
    (Variables|Default|SetMenuPage Page)
    (Variables|Default|SetMenuRow 0)
    (Variables|Default|SetMenuTitle "")
    (Variables|Default|SetMenuNote "")
    (CallFunction|PhysisVoiceStop)
    (Game|SetGamePaused :bPaused (Variables|Default|GetLogOpen))))"""


MAP_MARK = """(fn MapMark (X Y Size Red Green Blue Left Top Side)
  (bind sx (+ Left (* (/ (+ Y %(half)s) %(full)s) Side)))
  (bind sy (+ Top (* (/ (- %(half)s X) %(full)s) Side)))
  (HUD|DrawRect :RectColor "(R=0.0,G=0.01,B=0.02,A=0.85)" :ScreenX (- sx (+ (/ Size 2.0) 2.0)) :ScreenY (- sy (+ (/ Size 2.0) 2.0)) :ScreenW (+ Size 4.0) :ScreenH (+ Size 4.0))
  (HUD|DrawRect :RectColor (Utilities|Struct|MakeLinearColor :R Red :G Green :B Blue :A 1.0) :ScreenX (- sx (/ Size 2.0)) :ScreenY (- sy (/ Size 2.0)) :ScreenW Size :ScreenH Size))""" % {'half': MAP_HALF, 'full': 2 * MAP_HALF}


def map_page():
    """Writes the Map tab: MapMark and PageMap first, then DrawPauseMenu, which calls PageMap."""
    # The Settings page reads AutoParry (row 9) from the HUD, so BP_Physis is compiled first when the variable is new
    # (as conclave() does for Reach); quality.py makes it and loads it.
    if var(P, 'AutoParry', 'bool'):
        comp(P)
    graph(H, 'MapMark', [('X', 'float'), ('Y', 'float'), ('Size', 'float'), ('Red', 'float'), ('Green', 'float'), ('Blue', 'float'),
                         ('Left', 'float'), ('Top', 'float'), ('Side', 'float')])
    graph(H, 'PageMap', [('SizeX', 'float'), ('SizeY', 'float')])
    fn(H, 'MapMark', MAP_MARK)
    fn(H, 'PageMap', map_page_code(built(DIRECTOR)))
    fn(H, 'DrawPauseMenu', pause_menu_code())
    # DrawVisor rides in the same HUD batch (2026-11-08), so every full run keeps it current. A station rebuild's
    # hudfont.py used to write the old per-tag counter first; since 2026-11-09 it skips DrawVisor (CENTER_OWNED).
    # Part visor writes it alone.
    graph(H, 'DrawVisor', [('SizeX', 'float'), ('SizeY', 'float')])
    fn(H, 'DrawVisor', visor_code())
    comp(H)
    fn(P, 'PhysisMenu', PHYSIS_MENU)


def visor_code():
    """hudfont.py's DrawVisor (the station's, owned here since 2026-11-08): the frame, the reticle, a marker on every tag
    in view (grey once its kind is known, gold and pulsing if important, else green), the scan bar, the SCANS counter
    and the result panel. The counter is BP_Physis ScanKindDone / ScanKindCount (different kinds, PhysisScanCount);
    it counted every tag actor, so the Center's 580 tags of 57 kinds gave numbers that rose and fell with kills.
    A known kind's marker no longer pulses."""
    targ = '(Actor|GetAllActorsOfClass :ActorClass %s)' % TARGETS
    colour = ('(Utilities|Struct|MakeLinearColor :R (select done 0.55 (select important 1.0 0.25)) :G (select done 0.58 (select important 0.82 1.0)) '
              ':B (select done 0.6 (select important 0.15 0.55)) :A 1.0)')
    return """(fn DrawVisor (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (HUD|GetOwningPawn))
    (:then
      (bind blend (Class|BPPhysis|GetVisorBlend :self physis))
      (if (> blend 0.01)
        """ + tex('T_UI_VisorFrame', '0.0', '0.0', 'SizeX', 'SizeY', '(Utilities|Struct|MakeLinearColor :R 1.0 :G 1.0 :B 1.0 :A blend)') + """
        """ + tex('T_UI_Reticle', '(- (/ SizeX 2.0) (* u 56.0))', '(- (/ SizeY 2.0) (* u 56.0))', '(* u 112.0)', '(* u 112.0)') + """
        (Variables|Default|SetLogbookSeen (Class|BPPhysis|GetScanKindCount :self physis))
        (Variables|Default|SetLogbookDone (Class|BPPhysis|GetScanKindDone :self physis))
        (bind clock (Utilities|Time|GetGameTimeinSeconds))
        (for found """ + targ + """
          (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found)
            (:then
              (bind done (Class|BPScanTarget|GetScanDone :self item))
              (bind important (Class|BPScanTarget|GetScanImportant :self item))
              (bind aimed (Class|BPScanTarget|GetScanAimed :self item))
              (if (Class|BPScanTarget|GetScanInView :self item)
                (bind at (HUD|Project :Location (Transformation|GetActorLocation :self item) :bClampToZeroPlane false))
                (bind pulse (+ 62.0 (* 8.0 (Math|Trig|Sin(Radians) (* clock 5.0)))))
                (bind size (* u (select aimed 96.0 (select (and important (not done)) pulse 50.0))))
                """ + tex('T_UI_ScanMarker', '(- (.x at) size)', '(- (.y at) size)', '(* size 2.0)', '(* size 2.0)', colour) + """
                (if (and aimed (not done))
                  (HUD|DrawRect :RectColor "(R=0.0,G=0.1,B=0.1,A=0.8)" :ScreenX (- (.x at) (* u 80.0)) :ScreenY (+ (.y at) (* u 100.0)) :ScreenW (* u 160.0) :ScreenH (* u 12.0))
                  """ + tex('T_UI_BarDivinity', '(- (.x at) (* u 80.0))', '(+ (.y at) (* u 100.0))', '(* u (* 160.0 (Class|BPScanTarget|GetScanProgress :self item)))', '(* u 12.0)') + """)))
            (:CastFailed)))
        """ + tex('T_UI_PanelScan', '(- SizeX (* u 500.0))', '(* u 20.0)', '(* u 476.0)', '(* u 112.0)') + """
        """ + text('"SCANS"', '(- SizeX (* u 460.0))', '(* u 40.0)', '(* u 1.43)', TEAL) + """
        """ + text('(Utilities|String|ToString(Integer) (Variables|Default|GetLogbookDone))', '(- SizeX (* u 225.0))', '(* u 40.0)', '(* u 1.43)', TEAL) + """
        """ + text('"/"', '(- SizeX (* u 165.0))', '(* u 40.0)', '(* u 1.43)', TEAL) + """
        """ + text('(Utilities|String|ToString(Integer) (Variables|Default|GetLogbookSeen))', '(- SizeX (* u 125.0))', '(* u 40.0)', '(* u 1.43)', TEAL) + """
        (if (< (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetScanResultHideAt))
          (bind message (Variables|Default|GetScanResult))
          (Variables|Default|SetWidestLine 0.0)
          (Variables|Default|SetLineCount 0)
          (for measured (Utilities|String|ParseIntoArray :SourceString message :Delimiter "~" :CullEmptyStrings false)
            (CallFunction|MeasureLine :Line measured :Scale (* u 1.43) :Icon 0.0))
          (bind width (Variables|Default|GetWidestLine))
          (bind high (* u (* 40.0 (Math|Conversions|ToFloat(Integer) (Variables|Default|GetLineCount)))))
          (bind panelX (/ (- SizeX width) 2.0))
          (bind panelY (* SizeY 0.42))
          """ + tex('T_UI_PanelScan', '(- panelX (* u 70.0))', '(- panelY (* u 26.0))', '(+ width (* u 140.0))', '(+ high (* u 44.0))') + """
          (CallFunction|DrawLines :Message message :X panelX :Y panelY :Scale (* u 1.43) :Step (* u 40.0) :Red 0.75 :Green 1.0 :Blue 0.92))))
    (:CastFailed)))"""


def visor():
    """Part visor: DrawVisor alone. It writes BP_PhysisHUD, so run it on its own, as the first write of a fresh editor,
    and save the HUD at once (memory note unreal-mcp-access); it is not in the default part list for that reason."""
    graph(H, 'DrawVisor', [('SizeX', 'float'), ('SizeY', 'float')])
    fn(H, 'DrawVisor', visor_code())
    comp(H)


# ---------------------------------------------------------------- the Conclave's people (part conclave)
# PhysisInteract and DrawInteract are station graphs the station's rebuild rewrites (scenario_bp.py, feat.py) before
# center_music.py runs this file, so their Conclave versions live here (Tools/conclave/README.md, "Graphs a station
# rebuild rewrites"). Part conclave writes PhysisInteract. DrawInteract is a HUD graph, so no part writes it: it goes in
# the Conclave's one HUD batch (conclave_hud.py, after DrawTalk, which it calls).
REAL = '(Utilities|Time|GetRealTimeSeconds)'


def interact_code():
    """The station's PhysisInteract (combat.py, scenario_bp.py's switches) with the Conclave's people first. A shown
    person within their talk range (BP_NPC Reach) starts a conversation, and nothing else runs on that press: a door or
    switch beside a person would otherwise open, or a sequence reset, with the talk. A talk only starts while
    DrawInteract has marked the HUD within the last second (TalkHudAt): only the Conclave's DrawInteract calls DrawTalk,
    which draws the talk and reads its keys, so with feat.py's DrawInteract a talk would pause the game with no way out
    (a station rebuild wrote it back until 2026-11-09, when CENTER_OWNED stopped that). Nothing runs while she talks,
    nor for 0.35 s (real time) after a talk ends."""
    return """(fn PhysisInteract ()
  (if (Variables|Default|GetCinematic)
    (CallFunction|PhysisCinemaEnd)
    (elif (and (not (Variables|Default|GetTalking)) (> %(real)s (+ (Variables|Default|GetTalkEndAt) 0.35)))
      (Variables|Default|SetActionFound false)
      (for someone (Actor|GetAllActorsOfClass :ActorClass %(npc)s)
        (bind person (Utilities|Casting|CastToBP_NPC :Object someone)
          (:then
            (if (and (and (not (Variables|Default|GetTalking)) (< %(real)s (+ (Variables|Default|GetTalkHudAt) 1.0))) (and (and (Class|BPNPC|GetShown :self person) (not (Class|BPNPC|GetTalking :self person))) (< (Transformation|GetDistanceTo :OtherActor person) (Class|BPNPC|GetReach :self person))))
              (Variables|Default|SetActionFound true)
              (Class|BPNPC|TalkStart :self person)))
          (:CastFailed)))
      (if (not (Variables|Default|GetTalking))
        (for found (Actor|GetAllActorsOfClass :ActorClass "%(b)sBP_StationDoor.BP_StationDoor_C")
          (bind door (Utilities|Casting|CastToBP_StationDoor :Object found)
            (:then
              (if (< (Transformation|GetDistanceTo :OtherActor door) 330.0)
                (Variables|Default|SetActionFound true)
                (if (Class|BPStationDoor|GetDoorLocked :self door)
                  (CallFunction|PhysisSay :Message (Class|BPStationDoor|GetLockedText :self door))
                  (else
                    (Class|BPStationDoor|OpenDoor :self door)
                    (CallFunction|PhysisSay :Message "Door opened")))))
            (:CastFailed)))
        (for lever (Actor|GetAllActorsOfClass :ActorClass "%(b)sBP_Switch.BP_Switch_C")
          (bind switch (Utilities|Casting|CastToBP_Switch :Object lever)
            (:then
              (if (< (Transformation|GetDistanceTo :OtherActor switch) %(reach)s)
                (Variables|Default|SetActionFound true)
                (Class|BPSwitch|UseSwitch :self switch)))
            (:CastFailed)))
        (if (not (Variables|Default|GetActionFound))
          (CallFunction|PhysisSay :Message "Nothing to interact with here"))))))""" % {'real': REAL, 'npc': NPC_CLASS, 'b': B, 'reach': switch_reach('switch')}


def switch_reach(switch):
    """A BP_Switch's interact range: its Reach when set, else the station's 260 cm. The Heartbloom pedestal sets
    Reach 450 (Center session, 2026-11-07). Its origin is the top of the sanctum pedestal's column, at the centre of a
    3 m drum whose rim is too high to step onto. From the floor around the drum she stops 335 cm out, about 3.8 m from
    that origin (tested in Play). Only part conclave's PhysisInteract and conclave_hud.py's DrawInteract read Reach.
    The station's own versions use 260; since 2026-11-09 a station rebuild no longer writes them (CENTER_OWNED)."""
    return '(select (> (Class|BPSwitch|GetReach :self %s) 0.0) (Class|BPSwitch|GetReach :self %s) 260.0)' % (switch, switch)


def interact_near(cls, radius, used):
    """feat.py's near(): "E  Use" over a switch or door within radius; used is the extra test, %s the actor (in radius too)."""
    thing = 'thing_' + cls
    return ("""
  (for found_%s (Actor|GetAllActorsOfClass :ActorClass "%s%s.%s_C")
    (bind %s (Utilities|Casting|CastTo%s :Object found_%s)
      (:then
        (if (and %s (< (Transformation|GetDistanceTo :self %s :OtherActor (Game|GetPlayerPawn 0)) %s))
          (CallFunction|InteractIcon :Spot (+ (Transformation|GetActorLocation :self %s) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 150.0)) :Label "E  Use" :SizeY SizeY)))
      (:CastFailed)))""" % (cls, B, cls, cls, thing, cls, cls, used.replace('%s', thing), thing, radius.replace('%s', thing), thing))


def draw_interact_code():
    """BP_PhysisHUD DrawInteract: feat.py's ("E  Use" over switches and doors, the scan's continue hint; read back
    2026-11-06) with the Conclave's people: "E  Talk" over a shown person within their talk range (BP_NPC Reach, 3 m for a
    human) at their own height (Top), never during a talk. TalkHudAt marks each frame that this version, the one that
    calls DrawTalk, is in the HUD (interact_code reads it). DrawTalk last, inside the cast (a cast ends the exec flow)."""
    return """(fn DrawInteract (SizeX SizeY)
  (bind u (/ SizeY 1080.0))""" + interact_near('BP_Switch', switch_reach('%s'), '(not (Class|BPSwitch|GetUsed :self %s))') + interact_near('BP_StationDoor', '330.0', 'true') + """
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (Class|BPPhysis|SetTalkHudAt :self physis :TalkHudAt """ + REAL + """)
      (if (not (Class|BPPhysis|GetTalking :self physis))
        (for found (Actor|GetAllActorsOfClass :ActorClass """ + NPC_CLASS + """)
          (bind person (Utilities|Casting|CastToBP_NPC :Object found)
            (:then
              (if (and (Class|BPNPC|GetShown :self person) (< (Transformation|GetDistanceTo :self person :OtherActor physis) (Class|BPNPC|GetReach :self person)))
                (CallFunction|InteractIcon :Spot (+ (Transformation|GetActorLocation :self person) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (Class|BPNPC|GetTop :self person))) :Label "E  Talk" :SizeY SizeY)))
            (:CastFailed))))
      (if (Class|BPPhysis|GetScanPaused :self physis)
        """ + text('"Right Mouse / LT: continue"', '(- (/ SizeX 2.0) (* u 150.0))', '(- SizeY (* u 90.0))', '(* u 1.2)', TEAL) + """)
      (CallFunction|DrawTalk :SizeX SizeX :SizeY SizeY))
    (:CastFailed)))"""


def conclave():
    """PhysisInteract with the Conclave's people, once conclave_logic.py has given BP_NPC its talk (before then the
    graph would name a class or function that is not there, so the station's PhysisInteract is left alone).
    conclave_logic.py runs this part itself; center_music.py runs it in every full run.
    BP_Switch's instance-editable Reach (switch_reach) is made first, whatever the Conclave's state. The Center scenario
    sets it on the Heartbloom pedestal, and this PhysisInteract and draw_interact_code read it."""
    if var(SWITCH, 'Reach', 'float', True):
        comp(SWITCH)  # then save BP_Switch before BP_Physis: PhysisInteract reads Reach
    if not built(NPC, 'TalkStart'):
        print('PhysisInteract left as it is: BP_NPC has no TalkStart yet (conclave:blueprints, then conclave_logic.py)', flush=True)
        return False
    var(P, 'Talking', 'bool')
    for name in ('TalkEndAt', 'TalkHudAt'):
        var(P, name, 'float')
    fn(P, 'PhysisInteract', interact_code())
    return True


def use_switch_code():
    """BP_Switch UseSwitch: scenario_bp.py's (the station's, read back live on 2026-11-08 and unchanged), owned here
    since 2026-11-09, with two more optional requirements. NeedB and NeedC, when set, must be held too, each refused
    with its own DeniedB / DeniedC (Denied when that is empty). The Heartbloom pedestal needs ,sanctum, (its guardians
    down), NeedB ,temple, (the three Stillstones home: the colonnade's gaps let her into the sanctum without the door)
    and NeedC ,settle, (author, 2026-11-09: "I was able to get Mend before Settle. That should be impossible.")."""
    flags = '(Class|BPPhysis|GetFlags :self physis)'
    has = lambda v: '(Utilities|String|Contains :SearchIn %s :Substring %s)' % (flags, v)
    empty = lambda v: '(Utilities|String|EqualExactly(String) :A %s :B "")' % v
    say = lambda message: '(Class|BPPhysis|PhysisSay :self physis :Message %s)' % message
    gate = lambda need, denied, rest: ("""(if (and (not """ + empty('(Variables|Default|Get%s)' % need) + """) (not """ + has('(Variables|Default|Get%s)' % need) + """))
                (if """ + empty('(Variables|Default|Get%s)' % denied) + """
                  """ + say('(Variables|Default|GetDenied)') + """
                  (else
                    """ + say('(Variables|Default|Get%s)' % denied) + """))
                (else
                  """ + rest + """))""")
    rest = """(if (> (Variables|Default|GetCost) (Class|BPPhysis|GetDivinity :self physis))
                    """ + say('"This node needs more Divinity. Collect~crystals, or destroy enemies for them."') + """
                    (else
                      (if (> (Variables|Default|GetSeq) 0)
                        (if (== (Variables|Default|GetSeq) (+ (Class|BPPhysis|GetSeqStep :self physis) 1))
                          (Class|BPPhysis|SetSeqStep :self physis :SeqStep (Variables|Default|GetSeq))
                          """ + say('(Variables|Default|GetDone)') + """
                          (if (not """ + empty('(Variables|Default|GetGive)') + """)
                            (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive)))
                          (else
                            (Class|BPPhysis|SetSeqStep :self physis :SeqStep (Variables|Default|GetSeqBase))
                            """ + say('"Sequence rejected. The lockdown resets. Find~the right order."') + """))
                        (else
                          (Variables|Default|SetUsed true)
                          (Class|BPPhysis|SetDivinity :self physis :Divinity (- (Class|BPPhysis|GetDivinity :self physis) (Variables|Default|GetCost)))
                          (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive))
                          """ + say('(Variables|Default|GetDone)') + """
                          (if (Variables|Default|GetFinish)
                            (Class|BPPhysis|PhysisFinish :self physis))))))"""
    return """(fn UseSwitch ()
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (if (Variables|Default|GetUsed)
        """ + say('"Already done."') + """
        (else
          (if (and (not """ + empty('(Variables|Default|GetNeed)') + """) (not """ + has('(Variables|Default|GetNeed)') + """))
            """ + say('(Variables|Default|GetDenied)') + """
            (else
              """ + gate('NeedB', 'DeniedB', gate('NeedC', 'DeniedC', rest)) + """)))))
    (:CastFailed)))"""


def switches():
    """BP_Switch's extra requirements (NeedB, DeniedB, NeedC, DeniedC: instance-editable, set by the Center scenario)
    and UseSwitch, which reads them. Run before center:scenario, which refuses to place anything while they are missing."""
    for name in ('NeedB', 'DeniedB', 'NeedC', 'DeniedC'):
        var(SWITCH, name, 'string', True)
    fn(SWITCH, 'UseSwitch', use_switch_code())
    comp(SWITCH)


PARTS = {'music': music, 'start': start, 'death': death, 'saves': saves, 'progress': progress, 'menu': menu,
         'encounters': encounters, 'scans': scans, 'items': items, 'drones': drones, 'augments': augments,
         'map': map_page, 'conclave': conclave, 'switches': switches, 'visor': visor}
# Parts a full run (no arguments, as center_music.py runs it) leaves out: visor writes BP_PhysisHUD, and part map
# already writes the HUD in that run (one HUD batch per editor launch).
EXPLICIT = ('visor',)

if __name__ == '__main__':
    for part in sys.argv[1:] or [name for name in PARTS if name not in EXPLICIT]:
        PARTS[part]()
    comp(P)
    print('FAILED:', ', '.join(FAILED) or 'none')
