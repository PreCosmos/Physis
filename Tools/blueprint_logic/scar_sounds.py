"""Fades a level's scar sounds once its boss falls, in the live director graphs (2026-11-19).

grove_logic.tagged() only hides an actor and turns its collision off, and a hidden AmbientSound goes on playing, so
Arche's Lens hum (tag ArcheScar) kept humming after the Sunderer fell and the Grove's Array hum (tag GroveBlight)
after the Warden. arche_logic.director() and grove_logic.director() now end their State with grove_logic.hush(); this
script puts the same block into the live State graphs without rewriting the rest of either director: it reads the
graph, checks for its marker, appends the block inside the function and writes it back. The block binds her pawn
itself (hp), since a canonical read may have renamed the director's own binding.

Halcyon, Hesper and Morrow already faded their sounds (tags HalcyonHush, HesperHush, MorrowHush), but always over
3 s, so a load that found the boss fallen replayed the fade. Parts halcyon, hesper and morrow replace that block in the
live State with grove_logic.hush() on the same tag (their scripts' director() now writes the same): the block is found
by its `(set `self.Hushed` true)`, its condition is kept as the canonical read prints it, and the bool member Live
is added.

Run from the project folder with the editor open (better with the levels concerned closed: no placed director is
reinstanced then):
    python3 Tools/blueprint_logic/scar_sounds.py [arche] [grove] [halcyon] [hesper] [morrow] [--dry]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
ARGS = [a for a in sys.argv[1:] if a != '--dry']
_argv, sys.argv = sys.argv, [a for a in sys.argv if a == '--dry' or a == sys.argv[0]]
import grove_logic as gl  # noqa: E402
import arche_shared as ash  # noqa: E402  (imports arche_logic, which needs grove_logic first)
sys.argv = _argv

# part: (director, the tag its scar actors carry, the token that ends the scar)
DIRECTORS = {'arche': ('BP_ArcheDirector', 'ArcheScar', ',sunderer,'), 'grove': ('BP_GroveDirector', 'GroveBlight', ',warden,')}
# part: (director, the tag its faded sounds carry), for the levels whose State already fades over a fixed 3 s
REHUSH = {'halcyon': ('BP_HalcyonDirector', 'HalcyonHush'), 'hesper': ('BP_HesperDirector', 'HesperHush'),
          'morrow': ('BP_MorrowDirector', 'MorrowHush')}
PAWN = '(bind hp (cast `@P` (`GameplayStatics.GetPlayerPawn` 0)))'
MARKER = 'AudioComponent'


def block(tag, token):
    return gl.expand(PAWN + '\n  ' + gl.hush(tag, gl.has('(`@P.Flags` hp)', token)))


def patch(bp, tag, token):
    text = block(tag, token)
    if gl.DRY:
        print('=== %s State += \n  %s' % (bp, text))
        return
    for name in ('Live', 'Hushed'):
        gl.var(bp, name, 'bool')

    def change(code):
        start = code.index('(fn `State`')
        end = ash.form(code, start)
        return code[:end - 1].rstrip() + '\n  ' + text + ')' + code[end:]
    ash.edit(bp, 'State', MARKER, change)
    gl.comp(bp)


def refade(code, tag):
    """The State text with its fixed fade block replaced by grove_logic.hush() on `tag`, keeping its condition."""
    at = code.index('(set `self.Hushed` true)')
    start = code.rfind('(if (and ', 0, at)
    end = ash.form(code, start)
    old = code[start:end]
    if '"%s"' % tag not in old or 'AudioComponent.FadeOut' not in old or old.count('`self.Hushed`') != 2:
        raise ValueError('the fade block is not the expected one: ' + old[:160])
    cond = start + len('(if (and ')
    done = code[cond:ash.form(code, cond)]
    return code[:start] + gl.expand(gl.hush(tag, done)) + code[end:]


def rehush(bp, tag):
    if gl.DRY:
        print('=== %s State: fade on %s -> grove_logic.hush' % (bp, tag))
        return
    gl.var(bp, 'Live', 'bool')
    ash.edit(bp, 'State', '`self.Live`', lambda code: refade(code, tag))
    gl.comp(bp)


if __name__ == '__main__':
    for part in ARGS or ['arche', 'grove']:
        if part in REHUSH:
            rehush(*REHUSH[part])
            continue
        patch(*DIRECTORS[part])
    for bp in gl.TOUCHED:
        gl.save(bp)
    print('FAILED:', gl.FAILED or 'none')
