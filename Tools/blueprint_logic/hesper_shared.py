"""Hesper branches in the graphs other levels own (parts shared, hud, relic, bolt, music of hesper_logic.py).

Each edit reads the live graph, changes its text and writes it back (arche_shared.edit): a Hesper branch goes in front
of Halcyon's, found by its whole form (arche_shared.form), so nothing at the far end of a chain is counted. A graph that
already holds an edit's marker is left alone. The canonical read renames bindings, so Halcyon's director is found by
its class path and its branch by the binding the read gives it (halcyon_binding()).
"""
import re

import arche_shared as ash
import grove_logic as gl
import hesper_logic as sl

B = gl.B
HESPER = '(> (`KismetArrayLibrary.Array_Length` _hesper) 0)'
BIND = '(bind _hesper (`GameplayStatics.GetAllActorsOfClass` "%sBP_HesperDirector.BP_HesperDirector_C"))' % B
HALCYON_CLASS = 'BP_HalcyonDirector.BP_HalcyonDirector_C'
edit, once, form, before_form, has, flag = ash.edit, ash.once, ash.form, ash.before_form, ash.has, ash.flag


def bind_before(code, anchor):
    at = code.index(anchor)
    line = code.rfind('\n', 0, at) + 1
    indent = code[line:len(code) - len(code[line:].lstrip(' '))]
    return code[:line] + indent + BIND + '\n' + code[line:]


def halcyon_binding(code):
    """The name the canonical read gave Halcyon's director list (e.g. _outactors_3)."""
    found = re.search(r'\(bind (\S+) \(`GameplayStatics\.GetAllActorsOfClass` "[^"]*%s"\)\)' % re.escape(HALCYON_CLASS), code)
    if not found:
        raise ValueError('no Halcyon director binding')
    return found.group(1)


def shared():
    P = 'BP_Physis'

    def fidelity(code):
        stage = '(or (or (or (or %s %s) %s) %s) %s)' % (has(',settle,'), has(',conclave,'), has(',grove,'), has(',arche,'), has(',halcyon,'))
        code = once(code, stage, '(or %s %s)' % (stage, has(',hesper,')))
        for last, new in ((',aug_hp9,', ',aug_hp10,'), (',aug_katana7,', ',aug_katana8,'), (',aug_pistol6,', ',aug_pistol7,'),
                          (',aug_defense7,', ',aug_defense8,'), (',aug_agility7,', ',aug_agility8,')):
            code = once(code, flag(last), '(+ %s %s)' % (flag(last), flag(new)))
        return code
    edit(P, 'PhysisFidelity', ',aug_hp10,', fidelity)

    music = sl.sound('music')

    def pick(code):
        name = halcyon_binding(code)
        code = bind_before(code, HALCYON_CLASS)
        opening = '(if (> (`KismetArrayLibrary.Array_Length` %s) 0)' % name
        return before_form(code, opening, '(if %s\n    (bind _hespermusic (`GameplayStatics.SpawnSound2D` "%s.%s" (* 0.1 (`self.MusicVol`))))\n'
                                          '    (set `self.MusicComp` _hespermusic)\n    (else\n    {old}))' % (HESPER, music, music.split('/')[-1]))
    edit(P, 'PhysisMusicPick', 'BP_HesperDirector', pick)

    def load(code):
        opening = '(if (`KismetStringLibrary.Contains` (`%sBP_PhysisSave.Flags` _asbp_physis_save) ",at_halcyon,")' % B
        at = code.index(opening)
        end = form(code, at)
        old = '(elif' + code[at + 3:end]
        return code[:at] + ('(if (`KismetStringLibrary.Contains` (`%sBP_PhysisSave.Flags` _asbp_physis_save) ",at_hesper,")\n'
                            '(`GameplayStatics.OpenLevel` "L_Hesper" true "nocine,load")\n%s)' % (B, old)) + code[end:]
    edit(P, 'PhysisLoadGame', ',at_hesper,', load)
    edit('BP_MenuHUD', 'MenuContinue', ',at_hesper,', load)
    gl.comp('BP_MenuHUD')

    def world(anchor):
        def change(code):
            code = bind_before(code, HALCYON_CLASS)
            at = code.index(anchor) + len(anchor)
            assert code[at] == '(', code[at:at + 30]
            end = form(code, at)
            return code[:at] + '(select `bool` %s :`false` %s :`true` 7)' % (HESPER, code[at:end]) + code[end:]
        return change
    # The save's exact spot: world 7 while a BP_HesperDirector stands in the level.
    edit(P, 'PhysisSaveGame', 'BP_HesperDirector', world('SpotWorld` (select `bool` (`self.SpotSafe`) :`true` '))
    edit(P, 'PhysisRestore', 'BP_HesperDirector', world('(== (`%sBP_PhysisSave.SpotWorld` _asbp_physis_save) ' % B))
    gl.comp(P)


MAP_NAMES = (('The Sunward Stair', 'Sunward Stair'), ('The House of Listeners', 'House of Listeners'), ('The Hall of Withheld Votes', 'Hall'),
             ('The Choir Wall', 'Choir Wall'), ('The Bell Market', 'Bell Market'), ('The Reed Terraces', 'Reed Terraces'),
             ('The Amber Galleries', 'Amber Galleries'), ('The Watch Spire', 'Watch Spire'), ('The Nave', 'Nave'), ('The Concord', 'Concord'))


def hud():
    plan = sl.plan
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
        name = halcyon_binding(code)
        code = bind_before(code, HALCYON_CLASS)
        halcyon = '(elif (> (`KismetArrayLibrary.Array_Length` %s) 0)' % name
        if code.count(halcyon) != 3:
            raise ValueError('%d Halcyon branches, expected 3' % code.count(halcyon))
        code = before_form(code, halcyon, '(elif %s\n(`self.DrawTextPlate` "HESPER: THE CITY OF ONE VOICE" %s %s)\n'
                                          '(`self.DrawText` "HESPER: THE CITY OF ONE VOICE" (struct :`R` 1.0 :`G` 0.78 :`B` 0.40 :`A` 1.0) %s %s %s)\n{old})'
                           % (HESPER, title, big, title, font, big), 2)
        code = before_form(code, halcyon, '(elif %s\n%s\n{old})' % (HESPER, '\n'.join(labels)), 1)
        code = before_form(code, halcyon, '(elif %s\n(`self.DrawTexture` "/Game/UI/T_UI_MapHesper.T_UI_MapHesper" %s\n{old})' % (HESPER, draw), 0)
        legend = '"Echo Cache (cyan ray)"'
        if code.count(legend) != 2:
            raise ValueError('legend rows changed')
        return code.replace(legend, '(select `bool` %s :`false` %s :`true` "Dusk Cache (gold ray)")' % (HESPER, legend))
    edit('BP_PhysisHUD', 'PageMap', 'BP_HesperDirector', change)
    gl.comp('BP_PhysisHUD')


def relic():
    lore = sl.lore
    rows = {row[1]: row for row in lore.HESPER_SCANS}
    chain = ((',tuningfork,', "Tavor's Fork"), (',reedflute,', "Anwe's Flute"), (',aug_hp10,', "The Concord's Heart"), (',aug_katana8,', "The Dissenter's Blade"),
             (',hs_cache', 'Dusk Cache'))

    def change(code):
        opening = '(if (`KismetStringLibrary.Contains` _token ",logbook,")'
        at = code.index(opening)
        end = form(code, at)
        head = ''
        for index, (token, title) in enumerate(chain):
            head += '(%s (`KismetStringLibrary.Contains` _token "%s")\n(`self.RelicTagAs` %s %s %s)\n' % (
                'if' if index == 0 else 'elif', token, gl.lit(title), gl.lit(gl.wrap(rows[title][2])), 'true' if rows[title][4] else 'false')
        return code[:at] + head + '(elif' + code[at + 3:end] + ')' * len(chain) + code[end:]
    edit('BP_Relic', 'RelicTag', ',aug_hp10,', change)
    gl.comp('BP_Relic')


def bolt():
    """BP_EnemyBolt: inside her note (9 m, while BP_Physis.DissonanceUntil lasts) a bolt falters: a spark, and it is
    gone before it reaches her. Everywhere, not only in Hesper: the note is hers."""
    P = '%sBP_Physis' % B
    near = '(and (> (`%s.DissonanceUntil` _asbp_physis) (`KismetSystemLibrary.GetGameTimeInSeconds`)) (< (`self.GetDistanceTo` _asbp_physis) %.1f))' % (P, sl.REACH)
    spark = ('(`|SpawnActorFromClass` "%sBP_Spark.BP_Spark_C" (`KismetMathLibrary.MakeTransform` (`self.K2_GetActorLocation`) (`KismetMathLibrary.MakeRotator` 0.0) '
             '(`KismetMathLibrary.MakeVector` 1.0 1.0 1.0)) "AlwaysSpawn" "MultiplyWithRoot" null null)') % B

    def change(code):
        opening = '(if (< (`self.GetDistanceTo` _asbp_physis) 105.0)'
        return before_form(code, opening, '(if %s\n%s\n(`self.K2_DestroyActor`)\n(else\n{old}))' % (near, spark))
    edit('BP_EnemyBolt', 'EventGraph', 'DissonanceUntil', change)
    gl.comp('BP_EnemyBolt')


def music():
    """PhysisMusicPick plays S_Music_Hesper (after hesper:audio). Part `shared` wrote Hesper's branch with Arche's
    music while Hesper had none: it is the first of Arche's two uses."""
    own = sl.HS + 'S_Music_Hesper'
    if not (sl.ROOT / ('Content' + own[5:] + '.uasset')).exists():
        print('music: S_Music_Hesper is not imported yet')
        gl.FAILED.append('music (no S_Music_Hesper)')
        return
    arche = '"/Game/Arche/Audio/S_Music_Arche.S_Music_Arche"'

    def change(code):
        if code.count(arche) != 2:
            raise ValueError('%d uses of Arche\'s music, expected 2' % code.count(arche))
        return code.replace(arche, '"%s.S_Music_Hesper"' % own, 1)
    edit('BP_Physis', 'PhysisMusicPick', 'S_Music_Hesper', change)
    gl.comp('BP_Physis')


PARTS = {'shared': shared, 'hud': hud, 'relic': relic, 'bolt': bolt, 'music': music}
