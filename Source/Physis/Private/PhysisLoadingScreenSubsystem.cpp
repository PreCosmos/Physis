#include "PhysisLoadingScreenSubsystem.h"

#include <atomic>

#include "Brushes/SlateColorBrush.h"
#include "ContentStreaming.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LevelStreaming.h"
#include "Engine/World.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/IInputProcessor.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/PackageName.h"
#include "MoviePlayer.h"
#include "PipelineStateCache.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "ShaderPipelineCache.h"
#include "Styling/CoreStyle.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/SLeafWidget.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#endif

DEFINE_LOG_CATEGORY_STATIC(LogPhysisLoading, Log, All);

static TAutoConsoleVariable<int32> CVarPhysisLoadingScreen(
	TEXT("physis.LoadingScreen"),
	1,
	TEXT("Physis loading screen. 0: off. 1: on in the game, off in Play-In-Editor (default). 2: on everywhere."),
	ECVF_Default);

namespace PhysisLoading
{
	// Share of the bar for the map load itself; the rest follows the work that settles after it.
	constexpr float LoadShare = 0.8f;
	// After the load the screen stays at least this long: a loaded save is restored in the first frames.
	constexpr double MinHold = 0.6;
	// It goes once no work has been pending for this long and this many frames,
	constexpr double NeedCalmSeconds = 0.5;
	constexpr int32 NeedCalmFrames = 12;
	// or once the pending work has not fallen for this long (a count that never empties),
	constexpr double StallSeconds = 5.0;
	// and after this long at the most.
	constexpr double MaxHold = 30.0;
	// The world runs this many frames under the screen before it is paused, so first-frame logic has run.
	constexpr int32 FramesBeforePause = 2;
	// The full bar shows this long, then the screen fades out.
	constexpr double FullHold = 0.15;
	constexpr double FadeSeconds = 0.45;
	// A map load is timed at this many seconds until this machine has loaded that map once.
	constexpr double DefaultExpected = 8.0;
	const TCHAR* const ConfigSection = TEXT("Physis.LoadingScreen");

	const FLinearColor Gold(1.0f, 0.82f, 0.42f, 1.0f);
	const FLinearColor Mist(0.62f, 0.66f, 0.72f, 1.0f);

	FString TitleFor(const FString& Map)
	{
		if (Map == TEXT("L_BattleStation"))
		{
			return TEXT("Meridian Station");
		}
		if (Map == TEXT("L_CenterOfTheUniverse"))
		{
			return TEXT("Center of the Universe");
		}
		if (Map == TEXT("L_Conclave"))
		{
			return TEXT("The Conclave");
		}
		if (Map == TEXT("L_Grove"))
		{
			return TEXT("Earth");
		}
		if (Map == TEXT("L_Arche"))
		{
			return TEXT("Arche");
		}
		return FString();
	}

	bool IsWanted()
	{
		const int32 Mode = CVarPhysisLoadingScreen.GetValueOnGameThread();
		return Mode >= 2 || (Mode == 1 && !GIsEditor);
	}
}

/** What the screens show. Title, Start and Expected are set before any screen exists and only read afterwards. */
struct FPhysisLoadProgress
{
	FString Title;
	double Start = 0.0;
	double Expected = PhysisLoading::DefaultExpected;
	/** FPlatformTime seconds when the map finished loading; 0 while it loads. */
	std::atomic<double> LoadEnd{0.0};
	/** After the load: the share of the settling work that is done, 0 to 1. */
	std::atomic<float> WorkDone{0.f};
	/** Set once the work has settled: the bar fills, and the screen fades out from this time. */
	std::atomic<double> FadeStart{0.0};
	/** The fill last drawn, so the screen that takes over after the load continues from it. */
	std::atomic<float> Shown{0.f};
};

/**
 * The screen itself: deep navy, the destination in gold, a thin gold bar and LOADING under it. Everything is laid
 * out on a 1080-high reference and scaled to the window. During the map load it is drawn by the loading thread,
 * so it reads only its own fields and the progress atomics.
 */
class SPhysisLoadingScreen final : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SPhysisLoadingScreen) {}
		SLATE_ARGUMENT(TSharedPtr<FPhysisLoadProgress>, Progress)
		SLATE_ARGUMENT(const UFont*, Font)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		Progress = InArgs._Progress;
		check(Progress.IsValid());
		Shown = Progress->Shown.load();
		LastPaint = FPlatformTime::Seconds();
		TitleFont = InArgs._Font ? FSlateFontInfo(InArgs._Font, 30.f) : FCoreStyle::GetDefaultFontStyle(TEXT("Regular"), 30.f);
		TitleFont.LetterSpacing = 160;
		CaptionFont = InArgs._Font ? FSlateFontInfo(InArgs._Font, 12.f) : FCoreStyle::GetDefaultFontStyle(TEXT("Regular"), 12.f);
		CaptionFont.LetterSpacing = 420;
		// Measured once here, on the game thread; the loading thread only draws.
		const TSharedRef<FSlateFontMeasure> Measure = FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
		TitleSize = Measure->Measure(Progress->Title, TitleFont);
		CaptionSize = Measure->Measure(Caption, CaptionFont);
	}

	virtual FVector2D ComputeDesiredSize(float) const override
	{
		return FVector2D(1920.0, 1080.0);
	}

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override
	{
		using namespace PhysisLoading;
		const double Now = FPlatformTime::Seconds();
		const float Dt = static_cast<float>(FMath::Clamp(Now - LastPaint, 0.0, 0.25));
		LastPaint = Now;

		// The bar eases towards its target, so steps in the work read as motion, and never runs backwards.
		const float Goal = Target(Now);
		Shown = FMath::Max(Shown, Shown + (Goal - Shown) * (1.f - FMath::Exp(-7.f * Dt)));
		Progress->Shown.store(Shown);

		const double FadeStart = Progress->FadeStart.load();
		const float Out = FadeStart > 0.0 ? 1.f - static_cast<float>(FMath::Clamp((Now - FadeStart) / FadeSeconds, 0.0, 1.0)) : 1.f;
		const float Ink = Out * static_cast<float>(FMath::Clamp((Now - Progress->Start) / 0.25, 0.0, 1.0));

		const FVector2f Size = AllottedGeometry.GetLocalSize();
		if (Size.X < 2.f || Size.Y < 2.f)
		{
			return LayerId;
		}
		const float U = Size.Y / 1080.f;
		const float Cx = Size.X / U * 0.5f;
		const auto Rect = [&AllottedGeometry, U](float X, float Y, float W, float H)
		{
			return AllottedGeometry.ToPaintGeometry(FVector2f(W, H), FSlateLayoutTransform(U, FVector2f(X * U, Y * U)));
		};

		// Background: deep navy, a little lighter at the middle where the title and bar sit.
		TArray<FSlateGradientStop> Stops;
		Stops.Emplace(FVector2f(0.f, 0.f), FLinearColor(0.002f, 0.004f, 0.012f, Out));
		Stops.Emplace(FVector2f(0.f, Size.Y * 0.5f), FLinearColor(0.010f, 0.020f, 0.050f, Out));
		Stops.Emplace(FVector2f(0.f, Size.Y), FLinearColor(0.001f, 0.002f, 0.008f, Out));
		FSlateDrawElement::MakeGradient(OutDrawElements, LayerId, AllottedGeometry.ToPaintGeometry(), MoveTemp(Stops), Orient_Horizontal);

		const float BarW = 560.f;
		const float BarH = 3.f;
		const float BarX = Cx - BarW * 0.5f;
		const float BarY = 540.f;
		if (!Progress->Title.IsEmpty())
		{
			FSlateDrawElement::MakeText(OutDrawElements, LayerId + 1, Rect(Cx - TitleSize.X * 0.5f, BarY - 30.f - TitleSize.Y, TitleSize.X, TitleSize.Y),
				Progress->Title, TitleFont, ESlateDrawEffect::None, Gold.CopyWithNewOpacity(Ink));
		}
		FSlateDrawElement::MakeBox(OutDrawElements, LayerId + 1, Rect(BarX, BarY, BarW, BarH), &White, ESlateDrawEffect::None, Mist.CopyWithNewOpacity(0.22f * Ink));
		const float Fill = BarW * FMath::Clamp(Shown, 0.f, 1.f);
		if (Fill > 0.5f)
		{
			FSlateDrawElement::MakeBox(OutDrawElements, LayerId + 2, Rect(BarX, BarY - 3.f, Fill, BarH + 6.f), &White, ESlateDrawEffect::None, Gold.CopyWithNewOpacity(0.14f * Ink));
			FSlateDrawElement::MakeBox(OutDrawElements, LayerId + 3, Rect(BarX, BarY, Fill, BarH), &White, ESlateDrawEffect::None, Gold.CopyWithNewOpacity(Ink));
			// A soft light runs along the filled part, so the bar never looks frozen while the work is slow.
			const float Sweep = 96.f;
			const float Head = static_cast<float>(FMath::Fmod((Now - Progress->Start) * 280.0, static_cast<double>(Fill + Sweep)));
			const int32 Slices = 8;
			for (int32 Slice = 0; Slice < Slices; ++Slice)
			{
				const float From = FMath::Max(0.f, Head - Sweep + Sweep * Slice / Slices);
				const float To = FMath::Min(Fill, Head - Sweep + Sweep * (Slice + 1) / Slices);
				if (To > From)
				{
					const float Peak = 1.f - FMath::Abs((Slice + 0.5f) / Slices * 2.f - 1.f);
					FSlateDrawElement::MakeBox(OutDrawElements, LayerId + 4, Rect(BarX + From, BarY, To - From, BarH), &White, ESlateDrawEffect::None,
						FLinearColor(1.f, 0.96f, 0.86f, 0.7f * Peak * Ink));
				}
			}
		}
		FSlateDrawElement::MakeText(OutDrawElements, LayerId + 1, Rect(Cx - CaptionSize.X * 0.5f, BarY + 22.f, CaptionSize.X, CaptionSize.Y),
			Caption, CaptionFont, ESlateDrawEffect::None, Mist.CopyWithNewOpacity(0.8f * Ink));
		return LayerId + 4;
	}

private:
	virtual bool ComputeVolatility() const override
	{
		return true;
	}

	float Target(double Now) const
	{
		using namespace PhysisLoading;
		if (Progress->LoadEnd.load() <= 0.0)
		{
			// Timed from the last load of this map: straight to 90 % of the load share at 90 % of the expected time,
			// then easing on, so a slower load never stops the bar dead.
			const double X = (Now - Progress->Start) / FMath::Max(Progress->Expected, 0.5);
			const double Curve = X < 0.9 ? X : 0.9 + 0.1 * (1.0 - FMath::Exp(-(X - 0.9) / 0.1));
			return LoadShare * static_cast<float>(Curve);
		}
		if (Progress->FadeStart.load() > 0.0)
		{
			return 1.f;
		}
		return FMath::Min(0.97f, LoadShare + (1.f - LoadShare) * Progress->WorkDone.load());
	}

	TSharedPtr<FPhysisLoadProgress> Progress;
	FSlateFontInfo TitleFont;
	FSlateFontInfo CaptionFont;
	FVector2f TitleSize = FVector2f::ZeroVector;
	FVector2f CaptionSize = FVector2f::ZeroVector;
	FString Caption = TEXT("LOADING");
	FSlateColorBrush White = FSlateColorBrush(FLinearColor::White);
	mutable float Shown = 0.f;
	mutable double LastPaint = 0.0;
};

/** Holds the player's input while the screen covers the new level. Key releases pass, so no key stays pressed. */
class FPhysisInputBlocker final : public IInputProcessor
{
public:
	virtual void Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor) override {}
	virtual bool HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override { return true; }
	virtual bool HandleAnalogInputEvent(FSlateApplication& SlateApp, const FAnalogInputEvent& InAnalogInputEvent) override { return true; }
	virtual bool HandleMouseMoveEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override { return true; }
	virtual bool HandleMouseButtonDownEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override { return true; }
	virtual bool HandleMouseButtonDoubleClickEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override { return true; }
	virtual bool HandleMouseWheelOrGestureEvent(FSlateApplication& SlateApp, const FPointerEvent& InWheelEvent, const FPointerEvent* InGestureEvent) override { return true; }
	virtual const TCHAR* GetDebugName() const override { return TEXT("PhysisLoadingScreen"); }
};

UPhysisLoadingScreenSubsystem::UPhysisLoadingScreenSubsystem() = default;
UPhysisLoadingScreenSubsystem::~UPhysisLoadingScreenSubsystem() = default;

void UPhysisLoadingScreenSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (IsRunningDedicatedServer() || IsRunningCommandlet() || !FSlateApplication::IsInitialized())
	{
		return;
	}
	Font = LoadObject<UFont>(nullptr, TEXT("/Game/UI/F_Physis.F_Physis"));
	// PreLoadMapWithContext comes before PreLoadMap, where the MoviePlayer starts the screen we set up.
	PreLoadHandle = FCoreUObjectDelegates::PreLoadMapWithContext.AddUObject(this, &UPhysisLoadingScreenSubsystem::OnPreLoadMap);
	PostLoadHandle = FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this, &UPhysisLoadingScreenSubsystem::OnPostLoadMap);
}

void UPhysisLoadingScreenSubsystem::Deinitialize()
{
	FCoreUObjectDelegates::PreLoadMapWithContext.Remove(PreLoadHandle);
	FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(PostLoadHandle);
	PreLoadHandle.Reset();
	PostLoadHandle.Reset();
	EndHold();
	Progress.Reset();
	Font = nullptr;
	Super::Deinitialize();
}

void UPhysisLoadingScreenSubsystem::OnPreLoadMap(const FWorldContext& WorldContext, const FString& MapName)
{
	using namespace PhysisLoading;
	if (WorldContext.OwningGameInstance != GetGameInstance() || !IsWanted())
	{
		return;
	}
	// A new load while the last screen still holds: that screen goes at once.
	EndHold();
	LoadingMap = FPackageName::GetShortName(MapName);
	LoadStart = FPlatformTime::Seconds();
	Progress = MakeShared<FPhysisLoadProgress>();
	Progress->Title = TitleFor(LoadingMap);
	Progress->Start = LoadStart;
	double Learned = 0.0;
	if (GConfig && GConfig->GetDouble(ConfigSection, *LoadingMap, Learned, GGameUserSettingsIni) && Learned > 0.1)
	{
		Progress->Expected = Learned;
	}
	IGameMoviePlayer* Movie = GetMoviePlayer();
	if (Movie && IsMoviePlayerEnabled() && !Movie->IsMovieCurrentlyPlaying())
	{
		FLoadingScreenAttributes Screen;
		Screen.bAutoCompleteWhenLoadingCompletes = true;
		Screen.bMoviesAreSkippable = false;
		Screen.bWaitForManualStop = false;
		Screen.bAllowEngineTick = false;
		Screen.MinimumLoadingScreenDisplayTime = -1.f;
		Screen.WidgetLoadingScreen = SNew(SPhysisLoadingScreen).Progress(Progress).Font(Font.Get());
		Movie->SetupLoadingScreen(Screen);
	}
}

void UPhysisLoadingScreenSubsystem::OnPostLoadMap(UWorld* World)
{
	using namespace PhysisLoading;
	if (!Progress.IsValid() || Progress->LoadEnd.load() > 0.0)
	{
		return;
	}
	if (World == nullptr)
	{
		// The load failed; the engine goes back to its default map, which loads with its own screen.
		EndHold();
		return;
	}
	if (World->GetGameInstance() != GetGameInstance())
	{
		return;
	}
	const double Now = FPlatformTime::Seconds();
	const double Took = Now - LoadStart;
	UE_LOG(LogPhysisLoading, Log, TEXT("%s loaded in %.2f s (bar timed for %.2f s)."), *LoadingMap, Took, Progress->Expected);
	// The next load of this map is timed from this one (weighted towards the newest).
	if (GConfig && !LoadingMap.IsEmpty() && Took > 0.05)
	{
		double Before = 0.0;
		const bool bHad = GConfig->GetDouble(ConfigSection, *LoadingMap, Before, GGameUserSettingsIni) && Before > 0.1;
		GConfig->SetDouble(ConfigSection, *LoadingMap, bHad ? Before * 0.4 + Took * 0.6 : Took, GGameUserSettingsIni);
		GConfig->Flush(false, GGameUserSettingsIni);
	}
	Progress->LoadEnd.store(Now);

	HoldWorld = World;
	HoldStart = Now;
	LastProgress = Now;
	CalmSince = 0.0;
	FadeEnd = 0.0;
	HoldFrames = 0;
	CalmFrames = 0;
	MostWork = 0;
	LastWork = 0;
	bPausedWorld = false;
	bSettled = false;
	if (UGameViewportClient* Viewport = World->GetGameViewport())
	{
		Overlay = SNew(SPhysisLoadingScreen).Progress(Progress).Font(Font.Get());
		Viewport->AddViewportWidgetContent(Overlay.ToSharedRef(), 10000);
		OverlayViewport = Viewport;
	}
	// Held input: in a packaged game only, so Play-In-Editor never loses the editor's keys.
	if (!GIsEditor && FSlateApplication::IsInitialized())
	{
		InputBlocker = MakeShared<FPhysisInputBlocker>();
		FSlateApplication::Get().RegisterInputPreProcessor(InputBlocker);
	}
	HoldTicker = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UPhysisLoadingScreenSubsystem::TickHold));
}

bool UPhysisLoadingScreenSubsystem::TickHold(float DeltaSeconds)
{
	using namespace PhysisLoading;
	UWorld* World = HoldWorld.Get();
	if (World == nullptr || !Progress.IsValid())
	{
		HoldTicker.Reset();
		EndHold();
		return false;
	}
	const double Now = FPlatformTime::Seconds();
	++HoldFrames;
	if (bSettled)
	{
		if (Now >= FadeEnd)
		{
			HoldTicker.Reset();
			EndHold();
			return false;
		}
		return true;
	}
	// Paused after its first frames, the world waits for the screen: the opening sequence, timers and enemies start
	// when the player can see them. Rendering, streaming and shader work go on while paused.
	if (HoldFrames == FramesBeforePause && !GIsEditor && !World->IsPaused())
	{
		bPausedWorld = UGameplayStatics::SetGamePaused(World, true);
	}
	const int32 Work = CountPendingWork(World);
	MostWork = FMath::Max(MostWork, Work);
	if (Work == 0 || Work < LastWork)
	{
		LastProgress = Now;
	}
	LastWork = Work;
	Progress->WorkDone.store(MostWork > 0 ? 1.f - static_cast<float>(Work) / static_cast<float>(MostWork) : 1.f);
	if (Work == 0)
	{
		CalmSince = CalmSince > 0.0 ? CalmSince : Now;
		++CalmFrames;
	}
	else
	{
		CalmSince = 0.0;
		CalmFrames = 0;
	}
	const double Held = Now - HoldStart;
	if (Held < MinHold || HoldFrames <= FramesBeforePause)
	{
		return true;
	}
	if (CalmSince > 0.0 && Now - CalmSince >= NeedCalmSeconds && CalmFrames >= NeedCalmFrames)
	{
		Settle(World, Now, TEXT("settled"), Work);
	}
	else if (Now - LastProgress >= StallSeconds)
	{
		Settle(World, Now, TEXT("pending work stopped falling"), Work);
	}
	else if (Held >= MaxHold)
	{
		Settle(World, Now, TEXT("time limit"), Work);
	}
	return true;
}

void UPhysisLoadingScreenSubsystem::Settle(UWorld* World, double Now, const TCHAR* Reason, int32 Work)
{
	using namespace PhysisLoading;
	bSettled = true;
	Progress->WorkDone.store(1.f);
	Progress->FadeStart.store(Now + FullHold);
	FadeEnd = Now + FullHold + FadeSeconds;
	UE_LOG(LogPhysisLoading, Log, TEXT("%s ready %.2f s after loading, %d frames (%s; %d pending, %d at most)."),
		*LoadingMap, Now - HoldStart, HoldFrames, Reason, Work, MostWork);
	// The world starts as the full bar shows and fades.
	ReleaseWorld(World);
}

void UPhysisLoadingScreenSubsystem::ReleaseWorld(UWorld* World)
{
	if (InputBlocker.IsValid())
	{
		if (FSlateApplication::IsInitialized())
		{
			FSlateApplication::Get().UnregisterInputPreProcessor(InputBlocker);
		}
		InputBlocker.Reset();
	}
	if (bPausedWorld)
	{
		bPausedWorld = false;
		// Only our own pause is undone: if something unpaused the world meanwhile, it stays as it is.
		if (World != nullptr && World->IsPaused())
		{
			UGameplayStatics::SetGamePaused(World, false);
		}
	}
}

void UPhysisLoadingScreenSubsystem::EndHold()
{
	if (HoldTicker.IsValid())
	{
		FTSTicker::GetCoreTicker().RemoveTicker(HoldTicker);
		HoldTicker.Reset();
	}
	ReleaseWorld(HoldWorld.Get());
	if (Overlay.IsValid())
	{
		if (UGameViewportClient* Viewport = OverlayViewport.Get())
		{
			Viewport->RemoveViewportWidgetContent(Overlay.ToSharedRef());
		}
		Overlay.Reset();
	}
	OverlayViewport.Reset();
	HoldWorld.Reset();
	bSettled = false;
}

int32 UPhysisLoadingScreenSubsystem::CountPendingWork(UWorld* World) const
{
	// Packages still loading, shader pipelines still compiling (precache requests and the bundled cache).
	int64 Work = GetNumAsyncPackages();
	Work += PipelineStateCache::NumActivePrecacheRequests();
	Work += FShaderPipelineCache::NumPrecompilesRemaining();
	// Texture and mesh mips asked for and not yet in memory. With a tiny time limit this counts; it does not wait.
	if (!IStreamingManager::HasShutdown() && IStreamingManager::Get().IsRenderAssetStreamingEnabled(EStreamableRenderAssetType::None))
	{
		Work += IStreamingManager::Get().GetRenderAssetStreamingManager().BlockTillAllRequestsFinished(1e-7f, false);
	}
	for (const ULevelStreaming* Level : World->GetStreamingLevels())
	{
		if (Level != nullptr && Level->IsStreamingStatePending())
		{
			++Work;
		}
	}
#if WITH_EDITOR
	// An uncooked run (-game from the editor) also compiles shaders and assets on demand.
	if (GShaderCompilingManager != nullptr)
	{
		Work += GShaderCompilingManager->GetNumRemainingJobs();
	}
	Work += FAssetCompilingManager::Get().GetNumRemainingAssets();
#endif
	return static_cast<int32>(FMath::Min<int64>(Work, MAX_int32));
}
