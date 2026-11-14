"""Builds every Steam store and library image from in-game key art and the Physis logo.

Run with a Python that has Pillow: python build_steam_store_art.py
Reads Marketing/Steam/KeyArt/*.png (in-game captures) and Art/UI/T_UI_Title.png (logo with alpha).
Writes Marketing/Steam/Store/*.png|jpg|ico at the sizes Steamworks asks for.
"""
import pathlib

from PIL import Image, ImageEnhance, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = ROOT / 'Marketing/Steam/KeyArt'
OUT = ROOT / 'Marketing/Steam/Store'


def logo():
    """The title logo cropped to its visible pixels."""
    image = Image.open(ROOT / 'Art/UI/T_UI_Title.png').convert('RGBA')
    return image.crop(image.getchannel('A').point(lambda a: 255 if a > 12 else 0).getbbox())


def wordmark(full):
    """Only the PHYSIS lettering and rule, for wide, short capsules."""
    w, h = full.size
    part = full.crop((0, int(h * .72), w, h))
    return part.crop(part.getchannel('A').point(lambda a: 255 if a > 12 else 0).getbbox())


def emblem(full):
    """Only the tree emblem, for icons."""
    w, h = full.size
    part = full.crop((0, 0, w, int(h * .64)))
    return part.crop(part.getchannel('A').point(lambda a: 255 if a > 12 else 0).getbbox())


def cover(art, size, focus=(.5, .5)):
    """Scales art to fill size and crops around the focus point."""
    tw, th = size
    scale = max(tw / art.width, th / art.height)
    image = art.resize((round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    left = min(max(round(image.width * focus[0] - tw / 2), 0), image.width - tw)
    top = min(max(round(image.height * focus[1] - th / 2), 0), image.height - th)
    return image.crop((left, top, left + tw, top + th))


def shade(image, amount=.62, bottom=.0):
    """Darkens the art so the gold logo reads, more strongly towards the bottom when asked."""
    image = ImageEnhance.Brightness(image.convert('RGB')).enhance(amount)
    if bottom:
        ramp = Image.linear_gradient('L').resize(image.size)
        dark = Image.new('RGB', image.size, (0, 0, 0))
        image = Image.composite(dark, image, ramp.point(lambda v: int(v * bottom)))
    return image


def place(base, mark, width, centre):
    """Pastes the logo at a given width, centred on a point given in fractions."""
    height = round(mark.height * width / mark.width)
    if height > base.height * .9:
        height = round(base.height * .9)
        width = round(mark.width * height / mark.height)
    sized = mark.resize((width, height), Image.LANCZOS)
    glow = sized.getchannel('A').filter(ImageFilter.GaussianBlur(max(width // 40, 2)))
    shadow = Image.new('RGBA', sized.size, (0, 0, 0, 0))
    shadow.putalpha(glow.point(lambda a: int(a * .8)))
    x, y = round(base.width * centre[0] - width / 2), round(base.height * centre[1] - height / 2)
    base = base.convert('RGBA')
    base.alpha_composite(shadow, (x, y))
    base.alpha_composite(sized, (x, y))
    return base.convert('RGB')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    full = logo()
    word, tree = wordmark(full), emblem(full)
    arts = {path.stem: Image.open(path).convert('RGB') for path in sorted(KEY.glob('*.png'))}
    hero = arts.get('hero') or next(iter(arts.values()))
    battle = arts.get('battle', hero)
    tall = arts.get('tall', hero)
    # Physis stands just left of centre in the hero shot; tall crops centre on her.
    focus = (.47, .5)
    made = []

    def save(image, name, quality=None):
        path = OUT / name
        if name.endswith('.jpg'):
            image.convert('RGB').save(path, quality=quality or 92)
        else:
            image.save(path)
        made.append((name, image.size))

    header = place(shade(cover(battle, (920, 430)), .7), full, 300, (.5, .5))
    save(header, 'header_capsule_920x430.png')
    save(header, 'library_header_920x430.png')
    save(place(shade(cover(battle, (462, 174)), .55), word, 420, (.5, .5)), 'small_capsule_462x174.png')
    save(place(shade(cover(hero, (1232, 706), (.6, .45)), .72, .3), full, 380, (.27, .5)), 'main_capsule_1232x706.png')
    save(place(shade(cover(tall, (748, 896), focus), .75, .97), word, 560, (.5, .86)), 'vertical_capsule_748x896.png')
    save(place(shade(cover(tall, (600, 900), focus), .75, .97), word, 470, (.5, .87)), 'library_capsule_600x900.png')
    save(shade(cover(hero, (3840, 1240), (.5, .42)), .95), 'library_hero_3840x1240.png')
    background = cover(battle, (1438, 810)).filter(ImageFilter.GaussianBlur(6))
    save(shade(background, .45), 'page_background_1438x810.png')
    # Steam wants the library logo 1280 wide and/or 720 tall: the trimmed logo is scaled to exactly 720 tall.
    save(full.resize((round(full.width * 720 / full.height), 720), Image.LANCZOS), 'library_logo_transparent.png')
    icon = Image.new('RGBA', (512, 512), (14, 16, 22, 255))
    mark = tree.resize((round(tree.width * 440 / tree.height), 440), Image.LANCZOS)
    icon.alpha_composite(mark, ((512 - mark.width) // 2, 36))
    save(icon.resize((184, 184), Image.LANCZOS), 'community_icon_184x184.jpg', 95)
    save(icon.resize((256, 256), Image.LANCZOS), 'shortcut_icon_256x256.png')
    icon.save(OUT / 'shortcut_icon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    made.append(('shortcut_icon.ico', (256, 256)))
    save(place(shade(cover(hero, (800, 450), (.6, .45)), .72, .3), full, 250, (.25, .5)), 'event_cover_800x450.png')
    save(place(shade(cover(battle, (1920, 622)), .7), full, 420, (.5, .5)), 'event_header_1920x622.png')
    for name, size in made:
        print(name, size)


main()
