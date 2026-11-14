"""Run as `conclave:exec:Tools/conclave/apply_look.py` (absolute path) after conclave:materials, with Play stopped and
L_Conclave open: re-places the level's light (the Spine's sun and its two far-side fills), haze, post volume and the
Spine's halos from physis_conclave_tools' current constants, puts MI_CNSky on the sky and MI_CN_CapGlow on the end
caps' glow slots, puts the upper lands and the end caps on the fills' lighting channel alone, takes the ground-cover
scatter (RT_SKIP) out of the ray-tracing and distance-field scenes, rewrites the director's SunBase/SunStep and saves.
It touches nothing else, so the scenario's actors stay (conclave:level would remove them). The new sky light captures
the scene as it is placed; rerun this after any change to the drum's lighting so the capture matches. Sets RESULT."""
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if getattr(les, 'is_in_play_in_editor', None) and les.is_in_play_in_editor():
    raise RuntimeError('stop Play first')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world is None or world.get_path_name().split('.')[0] != LEVEL:
    raise RuntimeError('open %s first' % LEVEL)
check_level_materials()
sub = actors()
LOOK_LABELS = (('Spine Sun', 'Drum Light', 'Drum Haze', 'Conclave Look') + tuple(label for label, _, _ in FILLS)
               + tuple('Spine Halo %d' % (k + 1) for k in range(3)))
# A level built before the far-side fills (2026-11-07) still holds the single upward fill: it goes as well.
RETIRED_LABELS = ('Spine Fill',)
removed = 0
for actor in sub.get_all_level_actors():
    if actor.get_actor_label() in LOOK_LABELS + RETIRED_LABELS and str(actor.get_folder_path()).startswith(FOLDER):
        sub.destroy_actor(actor)
        removed += 1
RESULT = {'removed': removed, 'light': lighting(), 'post': post(), 'halos': spine_halos()}
# The upper lands and the end caps take the Spine's light from the fills alone (DRUM's last field, as drum() sets it).
fill_only_labels = [mesh[6:] for mesh, _, _, fill_only in DRUM if fill_only]
channelled = []
for actor in sub.get_all_level_actors():
    if (actor.get_actor_label() in fill_only_labels and isinstance(actor, unreal.StaticMeshActor)
            and str(actor.get_folder_path()).startswith(FOLDER + '/Drum')):
        actor.static_mesh_component.set_editor_property('lighting_channels', channels(1))
        channelled.append(actor.get_actor_label())
RESULT['fill_only'] = sorted(channelled)
sky_material = unreal.load_asset(MATS + '/MI_CNSky')
skies = 0
for actor in sub.get_all_level_actors():
    if actor.get_actor_label() == 'Sky' and isinstance(actor, unreal.StaticMeshActor) and str(actor.get_folder_path()).startswith(FOLDER):
        actor.static_mesh_component.set_material(0, sky_material)
        skies += 1
RESULT['sky'] = skies
cap_glow = unreal.load_asset(MATS + '/MI_CN_CapGlow')
caps = 0
for actor in sub.get_all_level_actors():
    if cap_glow and actor.get_actor_label() in ('CapSouth', 'CapNorth') and isinstance(actor, unreal.StaticMeshActor):
        part = actor.static_mesh_component
        for index, slot in enumerate(part.get_editor_property('static_mesh').get_editor_property('static_materials')):
            if slot_name(slot) == 'CN_Glow':
                part.set_material(index, cap_glow)
                caps += 1
RESULT['cap_glow_slots'] = caps if cap_glow else 'MI_CN_CapGlow is missing: run conclave:materials first'
# Ground cover leaves the ray-tracing and distance-field scenes (RT_SKIP; conclave:scatter does this for new actors).
rt_skipped, rt_failed = [], []
for actor in sub.get_all_level_actors():
    if not str(actor.get_folder_path()).startswith(FOLDER):
        continue
    for part in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent):
        mesh = part.get_editor_property('static_mesh')
        if mesh is not None and mesh.get_name().startswith(RT_SKIP):
            rt_skip(part, rt_failed)
            rt_skipped.append(actor.get_actor_label())
RESULT['rt_skipped'] = sorted(set(rt_skipped))
RESULT['rt_failed'] = sorted(set(rt_failed))
RESULT['sun'] = tune_director()
save_level()
