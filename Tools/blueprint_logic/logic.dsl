(fn PhysisMove ()
  (bind (x y) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_Move)))
  (bind facing (Math|Rotator|MakeRotator :Yaw (.yaw (Pawn|GetControlRotation))))
  (Pawn|Input|AddMovementInput (Math|Vector|GetForwardVector facing) y)
  (Pawn|Input|AddMovementInput (Math|Vector|GetRightVector facing) x))

(fn PhysisLookStick ()
  (bind (x y) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_Look)))
  (Pawn|Input|AddControllerYawInput x)
  (Pawn|Input|AddControllerPitchInput (- y)))

(fn PhysisLookMouse ()
  (bind (x y) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_MouseLook)))
  (Pawn|Input|AddControllerYawInput x)
  (Pawn|Input|AddControllerPitchInput y))

(fn PhysisSprintOn ()
  (Class|CharacterMovementComponent|SetMaxWalkSpeed (Variables|Character|GetCharacterMovement) 650.0))

(fn PhysisSprintOff ()
  (Class|CharacterMovementComponent|SetMaxWalkSpeed (Variables|Character|GetCharacterMovement) 400.0))

(fn PhysisAttack ()
  (bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))
  (Animation|Montage|MontagePlay anim "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Slash.AM_Physis_Slash"))

(fn PhysisDodge ()
  (bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))
  (Animation|Montage|MontagePlay anim "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Dodge.AM_Physis_Dodge")
  (Character|LaunchCharacter (* (Transformation|GetActorForwardVector) 900.0) true false))

(fn PhysisScan ()
  (Development|PrintString "Scan Visor placeholder"))

(fn PhysisInteract ()
  (Development|PrintString "Interact placeholder"))
