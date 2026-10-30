# Physis editor connection

Use Unreal Engine's built-in **Unreal MCP** server for editor work.

- Endpoint: `http://127.0.0.1:8000/mcp` (local computer only).
- Codex project configuration: `.codex/config.toml`.
- Automatic server startup: `Config/DefaultEditorPerProjectUserSettings.ini`.
- Listener address and restart port reuse: `Config/DefaultEngine.ini`.
- Editor tooling: `EditorToolset`.
- Character creation: `MetaHumanGenerator`, which enables MetaHuman Creator and its dependencies.
- Control Rig and Sequencer tooling: `AnimationAssistantToolset`.

The project explicitly enables Python Editor Script Plugin because Epic's editor
toolsets use Python internally. External Python remote execution is not required.
The MCP Client Toolset enables Unreal to act as a client of other servers; it is
separate from the MCP server used to control this editor.

## Use from this workspace

The local client uses Python's standard library and calls the actual Unreal MCP
endpoint. This lets a running chat use the server even before its native tool list
reloads the new project configuration.

```sh
python3 Tools/unreal_mcp.py tools
python3 Tools/unreal_mcp.py call list_toolsets
python3 Tools/unreal_mcp.py call describe_toolset '{"toolset_name":"metahuman_toolset.metahuman.MetaHumanToolset"}'
python3 Tools/unreal_mcp.py call call_tool '{"toolset_name":"editor_toolset.toolsets.scene.SceneTools","tool_name":"get_current_level","arguments":{}}'
```

Discover a tool's schema before constructing its arguments. UObject references use
`{"refPath":"/Game/..."}`. Tools may modify editor state or save assets; save only
when the work calls for it. The client does not retry commands automatically. If a
write times out, inspect the editor before retrying: it may already have completed.

MetaHuman tools require MetaHuman Creator Core Data. Registration in `list_toolsets`
confirms that the plugin found its subsystem and optional content. Creating final
characters may additionally need Epic account access and online services. Exposed
tools do not imply every Creator panel or animation workflow is automated.

## Launch issue observed during setup

Verified on 2026-10-30: MCP initialization, tool discovery, reading
`/Game/DemoTemplate/_Core/Lvl_IntroRoom`, changing the viewport camera position,
reading it back, and restoring the original camera all passed. No game assets
were created or saved during this check. The report is
`Saved/Connection/verification.json`.

The live MetaHuman schema exposes nine tools: create, begin/end editing, and
get/set operations for body shape, skin tone, and eye color. Control Rig and
Sequencer toolsets are separately registered. Full character assembly, clothing,
hair customization, and speech-driven facial animation have not been verified.

A normal relaunch crashed in NVIDIA's Vulkan compute pipeline compiler
(`libnvidia-gpucomp.so.615.78.08`). The connection setup used these session-only
arguments to reopen the editor:

```text
-noraytracing -ExecCmds="r.Nanite 0" -ModelContextProtocolStartServer
```

The launcher process also set `__GLX_VENDOR_LIBRARY_NAME=nvidia`. These are a
temporary editor launch workaround, not changes to the game's rendering settings.
Review rendering separately before using this launch to judge visual quality.
Startup output is in `Saved/Logs/ConnectionLaunch.log`.

If the MCP port fails to bind immediately after a restart, wait for previous TCP
connections to expire and start the server again with Unreal's console command
`ModelContextProtocol.StartServer`. Port reuse is enabled for subsequent launches.

Official Codex MCP configuration reference:
[Model Context Protocol](https://learn.chatgpt.com/docs/extend/mcp).
