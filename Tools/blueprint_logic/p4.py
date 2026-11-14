p='build_physis_ships.py';s=open(p,encoding='utf8').read()
def R(a,b):
    global s
    assert a in s, a[:50]
    s=s.replace(a,b)
# gem cuts
R("""def blade(length, width, thick, seed, sides=6, belly=.42, tip=.0, glow=(0, 3), seam=None, stations=None):""","""def gem_cuts(bm, rng, length, width, thick, count):
    # Slice the form with planes. Each cut leaves one large clean facet, the way a stone is cut.
    for _ in range(count):
        verts = bm.verts[:]
        if len(verts) < 8:
            return
        co = np.array([v.co[:] for v in verts])
        t = rng.uniform(.12, .9)
        x = co[:, 0].min() + (co[:, 0].max() - co[:, 0].min()) * t
        turn = rng.uniform(0, 2 * math.pi)
        normal = Vector((rng.uniform(-.5, .5), math.cos(turn), math.sin(turn) * width / max(thick, 1) * .7)).normalized()
        near = np.abs(co[:, 0] - x) < length * .3
        pool = co[near] if near.any() else co
        reach = (pool @ np.array(normal)).max()
        base = Vector((x, 0, 0)).dot(normal)
        plane = normal * (base + (reach - base) * rng.uniform(.74, .9))
        cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=.01, plane_co=plane, plane_no=normal, clear_outer=True)
        edges = [e for e in cut['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=64)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def blade(length, width, thick, seed, sides=6, belly=.42, tip=.0, glow=(0, 3), seam=None, stations=None, cuts=None):""")
R("""    for face in new:
        face.material_index = GLOW
    glows = set(new)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(9) and not any(f in glows for f in e.link_faces)]
    bevel_edges(bm, seam * .16, 1, 0, edges)
    return from_bm(bm, CRYSTAL, 0, keep=True)


def monolith_arc""","""    for face in new:
        face.material_index = GLOW
    gem_cuts(bm, rng, length, width, thick, cuts if cuts is not None else int(np.clip(length / 240, 3, 14)))
    glows = {f for f in bm.faces if f.material_index == GLOW}
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(9) and not any(f in glows for f in e.link_faces)]
    bevel_edges(bm, seam * .14, 1, 0, edges)
    return from_bm(bm, CRYSTAL, 0, keep=True)


def monolith_arc""")
R("seam = seam if seam is not None else width * .018","seam = max(seam if seam is not None else width * .018, length * .0035, 7.0)")
R("kit.add(filament((-1000, 0, 10), tuple(p[:3]), 5), tone=.5, uv=.3)","kit.add(filament((-1000, 0, 10), tuple(p[:3]), 2.4), tone=.5, uv=.3)")
R("kit.add(octa(330, 2.0), mat((-1000, 0, 10)), tone=.5, uv=.3)\n    kit.add(octa(150, 2.0), mat((-1000, 0, 10)), tone=.5, uv=.3)\n","kit.add(octa(210, 2.2), mat((-1000, 0, 10), (.5, 0, 0)), tone=.5, uv=.6)\n")
R("kit.add(filament((-340, -130, -14), (-1100, 760, 40), 2.5), tone=.5, uv=.3)","kit.add(filament((-340, -130, -14), (-1100, 760, 40), 1.6), tone=.5, uv=.3)")
# crystal shading
a=s.index("    veil1 = np.exp(-voronoi_veil(");b=s.index("    orm = np.dstack((ao * .8 + .2, np.clip(rough, .04, 1), np.zeros_like(rough)))")
s=s[:a]+"""    # A few thin fracture sheets deep inside, not a web across the surface.
    veil1 = np.exp(-voronoi_veil(obj, size, L * .2, L * .02, 1) / .012)
    veil2 = np.exp(-voronoi_veil(obj, size, L * .36, L * .05, 2, (-.6, .2, .77)) / .016)
    cloud = fft_noise(1024, 2.6, cfg['seed'])
    fog = sample(cloud, D[..., 0] / L * 2.2, D[..., 1] / L * 2.2)
    core = np.zeros((size, size), np.float32)
    for c in cfg['cores']:
        core = np.maximum(core, np.exp(-np.linalg.norm(P - np.array(c, np.float32), axis=2) / (L * .1)))
    # Each facet holds its own depth of colour, as cut gems do.
    facet = np.mod(np.abs(N[..., 0] * 17.1 + N[..., 1] * 31.3 + N[..., 2] * 23.7 + tone * 9), 1).astype(np.float32)[..., None]
    shallow = np.array((.03, .16, .24), np.float32)
    deep = np.array((.003, .016, .036), np.float32)
    colour = deep + (shallow - deep) * (facet ** 2.2 * .85 + fog[..., None] * .15)
    sheets = veil1 * smooth(.42, .66, fog) + veil2 * .7 * smooth(.3, .6, 1 - fog)
    colour = colour + np.array((.2, .5, .56), np.float32) * (sheets * .22)[..., None]
    colour = colour * (.7 + ao[..., None] * .3)
    halo = smooth(.08, .7, edge)
    teal = np.array((.2, .95, .84), np.float32)
    white = np.array((.72, 1, .95), np.float32)
    glow = teal * (sheets * (.03 + core * .36))[..., None]
    glow += teal * (core ** 2 * .16 * facet[..., 0])[..., None]
    glow += teal * (halo * (.012 + core * .05))[..., None]
    pulse = .7 + .3 * np.sin(P[..., 0] / L * 19 + fog * 4)
    seam_colour = teal * (1 - core[..., None]) + white * core[..., None]
    glow[glowing] = (seam_colour * (pulse * (.62 + core * .38))[..., None])[glowing]
    colour[glowing] = (.32, .8, .76)
    rough = .05 + facet[..., 0] * .1 + sheets * .05
    rough = np.where(glowing, .3, rough)
    # Faint cleavage planes, long and straight. Facets stay polished.
    phase = (P[..., 0] * .8 + P[..., 2] * .6) / (L * .02)
    height = np.minimum(np.abs(np.mod(phase, 1) - .5), .04) * L * .0016 * ~glowing
    height = height.astype(np.float32)
"""+s[b:]
R("preview_material(obj, name, clay=clay)","preview_material(obj, name, 7.0 if asset in FIRST_CFG else 14.0, clay)")
# hull streak cleanup
R("wash = sample(streaks, D[..., 0] / span * 1.3, D[..., 1] / span * 22)","wash = sample(streaks, D[..., 0] / span * .9, D[..., 1] / span * 9)")
R("seam * .62 + (1 - smooth(.25, .62, wash)) * .16, 0, 1)","seam * .62 + (1 - smooth(.25, .62, wash)) * .08, 0, 1)")
R("wear = np.clip(edge * (chips * 1.6 + blotch * .7) - .42, 0, 1) * 3.4","wear = np.clip(edge * (chips * 1.6 + blotch * .7) - .56, 0, 1) * 3.4")
R("rough = np.where(painted, .46 + (panel - .5) * .14, .34) + (chips - .5) * .16 + grime * .28","rough = np.where(painted, .46 + (panel - .5) * .14, .34) + (chips - .5) * .07 + grime * .28")
R("colour[zone == SCORCH] *= 1.8","colour[zone == SCORCH] *= 3.2\n    metal[zone == SCORCH] = .55")
R("'window_pitch': (70, 150), 'window_size': (40, 56),","'window_pitch': (100, 220), 'window_size': (62, 96),")
open(p,'w',encoding='utf8').write(s);print('ok')
