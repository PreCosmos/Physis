p='build_physis_kit.py'
s=open(p,encoding='utf8').read()
def R(a,b):
    global s
    assert s.count(a)>=1, a[:70]
    s=s.replace(a,b)
# paint: small clustered nicks, not spots
R("    chip = np.clip((tile_noise(size, 34, 7, 9) - .71) * 22, 0, 1)\n    height = height - soft(chip, 1) * .22\n",
  "    # Small nicks, clustered by a slow mask so whole tiles stay clean.\n    chip = np.clip((tile_noise(size, 34, 4, 90) - .70) * 30, 0, 1) * np.clip((tile_noise(size, 35, 3, 4) - .52) * 9, 0, 1)\n    height = height - soft(chip, 1) * .12\n")
R("    albedo = albedo * (1 - fine * .0) + fine * .16 + deep * .22\n","    albedo = albedo + fine * .10 + deep * .14\n")
R("    primer = np.array((.20, .19, .18))\n","    primer = np.array((.30, .29, .28))\n")
# wear: broader, softer, less white; no dashes
R("fine.inputs['Scale'].default_value = .46","fine.inputs['Scale'].default_value = .2")
R("    chips = ramp(fine.outputs[0], .47, .54)\n","    chips = ramp(fine.outputs[0], .42, .60)\n")
R("    wear = math_node('MULTIPLY', sep.outputs[0], math_node('MULTIPLY', chips, math_node('ADD', math_node('MULTIPLY', patches, .6), .4)))\n",
  "    wear = math_node('MULTIPLY', sep.outputs[0], math_node('MULTIPLY', chips, math_node('ADD', math_node('MULTIPLY', patches, .45), .3)))\n")
R("worn.inputs['B'].default_value = (.56, .58, .6, 1)","worn.inputs['B'].default_value = (.42, .44, .47, 1)")
# soot lighter so torn metal is seen
R("soot = math_node('MULTIPLY', ramp(dist.outputs['Value'], 215, 150), math_node('ADD', math_node('MULTIPLY', broad.outputs[0], 1.1), .25))","soot = math_node('MULTIPLY', ramp(dist.outputs['Value'], 215, 165), math_node('MULTIPLY', broad.outputs[0], 1.0))")
# rifle pip
R("    k.box(46, 58, -3.0, -2.8, 1.2, 2.0, 'M_Light', 0)\n","    k.box(50, 53, -3.0, -2.8, 1.2, 1.9, 'M_Light', 0)\n")
# viewport: bolts on the surface, plus clamps and a shutter-housing louvre
R("""        k.bolt((float(s), -42, 22), r=1.2, h=1.0)
        k.bolt((float(s), -42, 278), r=1.2, h=1.0)
""","""        k.bolt((float(s), -44.2, 27), r=1.2, h=1.0)
        k.bolt((float(s), -44.2, 273), r=1.2, h=1.0)
    # Glazing clamps round the frame: each carries the pane's load into the hull plate.
    for x in np.linspace(76, 324, 6):
        for z, sign in ((10, 1), (258, -1)):
            k.plate(crect(float(x) - 12, z, float(x) + 12, z + 12, 2), -29, -32.5, 'M_Wall', .7, 2, taper=.6)
            k.bolts([(float(x) + a, -32.5, z + 6) for a in (-7.5, 7.5)], r=1.1, h=.9)
    for side in (-1, 1):
        cx = 200 + side * 186
        k.plate(crect(cx - 7, 96, cx + 7, 204, 2), -28, -31, 'M_Wall', .7, 2, taper=.6)
        k.bolts([(cx, -31, z) for z in (106, 150, 194)], r=1.2, h=1.0)
""")
R("""    k.box(26, 374, -51.4, -50.2, 293, 298, 'M_Light', 0)
""","""    k.box(26, 374, -51.4, -50.2, 293, 298, 'M_Light', 0)
    for x in np.linspace(40, 360, 9):
        k.box(float(x) - 1.2, float(x) + 1.2, -52.2, -49.8, 288, 304, 'M_Trim', .3, 1)
    k.box(14, 386, -51, -49.6, 272, 282, 'M_Composite', .3, 1)
""")
# column: bolted splice plates on the chords
R("""            k.plate(chord, 40, H - 34, 'M_Wall', 1.4, 2, plane='XY', align=True)
""","""            k.plate(chord, 40, H - 34, 'M_Wall', 1.4, 2, plane='XY', align=True)
            for z in (96, 232, 372):
                k.box(61, 63, 41, 58, z - 15, z + 15, 'M_Trim', .5, 2)
                k.box(41, 58, 61, 63, z - 15, z + 15, 'M_Trim', .5, 2)
                for a in (-9, 9):
                    k.bolts([(63, 49.5, z + a)], (1, 0, 0), 1.2, 1.0)
                    k.bolts([(49.5, 63, z + a)], (0, 1, 0), 1.2, 1.0)
""")
# shots
R("    'breach': ((430, 40, 170), (74, 200, 235), 35),\n","    'breach': ((430, 40, 170), (74, 200, 235), 35),\n    'breachwide': ((760, 150, 200), (74, 200, 225), 40),\n")
open(p,'w',encoding='utf8').write(s)
