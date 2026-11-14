#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "PhysisSteamInputSubsystem.generated.h"

class UTexture2D;
class FSteamClientInstanceHandler;

/**
 * Runs the Steam Input API for the game: finds the player's controller and fetches Steam's own
 * glyph for each Xbox-style button the HUD shows, so prompts match the real pad (Xbox, PlayStation,
 * Switch, Steam Deck...). Input itself still arrives through Unreal's normal gamepad keys.
 */
UCLASS()
class PHYSIS_API UPhysisSteamInputSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	UPhysisSteamInputSubsystem();
	virtual ~UPhysisSteamInputSubsystem() override;

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** Steam's glyph for an HUD button token (A, B, X, Y, LB, RB, LT, RT, LS, RS, L3, R3, DU, DD, DL, DR, Menu, View), or null. */
	UTexture2D* GetGlyph(const FString& Token) const;

	/** Xbox, PlayStation, Switch, SteamDeck, SteamController, Generic, or None when Steam Input has no controller. */
	FString GetFamily() const { return Family; }

private:
	bool Tick(float DeltaSeconds);
	void Refresh();

	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<UTexture2D>> Glyphs;

	TSharedPtr<FSteamClientInstanceHandler> SteamHandle;
	FTSTicker::FDelegateHandle TickHandle;
	uint64 ActiveHandle = 0;
	int32 ActiveType = -1;
	float SinceRefresh = 0.f;
	bool bRunning = false;
	FString Family = TEXT("None");
};
