{"returnValue":"(fn MeasureLine (Line Scale Icon)
  (Variables|Default|SetTutorialIcon false)
  (Variables|Default|SetLineWidth 0.0)
  (for _array_element (Utilities|String|ParseIntoArray Line "|" false)
    (Variables|Default|SetLineWidth (+ (Variables|Default|GetLineWidth) (select (Variables|Default|GetTutorialIcon) Icon (HUD|GetTextSize _array_element "/Game/UI/F_Physis.F_Physis" Scale))))
    (Variables|Default|SetTutorialIcon (not (Variables|Default|GetTutorialIcon))))
  (Variables|Default|SetWidestLine (select (> (Variables|Default|GetLineWidth) (Variables|Default|GetWidestLine)) (Variables|Default|GetLineWidth) (Variables|Default|GetWidestLine)))
  (Variables|Default|SetLineCount (+ (Variables|Default|GetLineCount) 1)))
"}