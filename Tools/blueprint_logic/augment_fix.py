"""Two fixes to the augmentations, asked for by the author on 2026-11-19 ("Fix them").

1. Defense. BP_Physis.PhysisFidelity set HurtTaken = 1 - 0.15 * n (n = defense augmentations held). That reaches 0.1
   at six, and goes below zero at seven (Halcyon's) and eight (Hesper's): PhysisHurt treats a HurtTaken of 0 or less as
   "not set yet" and charges a full 1.0, so the seventh augmentation brought back full damage. Now each augmentation
   takes 15% off what is left: HurtTaken = 0.85 ^ n (1: 0.85, 4: 0.52, 6: 0.38, 8: 0.27), never zero, any n.

2. Reserve tanks. BP_PhysisHUD.DrawTimer drew at most nine reserve-tank icons, but MaxHealth through Hesper is 120:
   eleven reserves, two of them never shown. The row now holds sixteen (same 26 px spacing; the sixteenth ends at
   516 px of the 1080p layout, inside the 440 px health bar that starts at 106).

  python3 Tools/blueprint_logic/augment_fix.py          (the GUI editor running; safe to run again)

The level scripts that add augmentation tokens (grove_logic, arche_shared, halcyon_shared, hesper's) patch the token
chains inside these formulas, not the formulas, so they keep working; center_overrides.AUGMENT_VALUES has the new
defense formula too.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import elements as e  # noqa: E402  (its MCP client and helpers)

H = e.B + 'BP_PhysisHUD'
RESERVES = 16
STEP, FIRST = 26.0, 106.0


def balanced(code, start):
    """The expression that opens at code[start] == '('."""
    depth = 0
    for i in range(start, len(code)):
        depth += (code[i] == '(') - (code[i] == ')')
        if depth == 0:
            return code[start:i + 1]
    raise ValueError('unbalanced expression at %d' % start)


def tanks():
    code, _ = e.read(H, 'DrawTimer')
    if code is None:
        e.FAILED.append('DrawTimer not read')
        return
    last_x = FIRST + 8 * STEP                      # the ninth icon, 314
    at = code.find('(* _returnvalue %.1f)' % last_x)
    if at < 0:
        e.FAILED.append('DrawTimer: the ninth tank icon was not found')
        return
    ninth = balanced(code, code.rindex('(`self.DrawTexture`', 0, at))
    if code.count(ninth) != 1:
        e.FAILED.append('DrawTimer: the ninth tank icon is not unique')
        return
    more = ''
    for k in range(RESERVES, 9, -1):               # built from the innermost out
        icon = ninth.replace('(* _returnvalue %.1f)' % last_x, '(* _returnvalue %.1f)' % (FIRST + (k - 1) * STEP))
        icon = icon.replace('(> _returnvalue_2 8.5)', '(> _returnvalue_2 %.1f)' % (k - 0.5))
        more = '(if (> _returnvalue_3 %.1f)\n  %s%s)' % (k - 0.5, icon, ('\n  ' + more) if more else '')
    e.edit(H, 'DrawTimer', '(> _returnvalue_3 9.5)', [(ninth, ninth + '\n' + more)])


def defense():
    code, _ = e.read(e.P, 'PhysisFidelity')
    if code is None:
        e.FAILED.append('PhysisFidelity not read')
        return
    head = '(set `self.HurtTaken` (- 1.0 (* 0.15 '
    if head not in code:
        print('PhysisFidelity: HurtTaken is not the old linear formula (already fixed?)')
        return
    old = balanced(code, code.index(head))
    count = balanced(old, len(head))               # the sum of the defense tokens
    failed, body = e.call(e.DSL, 'Schema', {'assetPath': e.P, 'nodeType': 'KismetMathLibrary.MultiplyMultiply_FloatFloat'})
    if not failed:
        new = '(set `self.HurtTaken` (`KismetMathLibrary.MultiplyMultiply_FloatFloat` 0.85 %s))' % count
    else:                                          # 0.85 ^ n as exp(n ln 0.85)
        new = '(set `self.HurtTaken` (`KismetMathLibrary.Exp` (* %s -0.16251892949777494)))' % count
    print('defense via', 'Power' if not failed else 'Exp')
    e.edit(e.P, 'PhysisFidelity', 'self.HurtTaken` (`KismetMathLibrary.', [(old, new)])


def main():
    e.client.initialize()
    parts = sys.argv[1:] or ['tanks', 'defense']
    if 'tanks' in parts:
        tanks()
        e.compile_and_save(H)
    if 'defense' in parts:
        defense()
        e.compile_and_save(e.P)
    print('FAILED', e.FAILED) if e.FAILED else print('done')


if __name__ == '__main__':
    main()
