p='build_physis_kit.py'
s=open(p,encoding='utf8').read()
def R(a,b):
    global s
    assert s.count(a)>=1, a[:70]
    s=s.replace(a,b)
R("with k.at(T(x, -20, 62) @ Ry(-90) @ S(1.12, 1.25, 1.25)):","with k.at(T(x, -20, 93) @ Ry(-90) @ S(1, 1.25, 1.25)):")
R("bead = [(p[0] + 1.2 * noise.noise(Vector((p[0] * .1, p[1] * .1, 1))), .4, p[1]","bead = [(p[0] + 1.2 * noise.noise(Vector((p[0] * .1, p[1] * .1, 1))), -.6, p[1]")

# masks: no blurry scuff, tighter chips, soot round the breach
R("fine.inputs['Scale'].default_value = .16","fine.inputs['Scale'].default_value = .46")
R("    chips = ramp(fine.outputs[0], .40, .56)\n","    chips = ramp(fine.outputs[0], .47, .54)\n")
R("    edge = math_node('MULTIPLY', sep.outputs[0], math_node('ADD', math_node('MULTIPLY', chips, .8), math_node('MULTIPLY', patches, .35)))\n    scuff = math_node('MULTIPLY', ramp(fine.outputs[0], .6, .68), math_node('MULTIPLY', patches, .34))\n    wear = math_node('MAXIMUM', edge, scuff)\n",
  "    wear = math_node('MULTIPLY', sep.outputs[0], math_node('MULTIPLY', chips, math_node('ADD', math_node('MULTIPLY', patches, .6), .4)))\n")
R("""    comb = _node(t, 'ShaderNodeCombineColor')
    L(occ, comb.inputs[0])
""","""    if ob.name == 'SM_Kit_HullBreach':
        # Blast soot, thrown outward from the hole and broken up by the noise.
        dist = _node(t, 'ShaderNodeVectorMath', operation='DISTANCE')
        L(coord.outputs['Object'], dist.inputs[0])
        dist.inputs[1].default_value = (200, -30, 232)
        soot = math_node('MULTIPLY', ramp(dist.outputs['Value'], 215, 150), math_node('ADD', math_node('MULTIPLY', broad.outputs[0], 1.1), .25))
        grime = math_node('MAXIMUM', grime, soot)
    comb = _node(t, 'ShaderNodeCombineColor')
    L(occ, comb.inputs[0])
""")

# preview: textures, tone
R("""            em.inputs[0].default_value = (1, .95, .86, 1)
            em.inputs[1].default_value = 4.5
""","""            tex = _node(t, 'ShaderNodeTexImage', image=load(TEX / 'T_KitLight_Emissive.png', False))
            L(uv.outputs[0], tex.inputs[0])
            tint = _node(t, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
            tint.inputs['Factor'].default_value = 1
            L(tex.outputs[0], tint.inputs['A'])
            tint.inputs['B'].default_value = (.92, .96, 1, 1)
            L(tint.outputs['Result'], em.inputs[0])
            em.inputs[1].default_value = 2.4
""")
R("    folder = TEX if slot == 'M_Foam' else MATERIALS\n","    folder = TEX if stem and stem.startswith('T_Kit') else MATERIALS\n")
R("""        c = _node(t, 'ShaderNodeTexImage', image=colour)
        L(uv.outputs[0], c.inputs[0])
        base_socket = c.outputs[0]
""","""        c = _node(t, 'ShaderNodeTexImage', image=colour)
        L(uv.outputs[0], c.inputs[0])
        base_socket = c.outputs[0]
        if slot in ('M_Wall', 'M_Ceiling'):
            # Paint scheme from vertex colour B: the same three-way pick the master material needs.
            vc = _node(t, 'ShaderNodeVertexColor', layer_name='Col')
            vs = _node(t, 'ShaderNodeSeparateColor')
            L(vc.outputs[0], vs.inputs[0])
            is_grey = _node(t, 'ShaderNodeMath', operation='GREATER_THAN')
            L(vs.outputs[2], is_grey.inputs[0])
            is_grey.inputs[1].default_value = .9
            is_cargo = _node(t, 'ShaderNodeMath', operation='LESS_THAN')
            L(vs.outputs[2], is_cargo.inputs[0])
            is_cargo.inputs[1].default_value = .1
            pick = _node(t, 'ShaderNodeMix', data_type='RGBA')
            L(is_cargo.outputs[0], pick.inputs['Factor'])
            pick.inputs['A'].default_value = (*PAINT[BONE], 1)
            pick.inputs['B'].default_value = (*PAINT[CARGO], 1)
            pick2 = _node(t, 'ShaderNodeMix', data_type='RGBA')
            L(is_grey.outputs[0], pick2.inputs['Factor'])
            L(pick.outputs['Result'], pick2.inputs['A'])
            pick2.inputs['B'].default_value = (*PAINT[GREY], 1)
            tinted = _node(t, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
            tinted.inputs['Factor'].default_value = 1
            L(c.outputs[0], tinted.inputs['A'])
            L(pick2.outputs['Result'], tinted.inputs['B'])
            base_socket = tinted.outputs['Result']
""")
R("        foam_textures()\n","        paint_textures()\n        foam_textures()\n")
# room: gentle ceiling bounce fill, as a stand-in for Lumen diffuse GI off the deck
R("    area('c', (800, 560, 330), (800, 0, 0), 2.0e5, 200, (1, .55, .2))\n","    area('c', (800, 560, 330), (800, 0, 0), 2.0e5, 200, (1, .55, .2))\n    area('d', (800, 0, 40), (800, 0, 450), 4.0e5, 900, (.85, .92, 1))\n")

# screens: real type
a=s.index("def screen_textures():"); b=s.index("# ----------------------------------------------------------------------------------- mask baking")
s=s[:a]+'''def screen_type():
    """Render the type layer of the screen atlas with a real font. Returns premultiplied RGB and alpha."""
    scene, white = _text_scene()
    bpy.data.objects['atlas'].location = (1.5, 1.5, 5)
    bpy.data.cameras['atlas'].ortho_scale = 3
    rng = np.random.default_rng(14)
    mats = {}

    def ink(colour):
        if colour not in mats:
            m = white.copy()
            m.node_tree.nodes['Emission'].inputs[0].default_value = (*colour, 1)
            mats[colour] = m
        return mats[colour]
    ICE, GOLD, RED, WHITE = (.32, .72, 1), (1, .62, .14), (1, .16, .08), (1, 1, 1)

    def text(cell, x, y, body, size=.03, colour=ICE):
        col, row = cell
        cu = bpy.data.curves.new('t', 'FONT')
        cu.body = body
        cu.size = size
        cu.materials.append(ink(colour))
        ob = bpy.data.objects.new('t', cu)
        ob.location = (col + x, 3 - row - y, 0)
        scene.collection.objects.link(ob)

    def head(cell, title, code):
        text(cell, .03, .048, title, .03, (0, 0, 0))
        text(cell, .78, .048, code, .03, (0, 0, 0))

    def code(n):
        return ''.join(rng.choice(list('0123456789ABCDEF'), n))
    verbs = ('SEAL', 'VENT', 'PURGE', 'CYCLE', 'ROUTE', 'HOLD', 'ARM', 'SYNC', 'TRIM')
    parts = ('BLKHD', 'FRAME', 'BUS-A', 'COIL', 'ATMO', 'DECK', 'LOCK', 'PDC', 'SPINE')

    def log(cell, x, y, rows, gap=.031, size=.0235, colour=ICE):
        for r in range(rows):
            line = f'{int(rng.integers(0, 24)):02d}:{int(rng.integers(0, 60)):02d}  {rng.choice(verbs):5s} {rng.choice(parts):5s}-{int(rng.integers(1, 99)):02d}  {code(4)}  {rng.choice(("OK", "OK", "OK", "ACK", "WAIT"))}'
            text(cell, x, y + r * gap, line, size, colour)

    head((0, 0), 'FLEET TACTICAL  //  MERIDIAN', 'SWP 06')
    for i, label in enumerate(('CONTACTS   12', 'HOSTILE     6', 'CLOSING   41 KM', 'FIRST ONES', 'BRG 212.6', 'ELV 014.2', 'TTI 08:41')):
        text((0, 0), .8, .11 + i * .036, label, .022, RED if i in (1, 3) else ICE)
    log((0, 0), .8, .52, 12, .03, .0145)
    head((1, 0), 'STATION  HULL  STATUS', 'D-07')
    for i in range(8):
        text((1, 0), .07 + i * .105, .68, f'D{i + 1:02d}', .022, RED if i == 7 else GOLD if i in (2, 3) else ICE)
    log((1, 0), .07, .75, 7, .03)
    text((2, 0), .07, .09, 'COMMS LOG  //  CHANNEL 4  //  ENCRYPTED', .026, GOLD)
    log((2, 0), .07, .15, 18, .0285)
    text((2, 0), .13, .73, 'PRESSURE LOSS  DECK 07', .043, WHITE)
    text((2, 0), .13, .785, 'EVACUATE FRAME 118 TO 126', .03, WHITE)
    log((2, 0), .07, .86, 4, .0285, .0235, GOLD)
    head((0, 1), 'REACTOR  BUS  WAVEFORM', '12 KV')
    for i, (label, y, c) in enumerate((('PHASE A  398.2', .1, GOLD), ('PHASE B  401.7', .36, ICE), ('PHASE C  OUT OF BAND', .62, RED))):
        text((0, 1), .05, y, label, .024, c)
    log((0, 1), .06, .86, 4, .03)
    head((1, 1), 'SYSTEM  INTEGRITY', 'ROLL UP')
    for i in range(14):
        text((1, 1), .062 + i * .0644, .845, f'{i + 1:02d}', .017, ICE)
    log((1, 1), .06, .89, 3, .03)
    text((2, 1), .12, .49, 'LOCKDOWN', .13, WHITE)
    text((2, 1), .13, .57, 'BLAST DOORS SEALED  //  AUTH REQUIRED', .03, WHITE)
    head((0, 2), 'BOARDING  MAP', 'DECK 07')
    for i in range(16):
        text((0, 2), rng.uniform(.08, .8), rng.uniform(.12, .9), f'{rng.choice(parts)} {int(rng.integers(1, 99)):02d}', .02, ICE)
    text((1, 2), .06, .06, 'MAINTENANCE QUEUE', .03, GOLD)
    log((1, 2), .06, .11, 30, .029)
    text((2, 2), .39, .5, 'STANDBY', .05, GOLD)
    text((2, 2), .32, .9, 'MERIDIAN STATION 04', .03, GOLD)
    scene.render.resolution_x = scene.render.resolution_y = 2049
    scene.cycles.samples = 24
    scene.render.filepath = str(TEX / '_screen_raw.png')
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = str(TEX / '_screen_raw.exr')
    bpy.ops.render.render(write_still=True, scene=scene.name)
    img = bpy.data.images.load(scene.render.filepath)
    px = np.array(img.pixels[:], np.float32).reshape(2049, 2049, 4)[::-1]
    bpy.data.images.remove(img)
    (TEX / '_screen_raw.exr').unlink()
    bpy.data.scenes.remove(scene)
    return px[..., :3], px[..., 3:]


def screen_textures():
    """3x3 atlas of operating displays: drawn graphics under real rendered type, with a soft phosphor bloom."""
    cell = 683
    size = cell * 3
    out = np.zeros((size, size, 3))
    rng = np.random.default_rng(14)
    ice, gold, red = np.array((.32, .72, 1)), np.array((1, .62, .14)), np.array((1, .16, .08))

    def field():
        yy, xx = np.mgrid[0:cell, 0:cell]
        c = np.zeros((cell, cell, 3)) + np.array((.008, .02, .032))
        minor = ((xx % 24) < 1) | ((yy % 24) < 1)
        major = ((xx % 120) < 1.5) | ((yy % 120) < 1.5)
        c += minor[..., None] * ice * .025 + major[..., None] * ice * .06
        return c, xx, yy

    def box(c, x0, y0, x1, y1, colour, t=2):
        c[y0:y0 + t, x0:x1] = colour
        c[y1 - t:y1, x0:x1] = colour
        c[y0:y1, x0:x0 + t] = colour
        c[y0:y1, x1 - t:x1] = colour

    # 0,0 fleet tactical: range rings, contacts, a bearing sweep.
    c, xx, yy = field()
    cx, cy = cell * .4, cell * .52
    r = np.hypot(xx - cx, yy - cy)
    ang = np.arctan2(yy - cy, xx - cx)
    for ring in (80, 160, 240):
        c += (np.abs(r - ring) < 1.2)[..., None] * ice * .4
    sweep = np.mod(ang + .6, 6.283)
    c += ((r < 240) * np.exp(-sweep * 2.2))[..., None] * ice * .3
    for _ in range(12):
        a, q = rng.uniform(0, 6.28), rng.uniform(40, 235)
        px, py = int(cx + math.cos(a) * q), int(cy + math.sin(a) * q)
        col = red if rng.uniform() < .5 else ice
        box(c, px - 7, py - 7, px + 7, py + 7, col)
        c[py - 2:py + 2, px - 2:px + 2] = col
    c[:46, :] = gold * .8
    box(c, int(cell * .78), 56, cell - 16, cell - 16, ice * .4, 1)
    out[0:cell, 0:cell] = c
    # 0,1 station schematic: decks in profile with their status.
    c, xx, yy = field()
    y0, y1 = int(cell * .2), int(cell * .62)
    for i in range(8):
        x = 46 + i * 72
        tall = int(16 * (3 - abs(i - 3.5)))
        status = gold if i in (2, 3) else red if i == 7 else ice
        c[y0 - tall:y1 + tall // 2, x:x + 62] = status * .13
        box(c, x, y0 - tall, x + 62, y1 + tall // 2, status)
    c[:46, :] = ice * .7
    out[0:cell, cell:cell * 2] = c
    # 0,2 terminal: a tall comms log with a warning block.
    c, xx, yy = field()
    c[int(cell * .67):int(cell * .81), 50:cell - 50] = red * .55
    box(c, 50, int(cell * .67), cell - 50, int(cell * .81), red)
    out[0:cell, cell * 2:] = c
    # 1,0 power waveforms.
    c, xx, yy = field()
    x = np.arange(cell)
    for col, base, amp, freq in ((gold, 150, 56, 13), (ice, 325, 80, 7), (red, 500, 34, 27)):
        wave = base + amp * np.sin(x / cell * freq * 6.283) * (1 + .4 * np.sin(x / cell * 3.1))
        for i in x:
            y = int(wave[i])
            c[y - 2:y + 2, i] = col
            c[min(y, base):max(y, base), i] += col * .05
    c[:46, :] = gold * .8
    out[cell:cell * 2, 0:cell] = c
    # 1,1 bars of system health.
    c, xx, yy = field()
    for i in range(14):
        v = rng.uniform(.25, 1)
        x = 40 + i * 44
        tall = int(v * 460)
        col = red if v < .35 else gold if v < .6 else ice
        c[560 - tall:560, x:x + 30] = col * .55
        c[560 - tall:560 - tall + 3, x:x + 30] = col
    c[:46, :] = ice * .7
    out[cell:cell * 2, cell:cell * 2] = c
    # Remaining cells: a lockdown alarm, a boarding map and a standby page.
    c, xx, yy = field()
    band = np.mod(xx + yy, 120) < 60
    c[:70] = np.where(band[:70][..., None], gold, 0.015)
    c[-70:] = np.where(band[-70:][..., None], gold, 0.015)
    c[250:430, 50:cell - 50] = red * .55
    box(c, 50, 250, cell - 50, 430, red)
    out[cell:cell * 2, cell * 2:] = c
    c, xx, yy = field()
    for _ in range(26):
        a, b = rng.integers(40, cell - 150, 2)
        w, h = rng.integers(40, 150, 2)
        box(c, a, b, a + w, b + h, ice * .55)
        c[b:b + h, a:a + w] += ice * .03
    c[:46, :] = ice * .7
    out[cell * 2:, 0:cell] = c
    c, xx, yy = field()
    out[cell * 2:, cell:cell * 2] = c
    c, xx, yy = field()
    c += (np.abs(np.hypot(xx - cell / 2, yy - cell / 2) - 200) < 3)[..., None] * gold
    out[cell * 2:, cell * 2:] = c
    rgb, alpha = screen_type()
    out = out * (1 - alpha) + rgb
    # Phosphor bloom and a dim scanline; a little edge fall-off per cell sells the glass.
    bloom = out.copy()
    for _ in range(3):
        bloom = soft(bloom[::1], 3)
    out = out + bloom * .28
    edge = np.mgrid[0:size].astype(np.float32) % cell / cell
    fall = (.72 + .28 * np.clip(np.sin(edge * math.pi) * 3, 0, 1))
    out = out * fall[:, None, None] * fall[None, :, None]
    scan = (.9 + .1 * np.sin(np.arange(size) * 2.09))[:, None, None]
    write_png(TEX / 'T_KitScreen_Emissive.png', (np.clip(out * scan, 0, 1) ** (1 / 2.2))[:2048, :2048], 8)


'''+s[b:]
open(p,'w',encoding='utf8').write(s)
