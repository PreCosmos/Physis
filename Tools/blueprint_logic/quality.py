# Graphics Quality lock (Author, 2026-11-04). The pause menu's Quality levels unlock with the fidelity ladder:
#   stage 0 (new game, the station before the boss)       Low only
#   stage 1 (Mecha Breacher down, and anywhere in the Center)  Medium too
#   stage 2 and up (Settle learned)                         High too
# Quality is the level in use, which the menu row shows. QualityWanted is the player's choice, kept in the settings
# slot's Quality field. Picking the highest unlocked level stores 2 (High), so the game switches up by itself as
# levels unlock (author's choice); a lower pick stays. The level in use is the lower of the two, so loading a save
# or arriving in the Center lowers a saved choice that is above the current stage.
# Low and Medium also lower r.DetailMode the way the engine's EffectsQuality levels do (BaseScalability.ini:
# EffectsQuality 1 and 2 -> 1, 3 -> 3), never above the stage's own ladder value. Leaving play puts back the
# console values PhysisSettingsLoad captured at level start, before any of these were applied, so the editor returns
# to its own launch settings (the usual -ExecCmds use sg 2 to save memory) and menus are never left degraded. Without
# a capture it falls back to full detail and Epic quality. (2026-11-05: it used to force Epic, raising the editor.)
# This script owns PhysisFidelityApply and PhysisFidelityReset (moved here from fidelity.py) and pause.py's
# PhysisSetting, PhysisSettingsApply, PhysisSettingsLoad and PhysisSettingsSave. rebuild2.sh runs it right after
# fidelity.py. PhysisFidelity (which stage) belongs to Tools/blueprint_logic/center_overrides.py.
import re
import sys
sys.path.insert(0, 'Tools')
# Not named S: combat.py's helper head (exec'd below) rebinds S to BP_ScanTarget's path.
SCRATCH = '/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/'
pz = open(SCRATCH + 'pause.py').read()
exec(open(SCRATCH + 'combat.py').read().split("ANIM=")[0])
exec(re.search(r'^SETS=.*$', pz, re.M).group(0))  # the settings slot's fields, as pause.py saves them
exec(re.search(r'^STEP=.*$', pz, re.M).group(0))
var(P, 'QualityWanted', 'int')
var(P, 'QualityCap', 'int')
# Divine Parry is an assist, off by default (author, 2026-11-09: "Please remove the automatic parrying from being the
# default. It makes the fighting extremely easy."). Settings row 9, Assist: Divine Parry, turns it on; it is kept in
# the settings slot (pause.py SETS). A settings file from before has no AutoParry field and loads it as off.
# PhysisHurt (center_overrides.py, part augments) parries an unparried hit for 5 Divinity only while it is on.
var(P, 'AutoParry', 'bool')
var(B + 'BP_PhysisSave.BP_PhysisSave', 'AutoParry', 'bool')
comp(B + 'BP_PhysisSave.BP_PhysisSave')  # so the save and load graphs below can name its new field
# Console values from before play: captured once per level start, put back at End Play.
START = (('StartShadow', 'sg.ShadowQuality', 'Int'), ('StartEffects', 'sg.EffectsQuality', 'Int'), ('StartPost', 'sg.PostProcessQuality', 'Int'),
         ('StartTexture', 'sg.TextureQuality', 'Int'), ('StartDetail', 'r.DetailMode', 'Int'), ('StartForceLOD', 'r.ForceLOD', 'Int'),
         ('StartSkelBias', 'r.SkeletalMeshLODBias', 'Int'), ('StartMipBias', 'r.MipMapLODBias', 'Float'), ('StartView', 'r.ViewDistanceScale', 'Float'))
var(P, 'StartCaptured', 'bool')
for name, _, kind in START:
    var(P, name, 'int' if kind == 'Int' else 'float')
for name in ('PhysisSettingsApply', 'PhysisSettingsSave', 'PhysisSettingsLoad', 'PhysisFidelityReset'):
    shell(P, name)
shell(P, 'PhysisSetting', [('Row', 'int'), ('Delta', 'float')])
shell(P, 'PhysisFidelityApply', [('Stage', 'int')])

NOW_LEVEL = '(+ (Variables|Default|GetQuality) 1)'  # menu Low/Medium/High = engine scalability 1/2/3


def pick(values):
    a, b, c, d = values
    return '(select (== Stage 0) %s (select (== Stage 1) %s (select (== Stage 2) %s %s)))' % (a, b, c, d)


def console(name, value, kind='Integer'):
    return '(Development|ExecuteConsoleCommand :Command (Utilities|String|Append :A "%s " :B (Utilities|String|ToString(%s) %s)))' % (name, kind, value)


def fixed(command):
    return '(Development|ExecuteConsoleCommand :Command "%s")' % command


GROUPS = ('sg.ShadowQuality', 'sg.EffectsQuality', 'sg.PostProcessQuality', 'sg.TextureQuality')
LADDER_DETAIL = pick(('0', '1', '3', '3'))
MENU_DETAIL = '(select (== (Variables|Default|GetQuality) 2) 3 1)'

fn(P, 'PhysisFidelityApply', """(fn PhysisFidelityApply (Stage)
  (Variables|Default|SetQualityCap (select (> Stage 2) 2 Stage))
  (Variables|Default|SetQuality (select (< (Variables|Default|GetQualityWanted) (Variables|Default|GetQualityCap)) (Variables|Default|GetQualityWanted) (Variables|Default|GetQualityCap)))
  %s
  %s
  %s
  %s
  %s
  %s
  %s
  %s
  %s)""" % (console('r.ForceLOD', pick(('2', '1', '-1', '-1'))), console('r.SkeletalMeshLODBias', pick(('2', '1', '0', '0'))),
            console('r.MipMapLODBias', pick(('2', '1', '0', '0'))), console('r.ViewDistanceScale', pick(('0.6', '0.8', '1.0', '1.4')), 'Float'),
            console(GROUPS[0], NOW_LEVEL), console(GROUPS[1], NOW_LEVEL), console(GROUPS[2], NOW_LEVEL), console(GROUPS[3], NOW_LEVEL),
            console('r.DetailMode', '(select (< %s %s) %s %s)' % (LADDER_DETAIL, MENU_DETAIL, LADDER_DETAIL, MENU_DETAIL))))

CAPTURE = '\n    '.join('(Variables|Default|Set%s (Development|GetConsoleVariable%sValue :VariableName "%s"))' % (v, k, c) for v, c, k in START)
RESTORE = '\n    '.join(console(c, '(Variables|Default|Get%s)' % v, 'Integer' if k == 'Int' else 'Float') for v, c, k in START)
fn(P, 'PhysisFidelityReset', """(fn PhysisFidelityReset ()
  (Variables|Default|SetFidelityApplied 0)
  (if (Variables|Default|GetStartCaptured)
    """ + RESTORE + """
    (else
      (CallFunction|PhysisFidelityApply :Stage 2)
      %s
      %s
      %s
      %s
      %s)))""" % tuple(fixed(g + ' 3') for g in GROUPS + ('r.DetailMode',)))

# Graphics follow the stage, so they are applied through PhysisFidelityApply once the HUD has set the stage.
fn(P, 'PhysisSettingsApply', """(fn PhysisSettingsApply ()
  (bind pc (Game|GetPlayerController 0))
  (bind gain (/ (Variables|Default|GetLookSens) 5.0))
  (PlayerController|SetDeprecatedInputYawScale :self pc :NewValue (* (Variables|Default|GetBaseYaw) gain))
  (PlayerController|SetDeprecatedInputPitchScale :self pc :NewValue (* (* (Variables|Default|GetBasePitch) gain) (select (Variables|Default|GetInvertLook) -1.0 1.0)))
  (if (> (Variables|Default|GetFidelityApplied) 0)
    (CallFunction|PhysisFidelityApply :Stage (- (Variables|Default|GetFidelityApplied) 1)))
  (Utilities|IsValid (Variables|Default|GetMusicComp)
    (:"Is Valid" (Class|AudioComponent|SetVolumeMultiplier :self (Variables|Default|GetMusicComp) :VolumeMultiplier (* 0.1 (Variables|Default|GetMusicVol))))
    (:"Is Not Valid")))""")

SAVE = '(SaveGame|CreateSaveGameObject :SaveGameClass "/Game/Characters/Physis/Blueprints/BP_PhysisSave.BP_PhysisSave_C")'
mine = lambda n: 'QualityWanted' if n == 'Quality' else n
PUT = '\n      '.join('(Class|BPPhysisSave|Set%s :self saved :%s (Variables|Default|Get%s))' % (n, n, mine(n)) for n, _ in SETS)
GET = '\n        '.join('(Variables|Default|Set%s (Class|BPPhysisSave|Get%s :self saved))' % (mine(n), n) for n, _ in SETS)
assert 'GetQualityWanted' in PUT and 'SetQualityWanted (Class|BPPhysisSave|GetQuality' in GET

fn(P, 'PhysisSettingsSave', """(fn PhysisSettingsSave ()
  (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object """ + SAVE + """)
    (:then
      """ + PUT + """
      (SaveGame|SaveGametoSlot :SaveGameObject saved :SlotName "PhysisSettings" :UserIndex 0))
    (:CastFailed)))""")

fn(P, 'PhysisSettingsLoad', """(fn PhysisSettingsLoad ()
  (if (not (Variables|Default|GetStartCaptured))
    (Variables|Default|SetStartCaptured true)
    """ + CAPTURE + """)
  (bind pc (Game|GetPlayerController 0))
  (Variables|Default|SetBaseYaw (PlayerController|GetDeprecatedInputYawScale :self pc))
  (Variables|Default|SetBasePitch (PlayerController|GetDeprecatedInputPitchScale :self pc))
  (Variables|Default|SetMusicVol 6.0)
  (Variables|Default|SetVoiceVol 10.0)
  (Variables|Default|SetLookSens 5.0)
  (Variables|Default|SetShakeOn true)
  (Variables|Default|SetSlowOn true)
  (Variables|Default|SetAutoParry false)
  (Variables|Default|SetQualityWanted 2)
  (if (SaveGame|DoesSaveGameExist :SlotName "PhysisSettings" :UserIndex 0)
    (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object (SaveGame|LoadGamefromSlot :SlotName "PhysisSettings" :UserIndex 0))
      (:then
        """ + GET + """
        (CallFunction|PhysisSettingsApply))
      (:CastFailed (CallFunction|PhysisSettingsApply)))
    (else (CallFunction|PhysisSettingsApply))))""")
# A cast with :then/:CastFailed ends the exec flow (blueprint_dsl.py: "multi-exec terminates the enclosing exec
# flow"), so a call written after this if would only run on Branch.False. Each path calls Apply itself.

# Row 2 moves between the unlocked levels only; above them the menu says why it stops.
LOCKED = 'Higher quality unlocks as the story goes on.'
AUTO_PARRY_NOTE = 'A hit you do not parry is parried for you, for 5 Divinity.'
fn(P, 'PhysisSetting', """(fn PhysisSetting (Row Delta)
  (if (== Row 2)
    (Variables|Default|SetMenuNote "")
    (bind wanted (+ (Variables|Default|GetQuality) (select (> Delta 0.0) 1 -1)))
    (if (> wanted (Variables|Default|GetQualityCap))
      (if (< (Variables|Default|GetQualityCap) 2)
        (Variables|Default|SetMenuNote \"""" + LOCKED + """\"))
      (else
        (if (>= wanted 0)
          (Variables|Default|SetQualityWanted (select (== wanted (Variables|Default|GetQualityCap)) 2 wanted))))))
  (if (== Row 3) """ + STEP('MusicVol', '0.0', '10.0') + """)
  (if (== Row 4) """ + STEP('VoiceVol', '0.0', '10.0') + """)
  (if (== Row 5) (Variables|Default|SetShakeOn (not (Variables|Default|GetShakeOn))))
  (if (== Row 6) (Variables|Default|SetSlowOn (not (Variables|Default|GetSlowOn))))
  (if (== Row 7) """ + STEP('LookSens', '1.0', '10.0') + """)
  (if (== Row 8) (Variables|Default|SetInvertLook (not (Variables|Default|GetInvertLook))))
  (if (== Row 9)
    (Variables|Default|SetAutoParry (not (Variables|Default|GetAutoParry)))
    (Variables|Default|SetMenuNote (select (Variables|Default|GetAutoParry) \"""" + AUTO_PARRY_NOTE + """\" "")))
  (CallFunction|PhysisSettingsApply)
  (CallFunction|PhysisSettingsSave))""")
comp(P)
