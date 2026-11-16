"""Blueprint logic for level 4, Earth: the Wounded Grove (Tools/grove/README.md, Tools/grove/DESIGN_NOTES.md). Run from
the project folder with the editor open (Unreal 5.9: BlueprintToolsets.BlueprintDslToolset and BlueprintToolset), after
`grove:blueprints` has made the Blueprint assets and IA_Link:
    python3 Tools/blueprint_logic/grove_logic.py [node] [beam] [pull] [tether] [director] [current] [physis] [input] [shared] [--dry]

node      BP_LinkNode: shown by tokens, fed sockets restored, the aim's swell and glow, Linked (what a press does to it)
beam      BP_LinkBeam: the carried flow's thread (mode 0), a delivered flow's fixed beam (1), a pull's flash (2)
pull      BP_LinkPull: draws Physis to an anchor's perch
tether    BP_LinkTether: two Hedge machines sharing what either suffers
director  BP_GroveDirector: the arrival, MPC_Grove (Motion, Heal, Her), tagged actors by token, quests, the aim
current   BP_GroveCurrent: the Divinity current between the Center's temple and the Hollow
physis    BP_Physis: PhysisLink, PhysisLinkFind, PhysisLinkFoe, PhysisToGrove, PhysisGroveHome
input     IA_Link's Started event calls PhysisLink
shared    Grove branches in graphs other levels own: fidelity and augmentations, music, load, save and restore, the
          menu's Continue (edits of the live graphs: each replacement must match exactly once, or nothing is written)
hud       BP_PhysisHUD.PageMap: Earth's map page (after grove:map_art has imported T_UI_MapGrove)
relic     BP_Relic.RelicTag: the grove's relics' own Logbook entries
music     PhysisMusicPick plays S_Music_Grove on Earth (after grove:audio; the parts that play effects pick the grove's
          own sounds by themselves when they are rerun after the import)
--dry     prints every graph instead of sending it

This is the first logic script in the 5.9 dialect: graph-owned names in backticks, members as `Owner.Member`. In the
text below @P is BP_Physis, @N BP_LinkNode, @D BP_TrainingDrone, @B the Blueprint folder. A bound pure expression is
re-evaluated wherever it is used, so anything a later set would change is kept in a member variable first.
"""
import json
import pathlib
import struct
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
sys.path.insert(0, str(ROOT / 'Content/Python'))
import physis_grove_lore as lore  # noqa: E402
import physis_grove_plan as plan  # noqa: E402

DRY = '--dry' in sys.argv
ARGS = [a for a in sys.argv[1:] if a != '--dry']
B = '/Game/Characters/Physis/Blueprints/'
DSL = 'BlueprintToolsets.BlueprintDslToolset'
BPT = 'BlueprintToolsets.BlueprintToolset'
PY = 'editor_toolset.toolsets.python_scripting.PythonScriptingTools'
FAILED, TOUCHED, BROKEN = [], [], set()

if not DRY:
    from unreal_mcp import UnrealMCP
    c = UnrealMCP(300)
    c.initialize()


def ref(name):
    return B + name + '.' + name


def expand(code):
    return (code.replace('@P', B + 'BP_Physis').replace('@N', B + 'BP_LinkNode').replace('@D', B + 'BP_TrainingDrone')
            .replace('@B', B))


def call(toolset, tool, args, quiet=False):
    """(ok, value): value is the tool's returnValue, or its error text."""
    if DRY:
        return True, None
    for attempt in range(40):
        r = c.call('call_tool', {'toolset_name': toolset, 'tool_name': tool, 'arguments': args})
        text = ''.join(part.get('text', '') for part in r.get('content', []))
        if not (r.get('isError') and 'slow task' in text):   # the editor is busy (a save, a compile): made no changes
            break
        time.sleep(3)
    if r.get('isError'):
        if not quiet:
            print('ERR', tool, text[:1500], flush=True)
        return False, text
    try:
        data = json.loads(text)
        return True, data.get('returnValue', data) if isinstance(data, dict) else data
    except Exception:
        return True, text


def python(code):
    """Runs editor Python; the script's own RESULT line comes back as text."""
    ok, value = call(PY, 'execute_python', {'script': {'content': code, 'language': 'Python'}})
    return ok, value


_vars = {}


def variables(bp):
    if bp not in _vars:
        ok, rows = call(BPT, 'ListVariables', {'blueprint': {'refPath': ref(bp)}})
        _vars[bp] = {row['name'] for row in rows} if ok and isinstance(rows, list) else set()
    return _vars[bp]


def var(bp, name, kind, edit=False):
    """A member variable, added only when the Blueprint lacks it. kind: bool, int, float, string, Vector, or
    'object:<class path>' for an object reference."""
    if DRY:
        print('--- var %s.%s %s%s' % (bp, name, kind, ' (instance editable)' if edit else ''))
        return
    if name in variables(bp):
        return
    if kind.startswith('object:'):
        ok, _ = call(BPT, 'AddObjectVariable', {'blueprint': {'refPath': ref(bp)}, 'name': name, 'objectClass': {'refPath': kind[7:]}})
    else:
        ok, _ = call(BPT, 'AddVariable', {'blueprint': {'refPath': ref(bp)}, 'name': name, 'typeName': kind})
    if ok and edit:
        ok, _ = call(BPT, 'SetVariableInstanceEditable', {'blueprint': {'refPath': ref(bp)}, 'variableName': name, 'bInstanceEditable': True})
    if not ok:
        FAILED.append('var %s.%s' % (bp, name))
        BROKEN.add(bp)
    else:
        variables(bp).add(name)


def shell(bp, name):
    """An empty function graph (idempotent); its parameters come with the fn's (params ...) section."""
    if DRY:
        print('--- function %s.%s' % (bp, name))
        return
    ok, _ = call(BPT, 'AddFunctionGraph', {'blueprint': {'refPath': ref(bp)}, 'graphName': name})
    if not ok:
        FAILED.append('shell %s.%s' % (bp, name))
        BROKEN.add(bp)


def write(bp, scope, code, label=None):
    code = expand(code)
    label = label or '%s %s' % (bp, scope)
    if DRY:
        print('=== DSL %s:%s\n%s\n=== END' % (bp, scope, code))
        return True
    ok, value = call(DSL, 'Write', {'assetPath': B + bp, 'scope': scope, 'dsl': code})
    print(label, 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        FAILED.append(label)
        BROKEN.add(bp)
    if bp not in TOUCHED:
        TOUCHED.append(bp)
    return ok


def read(bp, scope):
    ok, value = call(DSL, 'Read', {'assetPath': B + bp, 'scope': scope, 'bIncludePositions': False})
    return value['dsl'] if ok and isinstance(value, dict) else None


def patch(bp, scope, swaps, marker, label=None):
    """Edits a live graph: every (old, new) must match exactly once in the graph as read now, and nothing is written
    unless all of them apply. A graph that already holds `marker` has the change (a rerun) and is left alone: the
    editor's canonical text renames what a write bound, so the new text itself cannot be looked for."""
    label = label or '%s %s' % (bp, scope)
    if DRY:
        print('--- patch %s:%s (%d replacements)' % (bp, scope, len(swaps)))
        return True
    code = read(bp, scope)
    if code is None:
        FAILED.append(label + ' (not read)')
        return False
    if marker in code:
        print(label, 'already has it', flush=True)
        return True
    changed = False
    for old, new in swaps:
        old, new = expand(old), expand(new)
        if code.count(old) != 1:
            print(label, 'FAILED: %d matches of %s' % (code.count(old), old[:90]), flush=True)
            FAILED.append(label)
            return False
        code = code.replace(old, new)
        changed = True
    if not changed:
        print(label, 'already has it', flush=True)
        return True
    ok, value = call(DSL, 'Write', {'assetPath': B + bp, 'scope': scope, 'dsl': code})
    print(label, 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        FAILED.append(label)
        BROKEN.add(bp)
    if bp not in TOUCHED:
        TOUCHED.append(bp)
    return ok


def comp(bp):
    if DRY:
        return
    ok, value = call(BPT, 'CompileBlueprint', {'blueprint': {'refPath': ref(bp)}})
    text = json.dumps(value) if not isinstance(value, str) else value
    bad = (not ok) or '"Error"' in text or 'bSuccess": false' in text
    print('compile', bp, 'FAILED ' + text[:1200] if bad else 'ok', flush=True)
    if bad:
        FAILED.append('compile ' + bp)
        BROKEN.add(bp)
    if bp not in TOUCHED:
        TOUCHED.append(bp)


def defaults(bp, values):
    """Class defaults, set on the generated class's default object."""
    if DRY:
        print('--- defaults %s %s' % (bp, values))
        return
    code = ('import unreal\ncdo = unreal.get_default_object(unreal.load_asset(%r).generated_class())\n'
            'for k, v in %r.items():\n    cdo.set_editor_property(k, v)\nprint("defaults set")') % (B + bp, values)
    ok, value = python(code)
    print('defaults', bp, values, 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        FAILED.append('defaults ' + bp)


def save(bp):
    if DRY:
        return
    if bp in BROKEN:
        print('not saved', bp, '(a write failed: fix it, then rerun this part)', flush=True)
        return
    # The call itself succeeds even when nothing was written (a Play session refuses saves), so the package's dirty
    # flag is what is read back.
    ok, value = python('import unreal\nunreal.EditorAssetLibrary.save_asset(%r, False)\n'
                       'assert %r not in [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]' % (B + bp, B + bp))
    print('saved', bp, 'ok' if ok else 'FAILED (still unsaved: is Play running?)', flush=True)
    if not ok:
        FAILED.append('save ' + bp)


def lit(text):
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')


# ---------------------------------------------------------------- shorthands (all expand to plain DSL)

PHYSIS = '(bind p (cast `@P` (`GameplayStatics.GetPlayerPawn` 0)))'
NOW = '(`KismetSystemLibrary.GetGameTimeInSeconds`)'
TICK = '(params (DeltaSeconds :type "Float (single-precision)"))'


def has(flags, token):
    return '(`KismetStringLibrary.Contains` %s %s)' % (flags, token if token.startswith('(') else '"%s"' % token)


def empty(value):
    return '(`KismetStringLibrary.EqualEqual_StrStr` %s "")' % value


def same(a, b):
    return '(`KismetStringLibrary.EqualEqual_StrStr` %s %s)' % (a, b)


def vec(x, y, z):
    return '(`KismetMathLibrary.MakeVector` %s %s %s)' % (x, y, z)


def pick(cond, yes, no):
    return '(select `bool` %s :`false` %s :`true` %s)' % (cond, no, yes)


def snd(path, volume=1.0):
    return '(`GameplayStatics.PlaySound2D` "%s.%s" %s)' % (path, path.split('/')[-1], volume)


def spawn(name, place, bind=''):
    form = ('(`|SpawnActorFromClass` "@B%s.%s_C" (`KismetMathLibrary.MakeTransform` %s (`KismetMathLibrary.MakeRotator` 0.0 0.0 0.0) %s) '
            '"AlwaysSpawn" "MultiplyWithRoot" null null)') % (name, name, place, vec(1.0, 1.0, 1.0))
    return '(bind %s %s)' % (bind, form) if bind else form


PF = '(`@P.Flags` p)'                # her flags, read through the cast
MINE = '(`self.Flags`)'              # the same inside BP_Physis
GA = '/Game/Grove/Audio/'
# Sounds: the grove's own once Tools/build_physis_grove_audio.py has made them, the earlier levels' until then.
SOUNDS = {'pull': (GA + 'S_LinkPull', '/Game/Conclave/Audio/S_LightStep'), 'take': (GA + 'S_LinkTake', '/Game/Audio/S_PickupDivinity'),
          'feed': (GA + 'S_LinkFeed', '/Game/Center/Audio/S_PuzzleSolved'), 'tether': (GA + 'S_LinkTether', '/Game/Audio/S_ChargeReady'),
          'travel': (GA + 'S_CurrentTravel', '/Game/Conclave/Audio/S_CurrentTravel'),
          'music': (GA + 'S_Music_Grove', '/Game/Center/Audio/S_Music_Center')}


def sound(key):
    own, other = SOUNDS[key]
    return own if (ROOT / ('Content' + own[5:] + '.uasset')).exists() else other


BEAM_COLOURS = {'': (.25, 1.0, .7), 'water': (.3, .75, 1.0), 'power': (1.0, .72, .25), 'surge': (.25, 1.0, .7)}


# ---------------------------------------------------------------- arrival points

def terrain_top(x, y, reach=3.0):
    meta, grid = ROOT / 'Art/Meshes/Grove/height.json', ROOT / 'Art/Meshes/Grove/height.bin'
    info = json.loads(meta.read_text())
    hx, hy, cell, nx, ny = info['half_x'], info['half_y'], info['cell'], int(info['nx']), int(info['ny'])
    data = grid.read_bytes()
    steps = int(reach / cell) + 1
    i0, j0 = int(round((x + hx) / cell)), int(round((y + hy) / cell))
    return max(struct.unpack_from('<f', data, 4 * (i * ny + j))[0]
               for i in range(i0 - steps, i0 + steps + 1) for j in range(j0 - steps, j0 + steps + 1) if 0 <= i < nx and 0 <= j < ny)


# Earth: on the Hollow's Still Point, 20 m from the current's pool, her capsule centre 1.6 m over the highest ground
# within 3 m. The scenario's TargetPoint GroveArrival is the real spot; this is the save's checkpoint until then.
ARRIVE = plan.HOLLOW_STILL
ARRIVE_CM = (ARRIVE[0] * 100.0, ARRIVE[1] * 100.0, round((terrain_top(*ARRIVE) + 1.6) * 100.0))
# The Center: the temple's top tier, east of the Heartbloom (physis_center_scenario TEMPLE (76000, 0), sanctum floor
# 4000 cm). The Conclave's current stands 16 m north of the pedestal; Earth's stands 16 m east (GROVE_PORTAL in
# physis_grove_scenario), and she comes back 5 m short of it (TargetPoint GroveReturn).
HOME_CM = (76000.0, 1100.0, 4000.0 + 130.0)


# ---------------------------------------------------------------- BP_LinkNode

FLOW_NAME = pick(same('(`self.Flow`)', '"water"'), '"the river"', pick(same('(`self.Flow`)', '"power"'), '"the charge"', '"the surge"'))


def node():
    N = 'BP_LinkNode'
    for name, kind in (('Kind', 'int'), ('Flow', 'string'), ('Need', 'string'), ('Hide', 'string'), ('Give', 'string'), ('Done', 'string'),
                       ('Range', 'float'), ('Reach', 'float'), ('Perch', 'Vector')):
        var(N, name, kind, True)
    for name, kind in (('Fed', 'bool'), ('Shown', 'bool'), ('Aimed', 'bool'), ('Swell', 'float')):
        var(N, name, kind)
    for name in ('Linked', 'Take'):
        shell(N, name)
    here = '(+ (`self.K2_GetActorLocation`) %s)' % vec(0.0, 0.0, 100.0)
    reach = pick('(> (`self.Reach`) 0.0)', '(`self.Reach`)', '3000.0')
    write(N, 'Take', """(fn `Take`
  """ + PHYSIS + """
  (set `@P.LinkFlow` (`self.Flow`) p)
  (set `@P.LinkFrom` """ + here + """ p)
  (set `@P.LinkReach` """ + reach + """ p)
  (set `@P.LinkCarry` (+ (`@P.LinkCarry` p) 1) p)
  (set `@P.LinkBeamMode` 0 p)
  (set `@P.LinkBeamFlow` (`self.Flow`) p)
  (set `@P.LinkBeamA` """ + here + """ p)
  (set `@P.LinkBeamB` (`Actor.K2_GetActorLocation` p) p)
  """ + spawn('BP_LinkBeam', here) + """
  (`@P.PhysisNote` p (`KismetStringLibrary.Concat_StrStr` "Carrying " """ + FLOW_NAME + """))
  """ + snd(sound('take'), .9) + ')')
    # What a press does to this node (PhysisLink has already checked that it is shown, in reach and in plain sight).
    write(N, 'Linked', """(fn `Linked`
  """ + PHYSIS + """
  (if (== (`self.Kind`) 0)
    (set `@P.LinkTo` (+ (+ (`self.K2_GetActorLocation`) (`self.Perch`)) """ + vec(0.0, 0.0, 96.0) + """) p)
    (set `@P.LinkBeamMode` 2 p)
    (set `@P.LinkBeamFlow` "" p)
    (set `@P.LinkBeamA` """ + here + """ p)
    (set `@P.LinkBeamB` (`Actor.K2_GetActorLocation` p) p)
    """ + spawn('BP_LinkBeam', here) + """
    """ + spawn('BP_LinkPull', '(`Actor.K2_GetActorLocation` p)') + """
    """ + snd(sound('pull'), .8) + """
    (elif (or (== (`self.Kind`) 1) (and (== (`self.Kind`) 3) (and (`self.Fed`) (not """ + same('(`@P.LinkFlow` p)', '(`self.Flow`)') + """))))
      (`self.Take`)
      (elif """ + same('(`@P.LinkFlow` p)', '(`self.Flow`)') + """
        (if (and (== (`self.Kind`) 2) (`self.Fed`))
          (`@P.PhysisNote` p "It already holds its flow.")
          (else
            (if (not (`self.Fed`))
              (set `self.Fed` true)
              (if (and (not """ + empty('(`self.Give`)') + """) (not """ + has(PF, '(`self.Give`)') + """))
                (`@P.PhysisGive` p (`self.Give`)))
              (if (not """ + empty('(`self.Done`)') + """)
                (`@P.PhysisSay` p (`self.Done`)))
              (set `@P.LinkBeamMode` 1 p)
              (set `@P.LinkBeamFlow` (`self.Flow`) p)
              (set `@P.LinkBeamA` (`@P.LinkFrom` p) p)
              (set `@P.LinkBeamB` """ + here + """ p)
              """ + spawn('BP_LinkBeam', here) + """
              """ + snd(sound('feed'), .9) + """)
            (if (== (`self.Kind`) 2)
              (set `@P.LinkFlow` "" p)
              (else
                (set `@P.LinkFrom` """ + here + """ p)
                (set `@P.LinkReach` """ + reach + """ p)))))
        (else
          (`@P.PhysisNote` p (`KismetStringLibrary.Concat_StrStr` "It waits for " (`KismetStringLibrary.Concat_StrStr` """ + FLOW_NAME + """ "."))))))))""")
    glow = pick('(`self.Fed`)', '9.0', pick('(>= (`self.Kind`) 2)', '1.5', '6.0'))
    size = '(+ 1.0 (* 0.22 (`self.Swell`)))'
    write(N, 'EventGraph', """(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Shown` (and (or """ + empty('(`self.Need`)') + ' ' + has(PF, '(`self.Need`)') + """) (or """ + empty('(`self.Hide`)') + ' (not ' + has(PF, '(`self.Hide`)') + """))))
  (`self.SetActorHiddenInGame` (not (`self.Shown`)))
  (if (and (not (`self.Fed`)) (and (>= (`self.Kind`) 2) (and (not """ + empty('(`self.Give`)') + ') ' + has(PF, '(`self.Give`)') + """)))
    (set `self.Fed` true))
  (set `self.Aimed` (and (`self.Shown`) (`KismetMathLibrary.EqualEqual_ObjectObject` (`@P.LinkAim` p) self)))
  (set `self.Swell` (`KismetMathLibrary.FInterpTo` (`self.Swell`) """ + pick('(`self.Aimed`)', '1.0', '0.0') + """ DeltaSeconds 10.0))
  (`SceneComponent.SetRelativeScale3D` (`self.Shape`) """ + vec(size, size, size) + """)
  (`LightComponent.SetIntensity` (`self.Glow`) (* """ + glow + """ (+ 1.0 (* 2.5 (`self.Swell`))))))""")
    comp(N)
    defaults(N, {'Range': 3200.0, 'Reach': 3000.0})


# ---------------------------------------------------------------- BP_LinkBeam

def colour(flow_value):
    """Custom primitive data 0-2 of Shape from a flow name (M_GRBeam's Colour)."""
    out = []
    for index in range(3):
        value = pick(same(flow_value, '"water"'), BEAM_COLOURS['water'][index],
                     pick(same(flow_value, '"power"'), BEAM_COLOURS['power'][index], BEAM_COLOURS[''][index]))
        out.append('(`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) %d %s)' % (index, value))
    return '\n  '.join(out)


def draw(a, b, width):
    """Lays Shape (the engine cylinder: 1 m tall along z, centred) from a to b."""
    span = '(`KismetMathLibrary.VSize` (- %s %s))' % (b, a)
    return """(`self.K2_SetActorLocation` (* (+ %s %s) 0.5) false true)
  (`self.K2_SetActorRotation` (`KismetMathLibrary.MakeRotFromZ` (- %s %s)) true)
  (`self.SetActorScale3D` %s)
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 4 %s)""" % (a, b, b, a, vec(width, width, '(/ %s 100.0)' % span), span)


def beam():
    N = 'BP_LinkBeam'
    for name, kind in (('Mode', 'int'), ('A', 'Vector'), ('B', 'Vector'), ('Flow', 'string'), ('Serial', 'int'), ('Age', 'float'),
                       ('Lost', 'float'), ('Over', 'bool')):
        var(N, name, kind)
    hand = '(+ (`Actor.K2_GetActorLocation` p) %s)' % vec(0.0, 0.0, 35.0)
    gap = '(`KismetMathLibrary.VSize` (- (`self.B`) (`self.A`)))'
    write(N, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "NoCollision")
  """ + PHYSIS + """
  (set `self.Mode` (`@P.LinkBeamMode` p))
  (set `self.A` (`@P.LinkBeamA` p))
  (set `self.B` (`@P.LinkBeamB` p))
  (set `self.Flow` (`@P.LinkBeamFlow` p))
  (set `self.Serial` (`@P.LinkCarry` p))
  """ + colour('(`self.Flow`)') + """
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 3 1.0)
  """ + draw('(`self.A`)', '(`self.B`)', .1) + """)

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Age` (+ (`self.Age`) DeltaSeconds))
  (if (== (`self.Mode`) 0)
    (set `self.A` (`@P.LinkFrom` p))
    (set `self.B` """ + hand + """)
    (if (or (!= (`self.Serial`) (`@P.LinkCarry` p)) """ + empty('(`@P.LinkFlow` p)') + """)
      (set `self.Over` true)
      (else
        (bind (_hit _blocked) (`KismetSystemLibrary.LineTraceSingle` (`self.A`) (`self.B`)))
        (set `self.Lost` """ + pick('_blocked', '(+ (`self.Lost`) DeltaSeconds)', '0.0') + """)
        (if (or (or (> """ + gap + """ (`@P.LinkReach` p)) (> (`self.Lost`) 1.5)) (or (`@P.PhysisDead` p) (`@P.Talking` p)))
          (set `@P.LinkFlow` "" p)
          (`@P.PhysisNote` p "The flow slips back.")
          (set `self.Over` true)))))
  (if (== (`self.Mode`) 2)
    (set `self.B` """ + hand + """)
    (if (> (`self.Age`) 0.45)
      (set `self.Over` true)))
  (if (`self.Over`)
    (`self.K2_DestroyActor`)
    (else
      """ + draw('(`self.A`)', '(`self.B`)', pick('(== (`self.Mode`) 1)', '0.07', '0.1')) + """)))""")
    comp(N)


# ---------------------------------------------------------------- BP_LinkPull

def pull():
    N = 'BP_LinkPull'
    for name, kind in (('From', 'Vector'), ('To', 'Vector'), ('Age', 'float'), ('Span', 'float'), ('Lift', 'float')):
        var(N, name, kind)
    far = '(`KismetMathLibrary.VSize` (- (`self.To`) (`self.From`)))'
    cmc = '(`Character.CharacterMovement` p)'
    t = '(`KismetMathLibrary.FClamp` (/ (`self.Age`) (`self.Span`)) 0.0 1.0)'
    spot = '(+ (`KismetMathLibrary.VLerp` (`self.From`) (`self.To`) %s) %s)' % (t, vec(0.0, 0.0, '(* (`self.Lift`) (`KismetMathLibrary.Sin` (* 3.14159 %s)))' % t))
    safe = '(+ %s (+ (`self.Span`) 0.4))' % NOW
    # 26 m/s, at least 0.25 s; gravity off, untouchable, a slight arc. No sweep: PhysisLinkFind checked the line of sight.
    write(N, 'EventGraph', """(event `self.ReceiveBeginPlay`
  """ + PHYSIS + """
  (set `self.From` (`Actor.K2_GetActorLocation` p))
  (set `self.To` (`@P.LinkTo` p))
  (set `self.Span` """ + pick('(> (/ %s 2600.0) 0.25)' % far, '(/ %s 2600.0)' % far, '0.25') + """)
  (set `self.Lift` """ + pick('(< (* %s 0.06) 220.0)' % far, '(* %s 0.06)' % far, '220.0') + """)
  (if (> (`CharacterMovementComponent.GravityScale` """ + cmc + """) 0.0)
    (set `@P.StepGravity` (`CharacterMovementComponent.GravityScale` """ + cmc + """) p))
  (set `CharacterMovementComponent.GravityScale` 0.0 """ + cmc + """)
  (set `@P.LinkPulling` true p)
  (set `@P.SafeUntil` """ + pick('(> (`@P.SafeUntil` p) %s)' % safe, '(`@P.SafeUntil` p)', safe) + """ p))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Age` (+ (`self.Age`) DeltaSeconds))
  (`Actor.K2_SetActorLocation` p """ + spot + """ false true)
  (set `MovementComponent.Velocity` """ + vec(0.0, 0.0, 0.0) + ' ' + cmc + """)
  (if (>= (`self.Age`) (`self.Span`))
    (set `CharacterMovementComponent.GravityScale` """ + pick('(> (`@P.StepGravity` p) 0.0)', '(`@P.StepGravity` p)', '1.0') + ' ' + cmc + """)
    (set `@P.LinkPulling` false p)
    (`self.K2_DestroyActor`)))""")
    comp(N)


# ---------------------------------------------------------------- BP_LinkTether

def tether():
    N = 'BP_LinkTether'
    drone = 'object:' + B + 'BP_TrainingDrone.BP_TrainingDrone_C'
    for name, kind in (('A', drone), ('B', drone), ('HA', 'int'), ('HB', 'int'), ('DA', 'int'), ('DB', 'int'), ('Age', 'float'),
                       ('Serial', 'int'), ('Over', 'bool')):
        var(N, name, kind)
    ha, hb = '(`@D.Health` (`self.A`))', '(`@D.Health` (`self.B`))'
    lost = lambda held, now: pick('(> (- %s %s) 0)' % (held, now), '(- %s %s)' % (held, now), '0')
    la, lb = '(`Actor.K2_GetActorLocation` (`self.A`))', '(`Actor.K2_GetActorLocation` (`self.B`))'
    # 8 s, or until one of the two is gone. What one lost since the last frame the other loses too, past its armour;
    # one brought to nothing that way is finished by its own TakeHit, so it bursts, drops and counts as usual. When one
    # dies of her blow before this tick sees it, the other loses what that one still had.
    write(N, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "NoCollision")
  """ + colour('"power"') + """
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 3 1.0)
  """ + PHYSIS + """
  (set `self.Serial` (`@P.LinkTie` p))
  (bind a (cast `@D` (`@P.LinkA` p)))
  (set `self.A` a)
  (set `self.HA` (`@D.Health` a))
  (bind b (cast `@D` (`@P.LinkB` p)))
  (set `self.B` b)
  (set `self.HB` (`@D.Health` b)))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Age` (+ (`self.Age`) DeltaSeconds))
  (if (and (`KismetSystemLibrary.IsValid` (`self.A`)) (`KismetSystemLibrary.IsValid` (`self.B`)))
    (set `self.DA` """ + lost('(`self.HA`)', ha) + """)
    (set `self.DB` """ + lost('(`self.HB`)', hb) + """)
    (set `@D.Health` (- """ + ha + """ (`self.DB`)) (`self.A`))
    (set `@D.Health` (- """ + hb + """ (`self.DA`)) (`self.B`))
    (set `self.HA` """ + ha + """)
    (set `self.HB` """ + hb + """)
    """ + draw(la, lb, .08) + """
    (if (or (> (`self.Age`) 8.0) (!= (`self.Serial`) (`@P.LinkTie` p)))
      (set `self.Over` true))
    (if (<= (`self.HB`) 0)
      (set `self.Over` true)
      (`@D.TakeHit` (`self.B`) 99))
    (if (<= (`self.HA`) 0)
      (set `self.Over` true)
      (`@D.TakeHit` (`self.A`) 99))
    (else
      (set `self.Over` true)
      (if (`KismetSystemLibrary.IsValid` (`self.A`))
        (set `@D.Health` (- """ + ha + """ (`self.HB`)) (`self.A`))
        (if (<= """ + ha + """ 0)
          (`@D.TakeHit` (`self.A`) 99)))
      (if (`KismetSystemLibrary.IsValid` (`self.B`))
        (set `@D.Health` (- """ + hb + """ (`self.HA`)) (`self.B`))
        (if (<= """ + hb + """ 0)
          (`@D.TakeHit` (`self.B`) 99)))))
  (if (`self.Over`)
    (`self.K2_DestroyActor`)))""")
    comp(N)


# ---------------------------------------------------------------- BP_GroveDirector

MPC = '"/Game/Grove/Materials/MPC_Grove.MPC_Grove"'


def tagged(tag, hidden, name):
    return """(for %s (`GameplayStatics.GetAllActorsWithTag` "%s")
    (`Actor.SetActorHiddenInGame` %s %s)
    (`Actor.SetActorEnableCollision` %s (not %s)))""" % (name, tag, name, hidden, name, hidden)


def once(token, cond, body):
    return '(if (and %s (not %s))\n    (`@P.PhysisGive` p "%s")\n    %s)' % (cond, has(PF, token), token, body)


def director():
    N = 'BP_GroveDirector'
    for name, kind in (('Motion', 'float'), ('Heal', 'float')):
        var(N, name, kind)
    for name in ('Arrive', 'State'):
        shell(N, name)
    # 0.5 s in, after PhysisRestore and BP_Awakening's Begin have set the flags: a direct start still gets ,grove, and
    # ,at_grove, (so its saves load here) and, with no objective and Thessaly not yet met, a quest; the first visit
    # says the arrival and narrates Divinity's line. A healed grove starts healed.
    write(N, 'Arrive', """(fn `Arrive`
  """ + PHYSIS + """
  (if (not """ + has(PF, ',grove,') + """)
    (`@P.PhysisGive` p ",grove,"))
  (if (not """ + has(PF, ',at_grove,') + """)
    (`@P.PhysisGive` p ",at_grove,"))
  (if (and """ + empty('(`@P.Objective` p)') + ' (not ' + has(PF, ',tess,') + """))
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_ARRIVE) + """))
  (if """ + has(PF, ',warden,') + """
    (set `self.Heal` 1.0))
  (if """ + has(PF, ',resonance,') + """
    (set `self.Motion` 1.0))
  (if (not """ + has(PF, ',grove_seen,') + """)
    (`@P.PhysisGive` p ",grove_seen,")
    (`@P.PhysisSay` p """ + lit(lore.MESSAGES['arrive']) + """)
    (`@P.PhysisNarrate` p """ + lit(lore.ARRIVAL_LINE[0]) + """)))""")
    water, power, warden = has(PF, ',water,'), has(PF, ',power,'), has(PF, ',warden,')
    first = '(or %s %s)' % (has(PF, ',gr_first_w,'), has(PF, ',gr_first_e,'))
    # Every 0.25 s: what the tokens show and hide, which lifeline came first (the living-terrain rule's saved choice),
    # and the quests that follow from a token rather than from a person or a Still Point.
    write(N, 'State', """(fn `State`
  """ + PHYSIS + """
  """ + tagged('GroveBlight', warden, 'blight') + """
  """ + tagged('GroveBloom', '(not %s)' % warden, 'bloom') + """
  """ + tagged('GroveWater', '(not %s)' % water, 'wet') + """
  """ + tagged('GrovePower', '(not %s)' % power, 'live') + """
  (if (and (and """ + water + ' (not ' + power + ')) (not ' + first + """))
    (`@P.PhysisGive` p ",gr_first_w,")
    (`@P.PhysisNote` p """ + lit(lore.MESSAGES['first_w']) + """))
  (if (and (and """ + power + ' (not ' + water + ')) (not ' + first + """))
    (`@P.PhysisGive` p ",gr_first_e,")
    (`@P.PhysisNote` p """ + lit(lore.MESSAGES['first_e']) + """))
  """ + once(',gr_q_gully,', has(PF, ',resonance,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_GULLY)) + """
  """ + once(',gr_q_gate,', '(and %s %s)' % (water, power), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_GATE)) + """
  """ + once(',gr_q_core,', has(PF, ',arraygate,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_CORE)) + """
  """ + once(',gr_q_warden,', has(PF, ',stabilized,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_WARDEN)) + ')')
    at = '(`Actor.K2_GetActorLocation` p)'
    write(N, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (set `self.Motion` 0.12)
  (`KismetSystemLibrary.K2_SetTimer` self "Arrive" 0.5 false)
  (`KismetSystemLibrary.K2_SetTimer` self "State" 0.25 true))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Motion` (`KismetMathLibrary.FInterpTo` (`self.Motion`) """ + pick(has(PF, ',resonance,'), '1.0', '0.12') + """ DeltaSeconds 0.6))
  (set `self.Heal` (`KismetMathLibrary.FInterpTo_Constant` (`self.Heal`) """ + pick(warden, '1.0', '0.0') + """ DeltaSeconds 0.04))
  (`KismetMaterialLibrary.SetScalarParameterValue` """ + MPC + """ "Motion" (`self.Motion`))
  (`KismetMaterialLibrary.SetScalarParameterValue` """ + MPC + """ "Heal" (`self.Heal`))
  (`KismetMaterialLibrary.SetVectorParameterValue` """ + MPC + """ "Her" (make `LinearColor` (.x """ + at + ') (.y ' + at + ') (.z ' + at + """) 0.0))
  (if (and """ + has(PF, ',resonance,') + """ (not (`@P.LinkPulling` p)))
    (`@P.PhysisLinkFind` p)))""")
    comp(N)


# ---------------------------------------------------------------- BP_GroveCurrent

def current():
    """BP_Current's graph for Earth: shown while Need is held; standing in it 0.8 s travels (Dest 1 PhysisToGrove, 2
    PhysisGroveHome). Armed once she has been outside it. After a load with ,trip_g, it takes the token and moves her
    onto the level's spot (TargetPoint GroveArrival here, GroveReturn in the Center). The temple's current points the
    quest at itself once (,gr_currenthint,) when the Shepherd has fallen and Earth is not yet visited."""
    N = 'BP_GroveCurrent'
    for name, kind in (('Need', 'string'), ('Dest', 'int'), ('Radius', 'float')):
        var(N, name, kind, True)
    for name, kind in (('Stay', 'float'), ('Armed', 'bool'), ('Gone', 'bool')):
        var(N, name, kind)
    land = '\n    '.join("""(for %s (`GameplayStatics.GetAllActorsWithTag` "%s")
      (`Actor.K2_SetActorLocation` p (`Actor.K2_GetActorLocation` %s) false true)
      (`@P.PhysisCheckpoint` p (.x (`Actor.K2_GetActorLocation` %s)) (.y (`Actor.K2_GetActorLocation` %s)) (.z (`Actor.K2_GetActorLocation` %s))))"""
                           % ((spot, tag) + (spot,) * 4) for spot, tag in (('spot', 'GroveArrival'), ('back', 'GroveReturn')))
    ready = '(or %s %s)' % (empty('(`self.Need`)'), has(PF, '(`self.Need`)'))
    reach = pick('(> (`self.Radius`) 0.0)', '(`self.Radius`)', '180.0')
    gap = '(`self.GetDistanceTo` p)'
    glow = '(/ (`self.Stay`) 0.8)'
    cam = '(`GameplayStatics.GetPlayerCameraManager` 0)'
    write(N, 'EventGraph', """(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (if """ + has(PF, ',trip_g,') + """
    (set `@P.Flags` (`KismetStringLibrary.Replace` """ + PF + """ ",trip_g," "" "CaseSensitive") p)
    """ + land + """)
  (if (and (and """ + ready + """ (== (`self.Dest`) 1)) (and (not """ + has(PF, ',grove,') + ') (not ' + has(PF, ',gr_currenthint,') + """)))
    (`@P.PhysisGive` p ",gr_currenthint,")
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_CURRENT) + """))
  (`self.SetActorHiddenInGame` (not """ + ready + """))
  (if (> """ + gap + ' (+ ' + reach + """ 150.0))
    (set `self.Armed` true))
  (if (and (and """ + ready + """ (`self.Armed`)) (and (< """ + gap + ' ' + reach + """) (and (not (`@P.Cinematic` p)) (not (`@P.PhysisDead` p)))))
    (if (<= (`self.Stay`) 0.0)
      """ + snd(sound('travel')) + """)
    (set `self.Stay` (+ (`self.Stay`) DeltaSeconds))
    (`PlayerCameraManager.SetManualCameraFade` """ + cam + ' ' + pick('(> %s 1.0)' % glow, '1.0', glow) + """ (make `LinearColor` 0.85 1.0 0.9 1.0) false)
    (if (and (>= (`self.Stay`) 0.8) (not (`self.Gone`)))
      (set `self.Gone` true)
      (if (== (`self.Dest`) 2)
        (`@P.PhysisGroveHome` p)
        (elif (== (`self.Dest`) 1)
          (`@P.PhysisToGrove` p))))
    (elif (> (`self.Stay`) 0.0)
      (set `self.Stay` 0.0)
      (`PlayerCameraManager.StopCameraFade` """ + cam + """))))""")
    comp(N)
    defaults(N, {'Radius': 180.0})


# ---------------------------------------------------------------- BP_Physis

def physis_shells():
    """Variables and empty functions first: the grove's Blueprints read and call them."""
    P = 'BP_Physis'
    actor = 'object:/Script/Engine.Actor'
    for name, kind in (('LinkReady', 'float'), ('LinkPulling', 'bool'), ('LinkFlow', 'string'), ('LinkFrom', 'Vector'), ('LinkReach', 'float'),
                       ('LinkCarry', 'int'), ('LinkTo', 'Vector'), ('LinkBeamMode', 'int'), ('LinkBeamFlow', 'string'), ('LinkBeamA', 'Vector'),
                       ('LinkBeamB', 'Vector'), ('LinkAim', actor), ('LinkDot', 'float'), ('LinkA', actor), ('LinkB', actor),
                       ('LinkGap', 'float'), ('LinkTie', 'int')):
        var(P, name, kind)
    for name in ('PhysisLink', 'PhysisLinkFind', 'PhysisLinkFoe', 'PhysisToGrove', 'PhysisGroveHome'):
        shell(P, name)
    comp(P)


def physis():
    P = 'BP_Physis'
    cam = '(`GameplayStatics.GetPlayerCameraManager` 0)'
    eye = '(`PlayerCameraManager.GetCameraLocation` %s)' % cam
    ahead = '(`KismetMathLibrary.GetForwardVector` (`PlayerCameraManager.GetCameraRotation` %s))' % cam
    head = '(+ (`self.K2_GetActorLocation`) %s)' % vec(0.0, 0.0, 60.0)
    # The node the next press would take: shown, within its own Range of her, within 30 degrees of the view's centre
    # and in plain sight from her head; of those, the one nearest the centre. BP_GroveDirector calls this every frame
    # (the aimed node swells), and PhysisLink once more at the press. The trace is against the meshes themselves
    # (complex): a cliff rock's collision hull bulges well past the rock, and would hide knots that are in plain sight.
    spot = '(+ (`Actor.K2_GetActorLocation` n) %s)' % vec(0.0, 0.0, 100.0)
    far = '(`KismetMathLibrary.VSize` (- %s %s))' % (spot, head)
    dot = '(`KismetMathLibrary.Dot_VectorVector` %s (`KismetMathLibrary.Normal` (- %s %s)))' % (ahead, spot, eye)
    write(P, 'PhysisLinkFind', """(fn `PhysisLinkFind`
  (set `self.LinkAim` null)
  (set `self.LinkDot` 0.866)
  (for e (`GameplayStatics.GetAllActorsOfClass` "@N.BP_LinkNode_C")
    (bind n (cast `@N` e))
    (if (and (`@N.Shown` n) (and (> """ + far + ' 160.0) (< ' + far + ' ' + pick('(> (`@N.Range` n) 0.0)', '(`@N.Range` n)', '3200.0') + """)))
      (if (> """ + dot + """ (`self.LinkDot`))
        (bind (_hit _blocked) (`KismetSystemLibrary.LineTraceSingle` """ + head + ' ' + spot + """ "TraceTypeQuery1" true))
        (if (not _blocked)
          (set `self.LinkDot` """ + dot + """)
          (set `self.LinkAim` n))))))""")
    # No node answers: the enemy nearest the view's centre (24 m, 35 degrees) is tied to its nearest neighbour within
    # 15 m (BP_LinkTether), or, alone, held still for 2 s. Static targets are never tethered.
    foe = '(`Actor.K2_GetActorLocation` d)'
    fdot = '(`KismetMathLibrary.Dot_VectorVector` %s (`KismetMathLibrary.Normal` (- %s %s)))' % (ahead, foe, eye)
    alive = lambda d: '(and (not (`@D.Static` %s)) (> (`@D.Health` %s) 0))' % (d, d)
    mid = '(`Actor.K2_GetActorLocation` (`self.LinkA`))'
    write(P, 'PhysisLinkFoe', """(fn `PhysisLinkFoe`
  (set `self.LinkA` null)
  (set `self.LinkB` null)
  (set `self.LinkDot` 0.819)
  (for e (`GameplayStatics.GetAllActorsOfClass` "@D.BP_TrainingDrone_C")
    (bind d (cast `@D` e))
    (if (and """ + alive('d') + ' (< (`KismetMathLibrary.VSize` (- ' + foe + """ (`self.K2_GetActorLocation`))) 2400.0))
      (if (> """ + fdot + """ (`self.LinkDot`))
        (set `self.LinkDot` """ + fdot + """)
        (set `self.LinkA` d))))
  (if (`KismetSystemLibrary.IsValid` (`self.LinkA`))
    (set `self.LinkReady` (+ """ + NOW + """ 0.6))
    (set `self.LinkGap` 1500.0)
    (for e2 (`GameplayStatics.GetAllActorsOfClass` "@D.BP_TrainingDrone_C")
      (bind d2 (cast `@D` e2))
      (if (and """ + alive('d2') + """ (not (`KismetMathLibrary.EqualEqual_ObjectObject` d2 (`self.LinkA`))))
        (if (< (`KismetMathLibrary.VSize` (- (`Actor.K2_GetActorLocation` d2) """ + mid + """)) (`self.LinkGap`))
          (set `self.LinkGap` (`KismetMathLibrary.VSize` (- (`Actor.K2_GetActorLocation` d2) """ + mid + """)))
          (set `self.LinkB` d2))))
    """ + snd(sound('tether'), .9) + """
    (if (`KismetSystemLibrary.IsValid` (`self.LinkB`))
      (set `self.LinkTie` (+ (`self.LinkTie`) 1))
      """ + spawn('BP_LinkTether', mid) + """
      (`self.PhysisNote` "Tethered: what one suffers, the other suffers.")
      (else
        (bind lone (cast `@D` (`self.LinkA`)))
        (set `@D.StunUntil` (+ """ + NOW + """ 2.0) lone)
        (`self.PhysisNote` "Held fast. Nothing near to tie it to.")))
    (else
      (`self.PhysisNote` "Nothing answers the link."))))""")
    # Resonance Link (G / left stick click): no cost, 0.6 s between uses. It reports the ability first, so the
    # Center's and the Conclave's resonance sockets answer it.
    write(P, 'PhysisLink', """(fn `PhysisLink`
  (if (and (and (not (`self.Cinematic`)) (not (`self.PhysisDead`))) (and (and (not (`self.Talking`)) (not (`self.LinkPulling`))) """ + has(MINE, ',resonance,') + """))
    (if (> """ + NOW + """ (`self.LinkReady`))
      (`self.PhysisUsedAbility` ",resonance,")
      (`self.PhysisLinkFind`)
      (if (`KismetSystemLibrary.IsValid` (`self.LinkAim`))
        (set `self.LinkReady` (+ """ + NOW + """ 0.6))
        (bind n (cast `@N` (`self.LinkAim`)))
        (`@N.Linked` n)
        (else
          (`self.PhysisLinkFoe`))))))""")
    # The temple's current to Earth (BP_GroveCurrent Dest 1, Need ,shepherd,). ,trip_g, has the current move her onto
    # the Hollow's arrival spot after the load; the save makes Earth load there (,at_grove,). A carried flow is never
    # saved. Leaving the Conclave's mark behind keeps PhysisLoadGame's order simple: only one ,at_*, is ever held.
    write(P, 'PhysisToGrove', """(fn `PhysisToGrove`
  (set `self.Flags` (`KismetStringLibrary.Replace` (`self.Flags`) ",at_conclave," "" "CaseSensitive"))
  (if (not """ + has(MINE, ',grove,') + """)
    (`self.PhysisGive` ",grove,"))
  (if (not """ + has(MINE, ',at_grove,') + """)
    (`self.PhysisGive` ",at_grove,"))
  (`self.PhysisGive` ",trip_g,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_Grove" true "nocine,load"))""" % ARRIVE_CM)
    write(P, 'PhysisGroveHome', """(fn `PhysisGroveHome`
  (set `self.LinkFlow` "")
  (set `self.Flags` (`KismetStringLibrary.Replace` (`self.Flags`) ",at_grove," "" "CaseSensitive"))
  (`self.PhysisGive` ",trip_g,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_CenterOfTheUniverse" true "nocine,load"))""" % HOME_CM)
    comp(P)


def wire():
    write('BP_Physis', 'EventGraph', """(event `EnhancedInput|/Game/Input/Actions/IA_Link`
  (:`Started`
    (`self.PhysisLink`)))""", 'input IA_Link')
    comp('BP_Physis')


# ---------------------------------------------------------------- Grove branches in the shared graphs

def flag(token):
    return '(select `bool` (`KismetStringLibrary.Contains` (`self.Flags`) "%s") :`false` 0.0 :`true` 1.0)' % token


def shared():
    P = 'BP_Physis'
    # Fidelity: Earth counts as stage 2 at least, like the Conclave. Augmentations: the grove's five.
    swaps = [('(or (`KismetStringLibrary.Contains` (`self.Flags`) ",settle,") (`KismetStringLibrary.Contains` (`self.Flags`) ",conclave,"))',
              '(or (or (`KismetStringLibrary.Contains` (`self.Flags`) ",settle,") (`KismetStringLibrary.Contains` (`self.Flags`) ",conclave,")) '
              '(`KismetStringLibrary.Contains` (`self.Flags`) ",grove,"))')]
    for last, new in ((',aug_hp6,', ',aug_hp7,'), (',aug_katana4,', ',aug_katana5,'), (',aug_pistol3,', ',aug_pistol4,'),
                      (',aug_defense4,', ',aug_defense5,'), (',aug_agility4,', ',aug_agility5,')):
        swaps.append((flag(last) + ')', '(+ %s %s))' % (flag(last), flag(new))))
    patch(P, 'PhysisFidelity', swaps, ',aug_hp7,')
    # Music: the grove's own while a BP_GroveDirector stands in the level.
    patch(P, 'PhysisMusicPick', [(
        '(fn `PhysisMusicPick`\n  (bind _outactors (`GameplayStatics.GetAllActorsOfClass` "@BBP_ConclaveDirector.BP_ConclaveDirector_C"))\n'
        '  (if (> (`KismetArrayLibrary.Array_Length` _outactors) 0)',
        '(fn `PhysisMusicPick`\n  (bind _outactors (`GameplayStatics.GetAllActorsOfClass` "@BBP_ConclaveDirector.BP_ConclaveDirector_C"))\n'
        '  (bind _groves (`GameplayStatics.GetAllActorsOfClass` "@BBP_GroveDirector.BP_GroveDirector_C"))\n'
        '  (if (> (`KismetArrayLibrary.Array_Length` _groves) 0)\n'
        '    (bind _grovemusic (`GameplayStatics.SpawnSound2D` "%s.%s" (* 0.1 (`self.MusicVol`))))\n'
        '    (set `self.MusicComp` _grovemusic)\n'
        '    (return))\n'
        '  (if (> (`KismetArrayLibrary.Array_Length` _outactors) 0)' % (sound('music'), sound('music').split('/')[-1]))], 'BP_GroveDirector')
    # Load Game and the menu's Continue: a save made on Earth opens L_Grove (tested first: ,center, is always held).
    save_flags = '(`@BBP_PhysisSave.Flags` _asbp_physis_save)'
    load = [('(if (`KismetStringLibrary.Contains` %s ",at_conclave,")\n' % save_flags,
             '(if (`KismetStringLibrary.Contains` %s ",at_grove,")\n(`GameplayStatics.OpenLevel` "L_Grove" true "nocine,load")\n'
             '(elif (`KismetStringLibrary.Contains` %s ",at_conclave,")\n' % (save_flags, save_flags)),
            ('(`GameplayStatics.OpenLevel` "L_BattleStation" true "nocine,load")', '(`GameplayStatics.OpenLevel` "L_BattleStation" true "nocine,load"))')]
    patch(P, 'PhysisLoadGame', load, ',at_grove,')
    patch('BP_MenuHUD', 'MenuContinue', load, ',at_grove,')
    comp('BP_MenuHUD')
    # The save's exact spot: world 4 while a BP_GroveDirector stands in the level (1 station, 2 Center, 3 Conclave).
    world_old = ('(select `bool` (> (`KismetArrayLibrary.Array_Length` %s) 0) :`false` (select `bool` (> (`KismetArrayLibrary.Array_Length` %s) 0) '
                 ':`false` 1 :`true` 2) :`true` 3)')
    world_new = '(select `bool` (> (`KismetArrayLibrary.Array_Length` _groves) 0) :`false` %s :`true` 4)'
    groves = '(bind _groves (`GameplayStatics.GetAllActorsOfClass` "@BBP_GroveDirector.BP_GroveDirector_C"))\n'
    old = world_old % ('_outactors_4', '_outactors_5')
    patch(P, 'PhysisSaveGame', [
        ('      (bind _outactors_4 (`GameplayStatics.GetAllActorsOfClass` "@BBP_ConclaveDirector.BP_ConclaveDirector_C"))\n',
         '      ' + groves + '      (bind _outactors_4 (`GameplayStatics.GetAllActorsOfClass` "@BBP_ConclaveDirector.BP_ConclaveDirector_C"))\n'),
        (old, world_new % old)], 'BP_GroveDirector')
    old = world_old % ('_outactors', '_outactors_2')
    patch(P, 'PhysisRestore', [
        ('  (bind _outactors (`GameplayStatics.GetAllActorsOfClass` "@BBP_ConclaveDirector.BP_ConclaveDirector_C"))\n',
         '  ' + groves + '  (bind _outactors (`GameplayStatics.GetAllActorsOfClass` "@BBP_ConclaveDirector.BP_ConclaveDirector_C"))\n'),
        (old, world_new % old)], 'BP_GroveDirector')
    comp(P)


# ---------------------------------------------------------------- the pause menu's map page and the relics' scan tags

def wrap(text, width=62):
    """HUD lines broken with ~ (physis_aaa_tools.wrap_text)."""
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


MAP_NAMES = (('The Hollow', 'Hollow'), ('The Reclaimed Road', 'Road'), ('Old Town', 'Old Town'), ('The Field Camp', 'Field Camp'),
             ('The Understory', 'Understory'), ('The Drowned Campus', 'Campus'), ('The Weir', 'Weir'), ('The High Canopy', 'Canopy'),
             ('The Relay', 'Relay'), ('The Heartwood', 'Heartwood'), ('The Falls', 'Falls'))


def hud():
    """BP_PhysisHUD.PageMap: Earth's page (T_UI_MapGrove, its title and its places' names) while a BP_GroveDirector
    stands in the level; the Center's and the Conclave's pages are untouched. Run after grove:map_art."""
    H = 'BP_PhysisHUD'
    grove = '(> (`KismetArrayLibrary.Array_Length` _groves) 0)'
    size = '(* (* _returnvalue 0.85) 0.35)'
    font = '"/Game/UI/F_Physis.F_Physis"'
    labels = []
    for region, name in MAP_NAMES:
        x, y = plan.REGIONS[region][:2]
        u, v = (y + plan.MAP_HALF) / (2 * plan.MAP_HALF), (plan.MAP_HALF - x) / (2 * plan.MAP_HALF)
        px = '(- (+ _returnvalue_2 (* %.5f _returnvalue_4)) (* _returnvalue %.1f))' % (u, len(name) * 4.4)
        py = '(- (+ _returnvalue_3 (* %.5f _returnvalue_4)) (* _returnvalue 30.0))' % v
        labels.append('(`self.DrawTextPlate` "%s" %s %s %s)' % (name, px, py, size))
        labels.append('(`self.DrawText` "%s" (struct :`R` 1.0 :`G` 0.92 :`B` 0.78 :`A` 1.0) %s %s %s %s)' % (name, px, py, font, size))
    draw = '_returnvalue_2 _returnvalue_3 _returnvalue_4 _returnvalue_4 0.0 0.0 1.0 1.0)'
    title = '(* _returnvalue 960.0) (* _returnvalue 150.0)'
    big = '(* (* _returnvalue 1.5) 0.35)'
    centre_title = ('(`self.DrawText` "THE CENTER OF THE UNIVERSE" (struct :`R` 1.0 :`G` 0.82 :`B` 0.42 :`A` 1.0) %s %s %s)' % (title, font, big))
    cache = '(select `bool` %s :`false` "Echo Cache (cyan ray)" :`true` "Seed Cache (blue ray)")' % grove
    patch(H, 'PageMap', [
        ('  (bind _returnvalue_6 (> (`KismetArrayLibrary.Array_Length` _outactors) 0))\n',
         '  (bind _returnvalue_6 (> (`KismetArrayLibrary.Array_Length` _outactors) 0))\n'
         '  (bind _groves (`GameplayStatics.GetAllActorsOfClass` "@BBP_GroveDirector.BP_GroveDirector_C"))\n'),
        ('      (else\n        (`self.DrawTexture` "/Game/UI/T_UI_MapCenter.T_UI_MapCenter" ' + draw + '))',
         '      (elif ' + grove + '\n        (`self.DrawTexture` "/Game/UI/T_UI_MapGrove.T_UI_MapGrove" ' + draw + '\n'
         '      (else\n        (`self.DrawTexture` "/Game/UI/T_UI_MapCenter.T_UI_MapCenter" ' + draw + ')))'),
        ('      (else\n        (`self.DrawTextPlate` "The Still Glade"',
         '      (elif ' + grove + '\n        ' + '\n        '.join(labels) + '\n      (else\n        (`self.DrawTextPlate` "The Still Glade"'),
        (size + ')))\n    (`self.DrawTexture` "/Game/UI/T_UI_Reticle.T_UI_Reticle" (* _returnvalue 958.0)',
         size + '))))\n    (`self.DrawTexture` "/Game/UI/T_UI_Reticle.T_UI_Reticle" (* _returnvalue 958.0)'),
        ('      (else\n        (`self.DrawTextPlate` "THE CENTER OF THE UNIVERSE"',
         '      (elif ' + grove + '\n        (`self.DrawTextPlate` "EARTH: THE WOUNDED GROVE" %s %s)\n' % (title, big) +
         '        (`self.DrawText` "EARTH: THE WOUNDED GROVE" (struct :`R` 1.0 :`G` 0.82 :`B` 0.42 :`A` 1.0) %s %s %s)\n' % (title, font, big) +
         '      (else\n        (`self.DrawTextPlate` "THE CENTER OF THE UNIVERSE"'),
        (centre_title + '))', centre_title + ')))'),
        ('(`self.DrawTextPlate` "Echo Cache (cyan ray)"', '(`self.DrawTextPlate` ' + cache),
        ('(`self.DrawText` "Echo Cache (cyan ray)"', '(`self.DrawText` ' + cache),
    ], 'BP_GroveDirector')
    comp(H)


def relic():
    """BP_Relic.RelicTag: the grove's relics get their own Logbook entries (by token, tested before the shared rows:
    ,aug_hp, would otherwise name the Heartwood's gift a vault's heart in the Center)."""
    rows = {row[1]: row for row in lore.GROVE_SCANS}
    chain = ((',pin,', "Burr's Coupling Pin"), (',can', 'A Seed Canister'), (',aug_hp7,', "The Heartwood's Gift"), (',aug_katana5,', 'The Old Edge'),
             (',gr_', 'Seed Cache'))
    head = ''
    for index, (token, title) in enumerate(chain):
        test = '(`KismetStringLibrary.Contains` _token "%s")' % token
        call_ = '(`self.RelicTagAs` %s %s %s)' % (lit(title), lit(wrap(rows[title][2])), 'true' if rows[title][4] else 'false')
        head += ('(if %s\n    %s\n    ' if index == 0 else '(elif %s\n    %s\n    ') % (test, call_)
    patch('BP_Relic', 'RelicTag', [
        ('  (if (`KismetStringLibrary.Contains` _token ",crown,")\n', '  ' + head + '(elif (`KismetStringLibrary.Contains` _token ",crown,")\n'),
        ('There are others in the Conclave.")', 'There are others in the Conclave.")' + ')' * len(chain)),
    ], ',aug_hp7,')
    comp('BP_Relic')


def music():
    """PhysisMusicPick's grove branch plays the grove's own music once grove:audio has imported it (part `shared`
    wrote that branch with the Center's theme while the grove had none)."""
    own = GA + 'S_Music_Grove'
    if not (ROOT / ('Content' + own[5:] + '.uasset')).exists():
        print('music: S_Music_Grove is not imported yet (Tools/build_physis_grove_audio.py, then grove:audio)')
        FAILED.append('music (no S_Music_Grove)')
        return
    head = '(if (> (`KismetArrayLibrary.Array_Length` _outactors_2) 0)\n    (bind _returnvalue (`GameplayStatics.SpawnSound2D` "%s.%s"'
    patch('BP_Physis', 'PhysisMusicPick', [(head % ('/Game/Center/Audio/S_Music_Center', 'S_Music_Center'), head % (own, 'S_Music_Grove'))],
          'S_Music_Grove')
    comp('BP_Physis')


PARTS = {'node': node, 'beam': beam, 'pull': pull, 'tether': tether, 'director': director, 'current': current, 'physis': physis,
         'input': wire, 'shared': shared, 'hud': hud, 'relic': relic, 'music': music}

if __name__ == '__main__':
    parts = ARGS or ['node', 'beam', 'pull', 'tether', 'director', 'current', 'physis', 'input']
    print('Earth arrival %s cm, Center arrival %s cm' % (ARRIVE_CM, HOME_CM))
    if any(part not in ('shared', 'hud', 'relic', 'music') for part in parts):
        physis_shells()
    for part in parts:
        PARTS[part]()
    for bp in TOUCHED:
        save(bp)
    print('FAILED:', FAILED or 'none')
