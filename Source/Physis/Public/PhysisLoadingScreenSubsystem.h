#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "PhysisLoadingScreenSubsystem.generated.h"

class IInputProcessor;
class SWidget;
class UFont;
class UGameViewportClient;
struct FPhysisLoadProgress;
struct FWorldContext;

/**
 * The loading screen for every level load: New Game, Continue and Load Game from the menus, the Divinity currents
 * between levels, and the reload after a death (author, 2026-11-07: "some form of loading bar needs to appear until
 * everything is loaded").
 *
 * Two parts with the same look:
 * 1. While the map loads the game thread is blocked, so the engine's MoviePlayer shows the screen from its own
 *    thread and the bar keeps moving. That part of the bar is timed from how long this map took to load last time
 *    on this machine (GameUserSettings.ini, [Physis.LoadingScreen]).
 * 2. After the load the same screen stays over the new level until its work has settled: packages still loading,
 *    shader pipelines still compiling, texture and mesh mips still streaming in, and in the editor shaders and assets
 *    still compiling. This part of the bar follows that work. The world is paused and input is held meanwhile (in a
 *    packaged game, not in Play-In-Editor), so nothing happens unseen; then the screen fades out.
 *
 * MoviePlayer does not run in the editor, so Play-In-Editor shows only the second part, and only after an
 * OpenLevel inside Play (Play itself does not load a map).
 */
UCLASS()
class PHYSIS_API UPhysisLoadingScreenSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	UPhysisLoadingScreenSubsystem();
	virtual ~UPhysisLoadingScreenSubsystem() override;

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

private:
	void OnPreLoadMap(const FWorldContext& WorldContext, const FString& MapName);
	void OnPostLoadMap(UWorld* World);
	bool TickHold(float DeltaSeconds);
	void Settle(UWorld* World, double Now, const TCHAR* Reason, int32 Work);
	void ReleaseWorld(UWorld* World);
	void EndHold();
	int32 CountPendingWork(UWorld* World) const;

	/** F_Physis, the game's font. Held here so it is never collected while the loading thread draws with it. */
	UPROPERTY(Transient)
	TObjectPtr<UFont> Font;

	TSharedPtr<FPhysisLoadProgress> Progress;
	TSharedPtr<SWidget> Overlay;
	TSharedPtr<IInputProcessor> InputBlocker;
	TWeakObjectPtr<UGameViewportClient> OverlayViewport;
	TWeakObjectPtr<UWorld> HoldWorld;
	FTSTicker::FDelegateHandle HoldTicker;
	FDelegateHandle PreLoadHandle;
	FDelegateHandle PostLoadHandle;
	FString LoadingMap;
	double LoadStart = 0.0;
	double HoldStart = 0.0;
	double CalmSince = 0.0;
	double LastProgress = 0.0;
	double FadeEnd = 0.0;
	int32 HoldFrames = 0;
	int32 CalmFrames = 0;
	int32 MostWork = 0;
	int32 LastWork = 0;
	bool bPausedWorld = false;
	bool bSettled = false;
};
