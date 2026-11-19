"""Elemental attacks for living monsters: fire, ice, thunder, wind, dark and light.

Author, 2026-11-17: "add monsters in all the levels with physical attacks and attacks like fire, ice, thunder, wind
and dark and light".

Run with the editor open (5.9 Blueprint DSL tools), once; run again, every part that is already there is left alone:
  python3 Tools/blueprint_logic/elements.py

A monster is one of the living animals (BP_TrainingDrone with Organic set: it closes, calls, draws back and strikes
with its body) that also has an Element, 1 fire, 2 ice, 3 thunder, 4 wind, 5 dark, 6 light:
  BP_TrainingDrone   Element (shown on placed actors), HealthBefore. DroneThink: an Organic with an Element also looses
                     a bolt of its element when its attack comes due and she is beyond its Reach (machines' rule: within
                     15 m, in sight); the bolt is given the Element and its colour. A body blow that costs her health
                     carries the element too. Spits (shown on placed actors): only an Organic with this set looses bolts.
  BP_EnemyBolt       Element, Before. It flies at the element's speed (thunder 2600 and light 2900 cm/s, wind 1300, the
                     rest the machines' 1700). A light bolt drops her guard as it lands (it cannot be blocked or
                     parried, only avoided). A bolt that costs her health calls PhysisElement.
  BP_Physis          PhysisElement(Element, FromX, FromY) and its timers:
                       fire     burns: half a point of health a second for three seconds (never the last point)
                       ice      her walking speed falls to 55 % for 3.5 s
                       thunder  she cannot act for 0.6 s
                       wind     she is thrown 11 m/s away from where it came from, and up
                       dark     15 Divinity is taken
                       light    nothing more: the beam's danger is that no guard stops it
                     each with a note on the HUD (PhysisNote). A blocked or parried hit carries no element.
"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
from unreal_mcp import UnrealMCP  # noqa: E402

B = '/Game/Characters/Physis/Blueprints/'
P, D, BOLT = B + 'BP_Physis', B + 'BP_TrainingDrone', B + 'BP_EnemyBolt'
DSL, TOOLS = 'BlueprintToolsets.BlueprintDslToolset', 'BlueprintToolsets.BlueprintToolset'
# Bolt colours by element (linear RGB; Glow is this times 5).
COLOURS = {1: (1.0, .30, .04), 2: (.50, .90, 1.0), 3: (1.0, .95, .35), 4: (.75, 1.0, .80), 5: (.35, .05, .60), 6: (1.0, 1.0, .85)}
SPEEDS = {3: 2600.0, 6: 2900.0, 4: 1300.0}
client = UnrealMCP(600)
FAILED = []


def call(toolset, tool, args):
    # The editor refuses tools while it is busy (a compile or a save just before): wait and ask again.
    for _ in range(20):
        reply = client.call('call_tool', {'toolset_name': toolset, 'tool_name': tool, 'arguments': args})
        body = ''.join(part.get('text', '') for part in reply.get('content', []))
        if not (reply.get('isError') and 'slow task' in body):
            break
        time.sleep(3)
    return reply.get('isError'), body


def read(bp, scope):
    failed, body = call(DSL, 'Read', {'assetPath': bp, 'scope': scope, 'bIncludePositions': False})
    if failed:
        return None, None
    got = json.loads(body)
    got = got.get('returnValue', got)
    return got['dsl'], got['revision']


def var(bp, name, kind, shown=False):
    failed, body = call(TOOLS, 'AddVariable', {'blueprint': {'refPath': '%s.%s' % (bp, bp.split('/')[-1])}, 'name': name, 'typeName': kind})
    if shown:
        call(TOOLS, 'SetVariableInstanceEditable', {'blueprint': {'refPath': '%s.%s' % (bp, bp.split('/')[-1])}, 'variableName': name, 'bInstanceEditable': True})
    print('var %s.%s' % (bp.split('/')[-1], name), 'FAILED ' + body[:200] if failed else 'ok', flush=True)


def function(bp, name, code):
    call(TOOLS, 'AddFunctionGraph', {'blueprint': {'refPath': '%s.%s' % (bp, bp.split('/')[-1])}, 'graphName': name})
    failed, body = call(DSL, 'Write', {'assetPath': bp, 'scope': name, 'dsl': code})
    print('fn %s.%s' % (bp.split('/')[-1], name), 'FAILED\n' + body[:1500] if failed else 'ok', flush=True)
    if failed:
        FAILED.append(name)


def edit(bp, scope, marker, changes):
    code, revision = read(bp, scope)
    label = '%s %s' % (bp.split('/')[-1], scope)
    if code is None:
        FAILED.append(label)
        print(label, 'not read')
        return
    if marker in code:
        print(label, 'already has it')
        return
    edits = []
    for old, new in changes:
        if code.count(old) != 1:
            FAILED.append(label)
            print(label, 'FAILED: %d matches of %s' % (code.count(old), old[:90]))
            return
        edits.append({'oldString': old, 'newString': new})
    failed, body = call(DSL, 'Edit', {'assetPath': bp, 'scope': scope, 'revision': revision, 'edits': edits})
    print(label, 'FAILED\n' + body[:1500] if failed else 'ok', flush=True)
    if failed:
        FAILED.append(label)


def by_element(values, default, element):
    """A value chosen by the element: nested selects."""
    out = default
    for key, value in values.items():
        out = '(select `bool` (== %s %d) :`false` %s :`true` %s)' % (element, key, out, value)
    return out


def compile_and_save(*bps):
    script = ('import unreal, json\nout = {}\nfor path in %r:\n    bp = unreal.load_asset(path)\n    unreal.BlueprintEditorLibrary.compile_blueprint(bp)\n'
              '    out[path.split("/")[-1]] = [str(bp.get_editor_property("status")), unreal.EditorAssetLibrary.save_loaded_asset(bp, False)]\n'
              'open(%r, "w").write(json.dumps(out))\n' % (list(bps), str(ROOT / 'Saved/Fauna/elements_save.json')))
    reply = client.call('call_tool', {'toolset_name': 'editor_toolset.toolsets.python_scripting.PythonScriptingTools', 'tool_name': 'execute_python',
                                      'arguments': {'script': {'content': script, 'language': 'Python'}}})
    print('compile and save:', (ROOT / 'Saved/Fauna/elements_save.json').read_text() if not reply.get('isError') else reply)


def physis():
    for name, kind in (('BurnLeft', 'int'), ('ChillSpeed', 'float')):
        var(P, name, kind)
    pc = '(`GameplayStatics.GetPlayerController` 0)'
    function(P, 'PhysisBurn', """(fn `PhysisBurn`
  (if (and (> (`self.BurnLeft`) 0) (not (`self.PhysisDead`)))
    (set `self.BurnLeft` (- (`self.BurnLeft`) 1))
    (if (> (`self.PhysisHealth`) 1.0)
      (set `self.PhysisHealth` (- (`self.PhysisHealth`) 0.5))
      (set `self.ShakeAmount` 2.0))
    (else
      (`KismetSystemLibrary.K2_ClearTimer` self "PhysisBurn"))))""")
    function(P, 'PhysisThaw', """(fn `PhysisThaw`
  (if (> (`self.ChillSpeed`) 0.0)
    (set `CharacterMovementComponent.MaxWalkSpeed` (`self.ChillSpeed`) (`self.CharacterMovement`))
    (set `self.ChillSpeed` 0.0)))""")
    function(P, 'PhysisUnstun', """(fn `PhysisUnstun`
  (if (and (not (`self.PhysisDead`)) (not (`self.Cinematic`)))
    (`self.EnableInput` %s)))""" % pc)
    function(P, 'PhysisElement', """(fn `PhysisElement`
  (params (Element :type Integer) (FromX :type "Float (double-precision)") (FromY :type "Float (double-precision)"))
  (if (and (not (`self.PhysisDead`)) (not (`self.Cinematic`)))
    (if (== Element 1)
      (set `self.BurnLeft` 3)
      (`KismetSystemLibrary.K2_SetTimer` self "PhysisBurn" 1.0 true)
      (`self.PhysisNote` "Burning"))
    (if (== Element 2)
      (if (<= (`self.ChillSpeed`) 0.0)
        (set `self.ChillSpeed` (`CharacterMovementComponent.MaxWalkSpeed` (`self.CharacterMovement`))))
      (set `CharacterMovementComponent.MaxWalkSpeed` (* (`self.ChillSpeed`) 0.55) (`self.CharacterMovement`))
      (`KismetSystemLibrary.K2_SetTimer` self "PhysisThaw" 3.5 false)
      (`self.PhysisNote` "Chilled"))
    (if (== Element 3)
      (`self.DisableInput` %s)
      (`KismetSystemLibrary.K2_SetTimer` self "PhysisUnstun" 0.6 false)
      (`self.PhysisNote` "Shocked"))
    (if (== Element 4)
      (`self.LaunchCharacter` (+ (* (`KismetMathLibrary.Normal` (`KismetMathLibrary.MakeVector` (- (.x (`self.K2_GetActorLocation`)) FromX) (- (.y (`self.K2_GetActorLocation`)) FromY) 0.0)) 1100.0) (`KismetMathLibrary.MakeVector` 0.0 0.0 380.0)) true true)
      (`self.PhysisNote` "Thrown back"))
    (if (== Element 5)
      (set `self.Divinity` (select `bool` (> (`self.Divinity`) 15.0) :`false` 0.0 :`true` (- (`self.Divinity`) 15.0)))
      (`self.PhysisNote` "Divinity drained"))
    (if (== Element 6)
      (`self.PhysisNote` "Seared by light"))))""" % pc)


def bolt():
    for name, kind in (('Element', 'int'), ('Before', 'float')):
        var(BOLT, name, kind, name == 'Element')
    hurt = '(`%s.PhysisHurt` _asbp_physis (> (`self.GetDotProductTo` _asbp_physis self) 0.0))' % P
    edit(BOLT, 'EventGraph', 'PhysisElement', (
        ('(* DeltaSeconds 1700.0)', '(* DeltaSeconds %s)' % by_element(SPEEDS, '1700.0', '(`self.Element`)')),
        (hurt, '(set `self.Before` (`%s.PhysisHealth` _asbp_physis))\n    (if (== (`self.Element`) 6)\n      (set `%s.BlockUntil` 0.0 _asbp_physis))\n    %s\n'
               '    (if (and (> (`self.Element`) 0) (< (`%s.PhysisHealth` _asbp_physis) (`self.Before`)))\n      (`%s.PhysisElement` _asbp_physis (`self.Element`) (.x (`self.K2_GetActorLocation`)) (.y (`self.K2_GetActorLocation`))))'
               % (P, P, hurt, P, P))))


def drone():
    for name, kind in (('Element', 'int'), ('HealthBefore', 'float')):
        var(D, name, kind, name == 'Element')
    element = '(`self.Element`)'
    hurt = '(`%s.PhysisHurt` _asbp_physis (> (`self.GetDotProductTo` _asbp_physis self) 0.0))' % P
    blow = ('(set `self.HealthBefore` (`%s.PhysisHealth` _asbp_physis))\n        %s\n'
            '        (if (and (> %s 0) (< (`%s.PhysisHealth` _asbp_physis) (`self.HealthBefore`)))\n          (`%s.PhysisElement` _asbp_physis %s (.x (`self.K2_GetActorLocation`)) (.y (`self.K2_GetActorLocation`))))' % (P, hurt, element, P, P, element))
    spawn = ('(`|SpawnActorFromClass` "%s.BP_EnemyBolt_C" (`KismetMathLibrary.MakeTransform` (+ (`self.K2_GetActorLocation`) (* (`self.GetActorForwardVector`) 100.0)) '
             '(`KismetMathLibrary.ComposeRotators` (`KismetMathLibrary.MakeRotator` 0.0) (`self.K2_GetActorRotation`)) (`KismetMathLibrary.MakeVector` 1.5 0.07 0.07)) "AlwaysSpawn" "MultiplyWithRoot" null null)' % BOLT)
    colour = lambda scale: '(`KismetMathLibrary.MakeVector` %s %s %s)' % tuple(
        by_element({k: round(v[i] * scale, 3) for k, v in COLOURS.items()}, '1.0', element) for i in range(3))
    dressed = ('(bind _elementbolt %s)\n        (if (> %s 0)\n          (set `%s.Element` %s _elementbolt)\n'
               '          (`SceneComponent.SetRelativeScale3D` (`%s.Shape` _elementbolt) (`KismetMathLibrary.MakeVector` 1.0 3.2 3.2))\n'
               '          (`MeshComponent.SetVectorParameterValueOnMaterials` (`%s.Shape` _elementbolt) "Colour" %s)\n'
               '          (`MeshComponent.SetVectorParameterValueOnMaterials` (`%s.Shape` _elementbolt) "Glow" %s))'
               % (spawn, element, BOLT, element, BOLT, BOLT, colour(1.0), BOLT, colour(5.0)))
    edit(D, 'DroneThink', 'PhysisElement', (
        (hurt, blow),
        ('(elif (and (not (`self.Organic`)) (and (< _returnvalue_8 1500.0) _returnvalue))', '(elif (and (or (not (`self.Organic`)) (> %s 0)) (and (< _returnvalue_8 1500.0) _returnvalue))' % element),
        (spawn + '\n        (if _boss', dressed + '\n        (if _boss')))


def spits():
    """Spits: an Organic with an Element looses bolts only when this is set. The small swarm animals carry their
    element on the bite alone (four of them at once would otherwise be four turrets); machines always fire."""
    var(D, 'Spits', 'bool', True)
    edit(D, 'DroneThink', '(`self.Spits`)', (
        ('(elif (and (or (not (`self.Organic`)) (> (`self.Element`) 0)) (and (< _returnvalue_8 1500.0) _returnvalue))',
         '(elif (and (or (not (`self.Organic`)) (and (> (`self.Element`) 0) (`self.Spits`))) (and (< _returnvalue_8 1500.0) _returnvalue))'),))


def main():
    client.initialize()
    parts = sys.argv[1:] or ['physis', 'bolt', 'drone', 'spits']
    if 'physis' in parts:
        physis()
    if FAILED:
        sys.exit('stopped: %s' % FAILED)
    compile_and_save(P)   # the bolt and the drone name PhysisElement
    if 'bolt' in parts:
        bolt()
    if 'drone' in parts:
        drone()
    if 'spits' in parts:
        spits()
    compile_and_save(P, BOLT, D)
    if FAILED:
        sys.exit('FAILED: %s' % FAILED)


if __name__ == '__main__':
    main()
