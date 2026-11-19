"""Halcyon branches in the graphs other levels own (parts shared, hud, relic of halcyon_logic.py).

Each edit reads the live graph, changes its text and writes it back (arche_shared.edit): a Halcyon branch goes in front
of Arche's, found by its whole form (arche_shared.form), so nothing at the far end of a chain is counted. A graph that
already holds an edit's marker is left alone.
"""
import arche_shared as ash
import grove_logic as gl
import halcyon_logic as hl

B = gl.B
HALCYON = '(> (`KismetArrayLibrary.Array_Length` _halcyon) 0)'
BIND = '(bind _halcyon (`GameplayStatics.GetAllActorsOfClass` "%sBP_HalcyonDirector.BP_HalcyonDirector_C"))' % B
ARCHE_CLASS = 'BP_ArcheDirector.BP_ArcheDirector_C'
edit, once, form, before_form, has, flag = ash.edit, ash.once, ash.form, ash.before_form, ash.has, ash.flag


def bind_before(code, anchor):
    at = code.index(anchor)
    line = code.rfind('\n', 0, at) + 1
    indent = code[line:len(code) - len(code[line:].lstrip(' '))]
    return code[:line] + indent + BIND + '\n' + code[line:]


def shared():
    P = 'BP_Physis'

    def fidelity(code):
        stage = '(or (or (or %s %s) %s) %s)' % (has(',settle,'), has(',conclave,'), has(',grove,'), has(',arche,'))
        code = once(code, stage, '(or %s %s)' % (stage, has(',halcyon,')))
        for last, new in ((',aug_hp8,', ',aug_hp9,'), (',aug_katana6,', ',aug_katana7,'), (',aug_pistol5,', ',aug_pistol6,'),
                          (',aug_defense6,', ',aug_defense7,'), (',aug_agility6,', ',aug_agility7,')):
            code = once(code, flag(last), '(+ %s %s)' % (flag(last), flag(new)))
        return code
    edit(P, 'PhysisFidelity', ',aug_hp9,', fidelity)

    music = hl.sound('music')

    def pick(code):
        code = bind_before(code, ARCHE_CLASS)
        opening = '(if (> (`KismetArrayLibrary.Array_Length` _outactors_2) 0)'
        return before_form(code, opening, '(if %s\n    (bind _halcyonmusic (`GameplayStatics.SpawnSound2D` "%s.%s" (* 0.1 (`self.MusicVol`))))\n'
                                          '    (set `self.MusicComp` _halcyonmusic)\n    (else\n    {old}))' % (HALCYON, music, music.split('/')[-1]))
    edit(P, 'PhysisMusicPick', 'BP_HalcyonDirector', pick)

    def load(code):
        opening = '(if (`KismetStringLibrary.Contains` (`%sBP_PhysisSave.Flags` _asbp_physis_save) ",at_arche,")' % B
        at = code.index(opening)
        end = form(code, at)
        old = '(elif' + code[at + 3:end]
        return code[:at] + ('(if (`KismetStringLibrary.Contains` (`%sBP_PhysisSave.Flags` _asbp_physis_save) ",at_halcyon,")\n'
                            '(`GameplayStatics.OpenLevel` "L_Halcyon" true "nocine,load")\n%s)' % (B, old)) + code[end:]
    edit(P, 'PhysisLoadGame', ',at_halcyon,', load)
    edit('BP_MenuHUD', 'MenuContinue', ',at_halcyon,', load)
    gl.comp('BP_MenuHUD')

    def world(anchor):
        def change(code):
            code = bind_before(code, ARCHE_CLASS)
            at = code.index(anchor) + len(anchor)
            assert code[at] == '(', code[at:at + 30]
            end = form(code, at)
            return code[:at] + '(select `bool` %s :`false` %s :`true` 6)' % (HALCYON, code[at:end]) + code[end:]
        return change
    # The save's exact spot: world 6 while a BP_HalcyonDirector stands in the level.
    edit(P, 'PhysisSaveGame', 'BP_HalcyonDirector', world('SpotWorld` (select `bool` (`self.SpotSafe`) :`true` '))
    edit(P, 'PhysisRestore', 'BP_HalcyonDirector', world('(== (`%sBP_PhysisSave.SpotWorld` _asbp_physis_save) ' % B))
    gl.comp(P)


MAP_NAMES = (('The Cliff Garden', 'Cliff Garden'), ('The Signal House', 'Signal House'), ('The Drowned Library', 'Library'), ('The Breach', 'Breach'),
             ('The Market Steps', 'Market Steps'), ('The Drowned Quarter', 'Drowned Quarter'), ('The Cannery Yards', 'Cannery Yards'),
             ('Lighthouse Point', 'Lighthouse'), ('The Mole', 'Mole'), ('Bastion Halcyon', 'Bastion'))


def hud():
    plan = hl.plan
    size = '(* (* _returnvalue 0.85) 0.35)'
    font = '"/Game/UI/F_Physis.F_Physis"'
    labels = []
    for region, name in MAP_NAMES:
        x, y = plan.REGIONS[region][:2]
        u, v = (y + plan.MAP_HALF) / (2 * plan.MAP_HALF), (plan.MAP_HALF - x) / (2 * plan.MAP_HALF)
        px = '(- (+ _returnvalue_2 (* %.5f _returnvalue_4)) (* _returnvalue %.1f))' % (u, len(name) * 4.4)
        py = '(- (+ _returnvalue_3 (* %.5f _returnvalue_4)) (* _returnvalue 30.0))' % v
        labels.append('(`self.DrawTextPlate` "%s" %s %s %s)' % (name, px, py, size))
        labels.append('(`self.DrawText` "%s" (struct :`R` 1.0 :`G` 0.92 :`B` 0.78 :`A` 1.0) %s %s %s %s)' % (name, px, py, font, size))
    draw = '_returnvalue_2 _returnvalue_3 _returnvalue_4 _returnvalue_4 0.0 0.0 1.0 1.0)'
    title = '(* _returnvalue 960.0) (* _returnvalue 150.0)'
    big = '(* (* _returnvalue 1.5) 0.35)'

    def change(code):
        code = bind_before(code, ARCHE_CLASS)
        # The Arche director's actors are the third binding of the page; its branch is (elif (> ... _outactors_3) 0).
        arche = '(elif (> (`KismetArrayLibrary.Array_Length` _outactors_3) 0)'
        if code.count(arche) != 3:
            raise ValueError('%d Arche branches, expected 3' % code.count(arche))
        code = before_form(code, arche, '(elif %s\n(`self.DrawTextPlate` "HALCYON: THE DROWNED HARBOUR" %s %s)\n'
                                        '(`self.DrawText` "HALCYON: THE DROWNED HARBOUR" (struct :`R` 1.0 :`G` 0.82 :`B` 0.42 :`A` 1.0) %s %s %s)\n{old})'
                           % (HALCYON, title, big, title, font, big), 2)
        code = before_form(code, arche, '(elif %s\n%s\n{old})' % (HALCYON, '\n'.join(labels)), 1)
        code = before_form(code, arche, '(elif %s\n(`self.DrawTexture` "/Game/UI/T_UI_MapHalcyon.T_UI_MapHalcyon" %s\n{old})' % (HALCYON, draw), 0)
        legend = '"Echo Cache (cyan ray)"'
        if code.count(legend) != 2:
            raise ValueError('legend rows changed')
        return code.replace(legend, '(select `bool` %s :`false` %s :`true` "Tide Cache (blue ray)")' % (HALCYON, legend))
    edit('BP_PhysisHUD', 'PageMap', 'BP_HalcyonDirector', change)
    gl.comp('BP_PhysisHUD')


def relic():
    lore = hl.lore
    rows = {row[1]: row for row in lore.HALCYON_SCANS}
    chain = ((',logbook,', "Ledger's Logbook"), (',aug_hp9,', "The Undertow's Heart"), (',aug_katana7,', "The Reader's Knife"), (',ha_cache', 'Tide Cache'))

    def change(code):
        opening = '(if (`KismetStringLibrary.Contains` _token ",chime,")'
        at = code.index(opening)
        end = form(code, at)
        head = ''
        for index, (token, title) in enumerate(chain):
            head += '(%s (`KismetStringLibrary.Contains` _token "%s")\n(`self.RelicTagAs` %s %s %s)\n' % (
                'if' if index == 0 else 'elif', token, gl.lit(title), gl.lit(gl.wrap(rows[title][2])), 'true' if rows[title][4] else 'false')
        return code[:at] + head + '(elif' + code[at + 3:end] + ')' * len(chain) + code[end:]
    edit('BP_Relic', 'RelicTag', ',aug_hp9,', change)
    gl.comp('BP_Relic')


PARTS = {'shared': shared, 'hud': hud, 'relic': relic}


def music():
    """PhysisMusicPick plays S_Music_Halcyon (after halcyon:audio). Part `shared` wrote Halcyon's branch with the
    Grove's music while Halcyon had none: it is the first of the Grove's two uses."""
    own = hl.HA + 'S_Music_Halcyon'
    if not (hl.ROOT / ('Content' + own[5:] + '.uasset')).exists():
        print('music: S_Music_Halcyon is not imported yet')
        gl.FAILED.append('music (no S_Music_Halcyon)')
        return
    grove = '"/Game/Grove/Audio/S_Music_Grove.S_Music_Grove"'

    def change(code):
        if code.count(grove) != 2:
            raise ValueError('%d uses of the Grove\'s music, expected 2' % code.count(grove))
        return code.replace(grove, '"%s.S_Music_Halcyon"' % own, 1)
    edit('BP_Physis', 'PhysisMusicPick', 'S_Music_Halcyon', change)
    gl.comp('BP_Physis')


PARTS['music'] = music
