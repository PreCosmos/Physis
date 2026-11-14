#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "PhysisSteamInputLibrary.generated.h"

class UTexture2D;

UCLASS()
class PHYSIS_API UPhysisSteamInputLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** The controller glyph Steam Input reports for a button token, or Fallback when Steam has none. */
	UFUNCTION(BlueprintPure, Category = "Physis|Input", meta = (WorldContext = "WorldContextObject"))
	static UTexture2D* GetPadGlyph(const UObject* WorldContextObject, const FString& Token, UTexture2D* Fallback);

	/** The connected controller family as Steam Input sees it (None without Steam Input). */
	UFUNCTION(BlueprintPure, Category = "Physis|Input", meta = (WorldContext = "WorldContextObject"))
	static FString GetPadFamily(const UObject* WorldContextObject);
};
