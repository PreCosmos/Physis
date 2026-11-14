{"returnValue":"(fn DrawLines (Message X Y Scale Step Red Green Blue)
  (Variables|Default|SetLineY Y)
  (for _array_element (Utilities|String|ParseIntoArray Message "~" false)
    (HUD|DrawText _array_element (Utilities|Struct|MakeLinearColor Red Green Blue 1.0) X (Variables|Default|GetLineY) "/Game/UI/F_Physis.F_Physis" Scale)
    (Variables|Default|SetLineY (+ (Variables|Default|GetLineY) Step))))
"}