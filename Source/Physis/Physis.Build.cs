using UnrealBuildTool;

// Physis game module. It exists for what Blueprints cannot reach: the Steam Input API (controller type and
// button glyphs) and the loading screen (MoviePlayer). The rest of the game stays in Blueprints.
public class Physis : ModuleRules
{
	public Physis(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore" });
		PrivateDependencyModuleNames.AddRange(new string[] { "MoviePlayer", "Slate", "SlateCore", "RenderCore", "RHI" });
		if (Target.Platform == UnrealTargetPlatform.Win64 || Target.Platform == UnrealTargetPlatform.Linux)
		{
			PrivateDependencyModuleNames.Add("SteamShared");
			AddEngineThirdPartyPrivateStaticDependencies(Target, "Steamworks");
			PrivateDefinitions.Add("PHYSIS_WITH_STEAM=1");
		}
		else
		{
			PrivateDefinitions.Add("PHYSIS_WITH_STEAM=0");
		}
	}
}
