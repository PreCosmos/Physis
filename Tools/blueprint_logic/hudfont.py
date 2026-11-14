import sys,re
sys.path.insert(0,'Tools')
src=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
exec(src.split("ANIM=")[0])
FONTPATH='/Game/UI/F_Physis.F_Physis'
exec('def tex'+src.split('def tex',1)[1].split("FONT=")[0])
FONT=' :Font "%s"'%FONTPATH
def text(t,x,y,scale,colour='"(R=1.0,G=0.9,B=0.7,A=1.0)"'):
    # Every HUD text sits on a dark plate so it reads over any background.
    # The font is cached at 40 pt (was 14), so every scale is multiplied by 14/40 to keep sizes and stay sharp.
    scale='(* %s 0.35)'%scale
    return '(CallFunction|DrawTextPlate :Text %s :X %s :Y %s :Scale %s)\n    '%(t,x,y,scale)+'(HUD|DrawText :Text %s :TextColor %s :ScreenX %s :ScreenY %s :Scale %s%s)'%(t,colour,x,y,scale,FONT)
TEAL='"(R=0.5,G=1.0,B=0.88,A=1.0)"'
def cut(a,b):
    i=src.index(a); return src[i:src.index(b,i)]
var(H,'LineY','float');var(H,'LineWidth','float');var(H,'WidestLine','float');var(H,'LineCount','int')
shell(H,'DrawLines',[('Message','string'),('X','float'),('Y','float'),('Scale','float'),('Step','float'),('Red','float'),('Green','float'),('Blue','float')])
fn(H,'DrawLines',"""(fn DrawLines (Message X Y Scale Step Red Green Blue)
  (Variables|Default|SetLineY Y)
  (for line (Utilities|String|ParseIntoArray :SourceString Message :Delimiter "~" :CullEmptyStrings false)
    """+text('line','X','(Variables|Default|GetLineY)','Scale','(Utilities|Struct|MakeLinearColor :R Red :G Green :B Blue :A 1.0)')+"""
    (Variables|Default|SetLineY (+ (Variables|Default|GetLineY) Step))))""")
shell(H,'MeasureLine',[('Line','string'),('Scale','float'),('Icon','float')])
fn(H,'MeasureLine',"""(fn MeasureLine (Line Scale Icon)
  (Variables|Default|SetTutorialIcon false)
  (Variables|Default|SetLineWidth 0.0)
  (for part (Utilities|String|ParseIntoArray :SourceString Line :Delimiter "|" :CullEmptyStrings false)
    (bind (width high) (HUD|GetTextSize :Text part :Font """+'"%s"'%FONTPATH+""" :Scale (* Scale 0.35)))
    (Variables|Default|SetLineWidth (+ (Variables|Default|GetLineWidth) (select (Variables|Default|GetTutorialIcon) Icon width)))
    (Variables|Default|SetTutorialIcon (not (Variables|Default|GetTutorialIcon))))
  (Variables|Default|SetWidestLine (select (> (Variables|Default|GetLineWidth) (Variables|Default|GetWidestLine)) (Variables|Default|GetLineWidth) (Variables|Default|GetWidestLine)))
  (Variables|Default|SetLineCount (+ (Variables|Default|GetLineCount) 1)))""")
ICONS=('A','B','X','Y','LB','RB','LT','RT','LS','RS','L3','DU','DD','DL','DR','Menu','View')  # DL DR Menu View added 2026-11-04 (Center prompts, Map)
# The glyphs are drawn by their own small function. Inside DrawTutorialLine's loop, 13 per-glyph branches
# already made a large graph, and 17 there made write_graph_dsl exhaust the editor's memory (2026-11-04).
glyphs='\n  '.join('(if (Utilities|String|EqualExactly(String) :A Piece :B "%s") %s)'%(n,tex('T_Pad_'+n,'X','Y','Size','Size').replace('"/Game/UI/T_Pad_%s.T_Pad_%s"'%(n,n),'(Physis|Input|GetPadGlyph :Token "%s" :Fallback "/Game/UI/T_Pad_%s.T_Pad_%s")'%(n,n,n))) for n in ICONS)
shell(H,'DrawPadGlyph',[('Piece','string'),('X','float'),('Y','float'),('Size','float')])
fn(H,'DrawPadGlyph',"""(fn DrawPadGlyph (Piece X Y Size)
  """+glyphs+""")""")
shell(H,'DrawTutorialLine',[('Line','string'),('Top','float'),('Scale','float'),('SizeX','float'),('SizeY','float')])
fn(H,'DrawTutorialLine',"""(fn DrawTutorialLine (Line Top Scale SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (CallFunction|MeasureLine :Line Line :Scale Scale :Icon (* u 48.0))
  (Variables|Default|SetTutorialX (/ (- SizeX (Variables|Default|GetLineWidth)) 2.0))
  (Variables|Default|SetTutorialIcon false)
  (for piece (Utilities|String|ParseIntoArray :SourceString Line :Delimiter "|" :CullEmptyStrings false)
    (bind (wide tall) (HUD|GetTextSize :Text piece :Font """+'"%s"'%FONTPATH+""" :Scale (* Scale 0.35)))
    (bind x (Variables|Default|GetTutorialX))
    (if (Variables|Default|GetTutorialIcon)
      (CallFunction|DrawPadGlyph :Piece piece :X x :Y (- Top (* u 10.0)) :Size (* u 44.0))
      (else """+text('piece','x','Top','Scale')+"""))
    (Variables|Default|SetTutorialX (+ (Variables|Default|GetTutorialX) (select (Variables|Default|GetTutorialIcon) (* u 48.0) wide)))
    (Variables|Default|SetTutorialIcon (not (Variables|Default|GetTutorialIcon)))))""")
fn(H,'DrawTutorial',"""(fn DrawTutorial (SizeX SizeY)
  (bind u (/ SizeY 1080.0))
  (bind scale (* u 1.43))
  (bind lines (Utilities|String|ParseIntoArray :SourceString (Variables|Default|GetTutorialText) :Delimiter "~" :CullEmptyStrings false))
  (Variables|Default|SetWidestLine 0.0)
  (Variables|Default|SetLineCount 0)
  (for measured lines
    (CallFunction|MeasureLine :Line measured :Scale scale :Icon (* u 48.0)))
  (bind total (Variables|Default|GetWidestLine))
  (bind tall (* u (* 40.0 (Math|Conversions|ToFloat(Integer) (Variables|Default|GetLineCount)))))
  (bind top (- SizeY (+ tall (* u 120.0))))
  """+tex('T_UI_Panel','(- (/ (- SizeX total) 2.0) (* u 70.0))','(- top (* u 30.0))','(+ total (* u 140.0))','(+ tall (* u 44.0))')+"""
  (Variables|Default|SetLineY top)
  (for shown lines
    (CallFunction|DrawTutorialLine :Line shown :Top (Variables|Default|GetLineY) :Scale scale :SizeX SizeX :SizeY SizeY)
    (Variables|Default|SetLineY (+ (Variables|Default|GetLineY) (* u 40.0)))))""")
block=cut("fn(H,'DrawCombat'","var(H,'TutorialIcon','bool')")
sub=block.index('          (bind message (Variables|Default|GetScanResult))'); end=block.index('''      )
    (:CastFailed)))""")''')
block=block[:sub]+'''          (bind message (Variables|Default|GetScanResult))
          (Variables|Default|SetWidestLine 0.0)
          (Variables|Default|SetLineCount 0)
          (for measured (Utilities|String|ParseIntoArray :SourceString message :Delimiter "~" :CullEmptyStrings false)
            (CallFunction|MeasureLine :Line measured :Scale (* u 1.43) :Icon 0.0))
          (bind width (Variables|Default|GetWidestLine))
          (bind high (* u (* 40.0 (Math|Conversions|ToFloat(Integer) (Variables|Default|GetLineCount)))))
          (bind panelX (/ (- SizeX width) 2.0))
          (bind panelY (* SizeY 0.42))
          """+tex('T_UI_PanelScan','(- panelX (* u 70.0))','(- panelY (* u 26.0))','(+ width (* u 140.0))','(+ high (* u 44.0))')+"""
          (CallFunction|DrawLines :Message message :X panelX :Y panelY :Scale (* u 1.43) :Step (* u 40.0) :Red 0.75 :Green 1.0 :Blue 0.92)))
'''+block[end:]
for old,new in (("'(+ wx (* u 160.0))','(+ wy (* u 98.0))','(* u 0.8)'","'(+ wx (* u 150.0))','(+ wy (* u 48.0))','(* u 0.8)'"),
                ("'(+ wx (* u 245.0))','(+ wy (* u 48.0))','(* u 0.8)'","'(+ wx (* u 262.0))','(+ wy (* u 86.0))','(* u 1.1)'"),
                ("'(+ wx (* u 160.0))','(+ wy (* u 44.0))','(* u 1.4)'","'(+ wx (* u 140.0))','(+ wy (* u 42.0))','(* u 1.43)'"),
                ("'(- SizeX (* u 320.0))','(* u 24.0)','(* u 296.0)','(* u 74.0)'","'(- SizeX (* u 500.0))','(* u 20.0)','(* u 476.0)','(* u 112.0)'"),
                ("'\"SCANS\"','(- SizeX (* u 290.0))','(* u 44.0)','(* u 1.1)'","'\"SCANS\"','(- SizeX (* u 460.0))','(* u 40.0)','(* u 1.43)'"),
                ("(Variables|Default|GetLogbookDone))','(- SizeX (* u 180.0))','(* u 44.0)','(* u 1.1)'","(Variables|Default|GetLogbookDone))','(- SizeX (* u 225.0))','(* u 40.0)','(* u 1.43)'"),
                ("'\"/\"','(- SizeX (* u 135.0))','(* u 44.0)','(* u 1.1)'","'\"/\"','(- SizeX (* u 165.0))','(* u 40.0)','(* u 1.43)'"),
                ("(Variables|Default|GetLogbookSeen))','(- SizeX (* u 112.0))','(* u 44.0)','(* u 1.1)'","(Variables|Default|GetLogbookSeen))','(- SizeX (* u 125.0))','(* u 40.0)','(* u 1.43)'")):
    if old not in block: print('MISSING',old[:50])
    block=block.replace(old,new)
for old,new in (("'(+ wx (* u 160.0))','(+ wy (* u 14.0))','(* u 3.4)'","'(+ wx (* u 168.0))','(+ wy (* u 20.0))','(* u 2.2)'"),
                ("'\"RESERVE\"','(+ wx (* u 150.0))','(+ wy (* u 48.0))','(* u 0.8)'","'\"RESERVE\"','(+ wx (* u 168.0))','(+ wy (* u 106.0))','(* u 0.75)'"),
                ("'(+ wx (* u 262.0))','(+ wy (* u 86.0))','(* u 1.1)'","'(+ wx (* u 262.0))','(+ wy (* u 100.0))','(* u 1.0)'")):
    if old not in block: print('AMMO MISSING',old[:40])
    block=block.replace(old,new)
exec(block)
cin=cut("fn(H,'DrawCinema'","print('hud',call")
cin=cin.replace("""'(- SizeX (* u 280.0))','(- SizeY (* u 76.0))','(* u 1.6)'""","""'(- SizeX (* u 440.0))','(- SizeY (* u 48.0))','(* u 1.95)'""")
exec(cin)
# DrawObjective is owned by pause.py, feat.py and feat2.py (Main Quest title, boss marker, timer).
for n in ('LogIndex','LogRow','LogField','LogTotal','LogFirst'):var(H,n,'int')
def press(*keys):
    out='(Game|Player|WasInputKeyJustPressed :self pc :Key "%s")'%keys[0]
    for k in keys[1:]:
        out='(or %s (Game|Player|WasInputKeyJustPressed :self pc :Key "%s"))'%(out,k)
    return out
fn(H,'DrawLogbook',"""(fn DrawLogbook (SizeX SizeY Data)
  (bind u (/ SizeY 1080.0))
  (bind pc (Game|GetPlayerController 0))
  (bind entries (Utilities|String|ParseIntoArray :SourceString Data :Delimiter "@" :CullEmptyStrings true))
  (Variables|Default|SetLogTotal 0)
  (for counted entries
    (Variables|Default|SetLogTotal (+ (Variables|Default|GetLogTotal) 1)))
  (if """+press('Up','W','Gamepad_DPad_Up','Gamepad_LeftStick_Up')+"""
    (Variables|Default|SetLogIndex (select (> (Variables|Default|GetLogIndex) 0) (- (Variables|Default|GetLogIndex) 1) 0)))
  (if """+press('Down','S','Gamepad_DPad_Down','Gamepad_LeftStick_Down')+"""
    (Variables|Default|SetLogIndex (select (< (Variables|Default|GetLogIndex) (- (Variables|Default|GetLogTotal) 1)) (+ (Variables|Default|GetLogIndex) 1) (Variables|Default|GetLogIndex))))
  (HUD|DrawRect :RectColor "(R=0.0,G=0.015,B=0.03,A=0.93)" :ScreenX 0.0 :ScreenY 0.0 :ScreenW SizeX :ScreenH SizeY)
  """+text('"LOGBOOK"','(* u 80.0)','(* u 44.0)','(* u 2.1)')+"""
  """+text('"Up / Down: choose     L / View: close"','(* u 80.0)','(- SizeY (* u 80.0))','(* u 1.1)',TEAL)+"""
  (if (== (Variables|Default|GetLogTotal) 0)
    """+text('"No entries yet. Scan things with Divinity Sense."','(* u 80.0)','(* u 170.0)','(* u 1.43)')+""")
  (Variables|Default|SetLogFirst (select (> (Variables|Default|GetLogIndex) 8) (- (Variables|Default|GetLogIndex) 8) 0))
  (Variables|Default|SetLogRow 0)
  (for entry entries
    (bind row (Variables|Default|GetLogRow))
    (bind place (- row (Variables|Default|GetLogFirst)))
    (bind chosen (== row (Variables|Default|GetLogIndex)))
    (Variables|Default|SetLogField 0)
    (for field (Utilities|String|ParseIntoArray :SourceString entry :Delimiter "^" :CullEmptyStrings false)
      (bind which (Variables|Default|GetLogField))
      (if (and (== which 1) (and (>= place 0) (< place 10)))
        (if chosen
          (HUD|DrawRect :RectColor "(R=1.0,G=0.8,B=0.4,A=0.14)" :ScreenX (* u 66.0) :ScreenY (* u (+ 150.0 (* 36.0 (Math|Conversions|ToFloat(Integer) place)))) :ScreenW (* u 620.0) :ScreenH (* u 34.0)))
        """+text('field','(* u 40.0)','(* u (+ 160.0 (* 36.0 (Math|Conversions|ToFloat(Integer) place))))','(* u 1.3)','(Utilities|Struct|MakeLinearColor :R (select chosen 1.0 0.62) :G (select chosen 0.82 0.68) :B (select chosen 0.42 0.74) :A 1.0)')+""")
      (if (and chosen (== which 0))
        """+text('field','(* u 790.0)','(* u 160.0)','(* u 1.1)',TEAL)+""")
      (if (and chosen (== which 2))
        (CallFunction|DrawLines :Message field :X (* u 790.0) :Y (* u 215.0) :Scale (* u 1.3) :Step (* u 32.0) :Red 1.0 :Green 0.92 :Blue 0.78))
      (Variables|Default|SetLogField (+ which 1)))
    (Variables|Default|SetLogRow (+ row 1))))""")
comp(H)
M=B+'BP_MenuHUD.BP_MenuHUD'
m=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/menu.py').read()
_text=text
text=lambda *a, **k: _text(*a, **k).replace('CallFunction|DrawTextPlate', 'CallFunction|MenuTextPlate')
exec(m[m.index('def hit('):m.index("print('events'")].replace("hit('Enter','SpaceBar'","hit('E','Enter','SpaceBar'").replace('(len(label)*7.4)','(len(label)*9.2)').replace("len(label)*7.4","len(label)*9.2").replace("(* u 210.0)","(* u 300.0)").replace("(* u 420.0)","(* u 600.0)").replace(":ScreenH (* u 64.0)",":ScreenH (* u 72.0)").replace("(y+13)","(y+8)").replace("'(* u 2.1)'","'(* u 2.2)'").replace("row('New Game',0,700)","row('New Game',0,680)").replace("row('Exit Game',1,780)","row('Exit Game',1,790)"))
text=_text
comp(M)
