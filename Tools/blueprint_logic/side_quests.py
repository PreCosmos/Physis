"""The pause menu's Quests page with three sections: Main Quest, Side Quests, Completed.

Author, 2026-11-17: "make a Side Quests submenu under the Quests menu and make the quests appear there with a
description as they are given. We also need a Completed quests section for the quests that have been already completed."

Run with the editor open (it rewrites one form of BP_PhysisHUD DrawPauseMenu through the 5.9 Blueprint DSL tools):
  python3 Tools/blueprint_logic/side_quests.py [--dry]
BP_PhysisHUD takes one write per editor launch: run it first thing after a launch, then it compiles and saves.

The page (tab 2) had the main objective, the finished objectives under it and the two achievements. Now a list on the
left names three sections, chosen with W / S, the arrow keys or the D-pad (BP_Physis.MenuRow, which changing tab sets
back to 0):
  Main Quest    the objective, and the achievements
  Side Quests   every side quest she has been given and has not finished: its name and world, what was asked, how many
                of a three-part thing she holds, and where to take it once she holds it. The Conclave's are in the left
                column, the Grove's and Arche's in the right.
  Completed     the main quest's finished objectives (as before), and every finished side quest with its reward
The quests and how the game marks them are in Content/Python/physis_side_quests.py; nothing in play was changed to
track them, the page only reads BP_Physis.Flags. Run again, it replaces its own page (it finds it by its marker).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'Tools'), str(ROOT / 'Content/Python')]
from unreal_mcp import UnrealMCP  # noqa: E402
import physis_side_quests as data  # noqa: E402

HUD = '/Game/Characters/Physis/Blueprints/BP_PhysisHUD'
P = '/Game/Characters/Physis/Blueprints/BP_Physis'
MARKER = '"Side Quests"'
U = '_returnvalue_2'                       # the page's unit: SizeY / 1080
FONT = '"/Game/UI/F_Physis.F_Physis"'
GOLD, DIM, CREAM, TEAL = (1.0, .82, .42), (.62, .68, .74), (1.0, .92, .78), (.5, 1.0, .88)
PRESS = '(`PlayerController.WasInputKeyJustPressed` _returnvalue (struct :`KeyName` %s))'


def u(value):
    return '(* %s %s)' % (U, float(value))


def lit(text):
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"')


def colour(rgb):
    return '(struct :`R` %s :`G` %s :`B` %s :`A` 1.0)' % rgb


def text(words, x, y, size, rgb):
    """A line of text with its dark plate, as the page's other lines are drawn; words is a DSL expression."""
    scale = '(* %s 0.35)' % u(size)
    return '(`self.DrawTextPlate` %s %s %s %s)\n(`self.DrawText` %s %s %s %s %s %s)' % (words, x, y, scale, words, colour(rgb), x, y, FONT, scale)


def lines(words, x, rgb, size=.95, step=28.0):
    return '(`self.DrawLines` %s %s (`self.LineY`) %s %s %s %s %s)' % (words, x, u(size), u(step), rgb[0], rgb[1], rgb[2])


def has(token):
    return '(`KismetStringLibrary.Contains` {F} %s)' % lit(token)


def chain(op, items):
    out = items[0]
    for item in items[1:]:
        out = '(%s %s %s)' % (op, out, item)
    return out


def down(amount):
    return '(set `self.LineY` (+ (`self.LineY`) %s))' % u(amount)


def pressed(*keys):
    return chain('or', [PRESS % key for key in keys])


def form_end(code, start):
    depth, i, quoted = 0, start, False
    while i < len(code):
        ch = code[i]
        if quoted:
            if ch == '\\':
                i += 1
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError('unclosed form')


def form_balance(code):
    depth, quoted, i = 0, False, 0
    while i < len(code):
        ch = code[i]
        if quoted:
            if ch == '\\':
                i += 1
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        i += 1
    return depth


def page(old, tag=''):
    """The new (if (== _menupage_2 2) ...) form; `old` is the one it replaces (its achievement lines are kept)."""
    keep = [line.strip() for line in old.split('\n') if 'Ach' in line or 'Finish Meridian' in line]
    # A kept line that ended a block (this script's own page, run again) carries that block's closing brackets.
    for k, line in enumerate(keep):
        while form_balance(line) < 0 and line.endswith(')'):
            line = line[:-1]
        keep[k] = line
    # Columns are placed by the page's width, so they stay inside the frame in a window narrower than 16:9.
    def across(share, extra=0.0):
        return '(+ %s (* %s (- SizeX %s)))' % (u(420 + extra), share, u(484))
    achievements = '\n'.join(keep)
    for was, now in ((900.0, across(.55)), (920.0, across(.55, 20)), (1200.0, across(.55)), (1220.0, across(.55, 20))):
        achievements = achievements.replace('(* %s %s)' % (U, was), now)
    if len(keep) < 8:
        raise ValueError('the achievement lines changed: %d found' % len(keep))
    limit = '(< (`self.LineY`) (- SizeY %s))' % u(150)
    names = {'F': '_sqflags' + tag, 'R': '_sqrow' + tag, 'S': '_sqsection' + tag}
    out = ['(if (== _menupage_2 2)',
           '(bind {F} (`%s.Flags` _asbp_physis))' % P,
           '(bind {R} (`%s.MenuRow` _asbp_physis))' % P,
           '(if %s\n(set `%s.MenuRow` (select `bool` (> {R} 0) :`false` 0 :`true` (- {R} 1)) _asbp_physis))' % (
               pressed('Up', 'W', 'Gamepad_DPad_Up', 'Gamepad_LeftStick_Up'), P),
           '(if %s\n(set `%s.MenuRow` (select `bool` (< {R} 2) :`false` 2 :`true` (+ {R} 1)) _asbp_physis))' % (
               pressed('Down', 'S', 'Gamepad_DPad_Down', 'Gamepad_LeftStick_Down'), P),
           '(bind {S} (select `bool` (> (`%s.MenuRow` _asbp_physis) 2) :`false` (`%s.MenuRow` _asbp_physis) :`true` 2))' % (P, P),
           '(`self.DrawRect` (struct :`R` 1.0 :`G` 0.78 :`B` 0.36 :`A` 0.35) %s %s %s (- SizeY %s))' % (u(385), u(140), u(2), u(290))]
    for row, name in enumerate(('Main Quest', 'Side Quests', 'Completed')):
        y = u(150 + 56 * row)
        out.append('(if (== {S} %d)\n(`self.DrawRect` (struct :`R` 1.0 :`G` 0.8 :`B` 0.4 :`A` 0.12) %s %s %s %s))' % (row, u(96), u(142 + 56 * row), u(270), u(46)))
        out.append('(`self.DrawTextPlate` %s %s %s (* %s 0.35))' % (lit(name), u(110), y, u(1.3)))
        out.append('(`self.DrawText` %s (make `LinearColor` (select `bool` (== {S} %d) :`false` 0.62 :`true` 1.0) (select `bool` (== {S} %d) :`false` 0.68 :`true` 0.82) '
                   '(select `bool` (== {S} %d) :`false` 0.74 :`true` 0.42) 1.0) %s %s %s (* %s 0.35))' % (lit(name), row, row, row, u(110), y, FONT, u(1.3)))
    out.append(text(lit('W, S / D-pad: section'), u(110), u(330), .8, DIM))
    # ---- Main Quest
    out.append('(if (== {S} 0)')
    out.append(text(lit('Main Quest'), u(420), u(150), 1.5, GOLD))
    out.append('(`self.DrawLines` (`%s.Objective` _asbp_physis) %s %s %s %s 1.0 0.92 0.78)' % (P, u(420), u(196), u(1.2), u(36)))
    out.append(achievements + ')')
    # ---- Side Quests
    out.append('(if (== {S} 1)')
    out.append(text(lit('Side Quests'), u(420), u(150), 1.5, GOLD))
    active = []
    for column, worlds in ((u(420), ('The Conclave',)), (across(.5), ('The Wounded Grove', 'Arche'))):
        out.append('(set `self.LineY` %s)' % u(204))
        for world, title, given, held, parts, done, about, back, reward in data.QUESTS:
            if world not in worlds:
                continue
            started = chain('or', [has(t) for t in (given, held) + tuple(parts)])
            live = '(and %s (not %s))' % (started, has(done))
            active.append(live)
            body = [text(lit('%s  (%s)' % (title, world)), column, '(`self.LineY`)', 1.15, GOLD), down(34), lines(lit(about), column, CREAM)]
            if parts:
                count = chain('+', ['(select `bool` %s :`false` 0 :`true` 1)' % has(t) for t in parts])
                found = '(`KismetStringLibrary.Concat_StrStr` "Found: " (`KismetStringLibrary.Concat_StrStr` (`KismetStringLibrary.Conv_IntToString` %s) " of %d"))' % (count, len(parts))
                body.append('(if (not %s)\n%s)' % (has(held), lines(found, column, TEAL)))
            body.append('(if %s\n%s)' % (has(held), lines(lit(back), column, TEAL)))
            body.append(down(22))
            out.append('(if %s\n(if %s\n%s))' % (live, limit, '\n'.join(body)))
    out.append('(if (not %s)\n%s)' % (chain('or', active), text(lit('Nobody has asked anything of you yet. People you meet may.'), u(420), u(204), 1.0, DIM)))
    out.append(')')
    # ---- Completed
    out.append('(if (== {S} 2)')
    out.append(text(lit('Completed'), u(420), u(150), 1.5, GOLD))
    out.append(text(lit('Main Quest'), u(420), u(204), 1.3, GOLD))
    out.append('(set `self.LineY` %s)' % u(252))
    out.append('(for _array_element (`KismetStringLibrary.ParseIntoArray` (`%s.QuestDone` _asbp_physis) "@")\n(if %s\n%s))' % (
        P, limit, lines('_array_element', u(420), DIM)))
    out.append(text(lit('Side Quests'), across(.62), u(204), 1.3, GOLD))
    out.append('(set `self.LineY` %s)' % u(252))
    finished = []
    for world, title, given, held, parts, done, about, back, reward in data.QUESTS:
        finished.append(has(done))
        out.append('(if %s\n(if %s\n%s\n%s\n%s\n%s))' % (has(done), limit, text(lit(title), across(.62), '(`self.LineY`)', 1.0, CREAM), down(28),
                                                   lines(lit('%s. Reward: %s.' % (world, reward)), across(.62), DIM, .85, 26.0), down(14)))
    out.append('(if (not %s)\n%s)' % (chain('or', finished), text(lit('None yet.'), across(.62), u(252), .95, DIM)))
    out.append('))')
    code = '\n'.join(out)
    for key, name in names.items():
        code = code.replace('{%s}' % key, name)
    return code


def main():
    client = UnrealMCP(600)
    client.initialize()

    def call(tool, args, toolset='BlueprintToolsets.BlueprintDslToolset'):
        reply = client.call('call_tool', {'toolset_name': toolset, 'tool_name': tool, 'arguments': args})
        return reply.get('isError'), ''.join(part.get('text', '') for part in reply.get('content', []))
    failed, body = call('Read', {'assetPath': HUD, 'scope': 'DrawPauseMenu', 'bIncludePositions': False})
    got = json.loads(body)
    got = got.get('returnValue', got)
    code = got['dsl']
    start = code.index('(if (== _menupage_2 2)')
    end = form_end(code, start)
    old = code[start:end]
    rest = code[:start] + code[end:]
    tag = next(t for t in ('', '2', '3', '4', '5', '6', '7', '8', '9') if '_sqflags' + t + ' ' not in rest and '_sqflags' + t + ')' not in rest)
    new = page(old, tag)
    print('page: %d characters replace %d; already ours: %s' % (len(new), len(old), MARKER in old))
    if '--dry' in sys.argv:
        (ROOT / 'Saved/Fauna/side_quests_page.dsl').write_text(new)
        return
    failed, body = call('Edit', {'assetPath': HUD, 'scope': 'DrawPauseMenu', 'revision': got['revision'], 'edits': [{'oldString': old, 'newString': new}]})
    print('edit:', 'FAILED\n' + body[:3000] if failed else 'ok')
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
