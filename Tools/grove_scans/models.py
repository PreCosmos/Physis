"""Which photo-scanned models the grove uses, and how each becomes game meshes (Tools/grove_scans/process.py reads
this in Blender; the textures follow from what it exports). A pure literal table.

A Poly Haven model is often a set: plant variants side by side, a kit of pieces, a clean and an aged copy. ROWS cuts
each into the meshes the level wants:

    (mesh, source id, nodes, use, options)

  mesh     the game mesh is SM_GS_<mesh> (Art/Meshes/Grove/Scans/SM_GS_<mesh>.fbx, /Game/Grove/Scans in the editor)
  nodes    a regular expression searched in the glTF node names; every matching node is merged into the mesh, where
           the model's own layout puts it (None: all of them)
  use      what it is in the level, which sets the defaults below (USES)
  options  overrides: tris (triangle budget; 0 keeps the scan's own), tex (texture size in px), collide, pivot, scale

USES columns:
  tris     LOD 0 triangle budget. A scan above it (by a fifth or more) is welded, decimated and given the original's
           normals back; cut-out foliage is never decimated (reduction tears leaf cards), so plants say 0
  tex      texture size (the scans are fetched at 2k; a small prop does not need it)
  collide  'none' walked through, 'box' one box, 'hull' one convex hull, 'mesh' the mesh itself
  pivot    'base' footprint centre at the lowest point, 'origin' the scan's own origin (a plant's root),
           'top' footprint centre at the highest point (a pier's deck)
  cull     metres at which scatter instances of it stop drawing (0: never), and whether it casts a shadow

Every mesh is turned so the scan's front (glTF +z) faces Unreal +x, like the grove's generated meshes.
Skipped on purpose: shrub_01 and shrub_04 (150k and 27k triangles of leaves for a small plant), moss_01 (2 cm cards:
the ground material grows the moss), rock_09 and stone_01 (pebbles), modular_electric_cables and modular_pipes, and
modular_fire_escape (its pieces are laid out apart, not assembled).
"""

USES = {
    'plant':  {'tris': 0, 'tex': 2048, 'collide': 'none', 'pivot': 'origin', 'cull': 90, 'shadow': True},
    'cover':  {'tris': 0, 'tex': 1024, 'collide': 'none', 'pivot': 'origin', 'cull': 45, 'shadow': False},
    'rock':   {'tris': 4500, 'tex': 2048, 'collide': 'hull', 'pivot': 'base', 'cull': 350, 'shadow': True},
    'cliff':  {'tris': 14000, 'tex': 2048, 'collide': 'mesh', 'pivot': 'base', 'cull': 0, 'shadow': True},
    'wood':   {'tris': 6000, 'tex': 2048, 'collide': 'hull', 'pivot': 'base', 'cull': 250, 'shadow': True},
    'debris': {'tris': 900, 'tex': 1024, 'collide': 'none', 'pivot': 'base', 'cull': 60, 'shadow': False},
    'prop':   {'tris': 10000, 'tex': 1024, 'collide': 'hull', 'pivot': 'base', 'cull': 200, 'shadow': True},
    'item':   {'tris': 4000, 'tex': 512, 'collide': 'none', 'pivot': 'base', 'cull': 80, 'shadow': True},
    'big':    {'tris': 30000, 'tex': 2048, 'collide': 'mesh', 'pivot': 'base', 'cull': 0, 'shadow': True},
}

ROWS = [
    # ---- undergrowth (cut-out foliage: never decimated)
    ('FernA', 'fern_02', r'fern_02_a$', 'plant', {}),
    ('FernB', 'fern_02', r'fern_02_b$', 'plant', {}),
    ('FernC', 'fern_02', r'fern_02_c$', 'plant', {}),
    ('FernD', 'fern_02', r'fern_02_d$', 'plant', {}),
    ('ShrubA', 'shrub_02', r'shrub_02_a$', 'plant', {'cull': 140}),
    ('ShrubB', 'shrub_02', r'shrub_02_b$', 'plant', {'cull': 140}),
    ('ShrubC', 'shrub_02', r'shrub_02_c$', 'plant', {'cull': 140}),
    ('ShrubD', 'shrub_02', r'shrub_02_d$', 'plant', {'cull': 140}),
    ('HerbA', 'shrub_03', r'shrub_03_a$', 'cover', {}),
    ('HerbB', 'shrub_03', r'shrub_03_b$', 'cover', {}),
    ('HerbC', 'shrub_03', r'shrub_03_c$', 'cover', {}),
    ('HerbD', 'shrub_03', r'shrub_03_d$', 'cover', {}),
    ('SorrelA', 'shrub_sorrel_01', r'shrub_sorrel_01_b$', 'cover', {'scale': 2.5}),
    ('SorrelB', 'shrub_sorrel_01', r'shrub_sorrel_01_a$', 'cover', {'scale': 2.5}),
    ('SorrelC', 'shrub_sorrel_01', r'shrub_sorrel_01_d$', 'cover', {'scale': 2.5}),
    ('SorrelD', 'shrub_sorrel_01', r'shrub_sorrel_01_e$', 'cover', {'scale': 2.5}),
    ('NettleA', 'nettle_plant', r'nettle_plant_tall_a', 'cover', {'scale': 3.5, 'cull': 60}),
    ('NettleB', 'nettle_plant', r'nettle_plant_tall_b', 'cover', {'scale': 3.5, 'cull': 60}),
    ('NettleC', 'nettle_plant', r'nettle_plant_medium_a', 'cover', {'scale': 3.5, 'cull': 60}),
    ('NettleD', 'nettle_plant', r'nettle_plant_medium_b', 'cover', {'scale': 3.5, 'cull': 60}),
    ('NettleE', 'nettle_plant', r'nettle_plant_small_a', 'cover', {'scale': 3.5, 'cull': 60}),
    ('NettleF', 'nettle_plant', r'nettle_plant_small_b', 'cover', {'scale': 3.5, 'cull': 60}),
    ('PeriwinkleA', 'periwinkle_plant', r'periwinkle_plant_03', 'cover', {}),
    ('PeriwinkleB', 'periwinkle_plant', r'periwinkle_plant_04', 'cover', {}),
    ('PeriwinkleC', 'periwinkle_plant', r'periwinkle_plant_05', 'cover', {}),
    ('PeriwinkleD', 'periwinkle_plant', r'periwinkle_plant_06', 'cover', {}),
    ('WeedA', 'weed_plant_02', r'weed_plant_02_a', 'cover', {'scale': 2.0}),
    ('WeedB', 'weed_plant_02', r'weed_plant_02_b', 'cover', {'scale': 2.0}),
    ('WeedC', 'weed_plant_02', r'weed_plant_02_c', 'cover', {'scale': 2.0}),
    ('WeedD', 'weed_plant_02', r'weed_plant_02_d', 'cover', {'scale': 2.0}),
    ('WeedE', 'weed_plant_02', r'weed_plant_02_e', 'cover', {'scale': 2.0}),
    ('DandelionA', 'dandelion_01', r'dandelion_01_c', 'cover', {'scale': 1.6}),
    ('DandelionB', 'dandelion_01', r'dandelion_01_d', 'cover', {'scale': 1.6}),
    ('DandelionC', 'dandelion_01', r'dandelion_01_e', 'cover', {'scale': 1.6}),
    # ---- rock
    ('Boulder', 'boulder_01', None, 'rock', {'tris': 8000}),
    ('MossRockA', 'rock_moss_set_01', r'rock01$', 'rock', {}),
    ('MossRockB', 'rock_moss_set_01', r'rock02$', 'rock', {}),
    ('MossRockC', 'rock_moss_set_01', r'rock03$', 'rock', {}),
    ('MossRockD', 'rock_moss_set_01', r'rock04$', 'rock', {}),
    ('MossRockE', 'rock_moss_set_01', r'rock05$', 'rock', {}),
    ('MossRockF', 'rock_moss_set_01', r'rock06$', 'rock', {}),
    ('MossRockG', 'rock_moss_set_02', r'rock07$', 'rock', {}),
    ('MossRockH', 'rock_moss_set_02', r'rock08$', 'rock', {}),
    ('MossRockI', 'rock_moss_set_02', r'rock09$', 'rock', {}),
    ('MossRockJ', 'rock_moss_set_02', r'rock10$', 'rock', {}),
    ('MossRockK', 'rock_moss_set_02', r'rock11$', 'rock', {}),
    ('MossRockL', 'rock_moss_set_02', r'rock12$', 'rock', {}),
    ('MossRockM', 'rock_moss_set_02', r'rock13$', 'rock', {}),
    ('Stone', 'rock_07', None, 'rock', {'tris': 2500, 'scale': 3.0}),
    ('CliffA', 'rock_face_01', None, 'cliff', {'tris': 12000}),
    ('CliffB', 'rock_face_02', None, 'cliff', {'tris': 12000}),
    ('CliffC', 'mountainside', None, 'cliff', {'tris': 28000}),
    # ---- deadwood
    ('LogA', 'dead_tree_trunk', None, 'wood', {'tris': 5000}),
    ('LogB', 'dead_tree_trunk_02', None, 'wood', {'tris': 9000, 'collide': 'mesh'}),
    ('StumpA', 'tree_stump_01', None, 'wood', {}),
    ('StumpB', 'tree_stump_02', None, 'wood', {}),
    ('RootsA', 'root_cluster_01', None, 'wood', {'tris': 14000, 'collide': 'mesh'}),
    ('RootsB', 'root_cluster_02', r'root_cluster_02_a$', 'wood', {'tris': 8000, 'collide': 'none'}),
    ('RootC', 'root_cluster_02', r'root_cluster_02_d$', 'wood', {'tris': 1800, 'collide': 'none', 'cull': 120}),
    ('RootD', 'root_cluster_02', r'root_cluster_02_f$', 'wood', {'tris': 1800, 'collide': 'none', 'cull': 120}),
    ('RootE', 'root_cluster_02', r'root_cluster_02_b$', 'wood', {'tris': 1500, 'collide': 'none', 'cull': 120}),
    ('RootF', 'single_root', None, 'wood', {'tris': 3000, 'collide': 'none', 'cull': 150}),
    ('RootMatA', 'pine_roots', r'pine_roots_a$', 'wood', {'collide': 'none'}),
    ('RootMatB', 'pine_roots', r'pine_roots_b$', 'wood', {'collide': 'none'}),
    ('BranchA', 'dry_branches_medium_01', r'_a$', 'debris', {'tris': 0, 'cull': 90}),
    ('BranchB', 'dry_branches_medium_01', r'_b$', 'debris', {'tris': 0, 'cull': 90}),
    ('BranchC', 'dry_branches_medium_01', r'_c$', 'debris', {'tris': 0, 'cull': 90}),
    ('BarkA', 'bark_debris_01', r'_a$', 'debris', {}),
    ('BarkB', 'bark_debris_01', r'_b$', 'debris', {}),
    ('BarkC', 'bark_debris_01', r'_c$', 'debris', {}),
    ('BarkD', 'bark_debris_01', r'_d$', 'debris', {}),
    # ---- the Field Camp and the Array: field equipment
    ('AmmoBox', 'ammo_box', None, 'item', {}),
    ('BarrelA', 'Barrel_01', None, 'prop', {}),
    ('BarrelB', 'Barrel_02', None, 'prop', {}),
    ('BarrelC', 'barrel_03', None, 'prop', {}),
    ('Binoculars', 'binoculars', None, 'item', {'tris': 6000}),
    ('CageLight', 'caged_hanging_light', None, 'item', {'tris': 8000}),
    ('Carton', 'cardboard_box_01', None, 'item', {}),
    ('ChemistrySet', 'chemistry_set', None, 'item', {'tris': 0, 'tex': 1024}),
    ('Compressor', 'old_military_compressor', None, 'big', {'tris': 18000, 'collide': 'hull'}),
    ('CrateA', 'wooden_crate_01', None, 'prop', {}),
    ('CrateB', 'wooden_crate_02', None, 'prop', {}),
    ('CrateC', 'wooden_military_crate', None, 'prop', {'tris': 9000}),
    ('Generator', 'portable_generator', None, 'prop', {'tris': 14000}),
    ('GasBottle', 'small_lpg_tank', None, 'item', {'tris': 5000, 'collide': 'hull'}),
    ('HandTruck', 'hand_truck', None, 'prop', {'tris': 9000}),
    ('JerrycanA', 'metal_jerrycan', None, 'item', {'tris': 5000}),
    ('JerrycanB', 'metal_jerrycan_green', None, 'item', {'tris': 5000}),
    ('JerrycanC', 'plastic_jerrycan', None, 'item', {}),
    ('Ladder', 'ladder_sectioned_01', None, 'prop', {'tris': 9000, 'collide': 'none'}),
    ('Lantern', 'Lantern_01', None, 'item', {'tris': 7000}),
    ('MedicalBox', 'medical_box', None, 'item', {}),
    ('Microscope', 'industrial_microscope', None, 'item', {'tris': 6000}),
    ('MilCrate', 'old_military_crate', r'old_military_crate(_lid|_loop|_latch|_cloth)?_a$', 'prop', {}),
    ('MilCrateOpen', 'old_military_crate', r'old_military_crate(_lid|_loop|_latch|_cloth)?_b$', 'prop', {}),
    ('PlasticCrateA', 'plastic_crate_01', None, 'item', {'tris': 5000}),
    ('PlasticCrateB', 'plastic_crate_02', None, 'item', {'tris': 0}),
    ('PropaneTank', 'propane_tank', None, 'item', {'collide': 'hull'}),
    ('Searchlight', 'portable_searchlight', None, 'item', {'tris': 7000}),
    ('Shelves', 'steel_frame_shelves_01', None, 'prop', {'collide': 'mesh'}),
    ('StorageCart', 'industrial_storage_cart', None, 'prop', {}),
    ('ToolCart', 'tool_cart', None, 'prop', {'tris': 12000}),
    ('ToolChest', 'metal_tool_chest', None, 'prop', {}),
    ('Toolbox', 'metal_toolbox', None, 'item', {'tris': 6000}),
    ('TrashCan', 'metal_trash_can', r'metal_trash_can_rust', 'prop', {}),
    # ---- Thessaly's nursery
    ('PlanterA', 'planter_box_01', None, 'prop', {}),
    ('PlanterB', 'planter_box_02', None, 'prop', {}),
    ('PlanterC', 'planter_box_03', None, 'prop', {}),
    ('Pot', 'planter_pot_clay', None, 'item', {}),
    ('SeedTray', 'seeding_tray_01', None, 'item', {'tris': 3000}),
    ('WateringCan', 'watering_can_metal_01', None, 'item', {'tris': 5000}),
    ('Sprinkler', 'garden_sprinkler_01', None, 'item', {'tris': 5000}),
    ('Spade', 'rusted_spade_01', None, 'item', {}),
    ('Trowel', 'trowel_01', None, 'item', {'tris': 2500}),
    ('CompostBag', 'compost_bag_02', None, 'item', {}),
    ('Bucket', 'wooden_bucket_01', None, 'item', {}),
    ('Basket', 'wicker_basket_01', None, 'item', {'tris': 6000}),
    # ---- the Reclaimed Road and Old Town
    ('BarrierA', 'concrete_road_barrier', None, 'prop', {'tris': 5000, 'tex': 2048}),
    ('BarrierB', 'concrete_road_barrier_02', None, 'prop', {'tris': 5000, 'tex': 2048}),
    ('CoveredCar', 'covered_car', None, 'big', {'tris': 0}),
    ('Tyre', 'old_tyre', None, 'item', {}),
    ('WheelRim', 'rusted_wheel_rim_01', None, 'item', {}),
    ('Hydrant', 'fire_hydrant', r'_aged$', 'prop', {'tris': 9000}),
    ('StreetLamp', 'street_lamp_01', None, 'big', {'tris': 10000, 'tex': 1024}),
    ('BracketLamp', 'street_lamp_02', None, 'prop', {'tris': 7000, 'collide': 'none'}),
    ('FencePanel', 'modular_chainlink_fence', r'modular_chainlink_fence_double$', 'prop', {'tris': 0, 'tex': 2048, 'collide': 'box'}),
    ('FencePost', 'modular_chainlink_fence', r'modular_chainlink_fence_post$', 'prop', {'tris': 0, 'tex': 2048, 'collide': 'box'}),
    ('FenceGate', 'modular_chainlink_fence', r'modular_chainlink_fence_door_(frame|gate|latch)$', 'prop',
     {'tris': 14000, 'tex': 2048, 'collide': 'box'}),
    ('PoleA', 'modular_electricity_poles', r'^preset_01_', 'big', {'tris': 12000}),
    ('PoleB', 'modular_electricity_poles', r'^preset_02_', 'big', {'tris': 12000}),
    ('PoleC', 'modular_electricity_poles', r'^preset_03_', 'big', {'tris': 12000}),
    ('Manhole', 'water_manhole_cover', None, 'item', {'tex': 1024}),
    ('Shutter', 'rollershutter_door', r'rollershutter_door$', 'prop', {'tex': 2048, 'collide': 'box'}),
    ('ShutterTagged', 'rollershutter_door', r'rollershutter_door_graffiti$', 'prop', {'tex': 2048, 'collide': 'box'}),
    ('Aircon', 'exterior_aircon_unit', r'exterior_aircon_unit_rusted$', 'prop', {'collide': 'box'}),
    ('Can', 'can_rusted', None, 'item', {'tris': 1500}),
    # ---- the weir, the relay, the campus and the Array: industrial fittings
    ('PipeStraight', 'modular_industrial_pipes_01', r'pipe02$', 'prop', {'collide': 'none'}),
    ('PipeBend', 'modular_industrial_pipes_01', r'pipe03$', 'prop', {'collide': 'none'}),
    ('PipeValve', 'modular_industrial_pipes_01', r'pipe08$', 'prop', {'collide': 'none'}),
    ('PowerBox', 'power_box_01', None, 'item', {'tris': 6000}),
    ('UtilityBoxA', 'utility_box_01', None, 'prop', {'collide': 'box'}),
    ('UtilityBoxB', 'utility_box_02', None, 'prop', {'collide': 'box'}),
    ('Crane', 'overhead_crane', None, 'big', {}),
    ('SecurityLight', 'security_light', None, 'item', {}),
    ('HangLamp', 'hanging_industrial_lamp', None, 'item', {'tris': 0}),
    ('WallLamp', 'industrial_wall_lamp', None, 'item', {'tris': 0}),
    ('TubeLight', 'mounted_fluorescent_lights', r'mounted_fluorescent_lights_d$', 'item', {}),
    ('DuctStraight', 'modular_airduct_rectangular_01', r'tripple_01$', 'prop', {'collide': 'none'}),
    ('DuctBend', 'modular_airduct_rectangular_01', r'bend_02$', 'prop', {'collide': 'none'}),
    ('DuctVent', 'modular_airduct_rectangular_01', r'vent_01$', 'item', {}),
    ('Lifebuoy', 'lifebuoy', None, 'item', {}),
    ('PierA', 'modular_wooden_pier', r'section_02$', 'big', {'tris': 0, 'pivot': 'top'}),
    ('PierB', 'modular_wooden_pier', r'section_03$', 'big', {'tris': 0, 'pivot': 'top'}),
    ('PierEnd', 'modular_wooden_pier', r'section_04$', 'big', {'tris': 0, 'pivot': 'top'}),
]


def rows():
    """ROWS as dictionaries with every option filled in from its use."""
    out = []
    for mesh, source, nodes, use, options in ROWS:
        row = dict(USES[use])
        row.update(options)
        row.update({'mesh': 'SM_GS_' + mesh, 'source': source, 'nodes': nodes, 'use': use, 'scale': float(options.get('scale', 1.0))})
        out.append(row)
    return out
