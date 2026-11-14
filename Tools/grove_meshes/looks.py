"""Which scanned texture set each surface of the grove's own meshes wears (README "Look"; the sets are
Tools/grove_scans/prepare.py's). A pure literal table: Unreal's side (Content/Python/physis_grove_looks.py) and the
Blender look-dev renderer (Tools/grove_scans/lookdev.py) both read it, so a preview and the game agree.

A look is (set, mode, tint):
  set   the texture set's name (T_GRS_<set>_D / _N / _ARM), or '' for a plain material in the vertex colour
  mode  'tint'   the scan's own colour, multiplied by the vertex colour over the slot's reference colour (weathering
                 painted on the mesh darkens the scan; a mesh in the reference colour shows the scan as it is)
        'paint'  the vertex colour is the paint's colour and the scan gives its wear: its brightness, chips and rust
        'leaf'   a leaf sheet: cards take the sheet through their uv, tinted by vertex colour; solid twigs are plain
        'glow'   emissive: the vertex colour is the light
        'glass'  translucent
        'plain'  no scan: vertex colour as the albedo, with the slot's roughness and metal
  ref   the vertex colour that leaves a 'tint' scan unchanged (the palette colour meshes paint that surface with)

SLOT_LOOK is each slot's default; MESH_LOOKS rows (mesh-name prefix, slot, look) come first, first match wins.
"""

# slot: (set, mode, ref colour or None, roughness, metallic) -- roughness and metallic only matter for 'plain'
SLOT_LOOK = {
    'CN_White': ('SConcrete', 'tint', (.43, .42, .395), .8, 0.0),       # CONCRETE
    'CN_Black': ('SRock', 'tint', (.21, .205, .195), .85, 0.0),         # ROCK
    'CN_Metal': ('SSteel', 'tint', (.27, .28, .29), .5, .8),            # STEEL
    'CN_Lacquer': ('SPaint', 'paint', None, .4, 0.0),                   # PAINT
    'CN_Gold': ('', 'plain', None, .32, 1.0),                           # BRASS and copper
    'CN_Red': ('SRust', 'tint', (.33, .13, .045), .85, 0.0),            # RUST
    'CN_Blue': ('', 'plain', None, .22, 0.0),                           # TILE: glazed ceramic, insulators
    'CN_Cloth': ('SCanvas', 'paint', None, .9, 0.0),                    # CLOTH
    'CN_Plaster': ('SMoss', 'tint', (.085, .135, .035), .95, 0.0),      # MOSS
    'CN_Bark': ('BBeech', 'tint', (.17, .155, .135), .85, 0.0),         # BARK (the grove's own trees: smooth grey)
    'CN_Leaf': ('LBroadleaf', 'leaf', None, .6, 0.0),
    'CN_Glow': ('', 'glow', None, .4, 0.0),
    'CN_Glass': ('', 'glass', None, .05, 0.0),
}

MESH_LOOKS = (
    # The grove's trees: one species at every age (the valley is one organism); conifers stand on the rim.
    ('SM_GV_Oak', 'CN_Bark', ('BOakGrey', 'tint', (.095, .065, .042), .85, 0.0)),
    ('SM_GV_GiantTree', 'CN_Bark', ('BGiant', 'tint', (.095, .065, .042), .85, 0.0)),
    ('SM_GV_Heartwood', 'CN_Bark', ('BHeart', 'tint', (.095, .065, .042), .85, 0.0)),
    ('SM_GV_Pine', 'CN_Bark', ('BPine', 'tint', (.042, .032, .026), .85, 0.0)),
    ('SM_GV_Pine', 'CN_Leaf', ('LFir', 'leaf', None, .6, 0.0)),
    ('SM_GV_Snag', 'CN_Bark', ('SWood', 'tint', (.17, .155, .135), .9, 0.0)),
    ('SM_GV_Log', 'CN_Bark', ('BOld', 'tint', (.095, .065, .042), .9, 0.0)),
    ('SM_GV_Thorn', 'CN_Bark', ('BRoot', 'paint', None, .7, 0.0)),
    ('SM_GV_Grass', 'CN_Leaf', ('LGrass', 'leaf', None, .7, 0.0)),
    ('SM_GV_Reeds', 'CN_Leaf', ('LGrass', 'leaf', None, .7, 0.0)),
    ('SM_GV_Fern', 'CN_Leaf', ('LFine', 'leaf', None, .6, 0.0)),
    ('SM_GV_Sapling', 'CN_Leaf', ('LBroadleaf', 'leaf', None, .6, 0.0)),
    ('SM_GV_Rock', 'CN_Black', ('SRock', 'tint', (.21, .205, .195), .85, 0.0)),
    # Living root-wood and thornroot (the link props, the bridge, the barriers).
    ('SM_GN_Link', 'CN_Bark', ('BRoot', 'tint', (.095, .065, .042), .8, 0.0)),
    ('SM_GN_RootBridge', 'CN_Bark', ('BRoot', 'tint', (.095, .065, .042), .8, 0.0)),
    ('SM_GN_SeedCache', 'CN_Bark', ('BRoot', 'tint', (.095, .065, .042), .8, 0.0)),
    ('SM_GN_Thorn', 'CN_Bark', ('BRoot', 'paint', None, .7, 0.0)),
    # Concrete by place: the Array is formed and tie-holed, the weir and quay mossy, the ruins cracked.
    ('SM_GN_Array', 'CN_White', ('SConcrete', 'tint', (.43, .42, .395), .8, 0.0)),
    ('SM_GN_Bunker', 'CN_White', ('SConcreteSlab', 'tint', (.43, .42, .395), .8, 0.0)),
    ('SM_GN_Weir', 'CN_White', ('SConcreteMoss', 'tint', (.43, .42, .395), .85, 0.0)),
    ('SM_GN_Quay', 'CN_White', ('SConcreteMoss', 'tint', (.43, .42, .395), .85, 0.0)),
    ('SM_GN_Ruin', 'CN_White', ('SConcreteCracked', 'tint', (.43, .42, .395), .85, 0.0)),
    ('SM_GN_WallChunk', 'CN_White', ('SConcreteCracked', 'tint', (.43, .42, .395), .85, 0.0)),
    ('SM_GN_Lab', 'CN_White', ('SConcreteOld', 'tint', (.43, .42, .395), .85, 0.0)),
    ('SM_GN_Overpass', 'CN_White', ('SConcreteOld', 'tint', (.43, .42, .395), .85, 0.0)),
    ('SM_GN_Overpass', 'CN_Black', ('SAsphalt', 'tint', (.05, .05, .054), .9, 0.0)),
    ('SM_GN_TreePlatform', 'CN_Bark', ('SPlanks', 'tint', (.15, .12, .09), .85, 0.0)),
    # Steel by use: riveted plate on the big works, deck plate underfoot, old paint on wrecks and on Burr.
    ('SM_GN_RelayTower', 'CN_Metal', ('SSteelPlates', 'tint', (.27, .28, .29), .5, .8)),
    ('SM_GN_Walkway', 'CN_Metal', ('SDeckPlate', 'tint', (.27, .28, .29), .5, .8)),
    ('SM_GN_Tank', 'CN_Metal', ('SSteelPlates', 'tint', (.27, .28, .29), .5, .8)),
    ('SM_GN_Hauler', 'CN_Lacquer', ('SPaintOld', 'paint', None, .5, 0.0)),
    ('SM_GN_CarWreck', 'CN_Lacquer', ('SPaintOld', 'paint', None, .5, 0.0)),
    ('SM_GN_Shelter', 'CN_Blue', ('SSolar', 'tint', (.035, .05, .11), .2, 0.0)),
    ('SM_GP_Burr', 'CN_Lacquer', ('SPaintOld', 'paint', None, .5, 0.0)),
    ('SM_GP_', 'CN_Metal', ('SGraphite', 'tint', (.045, .047, .052), .45, .9)),
    ('SM_GE_', 'CN_Metal', ('SGraphite', 'tint', (.045, .047, .052), .45, .9)),
    ('SM_GN_Array', 'CN_Lacquer', ('SPaintRust', 'paint', None, .45, 0.0)),
)


def look(mesh, slot):
    """The look of one slot of one mesh: (set, mode, ref, roughness, metallic)."""
    for prefix, name, row in MESH_LOOKS:
        if name == slot and mesh.startswith(prefix):
            return row
    return SLOT_LOOK.get(slot, ('', 'plain', None, .7, 0.0))
