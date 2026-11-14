#include "PhysisSteamInputLibrary.h"

#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "PhysisSteamInputSubsystem.h"

namespace
{
	const UPhysisSteamInputSubsystem* SubsystemFor(const UObject* WorldContextObject)
	{
		const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull) : nullptr;
		const UGameInstance* Game = World ? World->GetGameInstance() : nullptr;
		return Game ? Game->GetSubsystem<UPhysisSteamInputSubsystem>() : nullptr;
	}
}

UTexture2D* UPhysisSteamInputLibrary::GetPadGlyph(const UObject* WorldContextObject, const FString& Token, UTexture2D* Fallback)
{
	if (const UPhysisSteamInputSubsystem* Steam = SubsystemFor(WorldContextObject))
	{
		if (UTexture2D* Glyph = Steam->GetGlyph(Token))
		{
			return Glyph;
		}
	}
	return Fallback;
}

FString UPhysisSteamInputLibrary::GetPadFamily(const UObject* WorldContextObject)
{
	const UPhysisSteamInputSubsystem* Steam = SubsystemFor(WorldContextObject);
	return Steam ? Steam->GetFamily() : FString(TEXT("None"));
}
