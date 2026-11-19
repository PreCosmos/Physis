"""Music and ambience for Hesper, the City of One Voice (level 7, Arche).

Run with the Kokoro venv's packages from the project folder (numpy and soundfile: nothing here speaks):
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/build_physis_hesper_audio.py [music] [amb] [NAME ...]
--out DIR writes elsewhere; --excerpt SECONDS [--from-bar N] writes only that much (needs --out).

The music is a score for Tools/music/muse.py rendered by MuseScore 4 with Muse Sounds (Halcyon's Band, bed and line,
and its finishing: hall, loop fold, level ride, soft knee, the common loudness). Writes
Art/Audio/Hesper/S_Music_Hesper.wav; it loops without a seam.

The ambience beds are synthesised with the Conclave's loop-safe helpers: S_Amb_Hesper the plateau's wind at dusk,
S_Amb_Concord the engine's one tone (it stops with the Cantor: tag HesperHush), S_Amb_Reeds the Reed Terraces.
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'music')]
import build_physis_conclave_audio as conclave  # noqa: E402
import build_physis_halcyon_audio as ha  # noqa: E402
import muse  # noqa: E402
from build_physis_center_audio import band, t_  # noqa: E402
from build_physis_conclave_audio import MUSIC_LUFS, blend, bubble, drift, fold, hall, noise_bed, put, ride, ring, whole, wobble, write  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / 'Art/Audio/Hesper'
WORK = ROOT / 'Saved/Music'
RATE = 44100
HALL = .5
KNEE = 2.0

# A Aeolian round one tone, A: the Concord's. The chant (theme A) is sung in unison and doubled in unison, so for the
# first half of the piece there is no harmony at all, only octaves. Dissonance is the chant in canon a bar apart and a
# second away; the city speaking again is the chant harmonised in four real parts. Themes: each bar's (beat, key, beats).
CHANT = (((0, 69, 2), (2, 72, 1), (3, 71, 1)), ((0, 69, 1), (1, 67, 1), (2, 69, 2)),
         ((0, 72, 1), (1, 74, 1), (2, 76, 1.5), (3.5, 74, .5)), ((0, 72, 2), (2, 71, 2)),
         ((0, 69, 1), (1, 72, 1), (2, 74, 1), (3, 72, 1)), ((0, 71, 1.5), (1.5, 69, .5), (2, 67, 2)),
         ((0, 65, 1), (1, 67, 1), (2, 69, 1), (3, 71, 1)), ((0, 69, 4),))
# Its answer, the Serene's (theme B), heard only at the end: the same contour turned upward and left open.
ANSWER = (((0, 76, 1), (1, 74, 1), (2, 72, 2)), ((0, 74, 1), (1, 76, 1), (2, 79, 2)), ((0, 77, 1.5), (1.5, 76, .5), (2, 74, 2)), ((0, 76, 4),))
HARMONY = ('Am', 'Em', 'F', 'Am', 'Dm', 'Em', 'F', 'Asus')
DUSK = ('Am', 'F', 'C', 'G')
ha.CHORD.update({'A5': (33, 45, (57, 64), (69, 76)), 'Dm': (38, 50, (57, 62), (65, 69)), 'Em': (40, 52, (55, 59), (64, 67))})
CHORD = ha.CHORD
TEMPO, BARS = 60, 56


def drone(b, bar, bars, level, names=('Contrabasses', 'Violoncellos', 'Violas'), key=45):
    """The Concord's tone: A held in octaves."""
    at, beats = bar * 4, bars * 4
    for name, k in zip(names, (key - 12, key, key + 12)):
        b(name, at, level).note(at, beats, k)


def hesper_score():
    """Hesper: the City of One Voice (56 bars at 60 bpm, 3 min 44 s, loops).
    1  bars 0-7    The tone: A in the low strings and the women's voices, nothing else; a tubular bell once, far.
    2  bars 8-19   One voice: the chant in unison and octaves (women, English horn, violas, horn), no harmony at all,
                   over the drone; then once more with every part on it, louder, still one line.
    3  bars 20-27  Dusk: the drone gives way to a slow progression, harp and strings; the flute alone, unsure.
    4  bars 28-35  Dissonance: the chant in canon, the oboe a bar behind and a second up, the clarinet two bars behind
                   and a third down; tremolo strings, a timpani swell.
    5  bars 36-47  Many voices: the chant harmonised in four real parts (violins, horns, cellos, women), forte, and
                   the trumpet's answer over it.
    6  bars 48-55  Evening: the drone again, very soft, but the women hold a fifth and then a chord: the tone has
                   company; the oboe remembers the answer; into bar 0."""
    score = muse.Score(tempo=TEMPO, title='Physis - Hesper')
    b = ha.Band(score)
    # 1. The tone (bars 0-7).
    drone(b, 0, 8, 1)
    b('Women', 0, 0).note(8, 24, 69)
    b.swell('Women', 8, 20, 'crescendo')
    b('Tubular Bells', 16, 0).note(16, 6, (57, 69))
    # 2. One voice (bars 8-19).
    drone(b, 8, 12, 1)
    ha.line(b, 'Women', 8, CHANT, 2)
    ha.line(b, 'English Horn', 8, CHANT, 1, shift=-12)
    ha.line(b, 'Violins 2', 12, CHANT[4:], 1)
    ha.line(b, 'Women', 16, CHANT[:4], 3)
    ha.line(b, 'Horn in F', 16, CHANT[:4], 2, shift=-12)
    ha.line(b, 'Violins 1', 16, CHANT[:4], 2)
    ha.line(b, 'Oboe', 16, CHANT[:4], 2)
    # 3. Dusk (bars 20-27).
    for rep in range(2):
        for i, name in enumerate(DUSK):
            bar = 20 + rep * 4 + i
            ha.bed(b, bar, 1, name, 1, tremolo=rep == 1)
        ha.ripples(b, 20 + rep * 4, DUSK, 0, high=rep == 1)
    ha.line(b, 'Flute', 21, CHANT[:2], 1, shift=12)
    ha.line(b, 'Flute', 25, ANSWER[:2], 1)
    b('Vibraphone', 96, 0).note(96, 8, (81, 88))
    # 4. Dissonance (bars 28-35).
    b('Violas', 112, 2).note(112, 32, (57, 69), tremolo=3)
    b('Contrabasses', 112, 2).note(112, 32, 33)
    ha.line(b, 'Violins 1', 28, CHANT, 2)
    ha.line(b, 'Oboe', 29, CHANT[:7], 2, shift=2)
    ha.line(b, 'Clarinet in B♭', 30, CHANT[:6], 2, shift=-4)
    ha.line(b, 'Trombone', 31, CHANT[:5], 2, shift=-19)
    b('Timpani', 128, 1).note(128, 16, 45, tremolo=3)
    b.swell('Timpani', 128, 144, 'crescendo')
    b('Suspended Cymbal', 136, 0).note(136, 8, 60, tremolo=3)
    b.swell('Suspended Cymbal', 136, 144, 'crescendo')
    # 5. Many voices (bars 36-47): the chant harmonised, then the answer over it.
    for i in range(12):
        name = HARMONY[i % 8]
        bar = 36 + i
        ha.bed(b, bar, 1, name, 4 if bar < 44 else 3)
        at = bar * 4
        b('Tuba', at, 2).note(at, 4, CHORD[name][0] if CHORD[name][0] >= 34 else CHORD[name][0] + 12)
    ha.line(b, 'Violins 1', 36, CHANT, 4)
    ha.line(b, 'Women', 36, CHANT, 3)
    ha.line(b, 'Horn in F', 36, CHANT[:4], 3, shift=-5)
    ha.line(b, 'Horn in F', 40, CHANT[4:], 3, shift=-8)
    ha.line(b, 'Trumpet in B♭', 44, ANSWER, 3)
    ha.line(b, 'Flute', 44, ANSWER, 2, shift=12)
    ha.ripples(b, 36, HARMONY, 2)
    ha.ripples(b, 44, DUSK, 2, high=True)
    b('Timpani', 144, 3).note(144, 1, 45, artic='accent')
    b('Suspended Cymbal', 144, 1).note(144, 4, 60)
    b('Tubular Bells', 176, 2).note(176, 6, (57, 69))
    # 6. Evening (bars 48-55).
    drone(b, 48, 8, 0)
    b('Women', 192, 0).note(192, 8, 69)
    b('Women').note(200, 8, (64, 69))
    b('Women').note(208, 16, (60, 64, 69))
    ha.line(b, 'Oboe', 50, ANSWER, 1)
    ha.ripples(b, 52, ('Am',), 0)
    b('Tubular Bells', 212, 0).note(212, 6, (57, 69))
    return score


def hesper_music(excerpt=None, from_bar=0, profile='MuseSounds'):
    import soundfile
    WORK.mkdir(parents=True, exist_ok=True)
    score = hesper_score()
    assert score.bars() == BARS, score.bars()
    tag = 'Hesper' if profile == 'MuseSounds' else 'Hesper_basic'
    score.write(WORK / (tag + '.musicxml'))
    missing = muse.render(WORK / (tag + '.musicxml'), WORK / (tag + '_raw.wav'), profile=profile, keep_score=WORK / (tag + '.mscz'))
    print('Hesper: %d bars at %d bpm, profile %s; without a sound of the profile: %s' % (score.bars(), score.tempo, profile, missing), flush=True)
    audio, rate = soundfile.read(WORK / (tag + '_raw.wav'), dtype='float32')
    assert rate == RATE and audio.ndim == 2 and audio.shape[1] == 2, (rate, audio.shape)
    beat = 60 / TEMPO
    total = int((BARS * 4 * beat + 8.0) * RATE)
    mix = np.zeros((total, 2))
    mix[:min(total, len(audio))] = audio[:total]
    mix = hall(mix, 4.6, .6 * HALL, 71, 8000)
    if excerpt:
        mix = mix[int(from_bar * 4 * beat * RATE):][:int(excerpt * RATE)]
        mix[-int(1.5 * RATE):] *= np.linspace(1, 0, int(1.5 * RATE))[:, None]
        mix = ride(mix / np.abs(mix).max())
    else:
        mix = fold(mix, BARS * 4 * beat)
        pad = 12 * RATE
        mix = ride(np.concatenate((mix[-pad:], mix, mix[:pad])) / np.abs(mix).max())[pad:-pad]
    mix = mix / np.abs(mix).max()
    mix = np.tanh(mix * KNEE) / np.tanh(KNEE)
    write('S_Music_Hesper_Excerpt' if excerpt else 'S_Music_Hesper', mix, .9, MUSIC_LUFS)


# ---------------------------------------------------------------- ambience (loops)

rng = np.random.default_rng(71)


def amb_hesper(seconds=60):
    """The plateau at dusk: a dry wind that rises off the drop in long slow gusts, a whistle where it finds the
    columns, grass hissing, and far under it the Concord's tone, so faint it is felt more than heard."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    gust = (.5 + .5 * drift(n, 6, 771)) ** 1.6
    wind = noise_bed(n, 60, 280, 772) * (.5 + .5 * gust)[:, None] + noise_bed(n, 500, 2200, 773) * (.1 + .9 * gust)[:, None] * .45
    grass = noise_bed(n, 3000, 9000, 774) * (.15 + .85 * gust ** 2)[:, None]
    whistle = np.zeros((n, 2))
    for ch, f in enumerate((whole(523.3, n), whole(587.3, n))):
        whistle[:, ch] = np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * (gust ** 3) * (.5 + .5 * wobble(n, .3, 2, 775 + ch))
    tone = np.zeros((n, 2))
    for f, amp in ((whole(110.0, n), 1.0), (whole(220.0, n), .4)):
        for ch in range(2):
            tone[:, ch] += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 6))
    mix = blend((wind, -26), (grass, -36), (band(whistle, 300, 3000), -44), (tone, -46))
    write('S_Amb_Hesper', ring(mix, 3.0, .3, 779, 5000), .7, -23)


def amb_concord(seconds=40):
    """The Concord, near: one tone, A, enormous and perfectly steady, in the drum and pipes: a fundamental and its
    harmonics, each pipe a hair off so the whole slowly beats, and a breath of air through the horn. It stops when the
    Cantor falls (tag HesperHush)."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    tone = np.zeros((n, 2))
    for h, amp in ((1, 1.0), (2, .55), (3, .3), (4, .22), (5, .12), (6, .08), (8, .05)):
        for ch in range(2):
            f = whole(55.0 * h * (1 + (.0007 if ch else -.0007) * h), n)
            tone[:, ch] += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 6))
    tone *= (.85 + .15 * np.stack([wobble(n, .1, .5, 781 + ch) for ch in range(2)], 1))
    air = noise_bed(n, 200, 1400, 783) * (.6 + .4 * np.stack([wobble(n, .3, 1.5, 784 + ch) for ch in range(2)], 1))
    mix = blend((tone, -22), (air, -36))
    write('S_Amb_Concord', ring(mix, 2.6, .35, 789, 4000), .75, -21)


def amb_reeds(seconds=40):
    """The Reed Terraces: reeds rustling in the wind off the edge, water trickling from one pool to the next, now and
    then a drop or a small fish breaking the surface."""
    n = int(seconds * RATE)
    gust = (.5 + .5 * drift(n, 5, 791)) ** 1.4
    rustle = noise_bed(n, 1800, 7000, 792) * (.2 + .8 * gust)[:, None] * np.clip(np.stack([wobble(n, 4, 14, 793 + ch) for ch in range(2)], 1), 0, 1)
    trickle = noise_bed(n, 500, 3000, 795) * np.clip(np.stack([wobble(n, 2, 8, 796 + ch) for ch in range(2)], 1), 0, 1) ** 2
    drops = np.zeros((n, 2))
    at = rng.uniform(0, 1)
    while at < seconds:
        put(drops, bubble(rng.uniform(400, 1400), rng.uniform(.02, .06)), at, rng.uniform(.1, .3), rng.uniform(-.8, .8))
        at += rng.uniform(.3, 1.8)
    mix = blend((rustle, -30), (trickle, -32), (ring(drops, 1.0, .3, 798, 6000), -33))
    write('S_Amb_Reeds', mix, .7, -23)


SOUNDS = {'S_Amb_Hesper': amb_hesper, 'S_Amb_Concord': amb_concord, 'S_Amb_Reeds': amb_reeds}
PARTS = {'amb': list(SOUNDS)}


if __name__ == '__main__':
    args, options = sys.argv[1:], {}
    for flag in ('--out', '--excerpt', '--from-bar'):
        if flag in args:
            at = args.index(flag)
            options[flag] = args[at + 1]
            del args[at:at + 2]
    if '--excerpt' in options and '--out' not in options:
        sys.exit('--excerpt writes a test file: give --out DIR (not the import folder)')
    OUT = pathlib.Path(options.get('--out', OUT))
    OUT.mkdir(parents=True, exist_ok=True)
    conclave.OUT = OUT
    names = [name for part in (args or ['music', 'amb']) for name in (['S_Music_Hesper'] if part == 'music' else PARTS.get(part, [part]))]
    for name in names:
        conclave.reseed(name)
        rng = np.random.default_rng(conclave.zlib.crc32(name.encode()) + 7)
        if name == 'S_Music_Hesper':
            hesper_music(float(options['--excerpt']) if '--excerpt' in options else None, int(options.get('--from-bar', 0)))
        elif name in SOUNDS:
            SOUNDS[name]()
        else:
            sys.exit('unknown part %s; parts: music, amb, %s' % (name, ', '.join(SOUNDS)))
