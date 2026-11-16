"""Arche branches in the graphs other levels own (parts shared, hud, relic, music of arche_logic.py).

Each edit reads the live graph, changes its text and writes it back. Where the Grove's script replaced literal text,
these edits find a whole form by its opening text and its matching bracket (form()), so a new branch can be put in
front of an existing one without counting the brackets at the far end of a chain: (elif grove ...) becomes
(elif arche ... (elif grove ...)). A graph that already holds an edit's marker is left alone.
"""
import arche_logic as al
import grove_logic as gl

B = gl.B
ARCHE = '(> (`KismetArrayLibrary.Array_Length` _arche) 0)'
BIND = '(bind _arche (`GameplayStatics.GetAllActorsOfClass` "%sBP_ArcheDirector.BP_ArcheDirector_C"))' % B


def form(code, start):
    """The end index (exclusive) of the bracketed form opening at code[start] (strings are skipped)."""
    assert code[start] == '(', code[start:start + 40]
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
    raise ValueError('unclosed form at %d' % start)


def edit(bp, scope, marker, change):
    """Reads bp:scope, applies change(code) -> code (raise to refuse) unless marker is already there, writes it."""
    label = '%s %s' % (bp, scope)
    if gl.DRY:
        print('--- edit', label)
        return
    code = gl.read(bp, scope)
    if code is None:
        gl.FAILED.append(label + ' (not read)')
        return
    if marker in code:
        print(label, 'already has it', flush=True)
        return
    try:
        code = change(code)
    except Exception as error:
        print(label, 'FAILED:', error, flush=True)
        gl.FAILED.append(label)
        return
    ok, _ = gl.call(gl.DSL, 'Write', {'assetPath': B + bp, 'scope': scope, 'dsl': code})
    print(label, 'ok' if ok else 'FAILED', flush=True)
    if not ok:
        gl.FAILED.append(label)
        gl.BROKEN.add(bp)
    if bp not in gl.TOUCHED:
        gl.TOUCHED.append(bp)


def once(code, old, new):
    if code.count(old) != 1:
        raise ValueError('%d matches of %s' % (code.count(old), old[:80]))
    return code.replace(old, new)


def bind_before(code, anchor):
    """Puts the _arche binding on its own line before the line holding `anchor`."""
    at = code.index(anchor)
    line = code.rfind('\n', 0, at) + 1
    indent = code[line:len(code) - len(code[line:].lstrip(' '))]
    return code[:line] + indent + BIND + '\n' + code[line:]


def before_form(code, opening, text, nth=0):
    """Replaces the nth form that opens with `opening` by `text` with {old} standing for that form."""
    at = -1
    for _ in range(nth + 1):
        at = code.index(opening, at + 1)
    end = form(code, at)
    return code[:at] + text.replace('{old}', code[at:end]) + code[end:]


def has(token):
    return '(`KismetStringLibrary.Contains` (`self.Flags`) "%s")' % token


def flag(token):
    return '(select `bool` %s :`true` 1.0)' % has(token)


def shared():
    P = 'BP_Physis'

    def fidelity(code):
        stage = '(or (or %s %s) %s)' % (has(',settle,'), has(',conclave,'), has(',grove,'))
        code = once(code, stage, '(or %s %s)' % (stage, has(',arche,')))
        for last, new in ((',aug_hp7,', ',aug_hp8,'), (',aug_katana5,', ',aug_katana6,'), (',aug_pistol4,', ',aug_pistol5,'),
                          (',aug_defense5,', ',aug_defense6,'), (',aug_agility5,', ',aug_agility6,')):
            code = once(code, flag(last), '(+ %s %s)' % (flag(last), flag(new)))
        return code
    edit(P, 'PhysisFidelity', ',aug_hp8,', fidelity)

    music = al.sound('music')

    def pick(code):
        code = bind_before(code, 'BP_GroveDirector.BP_GroveDirector_C')
        opening = '(if (> (`KismetArrayLibrary.Array_Length` _outactors_2) 0)'
        return before_form(code, opening, '(if %s\n    (bind _archemusic (`GameplayStatics.SpawnSound2D` "%s.%s" (* 0.1 (`self.MusicVol`))))\n'
                                          '    (set `self.MusicComp` _archemusic)\n    (else\n    {old}))' % (ARCHE, music, music.split('/')[-1]))
    edit(P, 'PhysisMusicPick', 'BP_ArcheDirector', pick)

    def load(code):
        opening = '(if (`KismetStringLibrary.Contains` (`%sBP_PhysisSave.Flags` _asbp_physis_save) ",at_grove,")' % B
        at = code.index(opening)
        end = form(code, at)
        old = '(elif' + code[at + 3:end]
        return code[:at] + ('(if (`KismetStringLibrary.Contains` (`%sBP_PhysisSave.Flags` _asbp_physis_save) ",at_arche,")\n'
                            '(`GameplayStatics.OpenLevel` "L_Arche" true "nocine,load")\n%s)' % (B, old)) + code[end:]
    edit(P, 'PhysisLoadGame', ',at_arche,', load)
    edit('BP_MenuHUD', 'MenuContinue', ',at_arche,', load)
    gl.comp('BP_MenuHUD')

    def world(anchor):
        def change(code):
            code = bind_before(code, 'BP_GroveDirector.BP_GroveDirector_C')
            at = code.index(anchor) + len(anchor)
            assert code[at] == '(', code[at:at + 30]
            end = form(code, at)
            return code[:at] + '(select `bool` %s :`false` %s :`true` 5)' % (ARCHE, code[at:end]) + code[end:]
        return change
    # The save's exact spot: world 5 while a BP_ArcheDirector stands in the level.
    edit(P, 'PhysisSaveGame', 'BP_ArcheDirector', world('SpotWorld` (select `bool` (`self.SpotSafe`) :`true` '))
    edit(P, 'PhysisRestore', 'BP_ArcheDirector', world('(== (`%sBP_PhysisSave.SpotWorld` _asbp_physis_save) ' % B))
    gl.comp(P)


MAP_NAMES = (('The Landing', 'Landing'), ('The Hearthold', 'Hearthold'), ('The Ossuary', 'Ossuary'), ('The Great Chasm', 'Chasm'),
             ('The Concourse', 'Concourse'), ('The Cisterns', 'Cisterns'), ('The Middle Tier', 'Middle Tier'), ('The Crystal Garden', 'Garden'),
             ('The Galleries', 'Galleries'), ('The Lens Court', 'Lens Court'))


def hud():
    plan = al.plan
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
    grove = '(elif (> (`KismetArrayLibrary.Array_Length` _outactors_3) 0)'

    def change(code):
        code = bind_before(code, 'BP_GroveDirector.BP_GroveDirector_C')
        if code.count(grove) != 3:
            raise ValueError('%d Grove branches, expected 3' % code.count(grove))
        code = before_form(code, grove, '(elif %s\n(`self.DrawTextPlate` "ARCHE: THE CITY OF THE DESCENT" %s %s)\n'
                                        '(`self.DrawText` "ARCHE: THE CITY OF THE DESCENT" (struct :`R` 1.0 :`G` 0.82 :`B` 0.42 :`A` 1.0) %s %s %s)\n{old})'
                           % (ARCHE, title, big, title, font, big), 2)
        code = before_form(code, grove, '(elif %s\n%s\n{old})' % (ARCHE, '\n'.join(labels)), 1)
        code = before_form(code, grove, '(elif %s\n(`self.DrawTexture` "/Game/UI/T_UI_MapArche.T_UI_MapArche" %s\n{old})' % (ARCHE, draw), 0)
        cache = '(select `bool` %s :`false` "Echo Cache (cyan ray)" :`true` "Geode Cache (blue ray)")' % ARCHE
        if code.count('"Echo Cache (cyan ray)"') != 2:
            raise ValueError('legend rows changed')
        return code.replace('"Echo Cache (cyan ray)"', cache)
    edit('BP_PhysisHUD', 'PageMap', 'BP_ArcheDirector', change)
    gl.comp('BP_PhysisHUD')


def relic():
    lore = al.lore
    rows = {row[1]: row for row in lore.ARCHE_SCANS}
    chain = ((',chime,', "Ilun's Chime"), (',tab', 'A Record Tablet'), (',seedstone,', 'A Seedstone'), (',aug_hp8,', "The Lens's Heart"),
             (',aug_katana6,', "The Namer's Edge"), (',ar_cache', 'Geode Cache'))

    def change(code):
        opening = '(if (`KismetStringLibrary.Contains` _token ",pin,")'
        at = code.index(opening)
        end = form(code, at)
        head = ''
        for index, (token, title) in enumerate(chain):
            head += '(%s (`KismetStringLibrary.Contains` _token "%s")\n(`self.RelicTagAs` %s %s %s)\n' % (
                'if' if index == 0 else 'elif', token, gl.lit(title), gl.lit(gl.wrap(rows[title][2])), 'true' if rows[title][4] else 'false')
        return code[:at] + head + '(elif' + code[at + 3:end] + ')' * len(chain) + code[end:]
    edit('BP_Relic', 'RelicTag', ',aug_hp8,', change)
    gl.comp('BP_Relic')


def music():
    own = al.AA + 'S_Music_Arche'
    if not (al.ROOT / ('Content' + own[5:] + '.uasset')).exists():
        print('music: S_Music_Arche is not imported yet')
        gl.FAILED.append('music (no S_Music_Arche)')
        return
    grove = '"/Game/Grove/Audio/S_Music_Grove.S_Music_Grove"'

    def change(code):
        # Part `shared` wrote Arche's branch with the Grove's music while Arche had none: it is the first of the two.
        if code.count(grove) != 2:
            raise ValueError('%d uses of the Grove\'s music, expected 2' % code.count(grove))
        return code.replace(grove, '"%s.S_Music_Arche"' % own, 1)
    edit('BP_Physis', 'PhysisMusicPick', 'S_Music_Arche', change)
    gl.comp('BP_Physis')


PARTS = {'shared': shared, 'hud': hud, 'relic': relic, 'music': music}
