import sys,re
sys.path.insert(0,'Tools')
hf=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/hudfont.py').read()
exec(hf[:hf.index("var(H,'LineY','float')")])
A='/Game/Audio/'
ACT=lambda n:'"%s%s.%s_C"'%(B,n,n)
ALL=lambda n:'(Actor|GetAllActorsOfClass :ActorClass %s)'%ACT(n)
DR='BP_TrainingDrone'
C=B+'BP_Physis.BP_Physis'
EN,CK,SW,PICK,LV,SV=[B+n+'.'+n for n in ('BP_Encounter','BP_Checkpoint','BP_Switch','BP_Pickup','BP_LogVoice','BP_PhysisSave')]
call('add_object_variable',{'blueprint':{'refPath':LV},'name':'Image','object_class':{'refPath':'/Script/Engine.Texture2D'}},True)
call('set_variable_instance_editable',{'blueprint':{'refPath':LV},'variable_name':'Image','instance_editable':True})
call('add_object_variable',{'blueprint':{'refPath':LV},'name':'Voice','object_class':{'refPath':'/Script/Engine.SoundBase'}},True)
call('set_variable_instance_editable',{'blueprint':{'refPath':LV},'variable_name':'Voice','instance_editable':True})
var(LV,'Title','string',True);comp(LV)
var(EN,'NextGoal','string',True);var(PICK,'Token','string',True)
call('add_object_variable',{'blueprint':{'refPath':P},'name':'VoiceComp','object_class':{'refPath':'/Script/Engine.AudioComponent'}},True)
FIELDS=(('Flags','string'),('Objective','string'),('LogData','string'),('QuestDone','string'),('Fuses','int'),('SkillLevel','int'),('SeqStep','int'),('PhysisHealth','float'),('Divinity','float'),('GunAmmo','int'),('GunReserve','int'),('CheckX','float'),('CheckY','float'),('CheckZ','float'),('LevelTime','float'))
SETS=(('AchStation','bool'),('AchSwift','bool'),('MusicVol','float'),('VoiceVol','float'),('LookSens','float'),('ShakeOn','bool'),('SlowOn','bool'),('InvertLook','bool'),('Quality','int'),('AutoParry','bool'))
for n,k in (('BaseYaw','float'),('BasePitch','float'),('QuestDone','string'),('MenuPage','int'),('MenuRow','int'),('MenuTitle','string'),('MenuNote','string'))+SETS:var(P,n,k)
for n,k in FIELDS+SETS:var(SV,n,k)
comp(SV)
for name,ps in (('PhysisDuck',()),('PhysisVoiceStop',()),('PhysisNarrate',[('Title','string')]),('PhysisMenu',[('Page','int')]),('PhysisPause',()),('PhysisQuest',[('Goal','string')]),('PhysisSaveGame',()),('PhysisLoadGame',()),('PhysisRestore',()),('PhysisSettingsSave',()),('PhysisSettingsLoad',()),('PhysisSettingsApply',()),('PhysisSetting',[('Row','int'),('Delta','float')])):
    shell(P,name,ps)
SAVE='(SaveGame|CreateSaveGameObject :SaveGameClass %s)'%ACT('BP_PhysisSave')
fn(P,'PhysisDuck',"""(fn PhysisDuck ()
  (Utilities|IsValid (Variables|Default|GetMusicComp)
    (:"Is Valid"
      (Utilities|IsValid (Variables|Default|GetVoiceComp)
        (:"Is Valid" (Class|AudioComponent|SetVolumeMultiplier :self (Variables|Default|GetMusicComp) :VolumeMultiplier (* (* 0.1 (Variables|Default|GetMusicVol)) (select (Audio|Components|Audio|IsPlaying :self (Variables|Default|GetVoiceComp)) 0.3 1.0))))
        (:"Is Not Valid")))
    (:"Is Not Valid")))""")
fn(P,'PhysisVoiceStop',"""(fn PhysisVoiceStop ()
  (Utilities|IsValid (Variables|Default|GetVoiceComp)
    (:"Is Valid" (Audio|Components|Audio|Stop :self (Variables|Default|GetVoiceComp)))
    (:"Is Not Valid")))""")
fn(P,'PhysisNarrate',"""(fn PhysisNarrate (Title)
  (CallFunction|PhysisVoiceStop)
  (for found """+ALL('BP_LogVoice')+"""
    (bind bank (Utilities|Casting|CastToBP_LogVoice :Object found)
      (:then
        (if (Utilities|String|EqualExactly(String) :A (Class|BPLogVoice|GetTitle :self bank) :B Title)
          (bind speaker (Audio|CreateSound2D :Sound (Class|BPLogVoice|GetVoice :self bank) :VolumeMultiplier (/ (Variables|Default|GetVoiceVol) 8.0)))
          (Variables|Default|SetVoiceComp speaker)
          (Class|AudioComponent|SetIsUISound :self speaker :bIsUISound true)
          (Audio|Components|Audio|Play :self speaker :StartTime 0.0)))
      (:CastFailed))))""")
fn(P,'PhysisMenu',"""(fn PhysisMenu (Page)
  (if (not (Variables|Default|GetCinematic))
    (Variables|Default|SetLogOpen (not (Variables|Default|GetLogOpen)))
    (Variables|Default|SetMenuPage Page)
    (Variables|Default|SetMenuRow 0)
    (Variables|Default|SetMenuTitle "")
    (Variables|Default|SetMenuNote "")
    (CallFunction|PhysisVoiceStop)
    (Game|SetGamePaused :bPaused (Variables|Default|GetLogOpen))))""")
fn(P,'PhysisLogbook',"""(fn PhysisLogbook ()
  (CallFunction|PhysisMenu :Page 0))""")
fn(P,'PhysisPause',"""(fn PhysisPause ()
  (CallFunction|PhysisMenu :Page 3))""")
fn(P,'PhysisQuest',"""(fn PhysisQuest (Goal)
  (if (and (not (Utilities|String|EqualExactly(String) :A (Variables|Default|GetObjective) :B "")) (not (Utilities|String|EqualExactly(String) :A (Variables|Default|GetObjective) :B Goal)))
    (Variables|Default|SetQuestDone (Utilities|String|Append :A (Variables|Default|GetQuestDone) :B (Utilities|String|Append :A (Variables|Default|GetObjective) :B "@"))))
  (Variables|Default|SetObjective Goal))""")
def put(names): return '\n'.join('(Class|BPPhysisSave|Set%s :self saved :%s (Variables|Default|Get%s))'%(n,n,n) for n,_ in names)
def get(names): return '\n'.join('(Variables|Default|Set%s (Class|BPPhysisSave|Get%s :self saved))'%(n,n) for n,_ in names)
fn(P,'PhysisSaveGame',"""(fn PhysisSaveGame ()
  (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object """+SAVE+""")
    (:then
      """+put(FIELDS)+"""
      (SaveGame|SaveGametoSlot :SaveGameObject saved :SlotName "Physis" :UserIndex 0)
      (Variables|Default|SetMenuNote "Game saved."))
    (:CastFailed)))""")
fn(P,'PhysisLoadGame',"""(fn PhysisLoadGame ()
  (if (SaveGame|DoesSaveGameExist :SlotName "Physis" :UserIndex 0)
    (Game|OpenLevel(byName) :LevelName "L_BattleStation" :Options "nocine,load")
    (else
      (Variables|Default|SetMenuNote "No saved game yet."))))""")
fn(P,'PhysisSettingsSave',"""(fn PhysisSettingsSave ()
  (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object """+SAVE+""")
    (:then
      """+put(SETS)+"""
      (SaveGame|SaveGametoSlot :SaveGameObject saved :SlotName "PhysisSettings" :UserIndex 0))
    (:CastFailed)))""")
fn(P,'PhysisSettingsLoad',"""(fn PhysisSettingsLoad ()
  (bind pc (Game|GetPlayerController 0))
  (Variables|Default|SetBaseYaw (PlayerController|GetDeprecatedInputYawScale :self pc))
  (Variables|Default|SetBasePitch (PlayerController|GetDeprecatedInputPitchScale :self pc))
  (Variables|Default|SetMusicVol 6.0)
  (Variables|Default|SetVoiceVol 10.0)
  (Variables|Default|SetLookSens 5.0)
  (Variables|Default|SetShakeOn true)
  (Variables|Default|SetSlowOn true)
  (Variables|Default|SetQuality 2)
  (if (SaveGame|DoesSaveGameExist :SlotName "PhysisSettings" :UserIndex 0)
    (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object (SaveGame|LoadGamefromSlot :SlotName "PhysisSettings" :UserIndex 0))
      (:then
        """+get(SETS)+"""
        (CallFunction|PhysisSettingsApply))
      (:CastFailed))))""")
CMD=lambda c:'(Development|ExecuteConsoleCommand :Command (Utilities|String|Append :A "%s " :B (Utilities|String|ToString(Integer) level)))'%c
fn(P,'PhysisSettingsApply',"""(fn PhysisSettingsApply ()
  (bind level (+ (Variables|Default|GetQuality) 1))
  (bind pc (Game|GetPlayerController 0))
  (bind gain (/ (Variables|Default|GetLookSens) 5.0))
  (PlayerController|SetDeprecatedInputYawScale :self pc :NewValue (* (Variables|Default|GetBaseYaw) gain))
  (PlayerController|SetDeprecatedInputPitchScale :self pc :NewValue (* (* (Variables|Default|GetBasePitch) gain) (select (Variables|Default|GetInvertLook) -1.0 1.0)))
  """+CMD('sg.ShadowQuality')+CMD('sg.EffectsQuality')+CMD('sg.PostProcessQuality')+CMD('sg.TextureQuality')+"""
  (Utilities|IsValid (Variables|Default|GetMusicComp)
    (:"Is Valid" (Class|AudioComponent|SetVolumeMultiplier :self (Variables|Default|GetMusicComp) :VolumeMultiplier (* 0.1 (Variables|Default|GetMusicVol))))
    (:"Is Not Valid")))""")
STEP=lambda n,low,high:'(bind moved (+ (Variables|Default|Get%s) Delta))\n(Variables|Default|Set%s (select (< moved %s) %s (select (> moved %s) %s moved)))'%(n,n,low,low,high,high)
fn(P,'PhysisSetting',"""(fn PhysisSetting (Row Delta)
  (if (== Row 2)
    (bind wanted (+ (Variables|Default|GetQuality) (select (> Delta 0.0) 1 -1)))
    (Variables|Default|SetQuality (select (< wanted 0) 0 (select (> wanted 2) 2 wanted))))
  (if (== Row 3) """+STEP('MusicVol','0.0','10.0')+""")
  (if (== Row 4) """+STEP('VoiceVol','0.0','10.0')+""")
  (if (== Row 5) (Variables|Default|SetShakeOn (not (Variables|Default|GetShakeOn))))
  (if (== Row 6) (Variables|Default|SetSlowOn (not (Variables|Default|GetSlowOn))))
  (if (== Row 7) """+STEP('LookSens','1.0','10.0')+""")
  (if (== Row 8) (Variables|Default|SetInvertLook (not (Variables|Default|GetInvertLook))))
  (CallFunction|PhysisSettingsApply)
  (CallFunction|PhysisSettingsSave))""")
fn(P,'PhysisRestore',"""(fn PhysisRestore ()
  (bind saved (Utilities|Casting|CastToBP_PhysisSave :Object (SaveGame|LoadGamefromSlot :SlotName "Physis" :UserIndex 0))
    (:then
      """+get(FIELDS)+"""
      (Transformation|SetActorLocation :NewLocation (Math|Vector|MakeVector :X (Variables|Default|GetCheckX) :Y (Variables|Default|GetCheckY) :Z (Variables|Default|GetCheckZ)) :bSweep false :bTeleport true)
      (bind flags (Variables|Default|GetFlags))
      (for found1 """+ALL(DR)+"""
        (bind drone (Utilities|Casting|CastToBP_TrainingDrone :Object found1)
          (:then
            (bind room (Class|BPTrainingDrone|GetRoomId :self drone))
            (if (or (and (== room 1) (Utilities|String|Contains :SearchIn flags :Substring ",room1,")) (or (and (== room 2) (Utilities|String|Contains :SearchIn flags :Substring ",room2,")) (or (and (== room 3) (Utilities|String|Contains :SearchIn flags :Substring ",boss,")) (and (> room 100) (Utilities|String|Contains :SearchIn flags :Substring (Utilities|String|Append :A ",w" :B (Utilities|String|Append :A (Utilities|String|ToString(Integer) (- room 101)) :B ",")))))))
              (for tag (Actor|GetAttachedActors :self drone)
                (Actor|DestroyActor :self tag))
              (Actor|DestroyActor :self drone)))
          (:CastFailed)))
      (for found2 """+ALL('BP_ScanTarget')+"""
        (bind item (Utilities|Casting|CastToBP_ScanTarget :Object found2)
          (:then
            (if (and (not (Utilities|String|EqualExactly(String) :A (Class|BPScanTarget|GetScanTitle :self item) :B "")) (Utilities|String|Contains :SearchIn (Variables|Default|GetLogData) :Substring (Class|BPScanTarget|GetScanTitle :self item)))
              (Class|BPScanTarget|SetScanDone :self item :ScanDone true)))
          (:CastFailed)))
      (for found3 """+ALL('BP_Pickup')+"""
        (bind pick (Utilities|Casting|CastToBP_Pickup :Object found3)
          (:then
            (if (and (not (Utilities|String|EqualExactly(String) :A (Class|BPPickup|GetToken :self pick) :B "")) (Utilities|String|Contains :SearchIn flags :Substring (Class|BPPickup|GetToken :self pick)))
              (Actor|DestroyActor :self pick)))
          (:CastFailed)))
      (for found4 """+ALL('BP_Switch')+"""
        (bind lever (Utilities|Casting|CastToBP_Switch :Object found4)
          (:then
            (if (and (== (Class|BPSwitch|GetSeq :self lever) 0) (and (not (Utilities|String|EqualExactly(String) :A (Class|BPSwitch|GetGive :self lever) :B "")) (Utilities|String|Contains :SearchIn flags :Substring (Class|BPSwitch|GetGive :self lever))))
              (Class|BPSwitch|SetUsed :self lever :Used true)))
          (:CastFailed)))
      (for found5 """+ALL('BP_Encounter')+"""
        (bind fight (Utilities|Casting|CastToBP_Encounter :Object found5)
          (:then
            (if (Utilities|String|Contains :SearchIn flags :Substring (Class|BPEncounter|GetGive :self fight))
              (Class|BPEncounter|SetDone :self fight :Done true)))
          (:CastFailed)))
      (for found6 """+ALL('BP_Checkpoint')+"""
        (bind mark (Utilities|Casting|CastToBP_Checkpoint :Object found6)
          (:then
            (if (<= (.x (Transformation|GetActorLocation :self mark)) (+ (Variables|Default|GetCheckX) 1.0))
              (Class|BPCheckpoint|SetUsed :self mark :Used true)))
          (:CastFailed))))
    (:CastFailed)))""")
sb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/scenario_bp.py').read()
fn(P,'PhysisSlow',"""(fn PhysisSlow (Rate Seconds)
  (if (Variables|Default|GetSlowOn)
    (Utilities|Time|SetGlobalTimeDilation :TimeDilation Rate)
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PhysisSlowEnd" :Time (* Rate Seconds) :bLooping false)))""")
fn(P,'PhysisFeelTick',"""(fn PhysisFeelTick (DeltaSeconds)
  (bind left (- (Variables|Default|GetShakeAmount) (* DeltaSeconds 26.0)))
  (Variables|Default|SetShakeAmount (select (< left 0.0) 0.0 left))
  (bind amount (select (Variables|Default|GetShakeOn) (Variables|Default|GetShakeAmount) 0.0))
  (CallFunction|PhysisDuck)
  (Transformation|SetRelativeLocation :self (Variables|Default|GetFollowCamera) :NewLocation (Math|Vector|MakeVector :X 0.0 :Y (Math|Random|RandomFloatinRange :Min (* amount -1.0) :Max amount) :Z (Math|Random|RandomFloatinRange :Min (* amount -1.0) :Max amount)) :bSweep false :bTeleport false))""")
MUS='(Variables|Default|SetMusicComp (Audio|SpawnSound2D :Sound "/Game/Audio/S_Music_Combat.S_Music_Combat" :VolumeMultiplier (* 0.1 (Variables|Default|GetMusicVol))))'
fn(P,'PhysisMusic',"""(fn PhysisMusic ()
  (Utilities|IsValid (Variables|Default|GetMusicComp)
    (:"Is Valid"
      (Class|AudioComponent|SetVolumeMultiplier :self (Variables|Default|GetMusicComp) :VolumeMultiplier 0.0)
      %s)
    (:"Is Not Valid"
      %s)))"""%(MUS,MUS))
cb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
def ccut(a,b):
    i=cb.index(a); return cb[i:cb.index(b,i)]
exec("SHIPS="+re.search(r"^SHIPS=(.*)$",cb,re.M).group(1))
exec(ccut("fn(P,'PhysisCinemaStart'","fn(P,'PhysisCinemaEnd'").replace('(if (Utilities|String|Contains :SearchIn (Class|GameModeBase|GetOptionsString :self (Game|GetGameMode)) :Substring "nocine")\n    (CallFunction|PhysisCinemaCleanup)','(CallFunction|PhysisSettingsLoad)\n  (if (Utilities|String|Contains :SearchIn (Class|GameModeBase|GetOptionsString :self (Game|GetGameMode)) :Substring "nocine")\n    (CallFunction|PhysisCinemaCleanup)\n    (if (Utilities|String|Contains :SearchIn (Class|GameModeBase|GetOptionsString :self (Game|GetGameMode)) :Substring "load")\n      (CallFunction|PhysisRestore))').replace('(Sequencer|Player|Play','(Variables|Default|SetMusicComp (Audio|SpawnSound2D :Sound "/Game/Audio/S_Music_Theme.S_Music_Theme" :VolumeMultiplier (* 0.075 (Variables|Default|GetMusicVol))))\n      (Sequencer|Player|Play',1))
exec(sb[sb.index("fn(S,'VisorApply',"):sb.index("comp(S)\n# Gun and sword")].replace('''(Class|BPPhysis|PhysisAddLog :self physis''','''(if (not (Utilities|String|Contains :SearchIn (Class|BPPhysis|GetLogData :self physis) :Substring (Variables|Default|GetScanTitle)))
                    (Class|BPPhysis|PhysisNarrate :self physis :Title (Variables|Default|GetScanTitle)))
                  (Class|BPPhysis|PhysisAddLog :self physis'''))
comp(S)
comp(P)
PH='(bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))\n'
print('check',call('write_graph_dsl',{'graph':{'refPath':CK+':EventGraph'},'code':"""(event EventTick (DeltaSeconds)
  (if (not (Variables|Default|GetUsed))
    """+PH+"""      (:then
        (if (< (Transformation|GetDistanceTo :OtherActor physis) (Variables|Default|GetRadius))
          (Variables|Default|SetUsed true)
          (bind here (Transformation|GetActorLocation))
          (Class|BPPhysis|PhysisCheckpoint :self physis :X (.x here) :Y (.y here) :Z (.z here))
          (Class|BPPhysis|PhysisQuest :self physis :Goal (Variables|Default|GetObjective))))
      (:CastFailed))))"""}));comp(CK)
enc=sb[sb.index("print('encounter'"):sb.index("call('add_object_variable',{'blueprint':{'refPath':WT}")]
exec("PHYSIS=PH\n"+enc.replace("(Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive))","(Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetGive))\n          (Class|BPPhysis|PhysisQuest :self physis :Goal (Variables|Default|GetNextGoal))").replace("comp(EN)",""));comp(EN)
pk=cb[cb.index("print('pick',call("):cb.index("comp(PICK)",cb.index("print('pick',call("))]
exec(pk.replace("(Class|BPPhysis|PhysisCollect :self physis","(Class|BPPhysis|PhysisGive :self physis :Token (Variables|Default|GetToken))\n        (Class|BPPhysis|PhysisCollect :self physis"));comp(PICK)
for n in ('LastRow',):var(H,n,'int')
def press(*keys):
    out='(Game|Player|WasInputKeyJustPressed :self pc :Key "%s")'%keys[0]
    for k in keys[1:]:
        out='(or %s (Game|Player|WasInputKeyJustPressed :self pc :Key "%s"))'%(out,k)
    return out
UP=press('Up','W','Gamepad_DPad_Up','Gamepad_LeftStick_Up');DN=press('Down','S','Gamepad_DPad_Down','Gamepad_LeftStick_Down')
LF=press('Left','A','Gamepad_DPad_Left','Gamepad_LeftStick_Left');RT=press('Right','D','Gamepad_DPad_Right','Gamepad_LeftStick_Right')
TL=press('Tab','Gamepad_LeftShoulder');TR=press('Q','Gamepad_RightShoulder');OK=press('E','Enter','SpaceBar','Gamepad_FaceButton_Bottom')
GOLD='"(R=1.0,G=0.82,B=0.42,A=1.0)"';DIM='"(R=0.62,G=0.68,B=0.74,A=1.0)"';CREAM='"(R=1.0,G=0.92,B=0.78,A=1.0)"'
shell(H,'DrawPauseMenu',[('SizeX','float'),('SizeY','float')])
for name,ps in (('MenuTab',[('Label','string'),('Index','int'),('Page','int'),('SizeY','float')]),('MenuAbility',[('Name','string'),('Text','string'),('Slot','int'),('SizeY','float')]),('MenuRowDraw',[('Label','string'),('Value','string'),('Index','int'),('Row','int'),('SizeY','float')]),('PageLogbook',[('SizeX','float'),('SizeY','float'),('Data','string')])):
    shell(H,name,ps)
fn(H,'MenuTab',"""(fn MenuTab (Label Index Page SizeY)
  (bind u (/ SizeY 1080.0))
  (bind x (* u (+ 80.0 (* 250.0 (Math|Conversions|ToFloat(Integer) Index)))))
  (if (== Index Page)
    (HUD|DrawRect :RectColor "(R=1.0,G=0.8,B=0.4,A=0.12)" :ScreenX (- x (* u 16.0)) :ScreenY (* u 40.0) :ScreenW (* u 226.0) :ScreenH (* u 60.0))
    (HUD|DrawRect :RectColor "(R=1.0,G=0.82,B=0.42,A=1.0)" :ScreenX (- x (* u 16.0)) :ScreenY (* u 97.0) :ScreenW (* u 226.0) :ScreenH (* u 4.0)))
  """+text('Label','x','(* u 48.0)','(* u 1.6)','(Utilities|Struct|MakeLinearColor :R (select (== Index Page) 1.0 0.62) :G (select (== Index Page) 0.82 0.68) :B (select (== Index Page) 0.42 0.74) :A 1.0)')+""")""")
fn(H,'MenuAbility',"""(fn MenuAbility (Name Text Slot SizeY)
  (bind u (/ SizeY 1080.0))
  (bind y (* u (+ 150.0 (* 76.0 (Math|Conversions|ToFloat(Integer) Slot)))))
  """+text('Name','(* u 110.0)','y','(* u 1.5)',GOLD)+"""
  """+text('Text','(* u 110.0)','(+ y (* u 34.0))','(* u 1.05)',CREAM)+""")""")
fn(H,'MenuRowDraw',"""(fn MenuRowDraw (Label Value Index Row SizeY)
  (bind u (/ SizeY 1080.0))
  (bind y (* u (+ 146.0 (* 56.0 (Math|Conversions|ToFloat(Integer) Index)))))
  (if (== Index Row)
    (HUD|DrawRect :RectColor "(R=1.0,G=0.8,B=0.4,A=0.14)" :ScreenX (* u 90.0) :ScreenY (- y (* u 6.0)) :ScreenW (* u 800.0) :ScreenH (* u 48.0)))
  """+text('Label','(* u 110.0)','y','(* u 1.3)','(Utilities|Struct|MakeLinearColor :R (select (== Index Row) 1.0 0.62) :G (select (== Index Row) 0.82 0.68) :B (select (== Index Row) 0.42 0.74) :A 1.0)')+"""
  """+text('Value','(* u 680.0)','y','(* u 1.3)',CREAM)+""")""")
hb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/hudfont.py').read()
lb=hb[hb.index('fn(H,\'DrawLogbook\',"""(fn DrawLogbook'):hb.index('comp(H)',hb.index("fn(H,'DrawLogbook'"))]
lb=lb.replace("fn(H,'DrawLogbook',","fn(H,'PageLogbook',").replace("(fn DrawLogbook (SizeX SizeY Data)","(fn PageLogbook (SizeX SizeY Data)")
lb=lb.replace('''  (HUD|DrawRect :RectColor "(R=0.0,G=0.015,B=0.03,A=0.93)" :ScreenX 0.0 :ScreenY 0.0 :ScreenW SizeX :ScreenH SizeY)
  """+text('"LOGBOOK"','(* u 80.0)','(* u 44.0)','(* u 2.1)')+"""
  """+text('"Up / Down: choose     L / View: close"','(* u 80.0)','(- SizeY (* u 80.0))','(* u 1.1)',TEAL)+"""
''','')
lb=lb.replace('''      (if (and chosen (== which 0))''','''      (if (and chosen (== which 1))
        (CallFunction|LogNarrate :Title field))
      (if (and chosen (== which 0))''')
shell(H,'LogNarrate',[('Title','string')])
fn(H,'LogNarrate',"""(fn LogNarrate (Title)
  (bind reader (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (if (not (Utilities|String|EqualExactly(String) :A (Class|BPPhysis|GetMenuTitle :self reader) :B Title))
        (Class|BPPhysis|SetMenuTitle :self reader :MenuTitle Title)
        (Class|BPPhysis|PhysisNarrate :self reader :Title Title)))
    (:CastFailed)))""")
if '"LOGBOOK"' in lb: print('LOG HEADER STILL THERE')
lb=lb.replace(":ScreenX (* u 66.0) :ScreenY (* u (+ 150.0",":ScreenX (* u 90.0) :ScreenY (* u (+ 146.0").replace("text('field','(* u 40.0)','(* u (+ 160.0","text('field','(* u 110.0)','(* u (+ 150.0").replace("'(* u 790.0)','(* u 160.0)'","'(* u 790.0)','(* u 146.0)'").replace(":X (* u 790.0) :Y (* u 215.0)",":X (* u 790.0) :Y (* u 196.0)").replace(":ScreenW (* u 620.0)",":ScreenW (* u 640.0)")
exec(lb)
TECH=(('Rising Cut','Your chains extend to a fourth strike.'),('Crescent Step','Your chains extend to a fifth strike.'),('Falling Moon','Your chains extend to a sixth strike.'),('Thousand Petals','Your chains extend to a seventh strike.'),('Severing Wind','Your chains extend to an eighth strike.'),('Final Bloom','Your chains reach their ninth and final strike.'))
abil=''.join('\n          (if (>= skill %d) (CallFunction|MenuAbility :Name "%s" :Text "%s" :Slot %d :SizeY SizeY))'%(i+1,n,t,i+3) for i,(n,t) in enumerate(TECH))
rows=(('Save Game','""'),('Load Game','""'),('Graphics: Quality','(select (== (Class|BPPhysis|GetQuality :self physis) 0) "Low" (select (== (Class|BPPhysis|GetQuality :self physis) 1) "Medium" "High"))'),
      ('Audio: Music Volume','(Utilities|String|Append :A (Utilities|String|ToString(Integer) (Math|Float|TruncatetoInteger64 (* 10.0 (Class|BPPhysis|GetMusicVol :self physis)))) :B "%")'),('Audio: Voice Volume','(Utilities|String|Append :A (Utilities|String|ToString(Integer) (Math|Float|TruncatetoInteger64 (* 10.0 (Class|BPPhysis|GetVoiceVol :self physis)))) :B "%")'),
      ('Gameplay: Camera Shake','(select (Class|BPPhysis|GetShakeOn :self physis) "On" "Off")'),('Gameplay: Hit Slow-Motion','(select (Class|BPPhysis|GetSlowOn :self physis) "On" "Off")'),
      ('Controls: Look Sensitivity','(Utilities|String|ToString(Float) (Class|BPPhysis|GetLookSens :self physis))'),('Controls: Invert Look','(select (Class|BPPhysis|GetInvertLook :self physis) "On" "Off")'),
      # Row 9 is the Divine Parry assist (2026-11-09, quality.py PhysisSetting); Exit Game is row 10. The live menu is
      # center_overrides.py part map's DrawPauseMenu (with the Map tab); this station copy matches its Settings rows.
      ('Assist: Divine Parry','(select (Class|BPPhysis|GetAutoParry :self physis) "On" "Off")'),('Exit Game','""'))
rowdraw=''.join('\n          (CallFunction|MenuRowDraw :Label "%s" :Value %s :Index %d :Row row :SizeY SizeY)'%(l,v,i) for i,(l,v) in enumerate(rows))
BIND=('Light attack: Left Mouse / RB','Heavy attack: Middle Mouse, F / RT','Parry, or scan with Divinity Sense: Right Mouse / B, LT','Lock on: Left Shift / LT','Divinity Sense: Q / Y','Jump: Space / A','Dodge: Left Alt / B (parries if a hit is coming)','Interact: E / X','Sidearm: Tab / D-pad Up','Reload: R / D-pad Down','Logbook: L / View','Pause Menu: Esc / Menu')
binddraw=''.join('\n          '+text('"%s"'%b,'(* u 960.0)','(* u %d)'%(150+i*46),'(* u 1.05)',TEAL) for i,b in enumerate(BIND))
fn(H,'DrawPauseMenu',"""(fn DrawPauseMenu (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind pc (Game|GetPlayerController 0))
  (bind sky (select (> SizeX (* SizeY 2.0)) SizeX (* SizeY 2.0)))
  (HUD|DrawTexture :Texture "/Game/Cinematics/T_Sky_Space.T_Sky_Space" :ScreenX (- (/ SizeX 2.0) (/ sky 2.0)) :ScreenY (- (/ SizeY 2.0) (/ sky 4.0)) :ScreenW sky :ScreenH (/ sky 2.0) :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor "(R=0.6,G=0.6,B=0.68,A=1.0)")
  (HUD|DrawRect :RectColor "(R=0.0,G=0.012,B=0.03,A=0.72)" :ScreenX 0.0 :ScreenY 0.0 :ScreenW SizeX :ScreenH SizeY)
  (HUD|DrawRect :RectColor "(R=0.0,G=0.03,B=0.06,A=0.62)" :ScreenX (* u 64.0) :ScreenY (* u 118.0) :ScreenW (- SizeX (* u 128.0)) :ScreenH (- SizeY (* u 214.0)))
  (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX (* u 64.0) :ScreenY (- SizeY (* u 96.0)) :ScreenW (- SizeX (* u 128.0)) :ScreenH (* u 2.0))
  (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX (* u 64.0) :ScreenY (* u 118.0) :ScreenW (* u 2.0) :ScreenH (- SizeY (* u 214.0)))
  (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.5)" :ScreenX (- SizeX (* u 66.0)) :ScreenY (* u 118.0) :ScreenW (* u 2.0) :ScreenH (- SizeY (* u 214.0)))
  """+tex('T_UI_LogoMark','(- SizeX (* u 150.0))','(* u 12.0)','(* u 104.0)','(* u 104.0)')+"""
  (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.55)" :ScreenX (* u 64.0) :ScreenY (* u 100.0) :ScreenW (- SizeX (* u 240.0)) :ScreenH (* u 2.0))
  (bind physis (Utilities|Casting|CastToBP_Physis :Object (Game|GetPlayerPawn 0))
    (:then
      (bind page (Class|BPPhysis|GetMenuPage :self physis))
      (if (or """+TL+""" (and (not (== page 3)) """+LF+"""))
        (Class|BPPhysis|SetMenuPage :self physis :MenuPage (select (> page 0) (- page 1) 3))
        (Class|BPPhysis|SetMenuRow :self physis :MenuRow 0)
        (Class|BPPhysis|SetMenuTitle :self physis :MenuTitle "")
        (Class|BPPhysis|PhysisVoiceStop :self physis))
      (if (or """+TR+""" (and (not (== page 3)) """+RT+"""))
        (Class|BPPhysis|SetMenuPage :self physis :MenuPage (select (< page 3) (+ page 1) 0))
        (Class|BPPhysis|SetMenuRow :self physis :MenuRow 0)
        (Class|BPPhysis|SetMenuTitle :self physis :MenuTitle "")
        (Class|BPPhysis|PhysisVoiceStop :self physis))
      (bind shown (Class|BPPhysis|GetMenuPage :self physis))
      (CallFunction|MenuTab :Label "Logbook" :Index 0 :Page shown :SizeY SizeY)
      (CallFunction|MenuTab :Label "Abilities" :Index 1 :Page shown :SizeY SizeY)
      (CallFunction|MenuTab :Label "Quests" :Index 2 :Page shown :SizeY SizeY)
      (CallFunction|MenuTab :Label "Settings" :Index 3 :Page shown :SizeY SizeY)
      """+text('"Tab, Q / LB, RB: pages     E / A: select     Esc / Menu: resume"','(* u 80.0)','(- SizeY (* u 62.0))','(* u 1.1)',TEAL)+"""
      (if (== shown 0)
        (CallFunction|PageLogbook :SizeX SizeX :SizeY SizeY :Data (Class|BPPhysis|GetLogData :self physis)))
      (if (== shown 1)
        (CallFunction|PageAbilities :SizeX SizeX :SizeY SizeY :Skill (Class|BPPhysis|GetSkillLevel :self physis)))
      (if (== shown 2)
        """+text('"Main Quest"','(* u 110.0)','(* u 150.0)','(* u 1.5)',GOLD)+"""
        (CallFunction|DrawLines :Message (Class|BPPhysis|GetObjective :self physis) :X (* u 110.0) :Y (* u 196.0) :Scale (* u 1.2) :Step (* u 36.0) :Red 1.0 :Green 0.92 :Blue 0.78)
        (Variables|Default|SetLineY (+ (Variables|Default|GetLineY) (* u 30.0)))
        """+text('"Completed"','(* u 110.0)','(Variables|Default|GetLineY)','(* u 1.2)',DIM)+"""
        (Variables|Default|SetLineY (+ (Variables|Default|GetLineY) (* u 44.0)))
        """+text('"Achievements"','(* u 900.0)','(* u 150.0)','(* u 1.5)',GOLD)+"""
        """+text('(select (Class|BPPhysis|GetAchStation :self physis) "Unlocked:  Meridian Holds" "Locked:  Meridian Holds")','(* u 900.0)','(* u 200.0)','(* u 1.1)','(Utilities|Struct|MakeLinearColor :R 1.0 :G (select (Class|BPPhysis|GetAchStation :self physis) 0.85 0.6) :B (select (Class|BPPhysis|GetAchStation :self physis) 0.45 0.62) :A 1.0)')+"""
        """+text('"Finish Meridian Station."','(* u 920.0)','(* u 234.0)','(* u 0.9)',DIM)+"""
        """+text('(select (Class|BPPhysis|GetAchSwift :self physis) "Unlocked:  Swift as Light" "Locked:  Swift as Light")','(* u 900.0)','(* u 280.0)','(* u 1.1)','(Utilities|Struct|MakeLinearColor :R 1.0 :G (select (Class|BPPhysis|GetAchSwift :self physis) 0.85 0.6) :B (select (Class|BPPhysis|GetAchSwift :self physis) 0.45 0.62) :A 1.0)')+"""
        """+text('"Finish Meridian Station in under 10 minutes."','(* u 920.0)','(* u 314.0)','(* u 0.9)',DIM)+"""
        (for finished (Utilities|String|ParseIntoArray :SourceString (Class|BPPhysis|GetQuestDone :self physis) :Delimiter "@" :CullEmptyStrings true)
          (if (< (Variables|Default|GetLineY) (- SizeY (* u 130.0)))
            (bind start (Variables|Default|GetLineY))
            (CallFunction|DrawLines :Message finished :X (* u 110.0) :Y start :Scale (* u 0.95) :Step (* u 28.0) :Red 0.62 :Green 0.68 :Blue 0.74))))
      (if (== shown 3)
        (bind row (Class|BPPhysis|GetMenuRow :self physis))
        (if """+UP+"""
          (Class|BPPhysis|SetMenuRow :self physis :MenuRow (select (> row 0) (- row 1) 0)))
        (if """+DN+"""
          (Class|BPPhysis|SetMenuRow :self physis :MenuRow (select (< row 10) (+ row 1) 10)))
        (if """+LF+"""
          (Class|BPPhysis|PhysisSetting :self physis :Row row :Delta -1.0))
        (if """+RT+"""
          (Class|BPPhysis|PhysisSetting :self physis :Row row :Delta 1.0))
        (if (and (== row 0) """+OK+""")
          (Class|BPPhysis|PhysisSaveGame :self physis))
        (if (and (== row 1) """+OK+""")
          (Class|BPPhysis|PhysisLoadGame :self physis))
        (if (and (== row 10) """+OK+""")
          (Game|QuitGame))"""+rowdraw+binddraw+"""
        """+text('(Class|BPPhysis|GetMenuNote :self physis)','(* u 84.0)','(* u 776.0)','(* u 1.2)',GOLD)+"""))
    (:CastFailed)))""")
fn(H,'DrawObjective',"""(fn DrawObjective (SizeX SizeY Goal BossHealth)
  (bind u (/ SizeY 1080.0))
  (if (not (Utilities|String|EqualExactly(String) :A Goal :B ""))
    (Variables|Default|SetWidestLine 0.0)
    (Variables|Default|SetLineCount 0)
    (for measured (Utilities|String|ParseIntoArray :SourceString Goal :Delimiter "~" :CullEmptyStrings false)
      (CallFunction|MeasureLine :Line measured :Scale (* u 1.3) :Icon 0.0))
    (bind wq (+ (Variables|Default|GetWidestLine) (* u 60.0)))
    (bind qw (select (> wq (* u 320.0)) wq (* u 320.0)))
    (bind qh (+ (* u 84.0) (* u (* 30.0 (Math|Conversions|ToFloat(Integer) (Variables|Default|GetLineCount))))))
    """+tex('T_UI_Panel','(* u 22.0)','(* u 262.0)','qw','qh','"(R=1.0,G=0.95,B=0.85,A=0.95)"')+"""
    """+text('"MAIN QUEST"','(* u 46.0)','(* u 276.0)','(* u 1.1)','"(R=1.0,G=0.82,B=0.42,A=1.0)"')+"""
    (HUD|DrawRect :RectColor "(R=1.0,G=0.8,B=0.45,A=0.75)" :ScreenX (* u 46.0) :ScreenY (* u 308.0) :ScreenW (- qw (* u 50.0)) :ScreenH (* u 2.0))
    (CallFunction|DrawLines :Message Goal :X (* u 46.0) :Y (* u 318.0) :Scale (* u 1.3) :Step (* u 30.0) :Red 1.0 :Green 0.93 :Blue 0.8))
  (if (> BossHealth 0.0)
    (bind left (* u 720.0))
    (bind wide (- SizeX (* u 800.0)))
    """+tex('T_UI_Panel','(- left (* u 34.0))','(* u 18.0)','(+ wide (* u 68.0))','(* u 90.0)','"(R=1.0,G=0.55,B=0.5,A=0.92)"')+"""
    (HUD|DrawRect :RectColor "(R=0.05,G=0.01,B=0.01,A=0.9)" :ScreenX left :ScreenY (* u 66.0) :ScreenW wide :ScreenH (* u 24.0))
    (HUD|DrawTexture :Texture "/Game/UI/T_UI_BarHealth.T_UI_BarHealth" :ScreenX left :ScreenY (* u 66.0) :ScreenW (* wide BossHealth) :ScreenH (* u 24.0) :TextureUWidth BossHealth :TextureVHeight 1.0 :TintColor "(R=1.0,G=0.32,B=0.26,A=1.0)")
    (HUD|DrawRect :RectColor "(R=1.0,G=0.86,B=0.55,A=0.35)" :ScreenX left :ScreenY (* u 66.0) :ScreenW (* wide BossHealth) :ScreenH (* u 4.0))
    (HUD|DrawRect :RectColor "(R=1.0,G=0.8,B=0.45,A=0.9)" :ScreenX (- left (* u 2.0)) :ScreenY (* u 63.0) :ScreenW (+ wide (* u 4.0)) :ScreenH (* u 2.0))
    (HUD|DrawRect :RectColor "(R=1.0,G=0.8,B=0.45,A=0.9)" :ScreenX (- left (* u 2.0)) :ScreenY (* u 91.0) :ScreenW (+ wide (* u 4.0)) :ScreenH (* u 2.0))
    (bind (nw nh) (HUD|GetTextSize :Text "MECHA BREACHER" :Font "/Game/UI/F_Physis.F_Physis" :Scale (* (* u 1.25) 0.35)))
    """+text('"MECHA BREACHER"','(- (+ left (/ wide 2.0)) (/ nw 2.0))','(* u 28.0)','(* u 1.25)','"(R=1.0,G=0.82,B=0.42,A=1.0)"')+"""))""")
comp(H)
i=cb.index("print('hud',call('write_graph_dsl'");b=cb[i:cb.index("comp(H)",i)]
b=b.replace("(CallFunction|DrawCombat :SizeX SizeX :SizeY SizeY)","(CallFunction|DrawCombat :SizeX SizeX :SizeY SizeY)\n          (CallFunction|DrawObjective :SizeX SizeX :SizeY SizeY :Goal (Class|BPPhysis|GetObjective :self physis) :BossHealth (Class|BPPhysis|GetBossShown :self physis))")
b=b.replace("(CallFunction|DrawTutorial :SizeX SizeX :SizeY SizeY)","(CallFunction|DrawTutorial :SizeX SizeX :SizeY SizeY))\n          (if (Class|BPPhysis|GetLogOpen :self physis)\n            (CallFunction|DrawPauseMenu :SizeX SizeX :SizeY SizeY)")
exec(b);comp(H)

fn(P,'PhysisBlock',"""(fn PhysisBlock ()
  (if (Variables|Default|GetScanVisorOn)
    (CallFunction|PhysisScan)
    (else
      (bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))
      (if (and (and (not (Variables|Default|GetPhysisDead)) (not (Variables|Default|GetCinematic))) (> (Utilities|Time|GetGameTimeinSeconds) (Variables|Default|GetBlockUntil)))
        (Variables|Default|SetChainOpenAt 0.0)
        (Animation|Montage|MontagePlay :self anim :MontageToPlay "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Block.AM_Physis_Block" :InPlayRate 1.2)
        (Variables|Default|SetBlockUntil (+ (Utilities|Time|GetGameTimeinSeconds) 0.7))
        (Variables|Default|SetParryUntil (+ (Utilities|Time|GetGameTimeinSeconds) 0.3))))))""")
shell(P,'PhysisBlockEnd')
fn(P,'PhysisBlockEnd',"""(fn PhysisBlockEnd ()
  (Variables|Default|SetScanHeld false))""")
comp(P)

import importlib.util
spec=importlib.util.spec_from_file_location('lore','/var/home/precosmos/Έγγραφα/Unreal Projects/Physis/Content/Python/physis_lore.py');lore=importlib.util.module_from_spec(spec);spec.loader.exec_module(lore)
for n,k in (('SelTitle','string'),('SelBody','string'),('SelCat','string'),('LineNo','int'),('LogFirst','int'),('CatCount','int')):var(H,n,k)
shell(H,'LogCategory',[('Data','string'),('Cat','string'),('SizeY','float')])
shell(H,'LogImage',[('Title','string'),('X','float'),('Y','float'),('W','float'),('H','float')])
ROWY='(* u (+ 150.0 (* 36.0 (Math|Conversions|ToFloat(Integer) (- (Variables|Default|GetLineNo) (Variables|Default|GetLogFirst))))))'
VIS='(and (>= (Variables|Default|GetLineNo) (Variables|Default|GetLogFirst)) (< (Variables|Default|GetLineNo) (+ (Variables|Default|GetLogFirst) 22)))'
fn(H,'LogCategory',"""(fn LogCategory (Data Cat SizeY)
  (bind u (/ SizeY 1080.0))
  (Variables|Default|SetCatCount 0)
  (for counted (Utilities|String|ParseIntoArray :SourceString Data :Delimiter "@" :CullEmptyStrings true)
    (if (Utilities|String|StartsWith :SourceString counted :InPrefix (Utilities|String|Append :A Cat :B "^"))
      (Variables|Default|SetCatCount (+ (Variables|Default|GetCatCount) 1))))
  (if (> (Variables|Default|GetCatCount) 0)
    (if """+VIS+"""
      """+text('(Utilities|String|ToUpper Cat)','(* u 110.0)',ROWY,'(* u 1.0)',TEAL)+""")
    (Variables|Default|SetLineNo (+ (Variables|Default|GetLineNo) 1))
    (for entry (Utilities|String|ParseIntoArray :SourceString Data :Delimiter "@" :CullEmptyStrings true)
      (if (Utilities|String|StartsWith :SourceString entry :InPrefix (Utilities|String|Append :A Cat :B "^"))
        (bind fields (Utilities|String|ParseIntoArray :SourceString entry :Delimiter "^" :CullEmptyStrings false))
        (bind title (Utilities|Array|Get(acopy) fields 1))
        (bind chosen (== (Variables|Default|GetLogRow) (Variables|Default|GetLogIndex)))
        (if chosen
          (Variables|Default|SetSelTitle title)
          (Variables|Default|SetSelCat Cat)
          (Variables|Default|SetSelBody (Utilities|Array|Get(acopy) fields 2))
          (if (< (Variables|Default|GetLineNo) (+ (Variables|Default|GetLogFirst) 1))
            (Variables|Default|SetLogFirst (select (> (Variables|Default|GetLineNo) 1) (- (Variables|Default|GetLineNo) 1) 0)))
          (if (> (Variables|Default|GetLineNo) (+ (Variables|Default|GetLogFirst) 20))
            (Variables|Default|SetLogFirst (- (Variables|Default|GetLineNo) 20))))
        (if """+VIS+"""
          (if chosen
            (HUD|DrawRect :RectColor "(R=1.0,G=0.8,B=0.4,A=0.14)" :ScreenX (* u 100.0) :ScreenY (- """+ROWY+""" (* u 3.0)) :ScreenW (* u 560.0) :ScreenH (* u 34.0)))
          """+text('title','(* u 128.0)',ROWY,'(* u 1.2)','(Utilities|Struct|MakeLinearColor :R (select chosen 1.0 0.7) :G (select chosen 0.82 0.74) :B (select chosen 0.42 0.8) :A 1.0)')+""")
        (Variables|Default|SetLogRow (+ (Variables|Default|GetLogRow) 1))
        (Variables|Default|SetLineNo (+ (Variables|Default|GetLineNo) 1))))))""")
fn(H,'LogImage',"""(fn LogImage (Title X Y W H)
  (for found (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Physis/Blueprints/BP_LogVoice.BP_LogVoice_C")
    (bind bank (Utilities|Casting|CastToBP_LogVoice :Object found)
      (:then
        (if (Utilities|String|EqualExactly(String) :A (Class|BPLogVoice|GetTitle :self bank) :B Title)
          (HUD|DrawTexture :Texture (Class|BPLogVoice|GetImage :self bank) :ScreenX X :ScreenY Y :ScreenW W :ScreenH H :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor "(R=1.0,G=1.0,B=1.0,A=1.0)")
          (HUD|DrawRect :RectColor "(R=1.0,G=0.78,B=0.36,A=0.6)" :ScreenX X :ScreenY (+ Y H) :ScreenW W :ScreenH 2.0)))
      (:CastFailed))))""")
fn(H,'PageLogbook',"""(fn PageLogbook (SizeX SizeY Data)
  (bind u (/ SizeY 1080.0))
  (bind pc (Game|GetPlayerController 0))
  (Variables|Default|SetLogTotal 0)
  (for counted (Utilities|String|ParseIntoArray :SourceString Data :Delimiter "@" :CullEmptyStrings true)
    (Variables|Default|SetLogTotal (+ (Variables|Default|GetLogTotal) 1)))
  (if """+UP+"""
    (Variables|Default|SetLogIndex (select (> (Variables|Default|GetLogIndex) 0) (- (Variables|Default|GetLogIndex) 1) 0)))
  (if """+DN+"""
    (Variables|Default|SetLogIndex (select (< (Variables|Default|GetLogIndex) (- (Variables|Default|GetLogTotal) 1)) (+ (Variables|Default|GetLogIndex) 1) (Variables|Default|GetLogIndex))))
  (if (== (Variables|Default|GetLogTotal) 0)
    """+text('"No entries yet. Use Divinity Sense and scan the world."','(* u 110.0)','(* u 160.0)','(* u 1.3)')+""")
  (Variables|Default|SetLogRow 0)
  (Variables|Default|SetLineNo 0)
  (Variables|Default|SetSelTitle "")
  """+'\n  '.join('(CallFunction|LogCategory :Data Data :Cat "%s" :SizeY SizeY)'%c for c in lore.CATEGORIES)+"""
  (if (not (Utilities|String|EqualExactly(String) :A (Variables|Default|GetSelTitle) :B ""))
    (CallFunction|LogNarrate :Title (Variables|Default|GetSelTitle))
    (CallFunction|LogImage :Title (Variables|Default|GetSelTitle) :X (* u 720.0) :Y (* u 140.0) :W (* u 560.0) :H (* u 315.0))
    """+text('(Variables|Default|GetSelTitle)','(* u 720.0)','(* u 474.0)','(* u 1.6)',GOLD)+"""
    """+text('(Variables|Default|GetSelCat)','(* u 720.0)','(* u 520.0)','(* u 1.0)',TEAL)+"""
    (CallFunction|DrawLines :Message (Variables|Default|GetSelBody) :X (* u 720.0) :Y (* u 562.0) :Scale (* u 1.05) :Step (* u 30.0) :Red 1.0 :Green 0.92 :Blue 0.78)))""")
shell(H,'PageAbilities',[('SizeX','float'),('SizeY','float'),('Skill','int')])
shell(H,'AbilityRow',[('Name','string'),('Text','string'),('X','float'),('Y','float'),('SizeY','float')])
fn(H,'AbilityRow',"""(fn AbilityRow (Name Text X Y SizeY)
  (bind u (/ SizeY 1080.0))
  """+text('Name','(+ X (* u 80.0))','(+ Y (* u 4.0))','(* u 1.3)',GOLD)+"""
  (CallFunction|DrawLines :Message Text :X (+ X (* u 80.0)) :Y (+ Y (* u 38.0)) :Scale (* u 0.9) :Step (* u 24.0) :Red 1.0 :Green 0.92 :Blue 0.78))""")
rows=[];cols={'Perception':(110,150),'Combat':(110,280),'Techniques':(820,150)}
last=None;y=None
for i,(cat,name,textv) in enumerate(lore.ABILITIES):
    x0,y0=cols[cat]
    if cat!=last:
        y=y0; rows.append(text('"%s"'%cat.upper(),'(* u %d.0)'%x0,'(* u %d.0)'%y,'(* u 1.0)',TEAL)); y+=36; last=cat
    slug=''.join(c for c in name.title() if c.isalnum())
    slug={'DivinitySense':'ScanVisor'}.get(slug,slug)  # renamed 2026-11-07; the icon asset keeps its old name
    words=textv.split(' ');lines=[];cur=''
    for w in words:
        if cur and len(cur)+1+len(w)>46: lines.append(cur);cur=w
        else: cur=(cur+' '+w) if cur else w
    lines.append(cur);txt='~'.join(lines)
    call_row='(CallFunction|AbilityRow :Name "%s" :Text "%s" :X (* u %d.0) :Y (* u %d.0) :SizeY SizeY) '%(name,txt,x0,y)+'(HUD|DrawTexture :Texture "/Game/UI/Abilities/T_Ability_%s.T_Ability_%s" :ScreenX (* u %d.0) :ScreenY (* u %d.0) :ScreenW (* u 64.0) :ScreenH (* u 64.0) :TextureUWidth 1.0 :TextureVHeight 1.0 :TintColor "(R=1.0,G=1.0,B=1.0,A=1.0)")'%(slug,slug,x0,y)
    if cat=='Techniques':
        k=['Rising Cut','Crescent Step','Falling Moon','Thousand Petals','Severing Wind','Final Bloom'].index(name)+1
        call_row='(if (>= Skill %d) %s)'%(k,call_row)
    rows.append(call_row); y+=110 if cat=='Techniques' else 100
rows.append('(if (== Skill 0) '+text('"Techniques are earned by clearing rooms."','(* u 820.0)','(* u 190.0)','(* u 1.0)',DIM)+')')
code='(fn PageAbilities (SizeX SizeY Skill)\n  (bind u (/ SizeY 1080.0))\n  '+'\n  '.join(rows)+')'
fn(H,'PageAbilities',code)
comp(H)
