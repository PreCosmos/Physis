(fn PhysisEquip ()
  (Transformation|AttachComponentToComponent :self (Variables|Default|GetKatana) :Parent (Variables|Default|GetBody) :SocketName "hand_r" :LocationRule "KeepRelative" :RotationRule "KeepRelative" :ScaleRule "KeepRelative" :bWeldSimulatedBodies false))
