#include "PhysisSteamInputSubsystem.h"

#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/CoreMisc.h"
#include "Misc/Paths.h"

#if PHYSIS_WITH_STEAM && defined(STEAM_SDK_INSTALLED)
#include "SteamSharedModule.h"
THIRD_PARTY_INCLUDES_START
#include <steam/steam_api.h>
#include <steam/isteaminput.h>
THIRD_PARTY_INCLUDES_END
#define PHYSIS_STEAM_INPUT 1
#else
#define PHYSIS_STEAM_INPUT 0
#endif

DEFINE_LOG_CATEGORY_STATIC(LogPhysisSteamInput, Log, All);

UPhysisSteamInputSubsystem::UPhysisSteamInputSubsystem() = default;
UPhysisSteamInputSubsystem::~UPhysisSteamInputSubsystem() = default;

#if PHYSIS_STEAM_INPUT
namespace
{
	// HUD button tokens (the |TOKEN| names in prompts) and the Xbox origin each one stands for.
	struct FPadToken { const TCHAR* Token; EXboxOrigin Origin; };
	const FPadToken PadTokens[] = {
		{ TEXT("A"), k_EXboxOrigin_A }, { TEXT("B"), k_EXboxOrigin_B }, { TEXT("X"), k_EXboxOrigin_X }, { TEXT("Y"), k_EXboxOrigin_Y },
		{ TEXT("LB"), k_EXboxOrigin_LeftBumper }, { TEXT("RB"), k_EXboxOrigin_RightBumper },
		{ TEXT("LT"), k_EXboxOrigin_LeftTrigger_Pull }, { TEXT("RT"), k_EXboxOrigin_RightTrigger_Pull },
		{ TEXT("LS"), k_EXboxOrigin_LeftStick_Move }, { TEXT("RS"), k_EXboxOrigin_RightStick_Move },
		{ TEXT("L3"), k_EXboxOrigin_LeftStick_Click }, { TEXT("R3"), k_EXboxOrigin_RightStick_Click },
		{ TEXT("DU"), k_EXboxOrigin_DPad_North }, { TEXT("DD"), k_EXboxOrigin_DPad_South },
		{ TEXT("DL"), k_EXboxOrigin_DPad_West }, { TEXT("DR"), k_EXboxOrigin_DPad_East },
		{ TEXT("Menu"), k_EXboxOrigin_Menu }, { TEXT("View"), k_EXboxOrigin_View },
	};

	FString FamilyFor(int32 Type)
	{
		switch (Type)
		{
		case k_ESteamInputType_XBox360Controller:
		case k_ESteamInputType_XBoxOneController: return TEXT("Xbox");
		case k_ESteamInputType_PS3Controller:
		case k_ESteamInputType_PS4Controller:
		case k_ESteamInputType_PS5Controller: return TEXT("PlayStation");
		case k_ESteamInputType_SwitchProController:
		case k_ESteamInputType_SwitchJoyConPair:
		case k_ESteamInputType_SwitchJoyConSingle: return TEXT("Switch");
		case k_ESteamInputType_SteamDeckController: return TEXT("SteamDeck");
		case k_ESteamInputType_SteamController: return TEXT("SteamController");
		default: return TEXT("Generic");
		}
	}
}
#endif

void UPhysisSteamInputSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
#if PHYSIS_STEAM_INPUT
	// Play-in-editor must never start Steam: that would attach the editor process to the app.
	if (GIsEditor && !IsRunningGame())
	{
		return;
	}
	if (!FSteamSharedModule::IsAvailable())
	{
		UE_LOG(LogPhysisSteamInput, Log, TEXT("SteamShared not available; using built-in glyphs."));
		return;
	}
	SteamHandle = FSteamSharedModule::Get().ObtainSteamClientInstanceHandle();
	if (!SteamHandle.IsValid() || SteamInput() == nullptr)
	{
		UE_LOG(LogPhysisSteamInput, Log, TEXT("Steam is not running; using built-in glyphs."));
		SteamHandle.Reset();
		return;
	}
	// We call RunFrame ourselves on the game thread, so Steam Input state is fresh every frame.
	SteamInput()->Init(true);
	bRunning = true;
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UPhysisSteamInputSubsystem::Tick));
	UE_LOG(LogPhysisSteamInput, Log, TEXT("Steam Input initialised."));
#endif
}

void UPhysisSteamInputSubsystem::Deinitialize()
{
	if (TickHandle.IsValid())
	{
		FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
		TickHandle.Reset();
	}
#if PHYSIS_STEAM_INPUT
	if (bRunning && FSteamSharedModule::IsAvailable() && FSteamSharedModule::Get().AreSteamDllsLoaded() && SteamInput() != nullptr)
	{
		SteamInput()->Shutdown();
	}
#endif
	bRunning = false;
	SteamHandle.Reset();
	Glyphs.Reset();
	Super::Deinitialize();
}

bool UPhysisSteamInputSubsystem::Tick(float DeltaSeconds)
{
#if PHYSIS_STEAM_INPUT
	if (bRunning && SteamInput() != nullptr)
	{
		SteamInput()->RunFrame();
		SinceRefresh += DeltaSeconds;
		if (SinceRefresh >= 0.5f)
		{
			SinceRefresh = 0.f;
			Refresh();
		}
	}
#endif
	return true;
}

void UPhysisSteamInputSubsystem::Refresh()
{
#if PHYSIS_STEAM_INPUT
	ISteamInput* Input = SteamInput();
	if (Input == nullptr)
	{
		return;
	}
	InputHandle_t Handles[STEAM_INPUT_MAX_COUNT] = {};
	const int32 Count = Input->GetConnectedControllers(Handles);
	InputHandle_t Handle = Input->GetControllerForGamepadIndex(0);
	if (Handle == 0 && Count > 0)
	{
		Handle = Handles[0];
	}
	if (Handle == 0)
	{
		if (ActiveHandle != 0)
		{
			ActiveHandle = 0;
			ActiveType = -1;
			Family = TEXT("None");
			Glyphs.Reset();
		}
		return;
	}
	const int32 Type = static_cast<int32>(Input->GetInputTypeForHandle(Handle));
	if (Handle == ActiveHandle && Type == ActiveType)
	{
		return;
	}
	ActiveHandle = Handle;
	ActiveType = Type;
	Family = FamilyFor(Type);
	Glyphs.Reset();
	for (const FPadToken& Pad : PadTokens)
	{
		EInputActionOrigin Origin = Input->GetActionOriginFromXboxOrigin(Handle, Pad.Origin);
		if (static_cast<int32>(Origin) >= static_cast<int32>(k_EInputActionOrigin_Count))
		{
			Origin = Input->TranslateActionOrigin(k_ESteamInputType_Unknown, Origin);
		}
		if (Origin == k_EInputActionOrigin_None)
		{
			continue;
		}
		const char* Path = Input->GetGlyphPNGForActionOrigin(Origin, k_ESteamInputGlyphSize_Medium, static_cast<uint32>(ESteamInputGlyphStyle_Light));
		const FString File = Path ? FString(UTF8_TO_TCHAR(Path)) : FString();
		if (File.IsEmpty() || !FPaths::FileExists(File))
		{
			continue;
		}
		if (UTexture2D* Texture = FImageUtils::ImportFileAsTexture2D(File))
		{
			Texture->Filter = TF_Bilinear;
			Texture->LODGroup = TEXTUREGROUP_UI;
			Texture->UpdateResource();
			Glyphs.Add(Pad.Token, Texture);
		}
	}
	UE_LOG(LogPhysisSteamInput, Log, TEXT("Controller %s: %d glyphs loaded."), *Family, Glyphs.Num());
#endif
}

UTexture2D* UPhysisSteamInputSubsystem::GetGlyph(const FString& Token) const
{
	const TObjectPtr<UTexture2D>* Found = Glyphs.Find(Token);
	return Found ? Found->Get() : nullptr;
}
