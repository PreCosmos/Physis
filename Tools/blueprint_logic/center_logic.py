"""Blueprint logic for level 2, the Center of the Universe. Run from the project folder:
    python3 Tools/blueprint_logic/center_logic.py [actors] [relic] [physis] [input] [creatures] [jump] [swim]
after `outfit_operation center:blueprints` has created the new Blueprint assets. Without part names it runs every part
but relic, which actors covers.

actors  BP_Relic, BP_Rise, BP_Requirement, BP_SettleBarrier, BP_SettleWave, BP_AbilitySocket, BP_DivinityRay, BP_Awakening
relic   BP_Relic alone (actors writes it too, with the same code): its EventGraph, and the scan tag each augmentation,
        Stillstone and cache carries (RelicTag, RelicTagAs, Tagged), taken over from the scenario's tag beside it or
        made the first time it shows, and destroyed with it (EventEndPlay)
physis  Settle, Mend, the station-to-Center hand-off, save loading by level, fidelity stage 2
input   IA_Settle (V, D-pad Right), IA_Mend (Z, D-pad Left) and IA_Map (M, View), wired to BP_Physis
creatures  BP_Creature: animals circling their homes, ground animals on the terrain
jump    jumps in deep water, again on every press while she swims: BP_Physis PhysisWaterJump (WaterJumpAt, WaterJumped),
        run after IA_Jump's Character|Jump (its free 'then' pin, linked by link_jump; read the link back with
        get_node_infos, read_graph_dsl never shows it)
swim    BP_SwimDirector: tread or stroke in the water, the land animation and weapons out of it, the water jump's
        hop (mode 3), its capped landing and splash, and WaterJumped cleared once she swims again or stands on ground

Every BP_Physis function here is new. Graphs shared with the station's scripts (PhysisFinish,
PhysisLoadGame, PhysisFidelity, PhysisRestore, PhysisRestart, the music and start functions, ...)
live in center_overrides.py, which the station's rebuild runs last.

Order (2026-11-08): BP_ScanTarget.TagSetup comes from center_overrides.py part scans, so run that part (and save
BP_ScanTarget) before relic or actors; without it RelicTagAs fails to write and relics stay untagged. jump runs before
swim (the director names BP_Physis.WaterJumped). Save BP_Physis before BP_SwimDirector, and BP_ScanTarget before
BP_Relic.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
sys.path.insert(0, str(ROOT / 'Content/Python'))  # the lore modules (relic_kinds)
from unreal_mcp import UnrealMCP  # noqa: E402

c = UnrealMCP(timeout=600)
c.initialize()
T = 'editor_toolset.toolsets.blueprint.BlueprintTools'
B = '/Game/Characters/Physis/Blueprints/'
P = B + 'BP_Physis.BP_Physis'
REL, RISE, REQ, BAR, WAVE, AWK = [B + n + '.' + n for n in ('BP_Relic', 'BP_Rise', 'BP_Requirement', 'BP_SettleBarrier', 'BP_SettleWave', 'BP_Awakening')]
SOCK = B + 'BP_AbilitySocket.BP_AbilitySocket'
RAYBP = B + 'BP_DivinityRay.BP_DivinityRay'
CA = '/Game/Center/Audio/'
FAILED = []


def call(tool, args, quiet=False):
    r = c.call('call_tool', {'toolset_name': T, 'tool_name': tool, 'arguments': args})
    text = r['content'][0]['text']
    if r.get('isError') and not quiet:
        print('ERR', tool, text[:700])
    return None if r.get('isError') else text


def var(bp, name, kind, edit=False):
    """Only when missing (2026-11-07). add_variable on a name in use adds a numbered copy (Need_0, Need_1, ...), and
    set_variable_instance_editable marks the Blueprint changed on every call (center_overrides.var). True when it
    added the variable, so a caller can compile before another Blueprint's graph names it."""
    have = call('list_variables', {'blueprint': {'refPath': bp}}, True)
    if have and name in (json.loads(have).get('returnValue') or []):
        return False
    call('add_variable', {'blueprint': {'refPath': bp}, 'name': name, 'type_name': kind}, True)
    if edit:
        call('set_variable_instance_editable', {'blueprint': {'refPath': bp}, 'variable_name': name, 'instance_editable': True}, True)
    return True


def shell(bp, name, params=()):
    if call('add_function_graph', {'blueprint': {'refPath': bp}, 'graph_name': name}, True) is None:
        return
    for pn, pt in params:
        call('add_function_param', {'graph': {'refPath': bp + ':' + name}, 'param_name': pn, 'param_type': pt, 'input_param': True})


def fn(bp, name, code):
    ok = call('write_graph_dsl', {'graph': {'refPath': bp + ':' + name}, 'code': code})
    print(name, 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        FAILED.append(name)
    else:
        prune(bp, name)


def events(bp, code, label):
    ok = call('write_graph_dsl', {'graph': {'refPath': bp + ':EventGraph'}, 'code': code})
    print(label, 'events ok' if ok else 'events FAILED', flush=True)
    if not ok:
        FAILED.append(label)
    else:
        prune(bp, 'EventGraph')


def prune(bp, graph_name):
    """After a write: remove the dead nodes write_graph_dsl leaves behind (op center:prune; see center_overrides.prune
    and Content/Python/physis_graph_prune.py). A changed live DSL is a failure: do not save then."""
    r = c.call('call_tool', {'toolset_name': 'physis_character_tools.PhysisCharacterTools', 'tool_name': 'outfit_operation',
                             'arguments': {'operation': 'center:prune:%s:%s' % (bp, graph_name)}})
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


def snd(path, vol=1.0):
    name = path.split('/')[-1]
    return '(Audio|PlaySound2D :Sound "%s.%s" :VolumeMultiplier %s)' % (path, name, vol)


def at(path, where, vol=1.0):
    name = path.split('/')[-1]
    return '(Audio|PlaySoundatLocation :Sound "%s.%s" :Location %s :VolumeMultiplier %s)' % (path, name, where, vol)


def spawn(bp, where):
    return ('(Game|SpawnActorfromClass :Class "%s%s.%s_C" :SpawnTransform (Math|Transform|MakeTransform :Location %s :Rotation (Math|Rotator|MakeRotator :Yaw 0.0) '
            ':Scale (Math|Vector|MakeVector :X 1.0 :Y 1.0 :Z 1.0)) :CollisionHandlingOverride "AlwaysSpawn")') % (B, bp, bp, where)


def wrap_text(text, width=62):
    """physis_aaa_tools.wrap_text (that module needs the editor): HUD lines joined with ~, as every placed scan tag's
    text is wrapped (physis_center_scenario, the Conclave's wrap), so a runtime tag reads the same."""
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
    """A DSL string literal (the parser reads \\" and \\\\), as center_overrides.literal writes them."""
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"')


PHYSIS = '(bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))\n'
FLAGS = '(Class|BPPhysis|GetFlags :self physis)'
NOW = '(Utilities|Time|GetGameTimeinSeconds)'
EMPTY = lambda v: '(Utilities|String|EqualExactly(String) :A %s :B "")' % v
HAS = lambda flags, tok: '(Utilities|String|Contains :SearchIn %s :Substring %s)' % (flags, tok)
MAXP = '(select (> (Class|BPPhysis|GetMaxHealth :self physis) 0.0) (Class|BPPhysis|GetMaxHealth :self physis) 10.0)'
MAX = '(select (> (Variables|Default|GetMaxHealth) 0.0) (Variables|Default|GetMaxHealth) 10.0)'
WAKE = (-68400.0, 0.0)


# ---------------------------------------------------------------- new actors

TAGS = '"%sBP_ScanTarget.BP_ScanTarget_C"' % B
KEEP = ':LocationRule "KeepWorld" :RotationRule "KeepWorld" :ScaleRule "KeepWorld"'
# The scan entry a relic carries, by its Token (author, 2026-11-08: "all augmentations and items must be scannable"):
# token prefix, lore module, its table, title, important. Augmentations and Stillstones are gold 2 s scans and caches
# green 1.2 s ones, like the placed tags of the same titles. A Center cache with thorns round it (the caged caches
# and the Garden Cache, ,cache1, 2, 5, 6, 12, 16-19,) is an Echo Cache and every other one a Divinity Cache, by its exact
# token (',cache1' alone would also match ,cache10, to ,cache19,), and every
# Conclave relic with a ,cn_ token (its caches, gifts, hoards and vault gifts) a Light Cache; the Conclave's crown,
# kite, ledger pages, seed pod and core have their own rows. The first prefix found in the Token wins.
RELIC_SCANS = (
    # The Conclave's own items (Conclave session, 2026-11-08: rows in physis_conclave_lore). The crown first: its token
    # ,aug_hp5,,crown, would otherwise take the Center's Health Augmentation text below.
    (',crown,', 'physis_conclave_lore', 'CONCLAVE_SCANS', 'The Crown Augmentation', True),
    (',kite,', 'physis_conclave_lore', 'CONCLAVE_SCANS', "Tamsin's Kite", True),
    (',page', 'physis_conclave_lore', 'CONCLAVE_SCANS', 'A Ledger Page', True),
    (',seedpod,', 'physis_conclave_lore', 'CONCLAVE_SCANS', 'The Starlace Seed Pod', True),
    (',core,', 'physis_conclave_lore', 'CONCLAVE_SCANS', "Halden-7's Memory Core", True),
    (',aug_hp', 'physis_center_lore', 'AUG_SCANS', 'Health Augmentation', True),
    (',aug_katana', 'physis_center_lore', 'AUG_SCANS', 'Katana Augmentation', True),
    (',aug_pistol', 'physis_center_lore', 'AUG_SCANS', 'Pistol Augmentation', True),
    (',aug_defense', 'physis_center_lore', 'AUG_SCANS', 'Defense Augmentation', True),
    (',aug_agility', 'physis_center_lore', 'AUG_SCANS', 'Agility Augmentation', True),
    (',stone', 'physis_center_lore', 'CENTER_SCANS', 'Stillstone', True),
    (',cache3,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache4,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache7,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache8,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache9,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache10,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache11,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache13,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache14,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache15,', 'physis_center_lore', 'ITEM_ROWS', 'Divinity Cache', False),
    (',cache', 'physis_center_lore', 'CENTER_SCANS', 'Echo Cache', False),
    (',cn_', 'physis_conclave_lore', 'CONCLAVE_SCANS', 'Light Cache', False),
)


def relic_kinds():
    """RELIC_SCANS with each lore text, wrapped as the placed tags' texts are. The lore is read here, not on import, so
    the parts that do not need it still run if a lore module cannot load. None (and a FAILED entry) when a module does
    not load or holds no Items row with one of the titles: BP_Relic is then left as it is, rather than written with a
    kind the Logbook does not know."""
    import importlib  # noqa: PLC0415
    kinds = []
    for prefix, module, table, title, important in RELIC_SCANS:
        try:
            rows = getattr(importlib.import_module(module), table)
        except (ImportError, SyntaxError, AttributeError) as error:
            print('relic: cannot read %s.%s (%s) - BP_Relic left as it is' % (module, table, error), flush=True)
            FAILED.append('relic lore ' + module)
            return None
        row = next((row for row in rows if row[1] == title), None)
        if row is None or row[0] != 'Items':
            print('relic: %s has no Items row titled %r - BP_Relic left as it is' % (module, title), flush=True)
            FAILED.append('relic lore ' + title)
            return None
        kinds.append((prefix, title, wrap_text(row[2].replace('~', ' ')), important))
    return kinds


def relic_pick(kinds, depth=1):
    """RelicTag's body: one Contains test per kind, each the else branch of the one before (elif)."""
    (prefix, title, body, important), rest = kinds[0], kinds[1:]
    pad = '  ' * depth
    out = '%s(%s %s\n%s  (CallFunction|RelicTagAs :Title %s :Body %s :Important %s)' % (
        pad, 'if' if depth == 1 else 'elif', HAS('token', literal(prefix)), pad, literal(title), literal(body), 'true' if important else 'false')
    return out + ('\n' + relic_pick(rest, depth + 1) if rest else '') + ')'


def relic():
    """BP_Relic. actors() writes it with the other Center actors and part relic writes it alone (its scan tags without
    rewriting every Center actor); both run this function, so the two cannot differ.

    A walk-in pickup with a token, optional gate token, Divinity and healing. Tease shows it while it is still locked
    (a vault's augmentation, seen but out of reach); Locked is said once each time Physis touches it while it is
    locked. The heal runs after PhysisFidelity, so a Health Augmentation heals to the new maximum.

    Scan tags: the first time a relic shows (ready, or Tease), it sets Tagged and RelicTag picks its entry by Token
    (RELIC_SCANS). RelicTagAs then takes over a free tag of that title within 150 cm (the scenario's tags over the 15
    vault rewards and the Glade's Echo Cache), or else makes one at the relic, and TagSetup (BP_ScanTarget, made by
    center_overrides.py part scans) sets its texts and greys it if the Logbook already holds the kind. The tag rides on
    the relic and EventEndPlay destroys it with the relic, so no marker floats where an item was taken. A relic whose
    token is already held when the level starts only takes over its old tag, then goes, so that tag goes too; it makes
    none, since Tagged is still false. The tag is asked for before the take: a relic taken on the frame it shows takes
    its new tag with it, while a RelicTag after DestroyActor would leave a tag on a relic that is gone. EndPlay runs
    before the engine detaches the children (UWorld::DestroyActor calls Destroyed first). Its loop re-reads
    GetAttachedActors on every pass, so from a relic holding several tags it would leave about half; each relic holds
    one (it makes one only when it has none, and no relic has two same-title tags within 150 cm)."""
    kinds = relic_kinds()
    if not kinds:
        return
    for n, k in (('Token', 'string'), ('Need', 'string'), ('Message', 'string'), ('Divinity', 'float'), ('Heal', 'bool'),
                 ('Tease', 'bool'), ('Locked', 'string')):
        var(REL, n, k, True)
    var(REL, 'LockedSaid', 'bool')
    var(REL, 'Tagged', 'bool')
    shell(REL, 'RelicTagAs', [('Title', 'string'), ('Body', 'string'), ('Important', 'bool')])
    shell(REL, 'RelicTag')
    # A taken-over tag must be free: one riding on anything else stays where it is.
    fn(REL, 'RelicTagAs', """(fn RelicTagAs (Title Body Important)
  (for found (Actor|GetAllActorsOfClass :ActorClass """ + TAGS + """)
    (bind free (Utilities|Casting|CastToBP_ScanTarget :Object found)
      (:then
        (if (and (Utilities|String|EqualExactly(String) :A (Class|BPScanTarget|GetScanTitle :self free) :B Title) (< (Transformation|GetDistanceTo :self free :OtherActor self) 150.0))
          (Utilities|IsValid (Actor|GetAttachParentActor :self free)
            (:"Is Valid")
            (:"Is Not Valid"
              (Transformation|AttachActorToActor :self free :ParentActor self """ + KEEP + """)))))
      (:CastFailed)))
  (if (and (Variables|Default|GetTagged) (== (Utilities|Array|Length (Actor|GetAttachedActors)) 0))
    (bind made """ + spawn('BP_ScanTarget', '(Transformation|GetActorLocation)') + """)
    (Transformation|AttachActorToActor :self made :ParentActor self """ + KEEP + """))
  (for kid (Actor|GetAttachedActors)
    (bind tag (Utilities|Casting|CastToBP_ScanTarget :Object kid)
      (:then
        (Class|BPScanTarget|TagSetup :self tag :Category "Items" :Title Title :Body Body :Important Important))
      (:CastFailed))))""")
    fn(REL, 'RelicTag', """(fn RelicTag ()
  (bind token (Variables|Default|GetToken))
""" + relic_pick(kinds) + ')')
    events(REL, """(event EventTick (DeltaSeconds)
  (Transformation|AddActorWorldRotation :DeltaRotation (Math|Rotator|MakeRotator :Yaw (* DeltaSeconds 50.0)) :bSweep false :bTeleport false)
  """ + PHYSIS + """    (:then
      (bind flags """ + FLAGS + """)
      (if (and (not """ + EMPTY('(Variables|Default|GetToken)') + """) """ + HAS('flags', '(Variables|Default|GetToken)') + """)
        (CallFunction|RelicTag)
        (Actor|DestroyActor)
        (else
          (bind ready (or """ + EMPTY('(Variables|Default|GetNeed)') + ' ' + HAS('flags', '(Variables|Default|GetNeed)') + """))
          (bind near (< (Transformation|GetDistanceTo :OtherActor physis) 170.0))
          (Rendering|SetVisibility :self (Variables|Default|GetShape) :bNewVisibility (or ready (Variables|Default|GetTease)))
          (if (and (or ready (Variables|Default|GetTease)) (not (Variables|Default|GetTagged)))
            (Variables|Default|SetTagged true)
            (CallFunction|RelicTag))
          (if (and ready near)
            (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetToken))
            (Class|BPPhysis|SetDivinity :self physis :Divinity (select (> (+ (Class|BPPhysis|GetDivinity :self physis) (Variables|Default|GetDivinity)) 100.0) 100.0 (+ (Class|BPPhysis|GetDivinity :self physis) (Variables|Default|GetDivinity))))
            (if (Variables|Default|GetHeal)
              (Class|BPPhysis|PhysisFidelity :self physis)
              (Class|BPPhysis|SetPhysisHealth :self physis :PhysisHealth """ + MAXP + """))
            """ + snd(CA + 'S_Stillstone') + """
            (Class|BPPhysis|PhysisSay :self physis :Message (Variables|Default|GetMessage))
            (Actor|DestroyActor))
          (if (and (and (not ready) near) (and (not (Variables|Default|GetLockedSaid)) (not """ + EMPTY('(Variables|Default|GetLocked)') + """)))
            (Variables|Default|SetLockedSaid true)
            (Class|BPPhysis|PhysisSay :self physis :Message (Variables|Default|GetLocked)))
          (if (> (Transformation|GetDistanceTo :OtherActor physis) 600.0)
            (Variables|Default|SetLockedSaid false)))))
    (:CastFailed)))

(event EventEndPlay (EndPlayReason)
  (for kid (Actor|GetAttachedActors)
    (Actor|DestroyActor :self kid)))""", 'relic')
    comp(REL)


def actors():
    relic()

    # Rise: slides by Lift (up or down) once the Need token is held. Stepping stones, sockets, doors.
    for n, k in (('Need', 'string'), ('Lift', 'float'), ('Speed', 'float')):
        var(RISE, n, k, True)
    for n in ('HomeX', 'HomeY', 'HomeZ', 'Moved', 'Reach'):
        var(RISE, n, 'float')
    events(RISE, """(event EventBeginPlay
  (bind home (Transformation|GetActorLocation))
  (Variables|Default|SetHomeX (.x home))
  (Variables|Default|SetHomeY (.y home))
  (Variables|Default|SetHomeZ (.z home))
  (Variables|Default|SetReach (select (> (Variables|Default|GetLift) 0.0) (Variables|Default|GetLift) (* (Variables|Default|GetLift) -1.0))))

(event EventTick (DeltaSeconds)
  (if (< (Variables|Default|GetMoved) (Variables|Default|GetReach))
    """ + PHYSIS + """      (:then
        (if """ + HAS(FLAGS, '(Variables|Default|GetNeed)') + """
          (Variables|Default|SetMoved (+ (Variables|Default|GetMoved) (* DeltaSeconds (select (> (Variables|Default|GetSpeed) 0.0) (Variables|Default|GetSpeed) 150.0))))
          (bind gone (select (> (Variables|Default|GetMoved) (Variables|Default|GetReach)) (Variables|Default|GetReach) (Variables|Default|GetMoved)))
          (Transformation|SetActorLocation :NewLocation (Math|Vector|MakeVector :X (Variables|Default|GetHomeX) :Y (Variables|Default|GetHomeY) :Z (+ (Variables|Default|GetHomeZ) (* gone (select (> (Variables|Default|GetLift) 0.0) 1.0 -1.0)))) :bSweep false :bTeleport true)))
      (:CastFailed))))""", 'rise')
    comp(RISE)

    # Requirement: gives a token once every listed token is held (e.g. three Stillstones open the temple).
    for n in ('NeedA', 'NeedB', 'NeedC', 'NeedD', 'Give', 'Message'):
        var(REQ, n, 'string', True)
    var(REQ, 'Done', 'bool')
    ok = lambda v: '(or %s %s)' % (EMPTY(v), HAS('flags', v))
    events(REQ, """(event EventTick (DeltaSeconds)
  (if (not (Variables|Default|GetDone))
    """ + PHYSIS + """      (:then
        (bind flags """ + FLAGS + """)
        (if (and (and """ + ok('(Variables|Default|GetNeedA)') + ' ' + ok('(Variables|Default|GetNeedB)') + """) (and """ + ok('(Variables|Default|GetNeedC)') + ' ' + ok('(Variables|Default|GetNeedD)') + """))
          (Variables|Default|SetDone true)
          (if (not """ + HAS('flags', '(Variables|Default|GetGive)') + """)
            (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive))
            """ + snd(CA + 'S_PuzzleSolved') + """
            (Class|BPPhysis|PhysisSay :self physis :Message (Variables|Default|GetMessage)))))
      (:CastFailed))))""", 'requirement')
    comp(REQ)

    # Settle barrier: dissolves when Physis Settles within reach. Each barrier remembers the last Settle it
    # has seen (Seen) rather than looking for one in the last 0.3 s, so a long frame or a hitch right after
    # Settle (3 fps in an unfocused editor, a first-use asset load) cannot swallow it.
    var(BAR, 'Give', 'string', True)
    var(BAR, 'Gone', 'bool')
    var(BAR, 'Shrink', 'float')
    var(BAR, 'Seen', 'float')
    events(BAR, """(event EventBeginPlay
  (Variables|Default|SetShrink 1.0))

(event EventTick (DeltaSeconds)
  """ + PHYSIS + """    (:then
      (if (not (Variables|Default|GetGone))
        (if (> (Class|BPPhysis|GetSettleAt :self physis) (Variables|Default|GetSeen))
          (Variables|Default|SetSeen (Class|BPPhysis|GetSettleAt :self physis))
          (if (< (Transformation|GetDistanceTo :OtherActor physis) 1700.0)
          (Variables|Default|SetGone true)
          (Collision|SetCollisionEnabled :self (Variables|Default|GetShape) :NewType "NoCollision")
          """ + at(CA + 'S_BarrierDissolve', '(Transformation|GetActorLocation)') + """
          (if (not """ + EMPTY('(Variables|Default|GetGive)') + """)
            (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive)))))
        (else
          (Variables|Default|SetShrink (- (Variables|Default|GetShrink) (* DeltaSeconds 0.9)))
          (Transformation|SetRelativeScale3D :self (Variables|Default|GetShape) :NewScale3D (Math|Vector|MakeVector :X (+ 1.0 (* (- 1.0 (Variables|Default|GetShrink)) 0.4)) :Y 1.0 :Z (select (> (Variables|Default|GetShrink) 0.02) (Variables|Default|GetShrink) 0.02)))
          (if (<= (Variables|Default|GetShrink) 0.0)
            (Actor|DestroyActor)))))
    (:CastFailed)))""", 'barrier')
    comp(BAR)

    # Settle wave: the visible ring of stillness.
    var(WAVE, 'Age', 'float')
    events(WAVE, """(event EventTick (DeltaSeconds)
  (Variables|Default|SetAge (+ (Variables|Default|GetAge) DeltaSeconds))
  (bind grow (+ 0.5 (* (Variables|Default|GetAge) 36.0)))
  (Transformation|SetActorScale3D :NewScale3D (Math|Vector|MakeVector :X grow :Y grow :Z (* grow 0.35)))
  (Rendering|Material|SetCustomPrimitiveDataFloat :self (Variables|Default|GetShape) :DataIndex 0 :Value (- 1.0 (/ (Variables|Default|GetAge) 0.9)))
  (if (> (Variables|Default|GetAge) 0.9)
    (Actor|DestroyActor)))""", 'wave')
    comp(WAVE)

    # Ability socket: a lock that opens when Physis uses one ability within Radius. Ability is that ability's
    # flag token (",settle,", and the later ",lightstep,", ",resonance,", ",trace,", ",dissonance,",
    # ",reweave,", ",sitwith,"); every ability calls BP_Physis.PhysisUsedAbility with its token when used, and
    # the socket remembers the last use it has seen (Seen), so no frame rate can miss one. On use it gives
    # Give (once) and says Message. Solid sockets are gates whose Shape blocks the way: Hold 0 opens them for
    # good, Hold > 0 only for that many seconds (a timed passage), and a gate never closes on Physis while she
    # stands in it.
    for n, k in (('Ability', 'string'), ('Give', 'string'), ('Message', 'string'), ('Radius', 'float'), ('Hold', 'float'), ('Solid', 'bool')):
        var(SOCK, n, k, True)
    for n, k in (('Seen', 'float'), ('OpenUntil', 'float'), ('Done', 'bool'), ('Shut', 'bool')):
        var(SOCK, n, k)
    local = '(Math|Transform|InverseTransformLocation :T (Transformation|GetActorTransform) :Location (Transformation|GetActorLocation :self physis))'
    events(SOCK, """(event EventBeginPlay
  (Variables|Default|SetShut true)
  (if (not (Variables|Default|GetSolid))
    (Collision|SetCollisionEnabled :self (Variables|Default|GetShape) :NewType "NoCollision")))

(event EventTick (DeltaSeconds)
  """ + PHYSIS + """    (:then
      (bind flags """ + FLAGS + """)
      (if (and (not (Variables|Default|GetDone)) """ + HAS('flags', '(Variables|Default|GetAbility)') + """)
        (if (and (Utilities|String|EqualExactly(String) :A (Class|BPPhysis|GetAbilityUsed :self physis) :B (Variables|Default|GetAbility)) (> (Class|BPPhysis|GetAbilityAt :self physis) (Variables|Default|GetSeen)))
          (Variables|Default|SetSeen (Class|BPPhysis|GetAbilityAt :self physis))
          (if (< (Transformation|GetDistanceTo :OtherActor physis) (Variables|Default|GetRadius))
            (Variables|Default|SetOpenUntil (+ """ + NOW + """ (Variables|Default|GetHold)))
            """ + at(CA + 'S_BarrierDissolve', '(Transformation|GetActorLocation)') + """
            """ + spawn('BP_SettleWave', '(Transformation|GetActorLocation)') + """
            (if (<= (Variables|Default|GetHold) 0.0)
              (Variables|Default|SetDone true))
            (if (and (not """ + EMPTY('(Variables|Default|GetGive)') + """) (not """ + HAS('flags', '(Variables|Default|GetGive)') + """))
              (Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive))
              (Class|BPPhysis|PhysisSay :self physis :Message (Variables|Default|GetMessage))))))
      (if (Variables|Default|GetSolid)
        (bind open (or (Variables|Default|GetDone) (< """ + NOW + """ (Variables|Default|GetOpenUntil))))
        (if (and open (Variables|Default|GetShut))
          (Variables|Default|SetShut false)
          (Collision|SetCollisionEnabled :self (Variables|Default|GetShape) :NewType "NoCollision")
          (Rendering|SetVisibility :self (Variables|Default|GetShape) :bNewVisibility false))
        (if (and (not open) (not (Variables|Default|GetShut)))
          (bind here """ + local + """)
          (if (or (> (select (< (.x here) 0.0) (* (.x here) -1.0) (.x here)) 260.0) (> (select (< (.y here) 0.0) (* (.y here) -1.0) (.y here)) 700.0))
            (Variables|Default|SetShut true)
            (Collision|SetCollisionEnabled :self (Variables|Default|GetShape) :NewType "QueryAndPhysics")
            (Rendering|SetVisibility :self (Variables|Default|GetShape) :bNewVisibility true)))))
    (:CastFailed)))""", 'socket')
    comp(SOCK)

    # Divinity Ray: a shaft of light over a puzzle, Echo Cache or ability vault (physis_center_scenario.divinity_rays).
    # It goes out once its reward (DoneToken) is taken. Kind (0 puzzle, 1 vault, 2 Echo Cache) and Title are read by
    # the pause menu's map (center_overrides.py part map), which marks every ray.
    for n, k in (('DoneToken', 'string'), ('Kind', 'int'), ('Title', 'string')):
        var(RAYBP, n, k, True)
    events(RAYBP, """(event EventTick (DeltaSeconds)
  """ + PHYSIS + """    (:then
      (Rendering|SetVisibility :self (Variables|Default|GetShape) :bNewVisibility (not (and (not """ + EMPTY('(Variables|Default|GetDoneToken)') + """) """ + HAS(FLAGS, '(Variables|Default|GetDoneToken)') + """))))
    (:CastFailed)))""", 'ray')
    comp(RAYBP)

    # Awakening director: plays the arrival cinematic once, only when Physis has just come from the Battle
    # Station's final terminal (PhysisToCenter opens the level with the "arrive" option, and ,awoke, is not
    # yet held) or TestArrival is ticked; every other start (a loaded save, a plain editor Play) goes
    # straight to play with music. TestArrival is an editor test switch: a Shipping build ignores it, so a
    # map saved with it ticked cannot replay the awakening on every load.
    shell(AWK, 'Begin')
    shell(AWK, 'Wake')
    shell(AWK, 'StartMusic')
    shell(AWK, 'WakeNow')
    shell(AWK, 'Prepare')
    shell(AWK, 'CineClear')
    shell(AWK, 'AttachTags')
    shell(AWK, 'Budget')
    var(AWK, 'Watching', 'bool')
    var(AWK, 'TestArrival', 'bool', True)
    var(AWK, 'Arrived', 'bool')  # stored, not bound: a bound pure check is re-read after ,center, is given  # editor testing only: play the arrival without coming from the station
    var(AWK, 'Woken', 'bool')
    var(AWK, 'Prepared', 'bool')
    var(AWK, 'MixReady', 'bool')
    var(AWK, 'MixMusic', 'float')
    var(AWK, 'MixVoice', 'float')
    shell(AWK, 'SyncMix')
    shell(AWK, 'CineEach', [('Mode', 'int')])
    shell(AWK, 'CineRise')
    shell(AWK, 'CineStand')
    # The stand-in Physis (tag CineOnly) is laid down and lifted by SEQ_Awakening; mode 0 puts the
    # eye-opening clip on her face.
    anim = lambda name: '"/Game/Characters/Physis/Animations/%s.%s"' % (name, name)
    fn(AWK, 'CineEach', """(fn CineEach (Mode)
  (for cine (Actor|GetAllActorswithTag :Tag "CineOnly")
    (for part (Actor|GetComponentsByClass :self cine :ComponentClass "/Script/Engine.SkeletalMeshComponent")
      (bind mesh (Utilities|Casting|CastToSkeletalMeshComponent :Object part)
        (:then
          (bind name (Utilities|GetObjectName :Object mesh))
          (if (and (== Mode 0) (Utilities|String|EqualExactly(String) :A name :B "Body"))
            (Components|Animation|PlayAnimation :self mesh :NewAnimToPlay """ + anim('A_Physis_GetUp') + """ :bLooping false))
          (if (and (== Mode 0) (Utilities|String|EqualExactly(String) :A name :B "Face"))
            (Components|Animation|PlayAnimation :self mesh :NewAnimToPlay "/Game/Center/Cinema/A_Physis_EyesOpen.A_Physis_EyesOpen" :bLooping false)))
        (:CastFailed)))))""")
    fn(AWK, 'CineRise', """(fn CineRise ()
  (CallFunction|CineEach :Mode 1))""")
    fn(AWK, 'CineStand', """(fn CineStand ()
  (CallFunction|CineEach :Mode 2))""")
    # PhysisMusic stops whatever is playing and picks the track for this level.
    fn(AWK, 'StartMusic', """(fn StartMusic ()
  """ + PHYSIS + """    (:then
      (Class|BPPhysis|PhysisMusic :self physis))
    (:CastFailed)))""")
    # Prepare runs on the first frame, from BP_Physis PhysisCinemaStart (after PhysisRestore), so nothing of
    # the gameplay view, the station clock or its countdown shows before the eye: LevelDone at once, and on
    # an arrival a black hold, the cinema HUD and a hidden player until SEQ_Awakening's fade track takes over.
    # Without an arrival the stand-in goes at once.
    fn(AWK, 'Prepare', """(fn Prepare ()
  """ + PHYSIS + """    (:then
      (CallFunction|SyncMix)
      (CallFunction|Budget)
      (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Budget" :Time 0.5 :bLooping true)
      (Variables|Default|SetPrepared true)
      (Class|BPPhysis|SetLevelDone :self physis :LevelDone true)
      (Variables|Default|SetArrived (or (and (Variables|Default|GetTestArrival) (not (Development|IsPackagedforDistribution))) (and """ + HAS('(Class|GameModeBase|GetOptionsString :self (Game|GetGameMode))', '"arrive"') + """ (not """ + HAS(FLAGS, '",awoke,"') + """))))
      (if (Variables|Default|GetArrived)
        (Class|BPPhysis|SetCinematic :self physis :Cinematic true)
        (Class|BPPhysis|SetCinemaStartedAt :self physis :CinemaStartedAt (- """ + NOW + """ 100.0))
        (Rendering|SetActorHiddenInGame :self physis :bNewHidden true)
        (Input|SetIgnoreMoveInput :self (Game|GetPlayerController 0) :bNewMoveInput true)
        (Input|SetIgnoreLookInput :self (Game|GetPlayerController 0) :bNewLookInput true)
        (CameraFades|SetManualCameraFade :self (Game|GetPlayerCameraManager 0) :InFadeAmount 1.0 :Color (Utilities|Struct|MakeLinearColor 0.0 0.0 0.0 1.0) :bInFadeAudio false)
        (else
          (for cine (Actor|GetAllActorswithTag :Tag "CineOnly")
            (Actor|DestroyActor :self cine)))))
    (:CastFailed)))""")
    # The awakening's music and voice-over and the temple music sit outside MusicComp / VoiceComp, so the
    # Music and Voice Volume settings reach them through their sound classes (physis_center_tools
    # sound_classes): MusicVol / 6 and VoiceVol / 10, both 1.0 at the defaults. Re-applied when they change.
    MIX = '"/Game/Center/Audio/SM_CenterSettings.SM_CenterSettings"'
    fn(AWK, 'SyncMix', """(fn SyncMix ()
  """ + PHYSIS + """    (:then
      (if (or (not (Variables|Default|GetMixReady)) (or (not (== (Variables|Default|GetMixMusic) (Class|BPPhysis|GetMusicVol :self physis))) (not (== (Variables|Default|GetMixVoice) (Class|BPPhysis|GetVoiceVol :self physis)))))
        (Variables|Default|SetMixMusic (Class|BPPhysis|GetMusicVol :self physis))
        (Variables|Default|SetMixVoice (Class|BPPhysis|GetVoiceVol :self physis))
        (Audio|SetSoundMixClassOverride :InSoundMixModifier """ + MIX + """ :InSoundClass "/Game/Center/Audio/SC_CenterMusic.SC_CenterMusic" :Volume (/ (Variables|Default|GetMixMusic) 6.0) :Pitch 1.0 :FadeInTime 0.0 :bApplyToChildren true)
        (Audio|SetSoundMixClassOverride :InSoundMixModifier """ + MIX + """ :InSoundClass "/Game/Center/Audio/SC_CenterVoice.SC_CenterVoice" :Volume (/ (Variables|Default|GetMixVoice) 10.0) :Pitch 1.0 :FadeInTime 0.0 :bApplyToChildren true)
        (if (not (Variables|Default|GetMixReady))
          (Variables|Default|SetMixReady true)
          (Audio|PushSoundMixModifier :InSoundMixModifier """ + MIX + """))))
    (:CastFailed)))""")
    # Each enemy's scan tag is placed 70 cm above it and attached by the scenario, yet the saved Center map
    # held all 78 unattached (cause not found; the station's drone tags stay attached through recompiles of
    # BP_TrainingDrone). A loose tag stays behind when its enemy moves, sits inside the enemy's body where
    # the visor cannot see it, and outlives the enemy. So every start of the Center re-attaches loose tags
    # to the drone they sit on, before a save is restored (PhysisRestore removes a cleared encounter's
    # drones together with their attached tags). Called by BP_Physis PhysisCenterStart.
    fn(AWK, 'AttachTags', """(fn AttachTags ()
  (for tag (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_ScanTarget.BP_ScanTarget_C")
    (Utilities|IsValid (Actor|GetAttachParentActor :self tag)
      (:"Is Not Valid"
        (for drone (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_TrainingDrone.BP_TrainingDrone_C")
          (if (< (Transformation|GetDistanceTo :self tag :OtherActor drone) 150.0)
            (Transformation|AttachActorToActor :self tag :ParentActor drone :LocationRule "KeepWorld" :RotationRule "KeepWorld" :ScaleRule "KeepWorld")))))))""")
    # The Center's tick budget, every half second: enemies tick every frame within 50 m of her and four times
    # a second beyond, animals every frame within 70 m and ten times a second beyond, and fight trackers (each
    # counts its room's drones) twice a second. Measured: every drone ticking every frame cost about 0.2 ms
    # each, most of a 60 fps frame at 78 drones. Started by Prepare.
    # Budget (every 0.5 s): far actors tick less. Drones 50 m, creatures 70 m; the vaults' rising stairs 80 m,
    # sockets, wounds, relics, barriers and pickups 60 m, drifting slabs 90 m; requirements, rays and fights twice
    # a second.
    # Sockets and barriers compare timestamps, so a slower tick never misses an ability.
    fn(AWK, 'Budget', """(fn Budget ()
  """ + PHYSIS + """    (:then
      (for drone (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_TrainingDrone.BP_TrainingDrone_C")
        (Actor|Tick|SetActorTickInterval :self drone :TickInterval (select (< (Transformation|GetDistanceTo :self drone :OtherActor physis) 5000.0) 0.0 0.25)))
      (for beast (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_Creature.BP_Creature_C")
        (Actor|Tick|SetActorTickInterval :self beast :TickInterval (select (< (Transformation|GetDistanceTo :self beast :OtherActor physis) 7000.0) 0.0 0.1)))
      (for fight (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_Encounter.BP_Encounter_C")
        (Actor|Tick|SetActorTickInterval :self fight :TickInterval 0.5))
""" + ''.join('''      (for piece (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/%s.%s_C")
        (Actor|Tick|SetActorTickInterval :self piece :TickInterval %s))
''' % (name, name, '(select (< (Transformation|GetDistanceTo :self piece :OtherActor physis) %s) 0.0 0.5)' % reach if reach else '0.5')
                 for name, reach in (('BP_Rise', '8000.0'), ('BP_AbilitySocket', '6000.0'), ('BP_Hazard', '6000.0'), ('BP_Relic', '6000.0'),
                                     ('BP_SettleBarrier', '6000.0'), ('BP_Platform', '9000.0'), ('BP_Requirement', None), ('BP_DivinityRay', None), ('BP_Pickup', '6000.0'))) + """    )
    (:CastFailed)))""")
    # A start without the cinematic: the player takes over at once with the Center's music, awake.
    fn(AWK, 'CineClear', """(fn CineClear ()
  """ + PHYSIS + """    (:then
      (Class|BPPhysis|SetCinematic :self physis :Cinematic false)
      (Rendering|SetActorHiddenInGame :self physis :bNewHidden false)
      (Input|ResetIgnoreMoveInput :self (Game|GetPlayerController 0))
      (Input|ResetIgnoreLookInput :self (Game|GetPlayerController 0))
      (for cine (Actor|GetAllActorswithTag :Tag "CineOnly")
        (Actor|DestroyActor :self cine))
      (CallFunction|StartMusic)
      (if (not """ + HAS(FLAGS, '",awoke,"') + """)
        (Class|BPPhysis|PhysisGive :self physis :Token ",awoke,")))
    (:CastFailed)))""")
    # Begin (0.25 s in, after every BeginPlay): an arrival plays SEQ_Awakening, unless the player already
    # skipped it during that quarter second (Prepare had set Cinematic; a skip clears it), then wakes at once.
    # Without Prepare (BP_Physis not calling it) Begin still plays the cinematic as before.
    fn(AWK, 'Begin', """(fn Begin ()
  """ + PHYSIS + """    (:then
      (Class|BPPhysis|SetLevelDone :self physis :LevelDone true)
      (Variables|Default|SetArrived (or (and (Variables|Default|GetTestArrival) (not (Development|IsPackagedforDistribution))) (and """ + HAS('(Class|GameModeBase|GetOptionsString :self (Game|GetGameMode))', '"arrive"') + """ (not """ + HAS(FLAGS, '",awoke,"') + """))))
      (if (not """ + HAS(FLAGS, '",center,"') + """)
        (Class|BPPhysis|PhysisGive :self physis :Token ",center,"))
      (if (Variables|Default|GetArrived)
        (Class|BPPhysis|PhysisGive :self physis :Token ",awoke,")
        (if (or (not (Variables|Default|GetPrepared)) (Class|BPPhysis|GetCinematic :self physis))
          (Class|BPPhysis|PhysisMusicStop :self physis)
          (Class|BPPhysis|SetCinematic :self physis :Cinematic true)
          (Class|BPPhysis|SetCinemaStartedAt :self physis :CinemaStartedAt (- """ + NOW + """ 100.0))
          (Rendering|SetActorHiddenInGame :self physis :bNewHidden true)
          (Input|SetIgnoreMoveInput :self (Game|GetPlayerController 0) :bNewMoveInput true)
          (Input|SetIgnoreLookInput :self (Game|GetPlayerController 0) :bNewLookInput true)
          (Sequencer|Player|Play :self (Class|LevelSequenceActor|GetSequencePlayer :self (Actor|GetActorOfClass :ActorClass "/Script/LevelSequence.LevelSequenceActor")))
          (CallFunction|CineEach :Mode 0)
          (Variables|Default|SetWatching true)
          (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Wake" :Time 36.0 :bLooping false)
          (else
            (Variables|Default|SetWoken true)
            (CallFunction|WakeNow)))
        (else
          (CallFunction|CineClear))))
    (:CastFailed)))""")
    fn(AWK, 'Wake', """(fn Wake ()
  (if (not (Variables|Default|GetWoken))
    (Variables|Default|SetWoken true)
    (Variables|Default|SetWatching false)
    (CallFunction|WakeNow)))""")
    fn(AWK, 'WakeNow', """(fn WakeNow ()
  """ + PHYSIS + """    (:then
      (bind player (Game|GetPlayerController 0))
      (Sequencer|Player|Stop :self (Class|LevelSequenceActor|GetSequencePlayer :self (Actor|GetActorOfClass :ActorClass "/Script/LevelSequence.LevelSequenceActor")))
      (CameraFades|StopCameraFade :self (Game|GetPlayerCameraManager 0))
      (Rendering|SetActorHiddenInGame :self physis :bNewHidden false)
      (for cine (Actor|GetAllActorswithTag :Tag "CineOnly")
        (Actor|DestroyActor :self cine))
      (Input|ResetIgnoreMoveInput :self player)
      (Input|ResetIgnoreLookInput :self player)
      (Class|BPPhysis|SetCinematic :self physis :Cinematic false)
      (CallFunction|StartMusic)
      (Class|BPPhysis|PhysisQuest :self physis :Goal "Explore the Center of the Universe")
      (Class|BPPhysis|PhysisSay :self physis :Message "The Center of the Universe.~Physis is home, and the Center is wide open. Explore it."))
    (:CastFailed)))""")
    # Skipping the cinematic (Interact) clears Physis's Cinematic flag; wake her at once when it does.
    events(AWK, """(event EventBeginPlay
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Begin" :Time 0.25 :bLooping false))

(event EventTick (DeltaSeconds)
  (CallFunction|SyncMix)
  (if (Variables|Default|GetWatching)
    """ + PHYSIS + """      (:then
        (if (not (Class|BPPhysis|GetCinematic :self physis))
          (CallFunction|Wake)))
      (:CastFailed))))""", 'awakening')
    comp(AWK)


# ---------------------------------------------------------------- creatures

CR = B + 'BP_Creature.BP_Creature'


def creatures():
    """Each animal circles its home like the old shader motion, but as an actor, so its scan tag
    (attached) follows it. Ground animals follow the terrain with a downward trace."""
    for n in ('Radius', 'Speed', 'Bob', 'Phase', 'YawOffset'):
        var(CR, n, 'float', True)
    var(CR, 'Ground', 'bool', True)
    for n in ('HomeX', 'HomeY', 'HomeZ'):
        var(CR, n, 'float')
    events(CR, """(event EventBeginPlay
  (bind home (Transformation|GetActorLocation))
  (Variables|Default|SetHomeX (.x home))
  (Variables|Default|SetHomeY (.y home))
  (Variables|Default|SetHomeZ (.z home)))

(event EventTick (DeltaSeconds)
  (bind clock (Utilities|Time|GetGameTimeinSeconds))
  (bind ang (+ (* clock (Variables|Default|GetSpeed)) (Variables|Default|GetPhase)))
  (bind x (+ (Variables|Default|GetHomeX) (* (Math|Trig|Cos(Radians) ang) (Variables|Default|GetRadius))))
  (bind y (+ (Variables|Default|GetHomeY) (* (Math|Trig|Sin(Radians) ang) (Variables|Default|GetRadius))))
  (bind z (+ (Variables|Default|GetHomeZ) (* (Math|Trig|Sin(Radians) (+ (* clock 1.3) (* (Variables|Default|GetPhase) 3.0))) (Variables|Default|GetBob))))
  (bind yaw (+ (* ang 57.2958) (+ (select (>= (Variables|Default|GetSpeed) 0.0) 90.0 -90.0) (Variables|Default|GetYawOffset))))
  (if (Variables|Default|GetGround)
    (bind (floor hit) (Collision|LineTraceByChannel :Start (Math|Vector|MakeVector :X x :Y y :Z (+ z 600.0)) :End (Math|Vector|MakeVector :X x :Y y :Z (- z 1500.0)) :TraceChannel "Visibility" :bTraceComplex true :DrawDebugType "None" :bIgnoreSelf true))
    (bind (blocking overlap time dist where impact) (Collision|BreakHitResult floor))
    (Transformation|SetActorLocationAndRotation :NewLocation (Math|Vector|MakeVector :X x :Y y :Z (select hit (.z impact) z)) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw yaw) :bSweep false :bTeleport true)
    (else
      (Transformation|SetActorLocationAndRotation :NewLocation (Math|Vector|MakeVector :X x :Y y :Z z) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw yaw) :bSweep false :bTeleport true))))""", 'creature')
    comp(CR)


# ---------------------------------------------------------------- water jump

def jump():
    """Physis jumps in deep water (author, 2026-11-08: "Physis can jump once while in water"; the same day: "I need a
    higher jump while Physis is in the water and ... be able to jump constantly while she's in the water, not only
    once until she finds land again"). IA_Jump's Started runs
    Character|Jump (wire2.py), which does nothing while she swims: the movement component lets her jump only walking or
    falling, and its own way out of the water needs her to swim upward, which her yaw-only movement input never does.
    link_jump() runs PhysisWaterJump after Character|Jump on the same press.
    She floats with her capsule centre about 47 cm under the surface (buoyancy 1.3, capsule 34 x 88). 1000 cm/s (was
    700) lifts her centre about 3 m, to about +250, and her feet to about +165 at 0.6 s; she is back in the water after
    about 1.15 s. High enough to leap onto a bank, and also onto the +60 tops of the Causeway Islet and Stillstone Isle
    and the Conclave's +90 buoys. Below -160 (deep in a plunge) she must float up first. The launch sets only her vertical speed, so she keeps her swim along the water, and StopJumping drops the
    native jump input, so holding the button cannot stretch the hop.
    Under a pier, a beam or any cover lower than 1 m over the water line (five traces round her axis, up to z +100
    whatever her depth) there is no hop: one stopped short would leave her falling inside the water with no buoyancy
    (2026-11-08 reviews).
    Every press while she swims jumps again; WaterJumpAt keeps a second press within 0.4 s (before the launch has
    taken her out of the water) from launching twice. WaterJumped marks a jump in the air (BP_SwimDirector's mode 3,
    and PhysisStrikeNow keeps the blade off Static targets then); the director clears it once she swims again or
    stands on ground. On land the function does nothing, so land jumps (held for height too) are as they were."""
    var(P, 'WaterJumped', 'bool')
    var(P, 'WaterJumpAt', 'float')
    shell(P, 'PhysisWaterJump')
    fn(P, 'PhysisWaterJump', """(fn PhysisWaterJump ()
  (if (and (Movement|IsSwimming :self (Variables|Character|GetCharacterMovement)) (> (- (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetWaterJumpAt)) 0.4))
    (bind (up0h up0) (Collision|LineTraceByChannel :Start (+ (Transformation|GetActorLocation) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0)) :End (Math|Vector|MakeVector :X (+ (.x (Transformation|GetActorLocation)) 0.0) :Y (+ (.y (Transformation|GetActorLocation)) 0.0) :Z 100.0) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
    (bind (up1h up1) (Collision|LineTraceByChannel :Start (+ (Transformation|GetActorLocation) (Math|Vector|MakeVector :X 20.0 :Y 0.0 :Z 0.0)) :End (Math|Vector|MakeVector :X (+ (.x (Transformation|GetActorLocation)) 20.0) :Y (+ (.y (Transformation|GetActorLocation)) 0.0) :Z 100.0) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
    (bind (up2h up2) (Collision|LineTraceByChannel :Start (+ (Transformation|GetActorLocation) (Math|Vector|MakeVector :X -20.0 :Y 0.0 :Z 0.0)) :End (Math|Vector|MakeVector :X (+ (.x (Transformation|GetActorLocation)) -20.0) :Y (+ (.y (Transformation|GetActorLocation)) 0.0) :Z 100.0) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
    (bind (up3h up3) (Collision|LineTraceByChannel :Start (+ (Transformation|GetActorLocation) (Math|Vector|MakeVector :X 0.0 :Y 20.0 :Z 0.0)) :End (Math|Vector|MakeVector :X (+ (.x (Transformation|GetActorLocation)) 0.0) :Y (+ (.y (Transformation|GetActorLocation)) 20.0) :Z 100.0) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
    (bind (up4h up4) (Collision|LineTraceByChannel :Start (+ (Transformation|GetActorLocation) (Math|Vector|MakeVector :X 0.0 :Y -20.0 :Z 0.0)) :End (Math|Vector|MakeVector :X (+ (.x (Transformation|GetActorLocation)) 0.0) :Y (+ (.y (Transformation|GetActorLocation)) -20.0) :Z 100.0) :TraceChannel "Visibility" :bTraceComplex false :DrawDebugType "None" :bIgnoreSelf true))
    (if (and (and (and (not (Variables|Default|GetCinematic)) (not (Variables|Default|GetPhysisDead))) (> (.z (Transformation|GetActorLocation)) -160.0)) (not (or (or up0 up1) (or (or up2 up3) up4))))
      (Variables|Default|SetWaterJumped true)
      (Variables|Default|SetWaterJumpAt (Utilities|Time|GetGameTimeinSeconds))
      (Character|LaunchCharacter :LaunchVelocity (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 1000.0) :bXYOverride false :bZOverride true)
      (Character|StopJumping)
      """ + at(CA + 'S_Splash', '(Transformation|GetActorLocation)', .7) + """)))""")
    comp(P)
    link_jump()


def link_jump():
    """IA_Jump: Started -> Character|Jump -> then -> PhysisWaterJump, so every press also tries the water jump, after the
    native jump. The DSL cannot write this: an (event ...) body hangs off the entry's 'then' pin, which input events
    lack (Started, Triggered, Completed, ...), and read_graph_dsl never prints their links either. So it links nodes,
    like wire(). An exec output takes one link and connect_pins replaces a linked one, so the call hangs off Jump's free
    'then' pin, never off Started. Anything not as wire2.py left it (one IA_Jump event, Started to Character|Jump alone,
    an empty then) is refused with a FAILED entry, not guessed at; a link already there is left as it is, so a rerun
    changes nothing. Check it with get_node_infos on the IA_Jump event. Never rerun wire2.py: it makes new events."""
    G = {'refPath': P + ':EventGraph'}

    def j(tool, args):
        r = call(tool, args)
        return json.loads(r)['returnValue'] if r else None

    def info(node):
        found = j('get_node_infos', {'nodes': [node]})
        return found[0] if found else {}

    def pin(node_info, name, side):
        return next((p for p in node_info.get(side) or [] if p.get('name') == name), None)

    def kinds(found):
        """The type_ids of the nodes a pin is linked to."""
        return [info(link['node']).get('type_id', '') for link in (found or {}).get('connected_pins') or []]

    def refuse(why):
        print('IA_Jump', why, flush=True)
        FAILED.append('jump link: ' + why)

    if 'PhysisWaterJump' in FAILED:
        return refuse('PhysisWaterJump was not written: not linked')
    events = [n for n in (j('find_nodes', {'graph': G, 'title': 'IA_Jump'}) or []) if 'EnhancedInputAction' in json.dumps(n)]
    if len(events) != 1:
        return refuse('has %d input events, expected 1: left as it is' % len(events))
    started = pin(info(events[0]), 'Started', 'output_pins')
    links = (started or {}).get('connected_pins') or []
    if len(links) != 1 or not kinds(started)[0].endswith('|Jump'):
        return refuse('Started is not linked to Character|Jump alone: left as it is')
    jumper = links[0]['node']
    jumper_info = info(jumper)
    then = pin(jumper_info, 'then', 'output_pins')
    if then is None:
        return refuse('Character|Jump shows no then pin: left as it is')
    after = kinds(then)
    if any(t.endswith('|PhysisWaterJump') for t in after):
        print('IA_Jump already runs PhysisWaterJump', flush=True)
        return
    if after:
        return refuse('Character|Jump already runs %s: left as it is' % ', '.join(after))
    spot = jumper_info.get('position') or {}
    target = j('create_node', {'graph': G, 'type_id': 'CallFunction|PhysisWaterJump', 'pos': {'x': int(spot.get('x', 0)) + 320, 'y': int(spot.get('y', 0))}})
    entry = pin(info(target), 'execute', 'input_pins') if target else None
    if entry is None:
        if target:
            call('delete_node', {'node': target}, True)
        return refuse('no PhysisWaterJump call node could be made: not linked')
    call('connect_pins', {'output_pin': then['pin_id'], 'input_pin': entry['pin_id']})
    if not any(t.endswith('|PhysisWaterJump') for t in kinds(pin(info(jumper), 'then', 'output_pins'))):
        call('delete_node', {'node': target}, True)
        return refuse('the link did not take: left as it was')
    print('IA_Jump: Character|Jump -> PhysisWaterJump', flush=True)
    comp(P)


# ---------------------------------------------------------------- swimming

SW = B + 'BP_SwimDirector.BP_SwimDirector'


def swimming():
    """In deep water Physis's movement switches to swimming (the level's water volume). This director puts her body on
    the treading or breaststroke loop, and back on her normal animation on land. Modes: 0 land (her Animation
    Blueprint, weapons shown), 1 treading, 2 breaststroke, 3 a water jump in the air (part jump: falling with
    BP_Physis.WaterJumped set; the Animation Blueprint's jump and fall, weapons still hidden as in the water).
    Standing on ground, or swimming again more than 0.4 s after the jump, clears WaterJumped, so she can jump again
    at once (author, 2026-11-08). Coming into the water from land or from a jump she splashes. From a jump she comes
    back at about 920 cm/s (the water volume's terminal velocity, 600, then holds it), and the engine smooths only
    entries slower than 160 cm/s, so she would plunge metres: her fall is capped at 150 cm/s then, a dip of about 1 m. SetAnimationMode makes her anim instance anew (and runs OnAnimInitialized again) even
    in the mode it has, so it runs only on leaving a swim loop: a jump that lands on ground (3 to 0) keeps the instance
    it has. Tread or stroke goes by her speed along the water: she cannot swim up or down, and after a capped jump she
    bobs at up to about 140 cm/s, which by her full speed would flip the two loops and restart one on every bob.
    Every read of the old Mode (splash, cap, SetAnimationMode) comes before SetMode. want is re-read after it, but
    gives the same mode: 0 and 3 do not depend on Mode, and 1 and 2 keep their 90 / 40 cm/s hysteresis."""
    # 2026-11-15: the graph in the asset is ahead of the text below (edited with the 5.9 Blueprint DSL tools, which this
    # script is not ported to). Entering the water it now plays the blend space BS_Physis_Swim once (tread at 0, stroke
    # at 100) instead of one clip per mode, and every tick while swimming it eases the float Blend toward 0 (tread) or 1
    # (stroke) at 2.5 per second and sets the blend space position to 100 * smoothstep(Blend), so tread and stroke cross
    # over in 0.4 s instead of cutting. Port that before running this function again, or it puts the cut back.
    var(SW, 'Mode', 'int')
    if any([var(P, 'WaterJumped', 'bool'), var(P, 'WaterJumpAt', 'float')]):  # BP_Physis's (part jump); read here
        comp(P)
    anim = lambda name: '"/Game/Characters/Physis/Animations/%s.%s"' % (name, name)
    mode = '(Variables|Default|GetMode)'
    events(SW, """(event EventTick (DeltaSeconds)
  """ + PHYSIS + """    (:then
      (bind body (Class|BPPhysis|GetBody :self physis))
      (bind cmc (Class|Character|GetCharacterMovement :self physis))
      (bind swim (Movement|IsSwimming :self cmc))
      (bind air (Movement|IsFalling :self cmc))
      (if (or (and (not swim) (not air)) (and swim (> (- (Utilities|Time|GetGameTimeinSeconds) (Class|BPPhysis|GetWaterJumpAt :self physis)) 0.4)))
        (Class|BPPhysis|SetWaterJumped :self physis :WaterJumped false))
      (bind hop (and air (Class|BPPhysis|GetWaterJumped :self physis)))
      (bind vel (Transformation|GetVelocity :self physis))
      (bind speed (Math|Vector|VectorLength (Math|Vector|MakeVector :X (.x vel) :Y (.y vel) :Z 0.0)))
      (bind want (select swim (select (> speed (select (== """ + mode + """ 2) 40.0 90.0)) 2 1) (select hop 3 0)))
      (if (not (== want """ + mode + """))
        (if (and swim (or (== """ + mode + """ 0) (== """ + mode + """ 3)))
          """ + at(CA + 'S_Splash', '(Transformation|GetActorLocation :self physis)', .9) + """)
        (if (and swim (== """ + mode + """ 3))
          (bind sink (Class|MovementComponent|GetVelocity :self cmc))
          (Class|MovementComponent|SetVelocity :self cmc :Velocity (Math|Vector|MakeVector :X (.x sink) :Y (.y sink) :Z (select (< (.z sink) -150.0) -150.0 (.z sink)))))
        (if (and (or (== want 0) (== want 3)) (or (== """ + mode + """ 1) (== """ + mode + """ 2)))
          (Components|Animation|SetAnimationMode :self body :InAnimationMode "AnimationBlueprint"))
        (if (== want 1)
          (Components|Animation|PlayAnimation :self body :NewAnimToPlay """ + anim('A_Physis_SwimTread') + """ :bLooping true))
        (if (== want 2)
          (Components|Animation|PlayAnimation :self body :NewAnimToPlay """ + anim('A_Physis_SwimStroke') + """ :bLooping true))
        (Variables|Default|SetMode want)
        (bind gun (Class|BPPhysis|GetGunEquipped :self physis))
        (Rendering|SetVisibility :self (Class|BPPhysis|GetKatana :self physis) :bNewVisibility (and (== want 0) (not gun)))
        (Rendering|SetVisibility :self (Class|BPPhysis|GetGun :self physis) :bNewVisibility (and (== want 0) gun))))
    (:CastFailed)))""", 'swim')
    comp(SW)


# ---------------------------------------------------------------- scan targets

ST = B + 'BP_ScanTarget.BP_ScanTarget'


def scans():
    """BP_ScanTarget VisorMeasure is shared with the station's visor.py: it lives in center_overrides.py."""


# ---------------------------------------------------------------- BP_Physis

def physis():
    for n in ('SettleAt', 'SettleReady', 'MendReady', 'AbilityAt'):
        var(P, n, 'float')
    var(P, 'AbilityUsed', 'string')
    for name, params in (('PhysisSettle', ()), ('PhysisMend', ()), ('PhysisToCenter', ()), ('PhysisUsedAbility', (('Token', 'string'),)), ('PhysisMap', ())):
        shell(P, name, params)
    # Every ability calls this with its flag token when it is used (Settle below; Light Step, Resonance Link,
    # Trace Reading, Dissonance, Reweave and Sit With when their levels add them): BP_AbilitySocket locks
    # compare it with their own Ability and open when it was used within reach.
    fn(P, 'PhysisUsedAbility', """(fn PhysisUsedAbility (Token)
  (Variables|Default|SetAbilityUsed Token)
  (Variables|Default|SetAbilityAt """ + NOW + """))""")
    fn(P, 'PhysisSettle', """(fn PhysisSettle ()
  (if (and (not (Variables|Default|GetCinematic)) """ + HAS('(Variables|Default|GetFlags)', '",settle,"') + """)
    (if (> """ + NOW + """ (Variables|Default|GetSettleReady))
      (if (>= (Variables|Default|GetDivinity) 10.0)
        (Variables|Default|SetDivinity (- (Variables|Default|GetDivinity) 10.0))
        (Variables|Default|SetSettleReady (+ """ + NOW + """ 1.4))
        (Variables|Default|SetSettleAt """ + NOW + """)
        (CallFunction|PhysisUsedAbility :Token ",settle,")
        """ + snd(CA + 'S_Settle') + """
        """ + spawn('BP_SettleWave', '(+ (Transformation|GetActorLocation) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z -60.0))') + """
        (Variables|Default|SetShakeAmount 2.0)
        (for found (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_TrainingDrone.BP_TrainingDrone_C")
          (if (< (Transformation|GetDistanceTo :OtherActor found) 1500.0)
            (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found)
              (:then
                (if (not (Class|BPTrainingDrone|GetStatic :self drone))
                  (Class|BPTrainingDrone|SetStunUntil :self drone :StunUntil (+ """ + NOW + """ 4.0))
                  (Class|BPTrainingDrone|TakeHit :self drone :Amount 1)))
              (:CastFailed))))
        (for spot (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_Hazard.BP_Hazard_C")
          (if (< (Transformation|GetDistanceTo :OtherActor spot) 1600.0)
            (bind pool (Utilities|Casting|CastToBP_Hazard :Object spot)
              (:then
                (if (and (not """ + EMPTY('(Class|BPHazard|GetOff :self pool)') + """) (not """ + HAS('(Variables|Default|GetFlags)', '(Class|BPHazard|GetOff :self pool)') + """))
                  (CallFunction|PhysisGive :Token (Class|BPHazard|GetOff :self pool))
                  (CallFunction|PhysisSay :Message "The wound closes. Divinity is still here now.")))
              (:CastFailed))))
        (else
          (CallFunction|PhysisSay :Message "Settle needs 10 Divinity. Collect crystals,~or defeat enemies for them."))))))""")
    fn(P, 'PhysisMend', """(fn PhysisMend ()
  (if (and (not (Variables|Default|GetCinematic)) """ + HAS('(Variables|Default|GetFlags)', '",mend,"') + """)
    (if (> """ + NOW + """ (Variables|Default|GetMendReady))
      (if (>= (Variables|Default|GetPhysisHealth) """ + MAX + """)
        (CallFunction|PhysisSay :Message "Physis is already whole.")
        (else
          (if (>= (Variables|Default|GetDivinity) 25.0)
            (Variables|Default|SetDivinity (- (Variables|Default|GetDivinity) 25.0))
            (Variables|Default|SetMendReady (+ """ + NOW + """ 1.2))
            (Variables|Default|SetPhysisHealth (select (> (+ (Variables|Default|GetPhysisHealth) 6.0) """ + MAX + """) """ + MAX + """ (+ (Variables|Default|GetPhysisHealth) 6.0)))
            """ + snd(CA + 'S_Mend') + """
            """ + spawn('BP_SettleWave', '(Transformation|GetActorLocation)') + """
            (else
              (CallFunction|PhysisSay :Message "Mend needs 25 Divinity."))))))))""")
    # PhysisFinish (the station's final terminal, then PhysisToCenter after 8 s), PhysisLoadGame and
    # PhysisFidelity are shared with the station's scripts: see center_overrides.py.
    fn(P, 'PhysisToCenter', """(fn PhysisToCenter ()
  (CallFunction|PhysisGive :Token ",center,")
  (CallFunction|PhysisCheckpoint :X %s :Y %s :Z 1420.0)
  (Variables|Default|SetSeqStep 0)
  (Variables|Default|SetObjective "Explore the Center of the Universe")
  (CallFunction|PhysisSaveGame)
  (Game|OpenLevel(byName) :LevelName "L_CenterOfTheUniverse" :Options "nocine,load,arrive"))""" % WAKE)
    # M / View (IA_Map): the pause menu opens on its Map tab, page 4 (center_overrides.py part map). On the map it
    # closes the menu (PhysisMenu toggles); from another open tab it switches to the map.
    fn(P, 'PhysisMap', """(fn PhysisMap ()
  (if (and (Variables|Default|GetLogOpen) (not (== (Variables|Default|GetMenuPage) 4)))
    (Variables|Default|SetMenuPage 4)
    (Variables|Default|SetMenuRow 0)
    (Variables|Default|SetMenuTitle "")
    (CallFunction|PhysisVoiceStop)
    (else
      (CallFunction|PhysisMenu :Page 4))))""")
    comp(P)


# ---------------------------------------------------------------- input

def wire():
    G = {'refPath': P + ':EventGraph'}

    def j(tool, args):
        r = call(tool, args)
        return json.loads(r)['returnValue'] if r else None

    def pin(n, name, side):
        return next(p for p in j('get_node_infos', {'nodes': [n]})[0][side] if p['name'] == name)
    y = 9400
    for action, function in (('IA_Settle', 'PhysisSettle'), ('IA_Mend', 'PhysisMend'), ('IA_Map', 'PhysisMap')):
        found = j('find_nodes', {'graph': G, 'title': action}) or []
        if any('EnhancedInputAction' in json.dumps(n) for n in found):
            print(action, 'already wired')
            continue
        event = j('create_node', {'graph': G, 'type_id': 'Input|EnhancedActionEvents|' + action, 'pos': {'x': -400, 'y': y}})
        target = j('create_node', {'graph': G, 'type_id': 'CallFunction|' + function, 'pos': {'x': 0, 'y': y}})
        call('connect_pins', {'output_pin': pin(event, 'Started', 'output_pins')['pin_id'], 'input_pin': pin(target, 'execute', 'input_pins')['pin_id']})
        print(action, 'wired')
        y += 250
    comp(P)


if __name__ == '__main__':
    parts = sys.argv[1:] or ['physis', 'actors', 'input', 'scans', 'creatures', 'jump', 'swim']
    if 'scans' in parts:
        scans()
    if 'creatures' in parts:
        creatures()
    # The water jump before the director: the director reads and clears the WaterJumped variable it makes.
    if 'jump' in parts:
        jump()
    if 'swim' in parts:
        swimming()
    # Physis first: the barrier reads its SettleAt variable.
    if 'physis' in parts:
        physis()
    # actors() writes BP_Relic too, so relic alone only when actors is not run.
    if 'actors' in parts:
        actors()
    elif 'relic' in parts:
        relic()
    if 'input' in parts:
        wire()
    print('FAILED:', FAILED or 'none')
