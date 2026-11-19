"""Blueprint logic for level 5, Arche, the First Ones' Planet (Tools/arche/README.md). Run from the project folder
with the editor open, after `arche:blueprints` has made the Blueprint assets and IA_Reweave:
    python3 Tools/blueprint_logic/arche_logic.py [weave] [director] [current] [physis] [input] [shared] [hud] [relic] [music]

weave     BP_Weave: something the Lens unwove. Shown by tokens; its mark (a ring of slivers round a pearl light) turns
          while it is sundered and swells when aimed at; Weave() knits it (for good, or for Hold seconds), keeps its
          loom's limit, gives its token; a woven thing held by a token is whole again after a load
director  BP_ArcheDirector: the arrival, tagged actors by token (the sounds among the ArcheScar ones faded out once the
          Sunderer falls: hiding does not silence them), the quests that follow from a token, the aim
current   BP_ArcheCurrent: the Divinity current between the Center's temple and the Landing
physis    BP_Physis: PhysisReweave, PhysisWeaveFind, PhysisToArche, PhysisArcheHome
input     IA_Reweave's Started event calls PhysisReweave
shared    Arche branches in graphs other levels own: fidelity and augmentations, music, load, save and restore, the
          menu's Continue
hud       BP_PhysisHUD.PageMap: Arche's map page (after arche:map_art)
relic     BP_Relic.RelicTag: Arche's relics' own Logbook entries
music     PhysisMusicPick plays S_Music_Arche (after arche:audio)

It stands on grove_logic.py's helpers (the 5.9 dialect layer: var, shell, write, patch, comp, save). In the text
below @P is BP_Physis, @W BP_Weave, @D BP_TrainingDrone, @B the Blueprint folder.
"""
import json
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
sys.path.insert(0, str(ROOT / 'Content/Python'))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
ARGS = [a for a in sys.argv[1:] if a != '--dry']
_argv, sys.argv = sys.argv, [a for a in sys.argv if a == '--dry' or a == sys.argv[0]]
import grove_logic as gl  # noqa: E402
sys.argv = _argv
import physis_arche_lore as lore  # noqa: E402
import physis_arche_plan as plan  # noqa: E402

B = gl.B
_expand = gl.expand
gl.expand = lambda code: _expand(code.replace('@W', B + 'BP_Weave'))
var, shell, write, patch, comp, defaults, lit = gl.var, gl.shell, gl.write, gl.patch, gl.comp, gl.defaults, gl.lit
has, empty, same, vec, pick, snd, spawn = gl.has, gl.empty, gl.same, gl.vec, gl.pick, gl.snd, gl.spawn
PHYSIS, NOW, TICK, PF, MINE = gl.PHYSIS, gl.NOW, gl.TICK, gl.PF, gl.MINE
AA = '/Game/Arche/Audio/'
SOUNDS = {'weave': (AA + 'S_Weave', '/Game/Center/Audio/S_PuzzleSolved'), 'restless': (AA + 'S_WeaveRestless', '/Game/Audio/S_PickupDivinity'),
          'unweave': (AA + 'S_Unweave', '/Game/Center/Audio/S_BarrierDissolve'), 'travel': (AA + 'S_CurrentTravel', '/Game/Grove/Audio/S_CurrentTravel'),
          'music': (AA + 'S_Music_Arche', '/Game/Grove/Audio/S_Music_Grove')}
PIECES = 6


def sound(key):
    own, other = SOUNDS[key]
    return own if (ROOT / ('Content' + own[5:] + '.uasset')).exists() else other


def terrain_top(x, y, reach=3.0):
    meta, grid = ROOT / 'Art/Meshes/Arche/height.json', ROOT / 'Art/Meshes/Arche/height.bin'
    info = json.loads(meta.read_text())
    hx, hy, cell, nx, ny = info['half_x'], info['half_y'], info['cell'], int(info['nx']), int(info['ny'])
    data = grid.read_bytes()
    steps = int(reach / cell) + 1
    i0, j0 = int(round((x + hx) / cell)), int(round((y + hy) / cell))
    return max(struct.unpack_from('<f', data, 4 * (i * ny + j))[0]
               for i in range(i0 - steps, i0 + steps + 1) for j in range(j0 - steps, j0 + steps + 1) if 0 <= i < nx and 0 <= j < ny)


ARRIVE = plan.LANDING_STILL
ARRIVE_CM = (ARRIVE[0] * 100.0, ARRIVE[1] * 100.0, round((terrain_top(*ARRIVE) + 1.6) * 100.0))
# The Center: the temple's top tier, 16 m west of the Heartbloom (the Conclave's current is north, Earth's east); she
# comes back 5 m short of it (TargetPoint ArcheReturn, placed by arche:portal).
HOME_CM = (76000.0, -1100.0, 4000.0 + 130.0)


# ---------------------------------------------------------------- BP_Weave

def weave():
    W = 'BP_Weave'
    for name, kind in (('Need', 'string'), ('Hide', 'string'), ('Give', 'string'), ('Done', 'string'), ('Hold', 'float'), ('Loom', 'string'),
                       ('Limit', 'int'), ('Range', 'float'), ('Drift', 'float')):
        var(W, name, kind, True)
    for name, kind in (('Woven', 'bool'), ('T', 'float'), ('Until', 'float'), ('Order', 'int'), ('Shown', 'bool'), ('Aimed', 'bool'),
                       ('Swell', 'float'), ('Solid', 'bool'), ('Count', 'int'), ('Oldest', 'int'), ('Full', 'Vector'), ('Began', 'bool')):
        var(W, name, kind)
    var(W, 'Old', 'object:' + B + 'BP_Weave.BP_Weave_C')
    for name in ('Weave', 'LoomKeep'):
        shell(W, name)
    # A loom holds Limit shapes: the oldest woven thing of the same loom lets go when one more is woven.
    write(W, 'LoomKeep', """(fn `LoomKeep`
  (set `self.Count` 0)
  (set `self.Oldest` 2000000000)
  (set `self.Old` null)
  (for e (`GameplayStatics.GetAllActorsOfClass` "@W.BP_Weave_C")
    (bind w (cast `@W` e))
    (if (and (`@W.Woven` w) """ + same('(`@W.Loom` w)', '(`self.Loom`)') + """)
      (set `self.Count` (+ (`self.Count`) 1))
      (if (< (`@W.Order` w) (`self.Oldest`))
        (set `self.Oldest` (`@W.Order` w))
        (set `self.Old` w))))
  (if (and (> (`self.Count`) """ + pick('(> (`self.Limit`) 0)', '(`self.Limit`)', '1') + """) (`KismetSystemLibrary.IsValid` (`self.Old`)))
    (set `@W.Woven` false (`self.Old`))
    (`GameplayStatics.PlaySoundAtLocation` "%s.%s" (`Actor.K2_GetActorLocation` (`self.Old`)))))""" % (sound('unweave'), sound('unweave').split('/')[-1]))
    # What a press does to it: a restless thing already standing is held a while longer.
    write(W, 'Weave', """(fn `Weave`
  """ + PHYSIS + """
  (set `self.Until` (+ """ + NOW + """ (`self.Hold`)))
  (if (not (`self.Woven`))
    (set `self.Woven` true)
    (set `@P.WeaveSerial` (+ (`@P.WeaveSerial` p) 1) p)
    (set `self.Order` (`@P.WeaveSerial` p))
    (if (> (`self.Hold`) 0.0)
      """ + snd(sound('restless'), .9) + """
      (else
        """ + snd(sound('weave'), 1.0) + """))
    (if (and (not """ + empty('(`self.Give`)') + """) (not """ + has(PF, '(`self.Give`)') + """))
      (`@P.PhysisGive` p (`self.Give`))
      (if (not """ + empty('(`self.Done`)') + """)
        (`@P.PhysisSay` p (`self.Done`))))
    (if (not """ + empty('(`self.Loom`)') + """)
      (`self.LoomKeep`))))""")
    # The thing itself is one mesh cut into blocks (SM_AW_*, Tools/build_physis_arche_weave.py) in the weave materials
    # (arche:weave_materials): Shape's custom primitive data 0 is T (0 sundered: the blocks hang apart, turning; 1 whole)
    # and 1 is Drift (how far they hang, cm). The blocks come home in order along the mesh, so a bridge builds outward.
    # A lasting weave takes 2.4 s; a restless one (Hold > 0, used in fights) 1 s.
    t = '(`self.T`)'
    ease = '(* (* %s %s) (- 3.0 (* 2.0 %s)))' % (t, t, t)
    mark = '(`SceneComponent.K2_GetComponentLocation` (`self.Mark`))'
    pieces = []
    for k in range(PIECES):
        # Each sliver circles the mark while the thing is sundered and falls into it as it knits.
        angle = '(+ (* %s 0.7) %.4f)' % (NOW, k * 6.2832 / PIECES)
        radius = '(* (* (`self.Drift`) (- 1.0 %s)) %.2f)' % (ease, 1.0 + .25 * (k % 3))
        place = vec('(* %s (`KismetMathLibrary.Cos` %s))' % (radius, angle), '(* %s (`KismetMathLibrary.Sin` %s))' % (radius, angle),
                    '(* (* (`self.Drift`) 0.35) (* (- 1.0 %s) (`KismetMathLibrary.Sin` (+ (* %s 1.3) %d.0))))' % (ease, NOW, k))
        size = '(* (- 1.0 %s) %.2f)' % (ease, .16 + .05 * (k % 3))
        pieces.append('(`SceneComponent.K2_SetWorldLocation` (`self.P%d`) (+ %s %s) false true)' % (k, mark, place))
        pieces.append('(`SceneComponent.SetWorldScale3D` (`self.P%d`) %s)' % (k, vec(size, size, size)))
        pieces.append('(`SceneComponent.K2_SetWorldRotation` (`self.P%d`) (`KismetMathLibrary.MakeRotator` (* %s %d.0) (* %s 31.0) (* %s %d.0)) false true)'
                      % (k, NOW, 17 + 5 * k, NOW, NOW, 23 + 7 * k))
    full = '(`self.Full`)'
    grown = '(+ 0.02 (* 0.98 %s))' % ease
    write(W, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (set `self.Full` (`SceneComponent.RelativeScale3D` (`self.Shape`)))
  (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "NoCollision")
  (`PrimitiveComponent.SetCollisionEnabled` (`self.Mark`) "NoCollision")
  (if (<= (`self.Drift`) 0.0)
    (set `self.Drift` 260.0))
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 1 (`self.Drift`)))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Shown` (and (or """ + empty('(`self.Need`)') + ' ' + has(PF, '(`self.Need`)') + """) (or """ + empty('(`self.Hide`)') + ' (not ' + has(PF, '(`self.Hide`)') + """))))
  (`self.SetActorHiddenInGame` (not (`self.Shown`)))
  (if (and (not (`self.Began`)) (and (<= (`self.Hold`) 0.0) (and (not """ + empty('(`self.Give`)') + ') ' + has(PF, '(`self.Give`)') + """)))
    (set `self.Woven` true)
    (set `self.T` 1.0))
  (set `self.Began` true)
  (if (and (`self.Woven`) (and (> (`self.Hold`) 0.0) (> """ + NOW + """ (`self.Until`))))
    (set `self.Woven` false)
    (`GameplayStatics.PlaySoundAtLocation` "%s.%s" (`self.K2_GetActorLocation`)))
  (set `self.T` (`KismetMathLibrary.FInterpTo_Constant` (`self.T`) """ % (sound('unweave'), sound('unweave').split('/')[-1]) + pick('(`self.Woven`)', '1.0', '0.0') + """ DeltaSeconds """ + pick('(> (`self.Hold`) 0.0)', '1.0', '0.42') + """))
  (set `self.Aimed` (and (`self.Shown`) (`KismetMathLibrary.EqualEqual_ObjectObject` (`@P.WeaveAim` p) self)))
  (set `self.Swell` (`KismetMathLibrary.FInterpTo` (`self.Swell`) """ + pick('(`self.Aimed`)', '1.0', '0.0') + """ DeltaSeconds 10.0))
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 (`self.T`))
  (if (and (>= (`self.T`) 0.97) (not (`self.Solid`)))
    (set `self.Solid` true)
    (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "QueryAndPhysics"))
  (if (and (< (`self.T`) 0.97) (`self.Solid`))
    (set `self.Solid` false)
    (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "NoCollision"))
  (`SceneComponent.SetVisibility` (`self.Mark`) (< (`self.T`) 0.6) false)
  (`SceneComponent.SetWorldScale3D` (`self.Mark`) """ + vec(*['(* (+ 1.0 (* 0.3 (`self.Swell`))) (- 1.0 (* 0.6 (`self.T`))))'] * 3) + """)
  (`SceneComponent.K2_SetWorldRotation` (`self.Mark`) (`KismetMathLibrary.MakeRotator` 0.0 0.0 (* """ + NOW + """ 40.0)) false true)
  (`LightComponent.SetIntensity` (`self.Glow`) (+ (* (+ 5.0 (* 14.0 (`self.Swell`))) (- 1.0 (* 0.8 (`self.T`)))) (* 45.0 (`KismetMathLibrary.Sin` (* 3.1416 (`self.T`))))))
  """ + '\n  '.join(pieces) + ')')
    comp(W)
    defaults(W, {'Range': 4500.0, 'Limit': 1, 'Drift': 260.0})


# ---------------------------------------------------------------- BP_ArcheDirector

hush = gl.hush   # the Lens's hum (tag ArcheScar) fades once the Sunderer falls: hiding does not silence it


def director():
    N = 'BP_ArcheDirector'
    for name in ('Live', 'Hushed'):
        var(N, name, 'bool')
    for name in ('Arrive', 'State'):
        shell(N, name)
    write(N, 'Arrive', """(fn `Arrive`
  """ + PHYSIS + """
  (if (not """ + has(PF, ',arche,') + """)
    (`@P.PhysisGive` p ",arche,"))
  (if (not """ + has(PF, ',at_arche,') + """)
    (`@P.PhysisGive` p ",at_arche,"))
  (if (and """ + empty('(`@P.Objective` p)') + ' (not ' + has(PF, ',aeon,') + """))
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_ARRIVE) + """))
  (if (not """ + has(PF, ',arche_seen,') + """)
    (`@P.PhysisGive` p ",arche_seen,")
    (`@P.PhysisSay` p """ + lit(lore.MESSAGES['arrive']) + """)
    (`@P.PhysisNarrate` p """ + lit(lore.ARRIVAL_LINE[0]) + """)))""")
    done = has(PF, ',sunderer,')
    shows = ''.join('\n  ' + gl.tagged(tag, '(not %s)' % has(PF, token), name)
                    for tag, token, name in (('ArcheMirrorW', ',ar_mirror_w,', 'mw'), ('ArcheMirrorE', ',ar_mirror_e,', 'me'),
                                             ('ArcheMirrorN', ',ar_mirror_n,', 'mn')))
    write(N, 'State', """(fn `State`
  """ + PHYSIS + """
  """ + gl.tagged('ArcheScar', done, 'scar') + """
  """ + gl.tagged('ArcheBloom', '(not %s)' % done, 'bloom') + shows + """
  """ + gl.once(',ar_q_span,', has(PF, ',reweave,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_SPAN)) + """
  """ + gl.once(',ar_q_mirrors,', has(PF, ',ar_span,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_MIRRORS)) + """
  """ + gl.once(',ar_q_sunderer,', has(PF, ',ar_veil,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_SUNDERER)) + """
  """ + hush('ArcheScar', done) + ')')
    write(N, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`KismetSystemLibrary.K2_SetTimer` self "Arrive" 0.5 false)
  (`KismetSystemLibrary.K2_SetTimer` self "State" 0.25 true))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (if """ + has(PF, ',reweave,') + """
    (`@P.PhysisWeaveFind` p)))""")
    comp(N)


# ---------------------------------------------------------------- BP_ArcheCurrent

def current():
    """BP_GroveCurrent's graph for Arche: tags ArcheArrival (here) and ArcheReturn (the Center), token ,trip_a,."""
    N = 'BP_ArcheCurrent'
    for name, kind in (('Need', 'string'), ('Dest', 'int'), ('Radius', 'float')):
        var(N, name, kind, True)
    for name, kind in (('Stay', 'float'), ('Armed', 'bool'), ('Gone', 'bool')):
        var(N, name, kind)
    land = '\n    '.join("""(for %s (`GameplayStatics.GetAllActorsWithTag` "%s")
      (`Actor.K2_SetActorLocation` p (`Actor.K2_GetActorLocation` %s) false true)
      (`@P.PhysisCheckpoint` p (.x (`Actor.K2_GetActorLocation` %s)) (.y (`Actor.K2_GetActorLocation` %s)) (.z (`Actor.K2_GetActorLocation` %s))))"""
                           % ((spot, tag) + (spot,) * 4) for spot, tag in (('spot', 'ArcheArrival'), ('back', 'ArcheReturn')))
    ready = '(or %s %s)' % (empty('(`self.Need`)'), has(PF, '(`self.Need`)'))
    reach = pick('(> (`self.Radius`) 0.0)', '(`self.Radius`)', '180.0')
    gap = '(`self.GetDistanceTo` p)'
    glow = '(/ (`self.Stay`) 0.8)'
    cam = '(`GameplayStatics.GetPlayerCameraManager` 0)'
    write(N, 'EventGraph', """(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (if """ + has(PF, ',trip_a,') + """
    (set `@P.Flags` (`KismetStringLibrary.Replace` """ + PF + """ ",trip_a," "" "CaseSensitive") p)
    """ + land + """)
  (if (and (and """ + ready + """ (== (`self.Dest`) 1)) (and (not """ + has(PF, ',arche,') + ') (not ' + has(PF, ',ar_currenthint,') + """)))
    (`@P.PhysisGive` p ",ar_currenthint,")
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_CURRENT) + """))
  (`self.SetActorHiddenInGame` (not """ + ready + """))
  (if (> """ + gap + ' (+ ' + reach + """ 150.0))
    (set `self.Armed` true))
  (if (and (and """ + ready + """ (`self.Armed`)) (and (< """ + gap + ' ' + reach + """) (and (not (`@P.Cinematic` p)) (not (`@P.PhysisDead` p)))))
    (if (<= (`self.Stay`) 0.0)
      """ + snd(sound('travel')) + """)
    (set `self.Stay` (+ (`self.Stay`) DeltaSeconds))
    (`PlayerCameraManager.SetManualCameraFade` """ + cam + ' ' + pick('(> %s 1.0)' % glow, '1.0', glow) + """ (make `LinearColor` 0.8 0.9 1.0 1.0) false)
    (if (and (>= (`self.Stay`) 0.8) (not (`self.Gone`)))
      (set `self.Gone` true)
      (if (== (`self.Dest`) 2)
        (`@P.PhysisArcheHome` p)
        (elif (== (`self.Dest`) 1)
          (`@P.PhysisToArche` p))))
    (elif (> (`self.Stay`) 0.0)
      (set `self.Stay` 0.0)
      (`PlayerCameraManager.StopCameraFade` """ + cam + """))))""")
    comp(N)
    defaults(N, {'Radius': 180.0})


# ---------------------------------------------------------------- BP_Physis

def physis_shells():
    P = 'BP_Physis'
    for name, kind in (('WeaveReady', 'float'), ('WeaveAim', 'object:/Script/Engine.Actor'), ('WeaveDot', 'float'), ('WeaveSerial', 'int')):
        var(P, name, kind)
    for name in ('PhysisReweave', 'PhysisWeaveFind', 'PhysisToArche', 'PhysisArcheHome'):
        shell(P, name)
    comp(P)


def physis():
    P = 'BP_Physis'
    cam = '(`GameplayStatics.GetPlayerCameraManager` 0)'
    eye = '(`PlayerCameraManager.GetCameraLocation` %s)' % cam
    ahead = '(`KismetMathLibrary.GetForwardVector` (`PlayerCameraManager.GetCameraRotation` %s))' % cam
    head = '(+ (`self.K2_GetActorLocation`) %s)' % vec(0.0, 0.0, 60.0)
    spot = '(`SceneComponent.K2_GetComponentLocation` (`@W.Mark` w))'
    far = '(`KismetMathLibrary.VSize` (- %s %s))' % (spot, head)
    # Of marks in one line of sight the nearer wins: each 10 m of distance costs what half a degree off-centre does.
    dot = '(- (`KismetMathLibrary.Dot_VectorVector` %s (`KismetMathLibrary.Normal` (- %s %s))) (* %s 0.000008))' % (ahead, spot, eye, far)
    # The thing the next press would reweave: shown, sundered (or restless and standing, to hold it longer), within
    # its Range, within 30 degrees of the view's centre, its mark in plain sight. BP_ArcheDirector calls this every
    # frame (the aimed mark swells).
    open_ = '(or (not (`@W.Woven` w)) (> (`@W.Hold` w) 0.0))'
    write(P, 'PhysisWeaveFind', """(fn `PhysisWeaveFind`
  (set `self.WeaveAim` null)
  (set `self.WeaveDot` 0.866)
  (for e (`GameplayStatics.GetAllActorsOfClass` "@W.BP_Weave_C")
    (bind w (cast `@W` e))
    (if (and (and (`@W.Shown` w) """ + open_ + """) (< """ + far + ' ' + pick('(> (`@W.Range` w) 0.0)', '(`@W.Range` w)', '4500.0') + """))
      (if (> """ + dot + """ (`self.WeaveDot`))
        (bind (_hit _blocked) (`KismetSystemLibrary.LineTraceSingle` """ + head + ' ' + spot + """ "TraceTypeQuery1" true))
        (if (not _blocked)
          (set `self.WeaveDot` """ + dot + """)
          (set `self.WeaveAim` w))))))""")
    # Reweave (B / right stick click): no cost, 0.8 s between uses. It reports the ability first, so the other
    # worlds' reweave sockets answer it.
    write(P, 'PhysisReweave', """(fn `PhysisReweave`
  (if (and (and (not (`self.Cinematic`)) (not (`self.PhysisDead`))) (and (not (`self.Talking`)) """ + has(MINE, ',reweave,') + """))
    (if (> """ + NOW + """ (`self.WeaveReady`))
      (`self.PhysisUsedAbility` ",reweave,")
      (`self.PhysisWeaveFind`)
      (if (`KismetSystemLibrary.IsValid` (`self.WeaveAim`))
        (set `self.WeaveReady` (+ """ + NOW + """ 0.8))
        (bind w (cast `@W` (`self.WeaveAim`)))
        (`@W.Weave` w)
        (else
          (`self.PhysisNote` "Nothing here remembers a shape."))))))""")
    write(P, 'PhysisToArche', """(fn `PhysisToArche`
  (if (not """ + has(MINE, ',arche,') + """)
    (`self.PhysisGive` ",arche,"))
  (if (not """ + has(MINE, ',at_arche,') + """)
    (`self.PhysisGive` ",at_arche,"))
  (`self.PhysisGive` ",trip_a,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_Arche" true "nocine,load"))""" % ARRIVE_CM)
    write(P, 'PhysisArcheHome', """(fn `PhysisArcheHome`
  (set `self.Flags` (`KismetStringLibrary.Replace` (`self.Flags`) ",at_arche," "" "CaseSensitive"))
  (`self.PhysisGive` ",trip_a,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_CenterOfTheUniverse" true "nocine,load"))""" % HOME_CM)
    comp(P)


def wire():
    write('BP_Physis', 'EventGraph', """(event `EnhancedInput|/Game/Input/Actions/IA_Reweave`
  (:`Started`
    (`self.PhysisReweave`)))""", 'input IA_Reweave')
    comp('BP_Physis')


PARTS = {'weave': weave, 'director': director, 'current': current, 'physis': physis, 'input': wire}

if __name__ == '__main__':
    import arche_shared
    PARTS.update(arche_shared.PARTS)
    parts = ARGS or ['weave', 'director', 'current', 'physis', 'input']
    print('Arche arrival %s cm, Center arrival %s cm' % (ARRIVE_CM, HOME_CM))
    if any(part in ('weave', 'director', 'current', 'physis', 'input') for part in parts):
        physis_shells()
    for part in parts:
        PARTS[part]()
    for bp in gl.TOUCHED:
        gl.save(bp)
    print('FAILED:', gl.FAILED or 'none')
