import re,sys
p='build_physis_logo.py'
s=open(p,encoding='utf8').read()
def sub(a,b,n=1):
    global s
    assert s.count(a)>=1, a[:60]
    s=s.replace(a,b) if n==0 else s.replace(a,b,n)

# palette
sub("LEAF = np.array((0.34, 0.66, 0.16))\nLEAF_DEEP = np.array((0.36, 0.66, 0.26))",
    "LEAF = np.array((0.20, 0.58, 0.13))\nLEAF_DEEP = np.array((0.09, 0.42, 0.13))\nLEAF_LIGHT = np.array((0.62, 0.74, 0.20))")

# chiselled tube profile
sub("""    def segment(self, a, b, ra, rb, colour=GOLD, rough=.24, lift=0.0, flat=.8):""",
    """    def segment(self, a, b, ra, rb, colour=GOLD, rough=.24, lift=0.0, flat=.8, chisel=.7):""")
sub("""        h = np.sqrt(np.maximum(r * r - d * d, 0)) * flat + lift * (d < r)
""","""        # Mostly a V-cut facet with a little round: a ridge catches light, a pillow does not.
        round_h = np.sqrt(np.maximum(r * r - d * d, 0)) * flat
        vee = np.maximum(r - d, 0) * .62
        h = round_h * (1 - chisel) + vee * chisel + lift * (d < r)
""")
# bifold leaf
sub("""        half = width * .5 * np.sin(math.pi * safe ** .72) ** .85 * (u > 0) * (u < 1)""",
    """        half = width * .5 * np.sin(math.pi * safe ** .72) ** 1.12 * (u > 0) * (u < 1)""")
sub("""        dome = np.sqrt(np.maximum(1 - t * t, 0)) * half * relief * 2
        h = dome.copy()
        if width > 7:
            rib = max(.9, width * .022)
            h -= np.exp(-(across / rib) ** 2) * min(width * .05, 1.8) * inside
            h += np.exp(-(across / (rib * .45)) ** 2) * min(width * .03, 1.1) * inside
""","""        # Folded along the midrib like a real leaf: two planes meeting at a crisp crease.
        fold = np.maximum(1 - t, 0)
        h = (fold * .78 + np.sqrt(np.maximum(1 - t * t, 0)) * .22) * half * relief * 2
""")
# chiselled letters
a=s.index("        inside = mask > .5\n        window = int(math.ceil(bevel * 1.2))")
b=s.index("        if y_range:\n            t = np.clip((np.arange(self.h)")
s=s[:a]+"""        # Inscriptional V-cut: the slope runs right up to the medial axis, leaving a sharp
        # ridge down every stroke, as on a letter cut in stone and gilded.
        inside = mask > .5
        window = int(math.ceil(bevel * 1.25))
        d = distance(~inside, window) - .5
        d = np.minimum(np.maximum(d, 0) * inside, bevel)
        h = gauss((d * slope + lift * inside).astype(np.float32), .55 * self.w / 2048) * (mask > .02)
"""+s[b:]
sub("def text_layer(self, mask, bevel, colour_top, colour_low, rough=.2, lift=0.0, y_range=None):",
    "def text_layer(self, mask, bevel, colour_top, colour_low, rough=.2, lift=0.0, y_range=None, slope=.6):")

# colonize from a seeded skeleton
sub("""    nodes = [np.asarray(p, float) for p in trunk]
    parents = [-1] + list(range(len(trunk) - 1))
    points""","""    if isinstance(trunk, tuple):
        nodes = [np.asarray(p, float) for p in trunk[0]]
        parents = list(trunk[1])
    else:
        nodes = [np.asarray(p, float) for p in trunk]
        parents = [-1] + list(range(len(trunk) - 1))
    points""")
sub("def smooth_nodes(nodes, parents, passes=6, weight=.5):\n    nodes = nodes.copy()\n    n = len(nodes)",
    "def smooth_nodes(nodes, parents, passes=6, weight=.5, frozen=0):\n    nodes = nodes.copy()\n    n = len(nodes)")
sub("    fixed = [i for i in range(n) if parents[i] < 0 or len(children[i]) != 1]",
    "    fixed = [i for i in range(n) if parents[i] < 0 or len(children[i]) != 1 or i < frozen]")

# new emblem
a=s.index("def emblem_phi(rel, frame")
b=s.index("def emblem_phyllotaxis(rel, frame")
new=open(sys.argv[1],encoding='utf8').read()
s=s[:a]+new+"\n\n"+s[b:]

# remove old laurel/fiddlehead/taproot helpers
a=s.index("def laurel_strand(rel, frame")
b=s.index("def prune(nodes, parents")
s=s[:a]+s[b:]

# glow
sub("shadow = np.clip(near * .55 + wide * .55, 0, .72) * halo","shadow = np.clip(near * .6 + wide * .42, 0, .68) * halo")
sub("light = np.clip(aura * .55, 0, .22) * glow","light = np.clip(aura * .34, 0, .11) * glow")

# rule
a=s.index("def vine_rule(rel, k, mask):")
b=s.index("def build_title(")
s=s[:a]+'''def leaf_rule(rel, k, mask):
    """A swelled gilder's rule either side of a sprouting pair of leaves."""
    cx, cy = 1024 * k, RULE_Y * k
    for sign in (-1, 1):
        t = np.linspace(0, 1, 120)
        x = cx + sign * (44 * k + 400 * k * t)
        y = np.full_like(t, cy)
        rel.tube(np.stack((x, y), -1), (.7 + 3.1 * np.sin(np.clip(t * 1.25 + .02, 0, 1) * math.pi) ** .8 * (1 - t) ** .6) * k, GOLD, chisel=1)
        rel.leaf((cx, cy + 5 * k), (0 if sign > 0 else math.pi) - sign * .36, 40 * k, 13 * k, bend=sign * .10,
                 tip=LEAF, root=GOLD, veins=0, relief=.42)
    rel.leaf((cx, cy + 9 * k), -math.pi / 2, 30 * k, 11 * k, tip=LEAF, root=GOLD, veins=0, lift=2 * k, relief=.42)


'''+s[b:]
sub("def tube(self, points, radii, colour=GOLD, rough=.24, lift=0.0):","def tube(self, points, radii, colour=GOLD, rough=.24, lift=0.0, chisel=.7):")
sub("self.segment(points[i], points[i + 1], radii[i], radii[i + 1], colour, rough, lift)","self.segment(points[i], points[i + 1], radii[i], radii[i + 1], colour, rough, lift, chisel=chisel)")

# layout
sub("box = emblem_box or {'phi': (1024, 436, 282),","box = emblem_box or {'phi': (1024, 442, 304),")
sub("mask = text_mask('PHYSIS', W, H, 204 * k, 1024 * k, 74 * k, font, kern=[1.0, .92, .94, 1.0, 1.0],\n                         words_width=1250 * k)",
    "mask = text_mask('PHYSIS', W, H, CAP * k, WORD_Y * k, 74 * k, font, kern=[1.0, .92, .94, 1.0, 1.0],\n                         words_width=1120 * k)")
sub("rel.text_layer(mask, 11 * k, PALE_GOLD, GOLD, y_range=(900 * k, 1110 * k))",
    "rel.text_layer(mask, 15 * k, PALE_GOLD, GOLD, y_range=((WORD_Y - CAP / 2) * k, (WORD_Y + CAP / 2) * k))")
sub("refine=vine_rule","refine=leaf_rule")
sub("scale = {'phi': .295,","scale = {'phi': .345,")
sub("PHI = (1 + math.sqrt(5)) / 2\n","PHI = (1 + math.sqrt(5)) / 2\nCAP, WORD_Y, RULE_Y = 172, 1012, 1152  # wordmark layout in 2048-wide canvas pixels\n")

# save review textures for crops
sub("""    if deliver:
        write_png(UI / 'T_UI_Title.png', title)""","""    write_png(REVIEW / f'logo_{tag}_T.png', title)
    write_png(REVIEW / f'logo_{tag}_M.png', mark)
    if deliver:
        write_png(UI / 'T_UI_Title.png', title)""")
open(p,'w',encoding='utf8').write(s)
