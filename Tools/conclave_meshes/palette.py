"""The Conclave's palette (author, 2026-11-06; green added by the author 2026-11-08): only gold, light blue,
red, green, black and white may exist in the level, rendered realistically (no cel shading). Greys count
as mixes of black and white. Exception (author, 2026-11-09): people's skin, lips, nails, eyes and hair have
natural colours (the MetaHuman people, Tools/conclave/PEOPLE_DESIGN.md); this module never sees them, and their
clothes, headwear, makeup and props still pass allowed().

Colours here are LINEAR RGB (what vertex colours and material constants hold). allowed() is the rule
every vertex colour, material constant and light colour must pass; check.py runs it on every mesh.
The rule works in sRGB HSV, where a person would judge the colour:
  white / grey / black   saturation < 0.12 (any value)
  gold                   hue 36-52 deg, saturation >= 0.18, value >= 0.50
  red                    hue >= 345 or <= 10 deg, saturation >= 0.55, value >= 0.30
  light blue             hue 188-222 deg, saturation 0.10-0.68, value >= 0.58
  green                  hue 70-165 deg, saturation >= 0.15, value >= 0.20
Everything else (brown, olive, orange, purple, pink, navy, teal) is refused. Green's value floor is low
because real foliage albedo is dark (a leaf is about 0.35 in sRGB value); below 0.20 it reads black.
"""
import colorsys


def srgb(c):
    c = max(0.0, min(1.0, float(c)))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def family(rgb):
    """The palette family of a linear RGB colour ('white', 'gold', 'red', 'blue', 'green'), or None if refused."""
    r, g, b = (srgb(v) for v in rgb[:3])
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h *= 360.0
    if s < 0.12 or v < 0.04:
        return 'white'  # the black-to-white axis
    if 36.0 <= h <= 52.0 and s >= 0.18 and v >= 0.50:
        return 'gold'
    if (h >= 345.0 or h <= 10.0) and s >= 0.55 and v >= 0.30:
        return 'red'
    if 188.0 <= h <= 222.0 and 0.10 <= s <= 0.68 and v >= 0.58:
        return 'blue'
    if 70.0 <= h <= 165.0 and s >= 0.15 and v >= 0.20:
        return 'green'
    return None


def allowed(rgb):
    return family(rgb) is not None


def col(r, g, b, a=1.0):
    """A palette colour (linear RGB, alpha unused by the Conclave's materials: keep 1). Refuses colours
    outside the palette at once, so a bad colour fails where it is written."""
    if not allowed((r, g, b)):
        raise ValueError('colour (%.3f, %.3f, %.3f) is outside the Conclave palette' % (r, g, b))
    return (float(r), float(g), float(b), float(a))


def grey(v):
    return col(v, v, v)


# ---- named colours (linear). Albedo values stay physically plausible: nothing above 0.9.
WHITE = col(.82, .80, .76)        # warm white stone, plaster
WHITE_COOL = col(.78, .80, .82)   # cool white, porcelain
WHITE_PURE = col(.90, .90, .90)   # paint, cloth, blossom
IVORY = col(.85, .80, .70)        # aged white stone (still achromatic in sRGB)
ASH = grey(.32)                   # mid grey: worn stone, concrete
SLATE = grey(.12)                 # dark grey: slate, dark stone
CHARCOAL = grey(.05)              # near black
BLACK = col(.015, .015, .016)     # black lacquer, black stone, black metal
GOLD = col(1.0, .766, .336)       # metallic gold (use with the CN_Gold slot)
GOLD_PALE = col(.95, .80, .50)    # pale gold metal, brass-like but in palette
GOLD_DEEP = col(.80, .50, .12)    # deep gold paint, gilded cloth
GOLD_GRASS = col(.45, .30, .08)   # golden grass and wheat (non-metal)
GOLD_STRAW = col(.62, .48, .20)   # straw, dry stalks
RED = col(.60, .02, .02)          # red paint, cloth, banners
RED_DEEP = col(.30, .005, .008)   # deep red: leaves, lacquer
RED_BRIGHT = col(.80, .04, .03)   # red flowers, warning paint
BLUE = col(.35, .60, .85)         # light blue tiles, paint, cloth
BLUE_PALE = col(.60, .75, .90)    # very pale blue: glass tint, porcelain glaze
BLUE_ICE = col(.50, .72, .88)     # ice blue: Lightform light, water tint
GREEN_LEAF = col(.06, .14, .03)   # broadleaf foliage in full sun (sRGB value .41)
GREEN_DEEP = col(.025, .06, .015) # dark foliage: conifer needles, ivy, a crown's shaded inside
GREEN_GRASS = col(.09, .18, .04)  # lawn and meadow grass
GREEN_MOSS = col(.10, .14, .04)   # moss, lichen, yellow-green shoots
GREEN_PALE = col(.30, .50, .20)   # young leaves, sage, backlit blades

# ---- light colours (glow slot, lights in the level): normalised to their brightest channel.
LIGHT_WHITE = col(1.0, 1.0, 1.0)
LIGHT_WARM = col(1.0, .93, .80)   # still achromatic-ish warm white
LIGHT_GOLD = col(1.0, .72, .30)
LIGHT_BLUE = col(.55, .80, 1.0)
LIGHT_RED = col(1.0, .06, .04)
LIGHT_GREEN = col(.45, 1.0, .40)

PALETTE = {name: value for name, value in globals().items() if name.isupper() and isinstance(value, tuple) and len(value) == 4}
