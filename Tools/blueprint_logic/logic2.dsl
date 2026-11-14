(fn PhysisMove ()
  (bind (x y) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_Move)))
  (bind facing (Math|Rotator|MakeRotator :Yaw (.yaw (Pawn|GetControlRotation))))
  (Pawn|Input|AddMovementInput :WorldDirection (Math|Vector|GetForwardVector facing) :ScaleValue y)
  (Pawn|Input|AddMovementInput :WorldDirection (Math|Vector|GetRightVector facing) :ScaleValue x))

(fn PhysisLookStick ()
  (bind (x y) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_Look)))
  (Pawn|Input|AddControllerYawInput :Val x)
  (Pawn|Input|AddControllerPitchInput :Val (- y)))

(fn PhysisLookMouse ()
  (bind (x y) (Math|Vector2D|BreakVector2D (Input|EnhancedActionValues|IA_MouseLook)))
  (Pawn|Input|AddControllerYawInput :Val x)
  (Pawn|Input|AddControllerPitchInput :Val y))

(fn PhysisSprintOn ()
  (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (Variables|Character|GetCharacterMovement) :MaxWalkSpeed 650.0))

(fn PhysisSprintOff ()
  (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (Variables|Character|GetCharacterMovement) :MaxWalkSpeed 400.0))

(fn PhysisDodge ()
  (bind anim (Components|SkeletalMesh|GetAnimInstance (Variables|Default|GetBody)))
  (Animation|Montage|MontagePlay anim "/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Dodge.AM_Physis_Dodge")
  (Character|LaunchCharacter :LaunchVelocity (* (Transformation|GetActorForwardVector) 900.0) :bXYOverride true))
