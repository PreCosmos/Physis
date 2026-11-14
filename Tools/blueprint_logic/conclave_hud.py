"""The Conclave's one BP_PhysisHUD batch (Tools/conclave/README.md, "People (BP_NPC) and Blueprints"):
    python3 Tools/blueprint_logic/conclave_hud.py [--dry]

TalkOption  one topic row of the talk panel (plain parameters, so DrawTalk stays small)
TalkPoll    this frame's talk key into TalkCode: 1 confirm (E, Enter, Space, A, X), 2 up, 3 down, 4 leave (B, Backspace)
DrawTalk    while BP_Physis.Talking: the panel, the speaker, the page (DrawLines) or the topics, a hint line, the keys
            (polled, because talking pauses the game); the pause menu opening (LogOpen) ends the talk
DrawInteract  center_overrides.draw_interact_code(): the live graph (feat.py: "E  Use" over switches and doors, the
            scan's continue hint) plus "E  Talk" over a shown person in talk range, and DrawTalk last
PageMap     center_overrides.map_page_code(): the pause menu's map, the Conclave's when a BP_ConclaveDirector is present

Run it in a FRESH editor as its first write, after conclave_logic.py has made BP_NPC's variables and functions; it
saves the HUD at the end. Memory (unreal-mcp-access): a second BP_PhysisHUD write in one editor session ran the editor
out of memory and froze the machine, so this is the only HUD write of the launch, and every graph in it is small.
center_overrides.py part map must not run in the same launch (this batch already wrote its PageMap). Run it again, in
a fresh editor, after any station rebuild: feat.py writes the station's DrawInteract back, and until this batch runs
again people do not talk (center_overrides.interact_code only starts a talk while this DrawInteract marks the HUD).
--dry prints every call and DSL graph instead of sending them (no editor needed).
"""
import json
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
DRY = '--dry' in sys.argv
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

B, H, FONT = co.B, co.H, co.FONT
NPC_CLASS = co.NPC_CLASS
OUTFIT = 'physis_character_tools.PhysisCharacterTools'
# The panel keeps the HUD's own look (gold rules and titles), drawn on plain black, with the hint in the Conclave's
# light blue rather than the station's teal.
GOLD, TEAL = co.GOLD, co.TEAL
RULE = '"(R=1.0,G=0.78,B=0.36,A=0.5)"'
BLUE = '"(R=0.55,G=0.8,B=1.0,A=1.0)"'
text, press = co.text, co.press


def dry_call(tool, args, quiet=False):
    if tool == 'write_graph_dsl':
        print('=== DSL %s' % args['graph']['refPath'])
        print(args['code'])
        print('=== END')
    else:
        print('--- %s %s' % (tool, json.dumps(args, ensure_ascii=False)))
    return '{"returnValue": null}'


if DRY:
    co.call = dry_call  # center_overrides' graph(), var(), fn() and comp() look call up at run time
else:
    # The fresh-editor HUD batch took 35 s (memory); a write still running after 5 minutes is the runaway that has been
    # OOM-killed before, so the script stops waiting and says so rather than sitting on it for center_overrides' 10.
    co.c.timeout = 300


def save(path):
    """aaa:save_asset saves the HUD alone (aaa:save_all would also save the open map). After a failed write it is
    left unsaved: quit the editor without saving, fix the graph and run the batch again in a fresh editor."""
    if co.FAILED:
        print('BP_PhysisHUD not saved: a write failed', flush=True)
        return
    args = {'operation': 'aaa:save_asset:' + path.rsplit('.', 1)[0]}
    if DRY:
        print('--- outfit_operation %s' % json.dumps(args))
        return
    r = co.c.call('call_tool', {'toolset_name': OUTFIT, 'tool_name': 'outfit_operation', 'arguments': args})
    ok = not r.get('isError')
    print('saved BP_PhysisHUD', 'ok' if ok else 'FAILED ' + r['content'][0]['text'][:300], flush=True)
    if not ok:
        co.FAILED.append('save BP_PhysisHUD')


def talk_option():
    chosen = '(== Index Row)'
    colour = '(Utilities|Struct|MakeLinearColor :R (select %s 1.0 0.62) :G (select %s 0.82 0.68) :B (select %s 0.42 0.74) :A 1.0)' % (chosen, chosen, chosen)
    return """(fn TalkOption (Text Index Row X Y SizeY)
  (bind u (/ SizeY 1080.0))
  (if (not (Utilities|String|EqualExactly(String) :A Text :B ""))
    (if """ + chosen + """
      (HUD|DrawRect :RectColor "(R=1.0,G=0.8,B=0.4,A=0.14)" :ScreenX (- X (* u 18.0)) :ScreenY (- Y (* u 5.0)) :ScreenW (* u 640.0) :ScreenH (* u 40.0))
      (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.9)" :ScreenX (- X (* u 18.0)) :ScreenY (- Y (* u 5.0)) :ScreenW (* u 4.0) :ScreenH (* u 40.0)))
    """ + text('Text', 'X', 'Y', '(* u 1.2)', colour) + """))"""


def talk_poll():
    # Later tests win: leave over confirm over up over down, so one frame never sends two codes.
    return """(fn TalkPoll ()
  (bind pc (Game|GetPlayerController 0))
  (Variables|Default|SetTalkCode 0)
  (if """ + press('S', 'Down', 'Gamepad_DPad_Down', 'Gamepad_LeftStick_Down') + """
    (Variables|Default|SetTalkCode 3))
  (if """ + press('W', 'Up', 'Gamepad_DPad_Up', 'Gamepad_LeftStick_Up') + """
    (Variables|Default|SetTalkCode 2))
  (if """ + press('E', 'Enter', 'SpaceBar', 'Gamepad_FaceButton_Bottom', 'Gamepad_FaceButton_Left') + """
    (Variables|Default|SetTalkCode 1))
  (if """ + press('Gamepad_FaceButton_Right', 'BackSpace') + """
    (Variables|Default|SetTalkCode 4)))"""


def draw_talk():
    """The panel sits low and centred (1240u by 330u). Fresh (set by TalkStart) skips the keys on the talk's first frame,
    when the Interact press that opened it still reads as just pressed. TalkSeen catches a Talking flag with no person
    talking (a person removed mid-talk) and gives play back."""
    person = lambda name: '(Class|BPNPC|Get%s :self person)' % name
    rows = ''.join('\n                      (CallFunction|TalkOption :Text %s :Index %d :Row row :X (+ left (* u 64.0)) :Y (+ top (* u %d.0)) :SizeY SizeY)'
                   % (person('Opt%d' % k), k, 98 + 46 * k) for k in range(4))
    return """(fn DrawTalk (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (if (Class|BPPhysis|GetTalking :self physis)
        (Variables|Default|SetTalkSeen false)
        (for found (Actor|GetAllActorsOfClass :ActorClass """ + NPC_CLASS + """)
          (bind person (Utilities|Casting|CastToBP_NPC :Object found)
            (:then
              (if """ + person('Talking') + """
                (Variables|Default|SetTalkSeen true)
                (if (Class|BPPhysis|GetLogOpen :self physis)
                  (Class|BPNPC|TalkEnd :self person)
                  (else
                    (bind left (- (/ SizeX 2.0) (* u 620.0)))
                    (bind top (- SizeY (* u 420.0)))
                    (HUD|DrawRect :RectColor "(R=0.0,G=0.0,B=0.0,A=0.72)" :ScreenX left :ScreenY top :ScreenW (* u 1240.0) :ScreenH (* u 330.0))
                    (HUD|DrawRect :RectColor """ + RULE + """ :ScreenX left :ScreenY top :ScreenW (* u 1240.0) :ScreenH (* u 2.0))
                    (HUD|DrawRect :RectColor """ + RULE + """ :ScreenX left :ScreenY (+ top (* u 328.0)) :ScreenW (* u 1240.0) :ScreenH (* u 2.0))
                    """ + text(person('Speaker'), '(+ left (* u 44.0))', '(+ top (* u 22.0))', '(* u 1.5)', GOLD) + """
                    (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.35)" :ScreenX (+ left (* u 44.0)) :ScreenY (+ top (* u 76.0)) :ScreenW (* u 1152.0) :ScreenH (* u 2.0))
                    (if (== """ + person('Mode') + """ 1)
                      (bind row """ + person('Row') + ')' + rows + """
                      """ + text('"W, S / D-pad: choose      E / A: ask      Backspace / B: leave"', '(+ left (* u 44.0))', '(+ top (* u 284.0))', '(* u 0.95)', BLUE) + """
                      (else
                        (CallFunction|DrawLines :Message """ + person('PageText') + """ :X (+ left (* u 44.0)) :Y (+ top (* u 98.0)) :Scale (* u 1.15) :Step (* u 38.0) :Red 1.0 :Green 0.95 :Blue 0.88)
                        """ + text('"E / A: continue      Backspace / B: leave"', '(+ left (* u 44.0))', '(+ top (* u 284.0))', '(* u 0.95)', BLUE) + """))
                    (if """ + person('Fresh') + """
                      (Class|BPNPC|SetFresh :self person :Fresh false)
                      (else
                        (CallFunction|TalkPoll)
                        (if (> (Variables|Default|GetTalkCode) 0)
                          (Class|BPNPC|TalkKey :self person :Code (Variables|Default|GetTalkCode)))))))))
            (:CastFailed)))
        (if (not (Variables|Default|GetTalkSeen))
          (Class|BPPhysis|SetTalking :self physis :Talking false)
          (Game|SetGamePaused :bPaused (Class|BPPhysis|GetLogOpen :self physis)))))
    (:CastFailed)))"""


def batch():
    # Every graph here names BP_NPC's members or BP_ConclaveDirector; a write naming what is not there yet would spend
    # the launch's one HUD batch on a failure.
    if not (co.built(co.NPC, 'TalkStart') and co.built(co.DIRECTOR)):
        sys.exit('BP_NPC (with TalkStart) or BP_ConclaveDirector is missing: run conclave:blueprints and conclave_logic.py '
                 'first. Nothing was written to the HUD.')
    # DrawInteract reads BP_Switch.Reach (center_overrides.py part conclave makes it): without it the batch would fail on
    # DrawInteract and spend the launch's one HUD write.
    if not DRY:
        have = co.call('list_variables', {'blueprint': {'refPath': co.SWITCH}}, True)
        if 'Reach' not in ((json.loads(have).get('returnValue') or []) if have else []):
            sys.exit('BP_Switch has no Reach yet: run center_overrides.py conclave (or conclave_logic.py) and save BP_Switch '
                     'first. Nothing was written to the HUD.')
    co.var(H, 'TalkSeen', 'bool')
    co.var(H, 'TalkCode', 'int')
    co.graph(H, 'TalkOption', [('Text', 'string'), ('Index', 'int'), ('Row', 'int'), ('X', 'float'), ('Y', 'float'), ('SizeY', 'float')])
    co.graph(H, 'TalkPoll')
    co.graph(H, 'DrawTalk', [('SizeX', 'float'), ('SizeY', 'float')])
    # Callees first: TalkOption and TalkPoll before DrawTalk, DrawTalk before DrawInteract. MapMark (PageMap's callee)
    # is center_overrides part map's and already in the HUD.
    co.fn(H, 'TalkOption', talk_option())
    co.fn(H, 'TalkPoll', talk_poll())
    co.fn(H, 'DrawTalk', draw_talk())
    co.fn(H, 'DrawInteract', co.draw_interact_code())
    co.fn(H, 'PageMap', co.map_page_code())
    co.comp(H)
    save(H)


if __name__ == '__main__':
    try:
        batch()
    except OSError as error:  # urllib's timeout and connection errors are OSErrors
        sys.exit('A HUD call got no answer (%s). The editor may still be writing: watch its memory, do not send another '
                 'HUD write in this launch, and quit without saving if it recovers.' % error)
    print('FAILED:', ', '.join(co.FAILED) or 'none')
