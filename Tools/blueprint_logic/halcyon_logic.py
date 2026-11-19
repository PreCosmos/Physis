"""Blueprint logic for level 6, Halcyon, the Drowned Harbour (Tools/halcyon/README.md). Run from the project folder
with the editor open, after `halcyon:blueprints` has made the Blueprint assets and IA_TraceRead:
    python3 Tools/blueprint_logic/halcyon_logic.py [trace] [director] [current] [physis] [input] [shared] [hud] [relic]

trace     BP_Trace: what stood here once. While she reads (BP_Physis.TraceUntil) and is within its Range it shows in the
          trace material and bears her weight, fading over the reading's last 2 s; the first time it is read whole it
          gives its token and says its line (the echoes)
director  BP_HalcyonDirector: the arrival, tagged actors by token, the quests that follow from a token, MPC_Grove (the
          grass moves once she has the link; the forced ground heals once the Keel falls)
current   BP_HalcyonCurrent: the Divinity current between the Center's temple and the Cliff Garden
physis    BP_Physis: PhysisTraceRead, PhysisToHalcyon, PhysisHalcyonHome
input     IA_TraceRead's Triggered event calls PhysisTraceRead
shared    Halcyon branches in graphs other levels own: fidelity and augmentations, music, load, save and restore, the
          menu's Continue (halcyon_shared.py)
hud       BP_PhysisHUD.PageMap: Halcyon's map page (after halcyon:map_art)
relic     BP_Relic.RelicTag: Halcyon's relics' own Logbook entries

It stands on grove_logic.py's helpers (the 5.9 dialect layer: var, shell, write, patch, comp, save). In the text
below @P is BP_Physis, @T BP_Trace, @B the Blueprint folder.
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
import physis_halcyon_lore as lore  # noqa: E402
import physis_halcyon_plan as plan  # noqa: E402

B = gl.B
_expand = gl.expand
gl.expand = lambda code: _expand(code.replace('@T', B + 'BP_Trace'))
var, shell, write, patch, comp, defaults, lit = gl.var, gl.shell, gl.write, gl.patch, gl.comp, gl.defaults, gl.lit
has, empty, same, vec, pick, snd = gl.has, gl.empty, gl.same, gl.vec, gl.pick, gl.snd
PHYSIS, NOW, TICK, PF, MINE = gl.PHYSIS, gl.NOW, gl.TICK, gl.PF, gl.MINE
HA = '/Game/Halcyon/Audio/'
SOUNDS = {'read': (HA + 'S_TraceRead', '/Game/Arche/Audio/S_WeaveRestless'), 'echo': (HA + 'S_Echo', '/Game/Center/Audio/S_PuzzleSolved'),
          'travel': (HA + 'S_CurrentTravel', '/Game/Grove/Audio/S_CurrentTravel'), 'music': (HA + 'S_Music_Halcyon', '/Game/Grove/Audio/S_Music_Grove')}
READ_SECONDS, READ_GAP, FADE = 10.0, 1.0, 2.0


def sound(key):
    own, other = SOUNDS[key]
    if (ROOT / ('Content' + own[5:] + '.uasset')).exists():
        return own
    if (ROOT / ('Content' + other[5:] + '.uasset')).exists():
        return other
    return '/Game/Audio/S_PickupDivinity'


def terrain_top(x, y, reach=3.0):
    info = json.loads((ROOT / 'Art/Meshes/Halcyon/height.json').read_text())
    hx, hy, cell, ny = info['half_x'], info['half_y'], info['cell'], int(info['ny'])
    nx = int(info['nx'])
    data = (ROOT / 'Art/Meshes/Halcyon/height.bin').read_bytes()
    steps = int(reach / cell) + 1
    i0, j0 = int(round((x + hx) / cell)), int(round((y + hy) / cell))
    return max(struct.unpack_from('<f', data, 4 * (i * ny + j))[0]
               for i in range(i0 - steps, i0 + steps + 1) for j in range(j0 - steps, j0 + steps + 1) if 0 <= i < nx and 0 <= j < ny)


ARRIVE = plan.GARDEN_STILL
ARRIVE_CM = (ARRIVE[0] * 100.0, ARRIVE[1] * 100.0, round((terrain_top(*ARRIVE) + 1.6) * 100.0))
# The Center: the temple's top tier, north-west of the Heartbloom; she comes back 5 m short of the current (TargetPoint
# HalcyonReturn, placed by halcyon:portal).
HOME_CM = (76000.0 + 778.0, -778.0, 4000.0 + 130.0)


# ---------------------------------------------------------------- BP_Trace

def trace():
    T = 'BP_Trace'
    for name, kind in (('Need', 'string'), ('Hide', 'string'), ('Give', 'string'), ('Done', 'string'), ('Range', 'float')):
        var(T, name, kind, True)
    for name, kind in (('T', 'float'), ('Shown', 'bool'), ('Solid', 'bool'), ('Seen', 'bool'), ('Want', 'float')):
        var(T, name, kind)
    shell(T, 'Read')
    # What the first whole reading does: the echo's line, its token.
    write(T, 'Read', """(fn `Read`
  """ + PHYSIS + """
  (set `self.Seen` true)
  (if (and (not """ + empty('(`self.Give`)') + """) (not """ + has(PF, '(`self.Give`)') + """))
    (`@P.PhysisGive` p (`self.Give`))
    """ + snd(sound('echo'), .8) + """
    (if (not """ + empty('(`self.Done`)') + """)
      (`@P.PhysisSay` p (`self.Done`)))))""")
    # How strongly the past stands: 1 while she reads within Range, fading over the reading's last FADE seconds, 0
    # otherwise. It comes up in 0.4 s and goes down as the reading fades; solid above 0.3.
    left = '(- (`@P.TraceUntil` p) %s)' % NOW
    near = '(< (`self.GetDistanceTo` p) %s)' % pick('(> (`self.Range`) 0.0)', '(`self.Range`)', '4000.0')
    want = pick('(and (> %s 0.0) %s)' % (left, near), '(`KismetMathLibrary.FClamp` (/ %s %.1f) 0.0 1.0)' % (left, FADE), '0.0')
    write(T, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "NoCollision")
  (`SceneComponent.SetVisibility` (`self.Shape`) false false)
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 0.0))

(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (set `self.Shown` (and (or """ + empty('(`self.Need`)') + ' ' + has(PF, '(`self.Need`)') + """) (or """ + empty('(`self.Hide`)') + ' (not ' + has(PF, '(`self.Hide`)') + """))))
  (set `self.Want` """ + pick('(`self.Shown`)', want, '0.0') + """)
  (set `self.T` (`KismetMathLibrary.FInterpTo_Constant` (`self.T`) (`self.Want`) DeltaSeconds """ + pick('(> (`self.Want`) (`self.T`))', '2.5', '4.0') + """))
  (`PrimitiveComponent.SetCustomPrimitiveDataFloat` (`self.Shape`) 0 (`self.T`))
  (`SceneComponent.SetVisibility` (`self.Shape`) (> (`self.T`) 0.01) false)
  (`LightComponent.SetIntensity` (`self.Glow`) (* 30.0 (`self.T`)))
  (if (and (>= (`self.T`) 0.3) (not (`self.Solid`)))
    (set `self.Solid` true)
    (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "QueryAndPhysics"))
  (if (and (< (`self.T`) 0.3) (`self.Solid`))
    (set `self.Solid` false)
    (`PrimitiveComponent.SetCollisionEnabled` (`self.Shape`) "NoCollision"))
  (if (and (>= (`self.T`) 0.95) (not (`self.Seen`)))
    (`self.Read`)))""")
    comp(T)
    defaults(T, {'Range': 4000.0})


# ---------------------------------------------------------------- BP_HalcyonDirector

def director():
    N = 'BP_HalcyonDirector'
    for name, kind in (('Motion', 'float'), ('Heal', 'float'), ('Live', 'bool'), ('Hushed', 'bool')):
        var(N, name, kind)
    for name in ('Arrive', 'State'):
        shell(N, name)
    write(N, 'Arrive', """(fn `Arrive`
  """ + PHYSIS + """
  (if (not """ + has(PF, ',halcyon,') + """)
    (`@P.PhysisGive` p ",halcyon,"))
  (if (not """ + has(PF, ',at_halcyon,') + """)
    (`@P.PhysisGive` p ",at_halcyon,"))
  (if (and """ + empty('(`@P.Objective` p)') + ' (not ' + has(PF, ',kairos_h,') + """))
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_ARRIVE) + """))
  (if (not """ + has(PF, ',halcyon_seen,') + """)
    (`@P.PhysisGive` p ",halcyon_seen,")
    (`@P.PhysisSay` p """ + lit(lore.MESSAGES['arrive']) + """)
    (`@P.PhysisNarrate` p """ + lit(lore.ARRIVAL_LINE[0]) + """)))""")
    done = has(PF, ',keel,')
    lines = '(and (and %s %s) %s)' % (has(PF, ',ha_line1,'), has(PF, ',ha_line2,'), has(PF, ',ha_line3,'))
    write(N, 'State', """(fn `State`
  """ + PHYSIS + """
  """ + gl.tagged('HalcyonScar', done, 'scar') + """
  """ + gl.tagged('HalcyonBloom', '(not %s)' % done, 'bloom') + """
  """ + gl.once(',ha_q_breach,', has(PF, ',trace,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_BREACH)) + """
  """ + gl.once(',ha_q_echoes,', has(PF, ',ha_bridge,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_ECHOES)) + """
  """ + gl.once(',ha_q_gate,', lines, '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_GATE)) + """
  """ + gl.once(',ha_q_keel,', has(PF, ',ha_gate,'), '(`@P.PhysisQuest` p %s)' % lit(lore.QUEST_KEEL)) + """
  """ + gl.once(',halcyon_done,', has(PF, ',aug_agility7,'), '(`@P.PhysisNote` p "Halcyon\'s record is read.")') + """
  (set `self.Motion` """ + pick(has(PF, ',resonance,'), '1.0', '0.12') + """)
  (set `self.Heal` """ + pick(done, '1.0', '0.0') + """)
  (`KismetMaterialLibrary.SetScalarParameterValue` """ + gl.MPC + """ "Motion" (`self.Motion`))
  (`KismetMaterialLibrary.SetScalarParameterValue` """ + gl.MPC + """ "Heal" (`self.Heal`))
  """ + gl.hush('HalcyonHush', done) + ')')   # 3 s in play, at once after a load that finds it done
    write(N, 'EventGraph', """(event `self.ReceiveBeginPlay`
  (`KismetSystemLibrary.K2_SetTimer` self "Arrive" 0.5 false)
  (`KismetSystemLibrary.K2_SetTimer` self "State" 0.25 true))""")
    comp(N)


# ---------------------------------------------------------------- BP_HalcyonCurrent

def current():
    """BP_GroveCurrent's graph for Halcyon: tags HalcyonArrival (here) and HalcyonReturn (the Center), token ,trip_h,."""
    N = 'BP_HalcyonCurrent'
    for name, kind in (('Need', 'string'), ('Dest', 'int'), ('Radius', 'float')):
        var(N, name, kind, True)
    for name, kind in (('Stay', 'float'), ('Armed', 'bool'), ('Gone', 'bool')):
        var(N, name, kind)
    land = '\n    '.join("""(for %s (`GameplayStatics.GetAllActorsWithTag` "%s")
      (`Actor.K2_SetActorLocation` p (`Actor.K2_GetActorLocation` %s) false true)
      (`@P.PhysisCheckpoint` p (.x (`Actor.K2_GetActorLocation` %s)) (.y (`Actor.K2_GetActorLocation` %s)) (.z (`Actor.K2_GetActorLocation` %s))))"""
                           % ((spot, tag) + (spot,) * 4) for spot, tag in (('spot', 'HalcyonArrival'), ('back', 'HalcyonReturn')))
    ready = '(or %s %s)' % (empty('(`self.Need`)'), has(PF, '(`self.Need`)'))
    reach = pick('(> (`self.Radius`) 0.0)', '(`self.Radius`)', '180.0')
    gap = '(`self.GetDistanceTo` p)'
    glow = '(/ (`self.Stay`) 0.8)'
    cam = '(`GameplayStatics.GetPlayerCameraManager` 0)'
    write(N, 'EventGraph', """(event `self.ReceiveTick`
  """ + TICK + """
  """ + PHYSIS + """
  (if """ + has(PF, ',trip_h,') + """
    (set `@P.Flags` (`KismetStringLibrary.Replace` """ + PF + """ ",trip_h," "" "CaseSensitive") p)
    """ + land + """)
  (if (and (and """ + ready + """ (== (`self.Dest`) 1)) (and (not """ + has(PF, ',halcyon,') + ') (not ' + has(PF, ',ha_currenthint,') + """)))
    (`@P.PhysisGive` p ",ha_currenthint,")
    (`@P.PhysisQuest` p """ + lit(lore.QUEST_CURRENT) + """))
  (`self.SetActorHiddenInGame` (not """ + ready + """))
  (if (> """ + gap + ' (+ ' + reach + """ 150.0))
    (set `self.Armed` true))
  (if (and (and """ + ready + """ (`self.Armed`)) (and (< """ + gap + ' ' + reach + """) (and (not (`@P.Cinematic` p)) (not (`@P.PhysisDead` p)))))
    (if (<= (`self.Stay`) 0.0)
      """ + snd(sound('travel')) + """)
    (set `self.Stay` (+ (`self.Stay`) DeltaSeconds))
    (`PlayerCameraManager.SetManualCameraFade` """ + cam + ' ' + pick('(> %s 1.0)' % glow, '1.0', glow) + """ (make `LinearColor` 0.85 0.88 0.92 1.0) false)
    (if (and (>= (`self.Stay`) 0.8) (not (`self.Gone`)))
      (set `self.Gone` true)
      (if (== (`self.Dest`) 2)
        (`@P.PhysisHalcyonHome` p)
        (elif (== (`self.Dest`) 1)
          (`@P.PhysisToHalcyon` p))))
    (elif (> (`self.Stay`) 0.0)
      (set `self.Stay` 0.0)
      (`PlayerCameraManager.StopCameraFade` """ + cam + """))))""")
    comp(N)
    defaults(N, {'Radius': 180.0})


# ---------------------------------------------------------------- BP_Physis

def physis_shells():
    P = 'BP_Physis'
    for name, kind in (('TraceUntil', 'float'), ('TraceReady', 'float')):
        var(P, name, kind)
    for name in ('PhysisTraceRead', 'PhysisToHalcyon', 'PhysisHalcyonHome'):
        shell(P, name)
    comp(P)


def physis():
    P = 'BP_Physis'
    # Trace Reading (T / hold the D-pad down): no cost; a reading lasts READ_SECONDS, READ_GAP between presses, and
    # pressing again while one lasts renews it. It reports the ability first, so the trace sockets elsewhere answer it.
    write(P, 'PhysisTraceRead', """(fn `PhysisTraceRead`
  (if (and (and (not (`self.Cinematic`)) (not (`self.PhysisDead`))) (and (not (`self.Talking`)) """ + has(MINE, ',trace,') + """))
    (if (> """ + NOW + """ (`self.TraceReady`))
      (set `self.TraceReady` (+ """ + NOW + """ %.1f))
      (set `self.TraceUntil` (+ """ % READ_GAP + NOW + """ %.1f))
      (`self.PhysisUsedAbility` ",trace,")
      """ % READ_SECONDS + snd(sound('read'), .7) + """)))""")
    write(P, 'PhysisToHalcyon', """(fn `PhysisToHalcyon`
  (if (not """ + has(MINE, ',halcyon,') + """)
    (`self.PhysisGive` ",halcyon,"))
  (if (not """ + has(MINE, ',at_halcyon,') + """)
    (`self.PhysisGive` ",at_halcyon,"))
  (`self.PhysisGive` ",trip_h,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_Halcyon" true "nocine,load"))""" % ARRIVE_CM)
    write(P, 'PhysisHalcyonHome', """(fn `PhysisHalcyonHome`
  (set `self.Flags` (`KismetStringLibrary.Replace` (`self.Flags`) ",at_halcyon," "" "CaseSensitive"))
  (`self.PhysisGive` ",trip_h,")
  (`self.PhysisCheckpoint` %.1f %.1f %.1f)
  (`self.PhysisSaveGame`)
  (`GameplayStatics.OpenLevel` "L_CenterOfTheUniverse" true "nocine,load"))""" % HOME_CM)
    comp(P)


def wire():
    write('BP_Physis', 'EventGraph', """(event `EnhancedInput|/Game/Input/Actions/IA_TraceRead`
  (:`Triggered`
    (`self.PhysisTraceRead`)))""", 'input IA_TraceRead')
    comp('BP_Physis')


PARTS = {'trace': trace, 'director': director, 'current': current, 'physis': physis, 'input': wire}

if __name__ == '__main__':
    import halcyon_shared
    PARTS.update(halcyon_shared.PARTS)
    parts = ARGS or ['trace', 'director', 'current', 'physis', 'input']
    print('Halcyon arrival %s cm, Center arrival %s cm' % (ARRIVE_CM, HOME_CM))
    if any(part in ('director', 'current', 'physis', 'input') for part in parts):
        physis_shells()
    for part in parts:
        PARTS[part]()
    for bp in gl.TOUCHED:
        gl.save(bp)
    print('FAILED:', gl.FAILED or 'none')
