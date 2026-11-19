"""Blueprint logic for level 7, Hesper, the City of One Voice (Tools/hesper/README.md). Run from the project folder
with the editor open, after `hesper:blueprints` has made the Blueprint assets and IA_Dissonance:
    python3 Tools/blueprint_logic/hesper_logic.py [unison] [ring] [director] [current] [physis] [input] [shared] [hud] [relic] [bolt]

unison    BP_Unison: the Concord's tone standing in the air. Inside her note (BP_Physis.DissonanceUntil, 9 m round her,
          measured to the panel's box) it thins and lets her through, and never closes on her; a shell (Hold > 0) stays
          solid but breaks for good once her note has covered it Hold seconds, giving its token and saying its line
director  BP_HesperDirector: the arrival, tagged actors by token, the quests that follow from a token, the hush
current   BP_HesperCurrent: the Divinity current between the Center's sanctum and the Sunward Stair
ring      BP_Dissonance: her note as it shows, a ring 9 m round her that follows her and fades as the note ends
physis    BP_Physis: PhysisDissonance, PhysisToHesper, PhysisHesperHome
input     IA_Dissonance's Triggered event calls PhysisDissonance
shared    Hesper branches in graphs other levels own: fidelity and augmentations, music, load, save and restore, the
          menu's Continue (hesper_shared.py)
hud       BP_PhysisHUD.PageMap: Hesper's map page (after hesper:map_art)
relic     BP_Relic.RelicTag: Hesper's relics' own Logbook entries
bolt      BP_EnemyBolt: a bolt inside her note falters and goes out

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
import physis_hesper_lore as lore  # noqa: E402
import physis_hesper_plan as plan  # noqa: E402

B = gl.B
var, shell, write, patch, comp, defaults, lit = gl.var, gl.shell, gl.write, gl.patch, gl.comp, gl.defaults, gl.lit
has, empty, same, vec, pick, snd = gl.has, gl.empty, gl.same, gl.vec, gl.pick, gl.snd
PHYSIS, NOW, TICK, PF, MINE = gl.PHYSIS, gl.NOW, gl.TICK, gl.PF, gl.MINE
HS = '/Game/Hesper/Audio/'
SOUNDS = {'note': (HS + 'S_Dissonance', '/Game/Arche/Audio/S_WeaveRestless'), 'break': (HS + 'S_ShellBreak', '/Game/Center/Audio/S_PuzzleSolved'),
          'travel': (HS + 'S_CurrentTravel', '/Game/Arche/Audio/S_CurrentTravel'), 'music': (HS + 'S_Music_Hesper', '/Game/Arche/Audio/S_Music_Arche')}
NOTE_SECONDS, NOTE_REST, REACH = 8.0, 2.0, 900.0


def sound(key):
    own, other = SOUNDS[key]
    for path in (own, other, '/Game/Grove/Audio/S_CurrentTravel' if key == 'travel' else '/Game/Audio/S_PickupDivinity'):
        if (ROOT / ('Content' + path[5:] + '.uasset')).exists():
            return path
    return '/Game/Audio/S_PickupDivinity'


def terrain_top(x, y, reach=3.0):
    info = json.loads((ROOT / 'Art/Meshes/Hesper/height.json').read_text())
    hx, hy, cell, ny = info['half_x'], info['half_y'], info['cell'], int(info['ny'])
    nx = int(info['nx'])
    data = (ROOT / 'Art/Meshes/Hesper/height.bin').read_bytes()
    steps = int(reach / cell) + 1
    i0, j0 = int(round((x + hx) / cell)), int(round((y + hy) / cell))
    return max(struct.unpack_from('<f', data, 4 * (i * ny + j))[0]
               for i in range(i0 - steps, i0 + steps + 1) for j in range(j0 - steps, j0 + steps + 1) if 0 <= i < nx and 0 <= j < ny)


ARRIVE = plan.STAIR_STILL
ARRIVE_CM = (ARRIVE[0] * 100.0, ARRIVE[1] * 100.0, round((terrain_top(*ARRIVE) + 1.6) * 100.0))
# The Center: the temple's top tier, north-east of the Heartbloom; she comes back 11 m out from it (TargetPoint
# HesperReturn, placed by hesper:portal).
HOME_CM = (76000.0 + 778.0, 778.0, 4000.0 + 130.0)


# ---------------------------------------------------------------- BP_Unison

def unison():
    U = 'BP_Unison'
    for name, kind in (('Need', 'string'), ('Hide', 'string'), ('Give', 'string'), ('Done', 'string'), ('Hold', 'float'), ('HalfX', 'float'),
                       ('HalfY', 'float'), ('HalfZ', 'float')):
        var(U, name, kind, True)
    for name, kind in (('U', 'float'), ('Want', 'float'), ('Held', 'float'), ('Gap', 'float'), ('Here', 'Vector'), ('Shown', 'bool'), ('Covered', 'bool'),
                       ('Broken', 'bool'), ('Open', 'bool'), ('Solid', 'bool')):
        var(U, name, kind)
    shell(U, 'Break')
    write(U, 'Break', """(fn `Break`
  """ + PHYSIS + """
  (set `self.Broken` true)
  (if (and (not """ + empty('(`self.Give`)') + """) (not """ + has(PF, '(`self.Give`)') + """))
    (`@P.PhysisGive` p (`self.Give`))
    """ + snd(sound('break'), .9) + """
    (if (not """ + empty('(`self.Done`)') + """)
      (`@P.PhysisSay` p (`self.Done`)))))""")
    # Gap: how far she is from the panel's box (cm, in the actor's frame; 0 inside it).
    here = '(`self.Here`)'
    out = lambda axis, half: '(`KismetMathLibrary.FMax` (- (`KismetMathLibrary.Abs` (.%s %s)) (`self.%s`)) 0.0)' % (axis, here, half)
    shell_ = '(> (`self.Hold`) 0.0)'
    write(U, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (set `self.Open` true)
  (set `self.U` 1.0)
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 1.0))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Shown` (and (or """ + empty('(`self.Need`)') + ' ' + has(PF, '(`self.Need`)') + """) (or """ + empty('(`self.Hide`)') + ' (not ' + has(PF, '(`self.Hide`)') + """))))
  (if (and (not """ + empty('(`self.Give`)') + ') ' + has(PF, '(`self.Give`)') + """)
    (set `self.Broken` true))
  (set `self.Here` (`KismetMathLibrary.InverseTransformLocation` (`self.GetTransform`) (`Actor.K2_GetActorLocation` p)))
  (set `self.Gap` (`KismetMathLibrary.VSize` """ + vec(out('x', 'HalfX'), out('y', 'HalfY'), out('z', 'HalfZ')) + """))
  (set `self.Covered` (and (> (`@P.DissonanceUntil` p) """ + NOW + """) (< (`self.Gap`) %.1f)))""" % REACH + """
  (if (and """ + shell_ + """ (not (`self.Broken`)))
    (set `self.Held` """ + pick('(`self.Covered`)', '(+ (`self.Held`) DeltaSeconds)', '0.0') + """)
    (if (and (>= (`self.Held`) (`self.Hold`)) (`self.Shown`))
      (`self.Break`)))
  (set `self.Want` """ + pick('(and (`self.Shown`) (not (`self.Broken`)))', pick('(`self.Covered`)', pick(shell_, '0.55', '0.12'), '1.0'), '0.0') + """)
  (set `self.U` (`KismetMathLibrary.FInterpTo_Constant` (`self.U`) (`self.Want`) DeltaSeconds """ + pick('(> (`self.Want`) (`self.U`))', '2.0', '4.0') + """))
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 (`self.U`))
  (`SceneComponent.SetVisibility` (`self.Shape`) (> (`self.U`) 0.01) false)
  (`LightComponent.SetIntensity` (`self.Glow`) """ + pick(shell_, '(* 40.0 (`self.U`))', '0.0') + """)
  (set `self.Solid` (and (and (`self.Shown`) (not (`self.Broken`))) (or """ + shell_ + """ (not (`self.Covered`)))))
  (if (and (`self.Solid`) (and (`self.Open`) (> (`self.Gap`) 60.0)))
    (set `self.Open` false)
    (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "QueryAndPhysics"))
  (if (and (not (`self.Solid`)) (not (`self.Open`)))
    (set `self.Open` true)
    (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "NoCollision")))""")
    comp(U)
    defaults(U, {'HalfX': 300.0, 'HalfY': 600.0, 'HalfZ': 600.0})


# ---------------------------------------------------------------- BP_Dissonance

def ring():
    R = 'BP_Dissonance'
    for name, kind in (('Age', 'float'), ('S', 'float')):
        var(R, name, kind)
    left = '(- (`@P.DissonanceUntil` p) %s)' % NOW
    write(R, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 0.0))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Age` (+ (`self.Age`) DeltaSeconds))
  (`self.K2_SetActorLocation` (`Actor.K2_GetActorLocation` p) false true)
  (set `self.S` (* (`KismetMathLibrary.FClamp` (/ """ + left + """ 0.8) 0.0 1.0) (`KismetMathLibrary.FClamp` (/ (`self.Age`) 0.35) 0.0 1.0)))
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 (`self.S`))
  (`LightComponent.SetIntensity` (`self.Glow`) (* 25.0 (`self.S`)))
  (if (and (> (`self.Age`) 0.5) (<= """ + left + """ 0.0))
    (`self.K2_DestroyActor`)))""")
    comp(R)


# ---------------------------------------------------------------- BP_HesperDirector

def director():
    N = 'BP_HesperDirector'
    for name, kind in (('Motion', 'float'), ('Live', 'bool'), ('Hushed', 'bool')):
        var(N, name, kind)
    for name in ('Arrive', 'State'):
        shell(N, name)
    write(N, 'Arrive', """(fn `Arrive`
  """ + PHYSIS + """
  (if (not """ + has(PF, ',hesper,') + """)
    (`@P.PhysisGive` p ",hesper,"))
  (if (not """ + has(PF, ',at_hesper,') + """)
    (`@P.PhysisGive` p ",at_hesper,"))
  (if (and """ + empty('(`@P.Objective` p)') + ' (not ' + has(PF, ',aeon_h,') + """))
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_ARRIVE) + """))
  (if (not """ + has(PF, ',hesper_seen,') + """)
    (`@P.PhysisGive` p ",hesper_seen,")
    (`@P.PhysisSay` p """ + lit(lore.MESSAGES['arrive']) + """)
    (`@P.PhysisNarrate` p """ + lit(lore.ARRIVAL_LINE[0]) + """)))""")
    done = has(PF, ',cantor,')
    bells = '(and (and %s %s) %s)' % (has(PF, ',hs_bell1,'), has(PF, ',hs_bell2,'), has(PF, ',hs_bell3,'))
    # The Choir Gate opens the moment the third bell rings, wherever she is: the gate's objective stays until she
    # reaches it (25 m short of the gate, or anywhere past it), and the Cantor's never follows the Cantor.
    at_gate = '(> (.x (`Actor.K2_GetActorLocation` p)) %.1f)' % ((plan.CHOIR_GATE[0] - 25.0) * 100.0)
    to_cantor = '(and (and %s %s) (not %s))' % (has(PF, ',hs_gate,'), at_gate, done)
    write(N, 'State', """(fn `State`
  """ + PHYSIS + """
  """ + gl.tagged('HesperScar', done, 'scar') + """
  """ + gl.tagged('HesperBloom', '(not %s)' % done, 'bloom') + """
  """ + gl.once(',hs_q_wall,', has(PF, ',dissonance,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_WALL)) + """
  """ + gl.once(',hs_q_gate,', bells, '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_GATE)) + """
  """ + gl.once(',hs_q_cantor,', to_cantor, '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_CANTOR)) + """
  (set `self.Motion` """ + pick(has(PF, ',resonance,'), '1.0', '0.12') + """)
  (`KismetMaterialLibrary.SetScalarParameterValue` """ + gl.MPC + """ "Motion" (`self.Motion`))
  """ + gl.hush('HesperHush', done) + ')')   # 3 s in play, at once after a load that finds it done
    write(N, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`KismetSystemLibrary.K2_SetTimer` self "Arrive" 0.5 false)
  (`KismetSystemLibrary.K2_SetTimer` self "State" 0.25 true))""")
    comp(N)


# ---------------------------------------------------------------- BP_HesperCurrent

def current():
    """BP_HalcyonCurrent's graph for Hesper: tags HesperArrival (here) and HesperReturn (the Center), token ,trip_s,."""
    N = 'BP_HesperCurrent'
    for name, kind in (('Need', 'string'), ('Dest', 'int'), ('Radius', 'float')):
        var(N, name, kind, True)
    for name, kind in (('Stay', 'float'), ('Armed', 'bool'), ('Gone', 'bool')):
        var(N, name, kind)
    land = '\n    '.join("""(for %s (`GameplayStatics.GetAllActorsWithTag` "%s")
      (`Actor.K2_SetActorLocation` p (`Actor.K2_GetActorLocation` %s) false true)
      (`@P.PhysisCheckpoint` p (.x (`Actor.K2_GetActorLocation` %s)) (.y (`Actor.K2_GetActorLocation` %s)) (.z (`Actor.K2_GetActorLocation` %s))))"""
                           % ((spot, tag) + (spot,) * 4) for spot, tag in (('spot', 'HesperArrival'), ('back', 'HesperReturn')))
    ready = '(or %s %s)' % (empty('(`self.Need`)'), has(PF, '(`self.Need`)'))
    reach = pick('(> (`self.Radius`) 0.0)', '(`self.Radius`)', '180.0')
    gap = '(`self.GetDistanceTo` p)'
    glow = '(/ (`self.Stay`) 0.8)'
    cam = '(`GameplayStatics.GetPlayerCameraManager` 0)'
    write(N, 'EventGraph', """(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (if """ + has(PF, ',trip_s,') + """
    (set `@P.Flags` (`KismetStringLibrary.Replace` """ + PF + """ ",trip_s," "" "CaseSensitive") p)
    """ + land + """)
  (if (and (and """ + ready + """ (== (`self.Dest`) 1)) (and (not """ + has(PF, ',hesper,') + ') (not ' + has(PF, ',hs_currenthint,') + """)))
    (`@P.PhysisGive` p ",hs_currenthint,")
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_CURRENT) + """))
  (`self.SetActorHiddenInGame` (not """ + ready + """))
  (if (> """ + gap + ' (+ ' + reach + """ 150.0))
    (set `self.Armed` true))
  (if (and (and """ + ready + """ (`self.Armed`)) (and (< """ + gap + ' ' + reach + """) (and (not (`@P.Cinematic` p)) (not (`@P.PhysisDead` p)))))
    (if (<= (`self.Stay`) 0.0)
      """ + snd(sound('travel')) + """)
    (set `self.Stay` (+ (`self.Stay`) DeltaSeconds))
    (`PlayerCameraManager.SetManualCameraFade` """ + cam + ' ' + pick('(> %s 1.0)' % glow, '1.0', glow) + """ (make `LinearColor` 1.0 0.82 0.6 1.0) false)
    (if (and (>= (`self.Stay`) 0.8) (not (`self.Gone`)))
      (set `self.Gone` true)
      (if (== (`self.Dest`) 2)
        (`@P.PhysisHesperHome` p)
        (elif (== (`self.Dest`) 1)
          (`@P.PhysisToHesper` p))))
    (elif (> (`self.Stay`) 0.0)
      (set `self.Stay` 0.0)
      (`PlayerCameraManager.StopCameraFade` """ + cam + """))))""")
    comp(N)
    defaults(N, {'Radius': 180.0})


# ---------------------------------------------------------------- BP_Physis

def physis_shells():
    P = 'BP_Physis'
    for name, kind in (('DissonanceUntil', 'float'), ('DissonanceReady', 'float')):
        var(P, name, kind)
    for name in ('PhysisDissonance', 'PhysisToHesper', 'PhysisHesperHome'):
        shell(P, name)
    comp(P)


def physis():
    P = 'BP_Physis'
    # Dissonance (C / hold the D-pad up): no cost; a note lasts NOTE_SECONDS, then NOTE_REST before the next. It reports
    # the ability first, so the Dissonance sockets elsewhere answer it, then shows the ring.
    ring_class = '"%sBP_Dissonance.BP_Dissonance_C"' % B
    write(P, 'PhysisDissonance', """(fn `PhysisDissonance`
  (if (and (and (not (`self.Cinematic`)) (not (`self.PhysisDead`))) (and (not (`self.Talking`)) """ + has(MINE, ',dissonance,') + """))
    (if (> """ + NOW + """ (`self.DissonanceReady`))
      (set `self.DissonanceUntil` (+ """ + NOW + """ %.1f))
      (set `self.DissonanceReady` (+ """ % NOTE_SECONDS + NOW + """ %.1f))
      (`self.PhysisUsedAbility` ",dissonance,")
      """ % (NOTE_SECONDS + NOTE_REST) + snd(sound('note'), .7) + """
      (`|SpawnActorFromClass` """ + ring_class + """ (`KismetMathLibrary.MakeTransform` (`self.K2_GetActorLocation`) (`KismetMathLibrary.MakeRotator` 0.0 0.0 0.0) """ + vec(1.0, 1.0, 1.0) + """) "AlwaysSpawn" "MultiplyWithRoot" null null))))""")
    write(P, 'PhysisToHesper', """(fn `PhysisToHesper`
  (if (not """ + has(MINE, ',hesper,') + """)
    (`self.PhysisGive` ",hesper,"))
  (if (not """ + has(MINE, ',at_hesper,') + """)
    (`self.PhysisGive` ",at_hesper,"))
  (`self.PhysisGive` ",trip_s,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_Hesper" true "nocine,load"))""" % ARRIVE_CM)
    write(P, 'PhysisHesperHome', """(fn `PhysisHesperHome`
  (set `self.Flags` (`KismetStringLibrary.Replace` (`self.Flags`) ",at_hesper," "" "CaseSensitive"))
  (`self.PhysisGive` ",trip_s,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_CenterOfTheUniverse" true "nocine,load"))""" % HOME_CM)
    comp(P)


def wire():
    write('BP_Physis', 'EventGraph', """(event `EnhancedInput|/Game/Input/Actions/IA_Dissonance`
  (:`Triggered`
    (`self.PhysisDissonance`)))""", 'input IA_Dissonance')
    comp('BP_Physis')


PARTS = {'unison': unison, 'ring': ring, 'director': director, 'current': current, 'physis': physis, 'input': wire}

if __name__ == '__main__':
    import hesper_shared
    PARTS.update(hesper_shared.PARTS)
    parts = ARGS or ['unison', 'ring', 'director', 'current', 'physis', 'input']
    print('Hesper arrival %s cm, Center arrival %s cm' % (ARRIVE_CM, HOME_CM))
    if any(part in ('unison', 'ring', 'director', 'current', 'physis', 'input') for part in parts):
        physis_shells()
    for part in parts:
        PARTS[part]()
    for bp in gl.TOUCHED:
        gl.save(bp)
    print('FAILED:', gl.FAILED or 'none')
