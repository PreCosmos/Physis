"""Blueprint logic for level 8, Morrow, the Valley Before Morning (Tools/morrow/README.md). Run from the project folder
with the editor open, after `morrow:blueprints` has made the Blueprint assets and IA_SitWith:
    python3 Tools/blueprint_logic/morrow_logic.py [stilled] [glow] [director] [current] [physis] [input] [shared] [hud] [relic] [music]

stilled   BP_Stilled: one of the Stilled, a memory of the Morning, or the kneeling Unrisen. While she sits (BP_Physis.
          Sitting) within Radius of it for Hold seconds it wakes: it thaws (custom primitive data 0, 1 .. 0), says its
          text and its voice ("Talk <Key> 0"), gives its token. A Need it waits for says Denied instead. With Pages it is
          the spoken stage: a page every Step seconds of sitting (paused, not lost, when she stands), voiced
          "Talk <Key> <k>", and it wakes after the last
glow      BP_SitWith: Sit With's small warm light round her; it watches her and ends the sitting when she moves, is
          struck, or a cinematic or death takes her
director  BP_MorrowDirector: the arrival, tagged actors by token, the quests that follow from a token, the way into the
          Morning and back out, falling in the Morning, the sunrise (the sun tagged MorrowSun, MPC_Grove Heal), the hush
current   BP_MorrowCurrent: the Divinity current between the Center's sanctum and the Pass Chapel
physis    BP_Physis: PhysisSitWith, PhysisStand, PhysisToMorrow, PhysisMorrowHome
input     IA_SitWith's Triggered event calls PhysisSitWith
shared    Morrow branches in graphs other levels own: fidelity and augmentations, music, load, save and restore, the
          menu's Continue (morrow_shared.py)
hud       BP_PhysisHUD.PageMap: Morrow's map page (after morrow:map_art)
relic     BP_Relic.RelicTag: Morrow's relics' own Logbook entries
music     PhysisMusicPick plays S_Music_Morrow (after morrow:audio)

It stands on grove_logic.py's helpers (the 5.9 dialect layer: var, shell, write, patch, comp, save). In the text
below @P is BP_Physis, @B the Blueprint folder.
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
import physis_morrow_lore as lore  # noqa: E402
import physis_morrow_plan as plan  # noqa: E402

B = gl.B
var, shell, write, patch, comp, defaults, lit = gl.var, gl.shell, gl.write, gl.patch, gl.comp, gl.defaults, gl.lit
has, empty, same, vec, pick, snd = gl.has, gl.empty, gl.same, gl.vec, gl.pick, gl.snd
PHYSIS, NOW, TICK, PF, MINE = gl.PHYSIS, gl.NOW, gl.TICK, gl.PF, gl.MINE
MW = '/Game/Morrow/Audio/'
SOUNDS = {'sit': (MW + 'S_SitWith', '/Game/Arche/Audio/S_WeaveRestless'), 'wake': (MW + 'S_Wake', '/Game/Center/Audio/S_PuzzleSolved'),
          'travel': (MW + 'S_CurrentTravel', '/Game/Arche/Audio/S_CurrentTravel'), 'music': (MW + 'S_Music_Morrow', '/Game/Halcyon/Audio/S_Music_Halcyon'),
          'inner': (MW + 'S_Inner', '/Game/Center/Audio/S_PuzzleSolved')}
KNEEL_CLIP = '/Game/Characters/Physis/Animations/A_Physis_GetUp'
KNEEL_AT = 14.1          # seconds into the get-up clip: the half-kneel, upright, her right foot forward, her left knee down
SUNRISE = 40.0           # seconds the sun takes to clear the ridge once the Lull stops
SUN_FROM, SUN_TO = (-5.0, 5.5, (1.0, .81, .72)), (-26.0, 15.0, (1.0, .92, .82))   # (pitch, lux, colour) before and after
SUN_YAW = 290.0
INNER_X = 1000.0         # plan metres: east of this is the Morning (a death or a load outside it while she is in it brings her back)


def sound(key):
    own, other = SOUNDS[key]
    for path in (own, other, '/Game/Audio/S_PickupDivinity'):
        if (ROOT / ('Content' + path[5:] + '.uasset')).exists():
            return path
    return '/Game/Audio/S_PickupDivinity'


def terrain_top(x, y, reach=3.0):
    info = json.loads((ROOT / 'Art/Meshes/Morrow/height.json').read_text())
    hx, hy, cell, ny = info['half_x'], info['half_y'], info['cell'], int(info['ny'])
    nx = int(info['nx'])
    data = (ROOT / 'Art/Meshes/Morrow/height.bin').read_bytes()
    steps = int(reach / cell) + 1
    i0, j0 = int(round((x + hx) / cell)), int(round((y + hy) / cell))
    return max(struct.unpack_from('<f', data, 4 * (i * ny + j))[0]
               for i in range(i0 - steps, i0 + steps + 1) for j in range(j0 - steps, j0 + steps + 1) if 0 <= i < nx and 0 <= j < ny)


ARRIVE = plan.CHAPEL_STILL
ARRIVE_CM = (ARRIVE[0] * 100.0, ARRIVE[1] * 100.0, round((terrain_top(*ARRIVE) + 1.6) * 100.0))
# The Center: the temple's top tier, south-east of the Heartbloom; she comes back 11 m out from it (TargetPoint
# MorrowReturn, placed by morrow:portal).
HOME_CM = (76000.0 - 778.0, 778.0, 4000.0 + 130.0)


def lerp(a, b, t):
    return '(`KismetMathLibrary.Lerp` %s %s %s)' % (a, b, t)


# ---------------------------------------------------------------- BP_Stilled

def stilled():
    S = 'BP_Stilled'
    for name, kind in (('Show', 'string'), ('Hide', 'string'), ('Need', 'string'), ('Give', 'string'), ('Done', 'string'), ('Denied', 'string'),
                       ('Key', 'string'), ('Pages', 'string'), ('Step', 'float'), ('Hold', 'float'), ('Radius', 'float')):
        var(S, name, kind, True)
    for name, kind in (('Held', 'float'), ('Thaw', 'float'), ('Light', 'float'), ('Said', 'int'), ('Count', 'int'), ('Shown', 'bool'), ('Woken', 'bool'),
                       ('Near', 'bool'), ('Ready', 'bool'), ('Refused', 'bool')):
        var(S, name, kind)
    for name in ('Wake', 'Page'):
        shell(S, name)
    write(S, 'Wake', """(fn `Wake`
  """ + PHYSIS + """
  (set `self.Woken` true)
  (if (and (not """ + empty('(`self.Give`)') + """) (not """ + has(PF, '(`self.Give`)') + """))
    (`@P.PhysisGive` p (`self.Give`))
    """ + snd(sound('wake'), .8) + """
    (if (not """ + empty('(`self.Done`)') + """)
      (`@P.PhysisSay` p (`self.Done`)))
    (if (and (not """ + empty('(`self.Key`)') + """) """ + empty('(`self.Pages`)') + """)
      (`@P.PhysisNarrate` p (`KismetStringLibrary.Concat_StrStr` (`KismetStringLibrary.Concat_StrStr` "Talk " (`self.Key`)) " 0")))))""")
    # The page Said of Pages: shown, and its voice ("Talk <Key> <Said>") played if it has one; then the next.
    write(S, 'Page', """(fn `Page`
  """ + PHYSIS + """
  (for (line k) (`KismetStringLibrary.ParseIntoArray` (`self.Pages`) "|" false)
    (if (== k (`self.Said`))
      (`@P.PhysisSay` p line)
      (`@P.PhysisNarrate` p (`KismetStringLibrary.Concat_StrStr` (`KismetStringLibrary.Concat_StrStr` (`KismetStringLibrary.Concat_StrStr` "Talk " (`self.Key`)) " ") (`KismetStringLibrary.Conv_IntToString` k)))))
  (set `self.Said` (+ (`self.Said`) 1)))""")
    staged = '(not %s)' % empty('(`self.Pages`)')
    write(S, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (set `self.Thaw` 1.0)
  (set `self.Count` (`KismetArrayLibrary.Array_Length` (`KismetStringLibrary.ParseIntoArray` (`self.Pages`) "|" false)))
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 1.0))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Shown` (and (or """ + empty('(`self.Show`)') + ' ' + has(PF, '(`self.Show`)') + """) (or """ + empty('(`self.Hide`)') + ' (not ' + has(PF, '(`self.Hide`)') + """))))
  (if (and (not """ + empty('(`self.Give`)') + ') ' + has(PF, '(`self.Give`)') + """)
    (set `self.Woken` true))
  (`self.SetActorHiddenInGame` (not (`self.Shown`)))
  (`self.SetActorEnableCollision` (`self.Shown`))
  (set `self.Ready` (or """ + empty('(`self.Need`)') + ' ' + has(PF, '(`self.Need`)') + """))
  (set `self.Near` (and (and (`self.Shown`) (not (`self.Woken`))) (and (`@P.Sitting` p) (< (`self.GetDistanceTo` p) (`self.Radius`)))))
  (if (`self.Near`)
    (set `self.Held` (+ (`self.Held`) DeltaSeconds))
    (if (`self.Ready`)
      (if """ + staged + """
        (if (and (< (`self.Said`) (`self.Count`)) (>= (`self.Held`) (+ (* (`self.Step`) (`self.Said`)) 0.4)))
          (`self.Page`))
        (if (>= (`self.Held`) (* (`self.Step`) (`self.Count`)))
          (`self.Wake`))
        (elif (>= (`self.Held`) (`self.Hold`))
          (`self.Wake`)))
      (elif (and (>= (`self.Held`) 2.0) (not (`self.Refused`)))
        (set `self.Refused` true)
        (`@P.PhysisSay` p (`self.Denied`))))
    (elif (not """ + staged + """)
      (set `self.Held` 0.0)))
  (if (not (`@P.Sitting` p))
    (set `self.Refused` false))
  (set `self.Thaw` (`KismetMathLibrary.FInterpTo_Constant` (`self.Thaw`) """ + pick('(`self.Woken`)', '0.0', '1.0') + """ DeltaSeconds 0.45))
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 (`self.Thaw`))
  (set `self.Light` (`KismetMathLibrary.FInterpTo_Constant` (`self.Light`) """ + pick('(`self.Near`)', '1.0', '0.0') + """ DeltaSeconds 1.2))
  (`LightComponent.SetIntensity` (`self.Glow`) (* 30.0 (`self.Light`))))""")
    comp(S)
    defaults(S, {'Hold': 4.0, 'Radius': 320.0, 'Step': 6.5})


# ---------------------------------------------------------------- BP_SitWith

def glow():
    G = 'BP_SitWith'
    for name, kind in (('Age', 'float'), ('S', 'float')):
        var(G, name, kind)
    sitting = '(`@P.Sitting` p)'
    struck = '(< (`@P.PhysisHealth` p) (`@P.SitHealth` p))'
    moved = '(and (> (`KismetMathLibrary.VSize` (`Actor.GetVelocity` p)) 45.0) (> (- %s (`@P.SitAt` p)) 0.4))' % NOW
    taken = '(or (`@P.Cinematic` p) (`@P.PhysisDead` p))'
    write(G, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`SceneComponent.SetRelativeScale3D` (`self.Shape`) """ + vec(3.2, 3.2, 1.8) + """)
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 0.0))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Age` (+ (`self.Age`) DeltaSeconds))
  (`self.K2_SetActorLocation` (`Actor.K2_GetActorLocation` p) false true)
  (if (and """ + sitting + """ (or (or """ + moved + ' ' + struck + """) """ + taken + """))
    (`@P.PhysisStand` p))
  (set `self.S` (`KismetMathLibrary.FInterpTo_Constant` (`self.S`) """ + pick(sitting, '1.0', '0.0') + """ DeltaSeconds 1.6))
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 (`self.S`))
  (`LightComponent.SetIntensity` (`self.Glow`) (* 45.0 (`self.S`)))
  (if (and (and (not """ + sitting + """) (<= (`self.S`) 0.0)) (> (`self.Age`) 0.3))
    (`self.K2_DestroyActor`)))""")
    comp(G)


# ---------------------------------------------------------------- BP_MorrowDirector

def director():
    N = 'BP_MorrowDirector'
    for name, kind in (('Motion', 'float'), ('Rise', 'float'), ('SunAt', 'float'), ('Live', 'bool'), ('Hushed', 'bool')):
        var(N, name, kind)
    for name in ('Arrive', 'State', 'Sun'):
        shell(N, name)
    write(N, 'Arrive', """(fn `Arrive`
  """ + PHYSIS + """
  (if (not """ + has(PF, ',morrow,') + """)
    (`@P.PhysisGive` p ",morrow,"))
  (if (not """ + has(PF, ',at_morrow,') + """)
    (`@P.PhysisGive` p ",at_morrow,"))
  (if (and """ + empty('(`@P.Objective` p)') + ' (not ' + has(PF, ',edda,') + """))
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_ARRIVE) + """))
  (if (not """ + has(PF, ',morrow_seen,') + """)
    (`@P.PhysisGive` p ",morrow_seen,")
    (`@P.PhysisSay` p """ + lit(lore.MESSAGES['arrive']) + """)
    (`@P.PhysisNarrate` p """ + lit(lore.ARRIVAL_LINE[0]) + """)))""")
    done = has(PF, ',unrisen,')
    inside = '(and %s (not %s))' % (has(PF, ',mw_in,'), has(PF, ',mw_out,'))
    cam = '(`GameplayStatics.GetPlayerCameraManager` 0)'

    def go(tag, name):
        return """(for %s (`GameplayStatics.GetAllActorsWithTag` "%s")
      (`Actor.K2_SetActorLocation` p (`Actor.K2_GetActorLocation` %s) false true)
      (`@P.PhysisCheckpoint` p (.x (`Actor.K2_GetActorLocation` %s)) (.y (`Actor.K2_GetActorLocation` %s)) (.z (`Actor.K2_GetActorLocation` %s))))""" % (
            (name, tag) + (name,) * 4)
    fade = '(`PlayerCameraManager.StartCameraFade` %s 1.0 0.0 3.0 (make `LinearColor` 1.0 0.86 0.7 1.0) false false)' % cam
    write(N, 'State', """(fn `State`
  """ + PHYSIS + """
  """ + gl.tagged('MorrowScar', done, 'scar') + """
  """ + gl.tagged('MorrowBloom', '(not %s)' % done, 'bloom') + """
  """ + gl.tagged('MorrowBridge', has(PF, ',mw_bridge,'), 'bridge') + """
  """ + gl.tagged('MorrowRoom1', has(PF, ',mw_room1,'), 'room1') + """
  """ + gl.tagged('MorrowRoom2', has(PF, ',mw_room2,'), 'room2') + """
  """ + gl.tagged('MorrowWay', '(not %s)' % has(PF, ',mw_room3,'), 'way') + """
  """ + gl.once(',mw_q_miller,', has(PF, ',sitwith,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_MILLER)) + """
  """ + gl.once(',mw_q_bridge,', has(PF, ',mw_miller,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_BRIDGE)) + """
  """ + gl.once(',mw_q_three,', has(PF, ',mw_bridge,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_THREE)) + """
  """ + gl.once(',mw_q_crest,', has(PF, ',mw_mems,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_CREST)) + """
  """ + gl.once(',mw_q_unrisen,', has(PF, ',mw_room3,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_UNRISEN)) + """
  """ + gl.once(',morrow_done,', has(PF, ',aug_agility9,'), '_') + """
  (if (and """ + has(PF, ',mw_inner,') + ' (not ' + has(PF, ',mw_in,') + """))
    (`@P.PhysisGive` p ",mw_in,")
    (`@P.PhysisStand` p)
    """ + go('MorrowInner', 'inner') + """
    """ + fade + """
    """ + snd(sound('inner'), .8) + """
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_MORNING) + """)
    (`@P.PhysisSay` p """ + lit(gl.wrap(lore.MORNING_LINE[1])) + """)
    (`@P.PhysisNarrate` p """ + lit(lore.MORNING_LINE[0]) + """))
  (if (and """ + done + ' (not ' + has(PF, ',mw_out,') + """))
    (`@P.PhysisGive` p ",mw_out,")
    (`@P.PhysisStand` p)
    """ + go('MorrowCrest', 'crest') + """
    """ + fade + """
    (set `self.SunAt` """ + NOW + """)
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_MAREN) + """)
    (`@P.PhysisSay` p """ + lit(gl.wrap(lore.MESSAGES['sunrise'])) + """))
  (if (and """ + inside + """ (or (< (.z (`Actor.K2_GetActorLocation` p)) """ + '%.1f' % (plan.INNER_KILL_Z * 100.0) + """) (< (.x (`Actor.K2_GetActorLocation` p)) """ + '%.1f' % (INNER_X * 100.0) + """)))
    """ + go('MorrowInner', 'again') + """
    (`@P.PhysisSay` p """ + lit(lore.MESSAGES['fell']) + """))
  (set `self.Motion` """ + pick(has(PF, ',resonance,'), '1.0', '0.12') + """)
  (`KismetMaterialLibrary.SetScalarParameterValue` """ + gl.MPC + """ "Motion" (`self.Motion`))
  """ + gl.hush('MorrowHush', done) + ')')   # 3 s in play, at once after a load that finds it done
    # The sun: under the ridge until the Unrisen is sat with, then rising over SUNRISE seconds from the moment she comes
    # out (SunAt; a loaded game that already has it starts risen: SunAt's default is long ago). The frost thaws with it.
    t = '(`KismetMathLibrary.FClamp` (/ (- %s (`self.SunAt`)) %.1f) 0.0 1.0)' % (NOW, SUNRISE)
    rise = pick(done, '(* (* (`self.Rise`) (`self.Rise`)) (- 3.0 (* 2.0 (`self.Rise`))))', '0.0')
    (p0, l0, c0), (p1, l1, c1) = SUN_FROM, SUN_TO
    colour = '(make `LinearColor` %s %s %s 1.0)' % tuple(lerp(c0[k], c1[k], '_r') for k in range(3))
    write(N, 'Sun', """(fn `Sun`
  """ + PHYSIS + """
  (set `self.Rise` """ + t + """)
  (bind _r """ + rise + """)
  (for sun (`GameplayStatics.GetAllActorsWithTag` "MorrowSun")
    (`Actor.K2_SetActorRotation` sun (`KismetMathLibrary.MakeRotator` 0.0 """ + lerp(p0, p1, '_r') + ' %.1f' % SUN_YAW + """) false)
    (bind light (cast `/Script/Engine.DirectionalLight` sun))
    (`LightComponent.SetIntensity` (`Light.LightComponent` light) """ + lerp(l0, l1, '_r') + """)
    (`LightComponent.SetLightColor` (`Light.LightComponent` light) """ + colour + """ true))
  (`KismetMaterialLibrary.SetScalarParameterValue` """ + gl.MPC + """ "Heal" _r))""")
    write(N, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`KismetSystemLibrary.K2_SetTimer` self "Arrive" 0.5 false)
  (`KismetSystemLibrary.K2_SetTimer` self "State" 0.25 true)
  (`KismetSystemLibrary.K2_SetTimer` self "Sun" 0.1 true))""")
    comp(N)
    defaults(N, {'SunAt': -1000.0})


# ---------------------------------------------------------------- BP_MorrowCurrent

def current():
    """BP_HesperCurrent's graph for Morrow: tags MorrowArrival (here) and MorrowReturn (the Center), token ,trip_m,."""
    N = 'BP_MorrowCurrent'
    for name, kind in (('Need', 'string'), ('Dest', 'int'), ('Radius', 'float')):
        var(N, name, kind, True)
    for name, kind in (('Stay', 'float'), ('Armed', 'bool'), ('Gone', 'bool')):
        var(N, name, kind)
    land = '\n    '.join("""(for %s (`GameplayStatics.GetAllActorsWithTag` "%s")
      (`Actor.K2_SetActorLocation` p (`Actor.K2_GetActorLocation` %s) false true)
      (`@P.PhysisCheckpoint` p (.x (`Actor.K2_GetActorLocation` %s)) (.y (`Actor.K2_GetActorLocation` %s)) (.z (`Actor.K2_GetActorLocation` %s))))"""
                           % ((spot, tag) + (spot,) * 4) for spot, tag in (('spot', 'MorrowArrival'), ('back', 'MorrowReturn')))
    ready = '(or %s %s)' % (empty('(`self.Need`)'), has(PF, '(`self.Need`)'))
    reach = pick('(> (`self.Radius`) 0.0)', '(`self.Radius`)', '180.0')
    gap = '(`self.GetDistanceTo` p)'
    glow_ = '(/ (`self.Stay`) 0.8)'
    cam = '(`GameplayStatics.GetPlayerCameraManager` 0)'
    write(N, 'EventGraph', """(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (if """ + has(PF, ',trip_m,') + """
    (set `@P.Flags` (`KismetStringLibrary.Replace` """ + PF + """ ",trip_m," "" "CaseSensitive") p)
    """ + land + """)
  (if (and (and """ + ready + """ (== (`self.Dest`) 1)) (and (not """ + has(PF, ',morrow,') + ') (not ' + has(PF, ',mw_currenthint,') + """)))
    (`@P.PhysisGive` p ",mw_currenthint,")
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_CURRENT) + """))
  (`self.SetActorHiddenInGame` (not """ + ready + """))
  (if (> """ + gap + ' (+ ' + reach + """ 150.0))
    (set `self.Armed` true))
  (if (and (and """ + ready + """ (`self.Armed`)) (and (< """ + gap + ' ' + reach + """) (and (not (`@P.Cinematic` p)) (not (`@P.PhysisDead` p)))))
    (if (<= (`self.Stay`) 0.0)
      """ + snd(sound('travel')) + """)
    (set `self.Stay` (+ (`self.Stay`) DeltaSeconds))
    (`PlayerCameraManager.SetManualCameraFade` """ + cam + ' ' + pick('(> %s 1.0)' % glow_, '1.0', glow_) + """ (make `LinearColor` 0.8 0.86 1.0 1.0) false)
    (if (and (>= (`self.Stay`) 0.8) (not (`self.Gone`)))
      (set `self.Gone` true)
      (if (== (`self.Dest`) 2)
        (`@P.PhysisMorrowHome` p)
        (elif (== (`self.Dest`) 1)
          (`@P.PhysisToMorrow` p))))
    (elif (> (`self.Stay`) 0.0)
      (set `self.Stay` 0.0)
      (`PlayerCameraManager.StopCameraFade` """ + cam + """))))""")
    comp(N)
    defaults(N, {'Radius': 180.0})


# ---------------------------------------------------------------- BP_Physis

def physis_shells():
    P = 'BP_Physis'
    for name, kind in (('Sitting', 'bool'), ('SitAt', 'float'), ('SitReady', 'float'), ('SitHealth', 'float')):
        var(P, name, kind)
    for name in ('PhysisSitWith', 'PhysisStand', 'PhysisToMorrow', 'PhysisMorrowHome'):
        shell(P, name)
    comp(P)


def physis():
    P = 'BP_Physis'
    # Sit With (H / hold the D-pad left): no cost. She kneels where she stands (a held frame of the get-up clip), and
    # stays until she presses again, moves, or is struck (BP_SitWith watches for those). It reports the ability first,
    # so the Sit With sockets elsewhere answer it.
    clip = '"%s.%s"' % (KNEEL_CLIP, KNEEL_CLIP.split('/')[-1])
    glow_class = '"%sBP_SitWith.BP_SitWith_C"' % B
    write(P, 'PhysisSitWith', """(fn `PhysisSitWith`
  (if (`self.Sitting`)
    (`self.PhysisStand`)
    (elif (and (and (and (not (`self.Cinematic`)) (not (`self.PhysisDead`))) (and (not (`self.Talking`)) """ + has(MINE, ',sitwith,') + """)) (and (> """ + NOW + """ (`self.SitReady`)) (< (`KismetMathLibrary.VSize` (`self.GetVelocity`)) 60.0)))
      (set `self.Sitting` true)
      (set `self.SitAt` """ + NOW + """)
      (set `self.SitHealth` (`self.PhysisHealth`))
      (`self.PhysisUsedAbility` ",sitwith,")
      (`SkeletalMeshComponent.PlayAnimation` (`self.Body`) """ + clip + """ false)
      (`SkeletalMeshComponent.SetPosition` (`self.Body`) %.2f false)
      (`SkeletalMeshComponent.SetPlayRate` (`self.Body`) 0.0)
      (`SceneComponent.SetVisibility` (`self.Katana`) false false)
      (`SceneComponent.SetVisibility` (`self.Gun`) false false)
      """ % KNEEL_AT + snd(sound('sit'), .6) + """
      (`|SpawnActorFromClass` """ + glow_class + """ (`KismetMathLibrary.MakeTransform` (`self.K2_GetActorLocation`) (`KismetMathLibrary.MakeRotator` 0.0 0.0 0.0) """ + vec(1.0, 1.0, 1.0) + """) "AlwaysSpawn" "MultiplyWithRoot" null null))))""")
    write(P, 'PhysisStand', """(fn `PhysisStand`
  (if (`self.Sitting`)
    (set `self.Sitting` false)
    (set `self.SitReady` (+ """ + NOW + """ 0.5))
    (`SkeletalMeshComponent.SetAnimationMode` (`self.Body`) "AnimationBlueprint" true)
    (`SceneComponent.SetVisibility` (`self.Katana`) (not (`self.GunEquipped`)) false)
    (`SceneComponent.SetVisibility` (`self.Gun`) (`self.GunEquipped`) false)))""")
    write(P, 'PhysisToMorrow', """(fn `PhysisToMorrow`
  (if (not """ + has(MINE, ',morrow,') + """)
    (`self.PhysisGive` ",morrow,"))
  (if (not """ + has(MINE, ',at_morrow,') + """)
    (`self.PhysisGive` ",at_morrow,"))
  (`self.PhysisGive` ",trip_m,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_Morrow" true "nocine,load"))""" % ARRIVE_CM)
    write(P, 'PhysisMorrowHome', """(fn `PhysisMorrowHome`
  (set `self.Flags` (`KismetStringLibrary.Replace` (`self.Flags`) ",at_morrow," "" "CaseSensitive"))
  (`self.PhysisGive` ",trip_m,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_CenterOfTheUniverse" true "nocine,load"))""" % HOME_CM)
    comp(P)


def wire():
    write('BP_Physis', 'EventGraph', """(event `EnhancedInput|/Game/Input/Actions/IA_SitWith`
  (:`Triggered`
    (`self.PhysisSitWith`)))""", 'input IA_SitWith')
    comp('BP_Physis')


PARTS = {'stilled': stilled, 'glow': glow, 'director': director, 'current': current, 'physis': physis, 'input': wire}
OWN = ('stilled', 'glow', 'director', 'current', 'physis', 'input')

if __name__ == '__main__':
    import morrow_shared
    PARTS.update(morrow_shared.PARTS)
    parts = ARGS or list(OWN)
    print('Morrow arrival %s cm, Center arrival %s cm' % (ARRIVE_CM, HOME_CM))
    if any(part in OWN for part in parts):
        physis_shells()
    for part in parts:
        PARTS[part]()
    for bp in gl.TOUCHED:
        gl.save(bp)
    print('FAILED:', gl.FAILED or 'none')
