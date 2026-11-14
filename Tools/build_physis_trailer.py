"""Cuts the one-minute Steam trailer from recorded gameplay clips, title cards and the main theme.

Run with a Python that has Pillow, with ffmpeg on PATH: python build_physis_trailer.py
Clips are frame sequences in Marketing/Trailer/Clips/<name>/MovieFrame*.png, recorded in Unreal at
1/30 s of game time per frame. Writes Marketing/Trailer/Physis_Trailer_1080p.mp4 (H.264, AAC, 30 fps).
"""
import pathlib
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIPS = ROOT / 'Marketing/Trailer/Clips'
OUT = ROOT / 'Marketing/Trailer/Physis_Trailer_1080p.mp4'
FONT = str(ROOT / 'Art/Fonts/P052-Roman.otf')
W, H, FPS = 1920, 1080, 30
GOLD = (236, 200, 128)
MUSIC_START = 84.0  # the bridge, so the anthem lands as the battle opens

# (kind, value, first frame, frame count, crop): clips are trimmed to their best moments.
EDIT = (
    ('card', 'If you found God', 0, 120, None),
    ('clip', '01_battle', 0, 270, 'centre'),
    ('card', 'What would you say to Him?', 0, 120, None),
    ('clip', '02_scan', 0, 180, 'top'),
    ('clip', '03_platform', 0, 90, 'centre'),
    ('card', 'That He loves you?', 0, 120, None),
    ('clip', '04_katana', 0, 150, 'centre'),
    ('clip', '05_charge', 0, 180, 'centre'),
    ('clip', '07_boss', 0, 60, 'centre'),
    ('card', 'Or that He hurt you?', 0, 120, None),
    ('clip', '06_riddle', 0, 150, 'centre'),
    ('logo', None, 0, 210, None),
)
FADE = 8


def fit(image, crop):
    """Scales a recorded frame to 1920 wide and crops it to 1080 tall."""
    scale = W / image.width
    image = image.resize((W, round(image.height * scale)), Image.LANCZOS)
    top = 0 if crop == 'top' else (image.height - H) // 2
    return image.crop((0, top, W, top + H))


def card(text, alpha):
    """Gold serif line on black with a soft glow."""
    font = ImageFont.truetype(FONT, 76)
    layer = Image.new('RGB', (W, H), (0, 0, 0))
    glow = Image.new('L', (W, H), 0)
    box = ImageDraw.Draw(glow).textbbox((0, 0), text, font=font)
    x, y = (W - (box[2] - box[0])) // 2, (H - (box[3] - box[1])) // 2 - 20
    ImageDraw.Draw(glow).text((x, y), text, font=font, fill=255)
    halo = glow.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .55))
    layer.paste((150, 105, 40), mask=halo)
    ImageDraw.Draw(layer).text((x, y), text, font=font, fill=GOLD)
    return Image.blend(Image.new('RGB', (W, H)), layer, alpha)


def logo(alpha):
    mark = Image.open(ROOT / 'Art/UI/T_UI_Title.png').convert('RGBA')
    mark = mark.crop(mark.getchannel('A').point(lambda a: 255 if a > 12 else 0).getbbox())
    mark = mark.resize((round(mark.width * 760 / mark.height), 760), Image.LANCZOS)
    base = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    base.alpha_composite(mark, ((W - mark.width) // 2, (H - mark.height) // 2))
    return Image.blend(Image.new('RGB', (W, H)), base.convert('RGB'), alpha)


def frames():
    for kind, value, first, count, crop in EDIT:
        sequence = sorted((CLIPS / value).glob('MovieFrame*.png'))[first:first + count] if kind == 'clip' else None
        for i in range(count):
            edge = min(i + 1, count - i, FADE) / FADE
            if kind == 'card':
                yield card(value, min(1.0, min(i + 1, count - i) / 24))
            elif kind == 'logo':
                yield logo(min(1.0, (i + 1) / 45) * min(1.0, (count - i) / 30))
            else:
                image = fit(Image.open(sequence[min(i, len(sequence) - 1)]).convert('RGB'), crop)
                yield Image.blend(Image.new('RGB', (W, H)), image, edge) if edge < 1 else image


def main():
    total = sum(entry[3] for entry in EDIT)
    seconds = total / FPS
    music = ROOT / 'Art/Audio/Game/S_Music_MainTheme.wav'
    command = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
               '-ss', str(MUSIC_START), '-t', '%.3f' % seconds, '-i', str(music),
               '-af', 'afade=t=in:d=1.5,afade=t=out:st=%.3f:d=3.5' % (seconds - 3.5),
               '-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-b:v', '12M', '-maxrate', '16M', '-bufsize', '24M',
               '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', str(OUT)]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    for n, image in enumerate(frames()):
        encoder.stdin.write(image.tobytes())
        if n % 300 == 0:
            print('frame', n, 'of', total, flush=True)
    encoder.stdin.close()
    encoder.wait()
    print('wrote', OUT, round(seconds, 1), 's')


main()
