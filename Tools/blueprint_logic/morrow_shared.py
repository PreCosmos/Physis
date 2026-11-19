"""Morrow branches in the graphs other levels own (parts shared, hud, relic, music of morrow_logic.py).

Each edit reads the live graph, changes its text and writes it back (arche_shared.edit): a Morrow branch goes in front
of Hesper's, found by its whole form (arche_shared.form), so nothing at the far end of a chain is counted. A graph that
already holds an edit's marker is left alone. The canonical read renames bindings, so Hesper's director is found by its
class path and its branch by the binding the read gives it (hesper_binding()).
"""
import re

import arche_shared as ash
import grove_logic as gl
import morrow_logic as ml

B = gl.B
MORROW = '(> (`KismetArrayLibrary.Array_Length` _morrow) 0)'
BIND = '(bind _morrow (`GameplayStatics.GetAllActorsOfClass` "%sBP_MorrowDirector.BP_MorrowDirector_C"))' % B
HESPER_CLASS = 'BP_HesperDirector.BP_HesperDirector_C'
edit, once, form, before_form, has, flag = ash.edit, ash.once, ash.form, ash.before_form, ash.has, ash.flag


def bind_before(code, anchor):
    at = code.index(anchor)
    line = code.rfind('\n', 0, at) + 1
    indent = code[line:len(code) - len(code[line:].lstrip(' '))]
    return code[:line] + indent + BIND + '\n' + code[line:]


def hesper_binding(code):
    """The name the canonical read gave Hesper's director list (e.g. _outactors_4)."""
    found = re.search(r'\(bind (\S+) \(`GameplayStatics\.GetAllActorsOfClass` "[^"]*%s"\)\)' % re.escape(HESPER_CLASS), code)
    if not found:
        raise ValueError('no Hesper director binding')
    return found.group(1)


def shared():
    P = 'BP_Physis'

    def fidelity(code):
        stage = '(or (or (or (or (or %s %s) %s) %s) %s) %s)' % (has(',settle,'), has(',conclave,'), has(',grove,'), has(',arche,'), has(',halcyon,'),
                                                               has(',hesper,'))
        code = once(code, stage, '(or %s %s)' % (stage, has(',morrow,')))
        for last, new in ((',aug_hp10,', ',aug_hp11,'), (',aug_katana8,', ',aug_katana9,'), (',aug_pistol7,', ',aug_pistol8,'),
                          (',aug_defense8,', ',aug_defense9,'), (',aug_agility8,', ',aug_agility9,')):
            code = once(code, flag(last), '(+ %s %s)' % (flag(last), flag(new)))
        return code
    edit(P, 'PhysisFidelity', ',aug_hp11,', fidelity)

    music = ml.sound('music')

    def pick(code):
        name = hesper_binding(code)
        code = bind_before(code, HESPER_CLASS)
        opening = '(if (> (`KismetArrayLibrary.Array_Length` %s) 0)' % name
        return before_form(code, opening, '(if %s\n    (bind _morrowmusic (`GameplayStatics.SpawnSound2D` "%s.%s" (* 0.1 (`self.MusicVol`))))\n'
                                          '    (set `self.MusicComp` _morrowmusic)\n    (else\n    {old}))' % (MORROW, music, music.split('/')[-1]))
    edit(P, 'PhysisMusicPick', 'BP_MorrowDirector', pick)

    def load(code):
        opening = '(if (`KismetStringLibrary.Contains` (`%sBP_PhysisSave.Flags` _asbp_physis_save) ",at_hesper,")' % B
        at = code.index(opening)
        end = form(code, at)
        old = '(elif' + code[at + 3:end]
        return code[:at] + ('(if (`KismetStringLibrary.Contains` (`%sBP_PhysisSave.Flags` _asbp_physis_save) ",at_morrow,")\n'
                            '(`GameplayStatics.OpenLevel` "L_Morrow" true "nocine,load")\n%s)' % (B, old)) + code[end:]
    edit(P, 'PhysisLoadGame', ',at_morrow,', load)
    edit('BP_MenuHUD', 'MenuContinue', ',at_morrow,', load)
    gl.comp('BP_MenuHUD')

    def world(anchor):
        def change(code):
            code = bind_before(code, HESPER_CLASS)
            at = code.index(anchor) + len(anchor)
            assert code[at] == '(', code[at:at + 30]
            end = form(code, at)
            return code[:at] + '(select `bool` %s :`false` %s :`true` 8)' % (MORROW, code[at:end]) + code[end:]
        return change
    # The save's exact spot: world 8 while a BP_MorrowDirector stands in the level.
    edit(P, 'PhysisSaveGame', 'BP_MorrowDirector', world('SpotWorld` (select `bool` (`self.SpotSafe`) :`true` '))
    edit(P, 'PhysisRestore', 'BP_MorrowDirector', world('(== (`%sBP_PhysisSave.SpotWorld` _asbp_physis_save) ' % B))
    gl.comp(P)


MAP_NAMES = (('The Pass Chapel', 'Pass Chapel'), ('The Mill House', 'Mill House'), ('The Ice House', 'Ice House'), ('The Gorge', 'Gorge'),
             ('Chapel Square', 'Chapel Square'), ('The Schoolhouse', 'Schoolhouse'), ('The Glider Field', 'Glider Field'),
             ('The Telegraph House', 'Telegraph'), ('The Dam Stair', 'Dam Stair'), ('The Crest', 'Crest'))


def hud():
    plan = ml.plan
    size = '(* (* _returnvalue 0.85) 0.35)'
    font = '"/Game/UI/F_Physis.F_Physis"'
    labels = []
    for region, name in MAP_NAMES:
        x, y = plan.REGIONS[region][:2]
        u, v = (y + plan.MAP_HALF) / (2 * plan.MAP_HALF), (plan.MAP_HALF - x) / (2 * plan.MAP_HALF)
        px = '(- (+ _returnvalue_2 (* %.5f _returnvalue_4)) (* _returnvalue %.1f))' % (u, len(name) * 4.4)
        py = '(- (+ _returnvalue_3 (* %.5f _returnvalue_4)) (* _returnvalue 30.0))' % v
        labels.append('(`self.DrawTextPlate` "%s" %s %s %s)' % (name, px, py, size))
        labels.append('(`self.DrawText` "%s" (struct :`R` 0.92 :`G` 0.96 :`B` 1.0 :`A` 1.0) %s %s %s %s)' % (name, px, py, font, size))
    draw = '_returnvalue_2 _returnvalue_3 _returnvalue_4 _returnvalue_4 0.0 0.0 1.0 1.0)'
    title = '(* _returnvalue 960.0) (* _returnvalue 150.0)'
    big = '(* (* _returnvalue 1.5) 0.35)'

    def change(code):
        name = hesper_binding(code)
        code = bind_before(code, HESPER_CLASS)
        hesper = '(elif (> (`KismetArrayLibrary.Array_Length` %s) 0)' % name
        if code.count(hesper) != 3:
            raise ValueError('%d Hesper branches, expected 3' % code.count(hesper))
        code = before_form(code, hesper, '(elif %s\n(`self.DrawTextPlate` "MORROW: THE VALLEY BEFORE MORNING" %s %s)\n'
                                         '(`self.DrawText` "MORROW: THE VALLEY BEFORE MORNING" (struct :`R` 0.78 :`G` 0.88 :`B` 1.0 :`A` 1.0) %s %s %s)\n{old})'
                           % (MORROW, title, big, title, font, big), 2)
        code = before_form(code, hesper, '(elif %s\n%s\n{old})' % (MORROW, '\n'.join(labels)), 1)
        code = before_form(code, hesper, '(elif %s\n(`self.DrawTexture` "/Game/UI/T_UI_MapMorrow.T_UI_MapMorrow" %s\n{old})' % (MORROW, draw), 0)
        legend = '"Echo Cache (cyan ray)"'
        if code.count(legend) != 2:
            raise ValueError('legend rows changed')
        return code.replace(legend, '(select `bool` %s :`false` %s :`true` "Frost Cache (cyan ray)")' % (MORROW, legend))
    edit('BP_PhysisHUD', 'PageMap', 'BP_MorrowDirector', change)
    gl.comp('BP_PhysisHUD')


def relic():
    lore = ml.lore
    rows = {row[1]: row for row in lore.MORROW_SCANS}
    chain = ((',satchel,', "Pilgrim's Satchel"), (',aug_hp11,', "The Lull's Heart"), (',aug_katana9,', "The Icecutter's Blade"), (',mw_cache', 'Frost Cache'))

    def change(code):
        opening = '(if (`KismetStringLibrary.Contains` _token ",tuningfork,")'
        at = code.index(opening)
        end = form(code, at)
        head = ''
        for index, (token, title) in enumerate(chain):
            head += '(%s (`KismetStringLibrary.Contains` _token "%s")\n(`self.RelicTagAs` %s %s %s)\n' % (
                'if' if index == 0 else 'elif', token, gl.lit(title), gl.lit(gl.wrap(rows[title][2])), 'true' if rows[title][4] else 'false')
        return code[:at] + head + '(elif' + code[at + 3:end] + ')' * len(chain) + code[end:]
    edit('BP_Relic', 'RelicTag', ',aug_hp11,', change)
    gl.comp('BP_Relic')


def music():
    """PhysisMusicPick plays S_Music_Morrow (after morrow:audio). Part `shared` wrote Morrow's branch with Halcyon's
    music while Morrow had none: it is the first of Halcyon's uses."""
    own = ml.MW + 'S_Music_Morrow'
    if not (ml.ROOT / ('Content' + own[5:] + '.uasset')).exists():
        print('music: S_Music_Morrow is not imported yet')
        gl.FAILED.append('music (no S_Music_Morrow)')
        return
    halcyon = '"/Game/Halcyon/Audio/S_Music_Halcyon.S_Music_Halcyon"'

    def change(code):
        if code.count(halcyon) < 2:
            raise ValueError('%d uses of Halcyon\'s music, expected 2 or more' % code.count(halcyon))
        return code.replace(halcyon, '"%s.S_Music_Morrow"' % own, 1)
    edit('BP_Physis', 'PhysisMusicPick', 'S_Music_Morrow', change)
    gl.comp('BP_Physis')


PARTS = {'shared': shared, 'hud': hud, 'relic': relic, 'music': music}
