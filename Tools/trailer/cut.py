#!/usr/bin/env python3
"""Cuts the levels trailer from the frames Movie Render Queue wrote (Tools/trailer/render.sh) and the game's own audio.

Run with a Python that has Pillow, ffmpeg on PATH:  python3 Tools/trailer/cut.py [--draft]
Reads Saved/Trailer/v2/frames/SEQ_T2_<Level>/<shot>.NNNN.jpeg and Tools/trailer/shots.py for the shot order and lengths.
Writes Marketing/Trailer/Physis_Trailer_Five_Worlds_1080p.mp4 (H.264, AAC, 30 fps, 2.39:1 picture inside 16:9).
--draft writes Saved/Trailer/v2/draft.mp4 at 960x540, fast.
"""
import pathlib
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/trailer'))
import shots

DRAFT = '--draft' in sys.argv
FRAMES = ROOT / 'Saved/Trailer/v2/frames'
OUT = ROOT / ('Saved/Trailer/v2/draft.mp4' if DRAFT else 'Marketing/Trailer/Physis_Trailer_Five_Worlds_1080p.mp4')
FONT = str(ROOT / 'Art/Fonts/P052-Roman.otf')
AUDIO = ROOT / 'Art/Audio'
W, H, FPS = 1920, 1080, 30
BAR = round((H - W / 2.39) / 2)   # letterbox bars
GOLD = (236, 200, 128)
LEAD = 45        # black before the eye, under the first heartbeats
DIP = 9          # frames of fade to and from black where one level gives way to the next
CARD_LINE = 'Born to end a war.'

# Level order, the title shown over its first shot (the Center's comes up as the camera lifts off her), and how long.
ORDER = (('Awakening', None), ('Center', None), ('Station', 'MERIDIAN STATION'), ('Conclave', 'THE CONCLAVE'), ('Grove', 'THE WOUNDED GROVE'),
         ('Arche', 'ARCHE'))
# Shots left out of this cut so that the levels end with the main theme's anthem (it runs 52 s).
SKIP = {'c4_choir', 's4_hall', 's5_spine', 'n4_lake', 'n5_terraces', 'g4_falls'}
ANTHEM_ON = 's3_approach'   # the shot the anthem lands on
# The system ffmpeg may be broken by a partial upgrade: a cached build is kept in Saved/Trailer/ffmpeg (see its bin/ffmpeg).
LOCAL_FFMPEG = ROOT / 'Saved/Trailer/ffmpeg/bin/ffmpeg'
FFMPEG = str(LOCAL_FFMPEG) if LOCAL_FFMPEG.exists() else 'ffmpeg'
CENTER_TITLE = ('a6_reveal', 'THE CENTER OF THE UNIVERSE')
TITLE_FRAMES = 84


def timeline():
    """[(kind, value, frames, level)] and the frame each level and shot starts at."""
    rows, at, starts = [('black', None, LEAD, None)], LEAD, {}
    for level, _ in ORDER:
        starts[level] = at
        for shot in shots.LEVELS[level]['shots']:
            if shot['name'] in SKIP:
                continue
            starts[shot['name']] = at
            rows.append(('shot', shot['name'], shot['frames'], level))
            at += shot['frames']
    for kind, value, n in (('black', None, 12), ('card', CARD_LINE, 78), ('logo', None, 186)):
        starts[kind] = at
        rows.append((kind, value, n, None))
        at += n
    return rows, starts, at


def spaced(draw, xy, text, font, fill, gap):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + gap
    return x


def title_layer(text):
    """A level's name: letter-spaced gold capitals over a thin rule, low on the left of the picture."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    font = ImageFont.truetype(FONT, 58)
    shadow = Image.new('L', (W, H), 0)
    x0, y0 = 150, H - BAR - 170
    end = spaced(ImageDraw.Draw(shadow), (x0, y0), text, font, 255, 11)
    ImageDraw.Draw(shadow).rectangle((x0, y0 + 82, end - 11, y0 + 84), fill=255)
    soft = shadow.filter(ImageFilter.GaussianBlur(16)).point(lambda v: min(255, int(v * 3.2)))
    layer.paste((0, 0, 0, 255), mask=soft)
    spaced(ImageDraw.Draw(layer), (x0, y0), text, font, GOLD + (255,), 11)
    ImageDraw.Draw(layer).rectangle((x0, y0 + 82, end - 11, y0 + 84), fill=GOLD + (255,))
    return layer


def card(text):
    font = ImageFont.truetype(FONT, 78)
    layer = Image.new('RGB', (W, H), (0, 0, 0))
    glow = Image.new('L', (W, H), 0)
    box = ImageDraw.Draw(glow).textbbox((0, 0), text, font=font)
    x, y = (W - (box[2] - box[0])) // 2, (H - (box[3] - box[1])) // 2 - 20
    ImageDraw.Draw(glow).text((x, y), text, font=font, fill=255)
    halo = glow.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .55))
    layer.paste((150, 105, 40), mask=halo)
    ImageDraw.Draw(layer).text((x, y), text, font=font, fill=GOLD)
    return layer


def logo():
    mark = Image.open(ROOT / 'Art/UI/T_UI_Title.png').convert('RGBA')
    mark = mark.crop(mark.getchannel('A').point(lambda a: 255 if a > 12 else 0).getbbox())
    mark = mark.resize((round(mark.width * 700 / mark.height), 700), Image.LANCZOS)
    base = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    base.alpha_composite(mark, ((W - mark.width) // 2, (H - mark.height) // 2))
    return base.convert('RGB')


def frames():
    rows, starts, total = timeline()
    black = Image.new('RGB', (W, H))
    titles = {starts[CENTER_TITLE[0]] + 30: title_layer(CENTER_TITLE[1])}
    for level, text in ORDER:
        if text:
            titles[starts[level] + 14] = title_layer(text)
    level_starts = {starts[level] for level, _ in ORDER[1:]} | {starts['black']}
    card_image, logo_image = card(CARD_LINE), logo()
    at = 0
    for kind, value, count, level in rows:
        files = sorted((FRAMES / ('SEQ_T2_' + level)).glob(value + '.*.jpeg')) if kind == 'shot' else None
        if kind == 'shot' and len(files) < count:
            raise SystemExit('%s has %d of %d frames: render %s first' % (value, len(files), count, level))
        for i in range(count):
            n = at + i
            if kind == 'shot':
                image = Image.open(files[i]).convert('RGB')
                if image.size != (W, H):
                    image = image.resize((W, H), Image.LANCZOS)
                # Fades: the eye comes up out of black; levels dip to black between them.
                level_alpha = 1.0
                if value == 'a1_eye':
                    level_alpha = min(1.0, (i + 1) / 36)
                for edge in level_starts:
                    if 0 <= n - edge < DIP:
                        level_alpha = min(level_alpha, (n - edge + 1) / DIP)
                    if 0 < edge - n <= DIP:
                        level_alpha = min(level_alpha, (edge - n - 1) / DIP)
                for first, layer in titles.items():
                    k = n - first
                    if 0 <= k < TITLE_FRAMES:
                        a = min(1.0, (k + 1) / 15, (TITLE_FRAMES - k) / 15)
                        faded = layer.copy()
                        faded.putalpha(layer.getchannel('A').point(lambda v: int(v * a)))
                        image.paste(faded, (0, 0), faded)
                if level_alpha < 1:
                    image = Image.blend(black, image, max(0.0, level_alpha))
                ImageDraw.Draw(image).rectangle((0, 0, W, BAR - 1), fill=(0, 0, 0))
                ImageDraw.Draw(image).rectangle((0, H - BAR, W, H), fill=(0, 0, 0))
            elif kind == 'card':
                image = Image.blend(black, card_image, min(1.0, (i + 1) / 20, (count - i) / 20))
            elif kind == 'logo':
                image = Image.blend(black, logo_image, min(1.0, (i + 1) / 45, (count - i) / 36))
            else:
                image = black
            yield image
        at += count


def audio(starts, seconds):
    """ffmpeg inputs and a filter graph: the awakening's own sounds and music, the voice, then the main theme, whose
    anthem (96 s into the track) lands on ANTHEM_ON."""
    t = lambda frame: frame / FPS
    eye, gasp, reveal, station = t(starts['a1_eye']), t(starts['a1_gasp']), t(starts['a6_reveal']), t(starts['Station'])
    anthem = t(starts[ANTHEM_ON])
    center = t(starts['Center'])
    theme_from = 96.0 - (anthem - center)          # the bridge plays under the Center
    # (file, seek, length, start in the trailer, volume, fade in, fade out)
    clips = (
        ('Center/S_Awaken_Heart.wav', 0, 3.0, 0.1, 1.0, 0, .3),
        ('Center/S_Awaken_Heart.wav', 0, 3.0, 1.7, 1.0, 0, .3),
        ('Center/S_Awaken_Heart.wav', 0, 3.0, 3.3, 1.0, 0, .3),
        ('Center/S_Awaken_Gasp.wav', 0, 7.8, gasp - .1, 1.0, 0, 1.0),
        ('Center/S_Music_Awakening.wav', 0, center + 4.5 - eye, eye, 1.7, 1.5, 5.5),
        ('Voice/Center/S_VO_Awakening.wav', 0, 7.9, reveal + .4, 1.5, 0, .2),
        ('Game/S_Music_MainTheme.wav', theme_from, seconds - center, center, 1.45, 5.0, 3.0),
        ('S_Opening.wav', 14.0, 7.0, station, .45, .4, 1.5),
    )
    inputs, graph, names = [], [], []
    for k, (name, seek, length, start, volume, fade_in, fade_out) in enumerate(clips):
        inputs += ['-ss', '%.3f' % seek, '-t', '%.3f' % length, '-i', str(AUDIO / name)]
        chain = '[%d:a]aresample=48000,aformat=channel_layouts=stereo,volume=%.2f' % (k + 1, volume)
        if fade_in:
            chain += ',afade=t=in:d=%.2f' % fade_in
        if fade_out:
            chain += ',afade=t=out:st=%.3f:d=%.2f' % (max(0, length - fade_out), fade_out)
        chain += ',adelay=%d:all=1[a%d]' % (round(start * 1000), k)
        graph.append(chain)
        names.append('[a%d]' % k)
    graph.append('%samix=inputs=%d:normalize=0:duration=longest,alimiter=limit=0.95,afade=t=out:st=%.3f:d=2.5[mix]' % (''.join(names), len(names), seconds - 2.5))
    return inputs, ';'.join(graph)


def main():
    rows, starts, total = timeline()
    seconds = total / FPS
    inputs, graph = audio(starts, seconds)
    size = (960, 540) if DRAFT else (W, H)
    video = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24'] if DRAFT else \
            ['-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high', '-b:v', '14M', '-maxrate', '20M', '-bufsize', '28M']
    command = [FFMPEG, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % size, '-r', str(FPS), '-i', '-'] + inputs + \
              ['-filter_complex', graph, '-map', '0:v', '-map', '[mix]', '-t', '%.3f' % seconds] + video + \
              ['-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-movflags', '+faststart', str(OUT)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    for n, image in enumerate(frames()):
        if DRAFT:
            image = image.resize(size, Image.BILINEAR)
        encoder.stdin.write(image.tobytes())
        if n % 300 == 0:
            print('frame', n, 'of', total, flush=True)
    encoder.stdin.close()
    encoder.wait()
    print('wrote', OUT, round(seconds, 1), 's', 'starts', {k: round(v / FPS, 1) for k, v in starts.items() if k in ('a1_eye', 'Center', 'Station', ANTHEM_ON, 'Conclave', 'Grove', 'Arche', 'card', 'logo')})


main()
