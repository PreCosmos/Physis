"""Music, ambience and effects for Morrow, the Valley Before Morning (level 8, Earth).

Run with the Kokoro venv's packages from the project folder (numpy and soundfile: nothing here speaks):
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/build_physis_morrow_audio.py [music] [amb] [sfx] [NAME ...]
--out DIR writes elsewhere; --excerpt SECONDS [--from-bar N] writes only that much (needs --out).

The music is a score for Tools/music/muse.py rendered by MuseScore 4 with Muse Sounds (Halcyon's Band, bed and line, and
its finishing: hall, loop fold, level ride, soft knee, the common loudness). Writes Art/Audio/Morrow/S_Music_Morrow.wav;
it loops without a seam.

The beds and effects are synthesised with the Conclave's loop-safe helpers: S_Amb_Morrow the valley in the hour before
sunrise, S_Amb_Lull the Hold's cold engine (it stops with the Unrisen: tag MorrowHush), S_Amb_Morning the inside of
Maren's mind; S_SitWith (she kneels and stays), S_Wake (the Rime lets go of someone), S_Inner (the way into the
Morning).
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
from build_physis_conclave_audio import MUSIC_LUFS, blend, drift, fold, hall, noise_bed, put, ride, ring, whole, wobble, write  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / 'Art/Audio/Morrow'
WORK = ROOT / 'Saved/Music'
RATE = 44100
HALL = .55
KNEE = 2.0

# D minor, a lullaby (the theme: what Maren sang him, or might have; nobody says), eight bars of (beat, key, beats).
LULLABY = (((0, 69, 2), (2, 67, 1), (3, 65, 1)), ((0, 64, 1), (1, 65, 1), (2, 62, 2)),
           ((0, 65, 1), (1, 67, 1), (2, 69, 1.5), (3.5, 70, .5)), ((0, 69, 3), (3, 67, 1)),
           ((0, 70, 2), (2, 69, 1), (3, 67, 1)), ((0, 65, 1), (1, 64, 1), (2, 62, 2)),
           ((0, 64, 1), (1, 65, 1), (2, 67, 1), (3, 64, 1)), ((0, 62, 4),))
# The same tune in the morning: D major (F to F sharp, B flat to B), its last bar lifted to the third.
MORNING = tuple(tuple((beat, {65: 66, 70: 71}.get(key, key), beats) for beat, key, beats in bar) for bar in LULLABY[:7]) + (((0, 66, 2), (2, 69, 2)),)
MINOR = ('Dm', 'Bb', 'F', 'C', 'Gm', 'Dm', 'A', 'Dm')
MAJOR = ('D', 'G', 'A', 'Bm', 'G', 'D', 'A', 'D')
ha.CHORD.update({'Bb': (34, 46, (53, 58), (62, 65)), 'Bm': (35, 47, (54, 59), (62, 66)), 'D5': (38, 45, (57, 62), (69, 74))})
CHORD = ha.CHORD
TEMPO, BARS = 60, 56


def frost(b, bar, bars, level):
    """The frost: a held open fifth high in the violins, tremolo, and the basses' low D under it."""
    at, beats = bar * 4, bars * 4
    b('Violins 1', at, level).note(at, beats, (81, 88), tremolo=3)
    b('Contrabasses', at, level).note(at, beats, 38)


def ice(b, bar, bars, level, seed):
    """Ice ticking: the glockenspiel's stray high notes, out of time, from the chord's tones."""
    rng = np.random.default_rng(seed)
    for k in range(bars * 2):
        at = bar * 4 + k * 2 + float(rng.choice((0, .5, 1, 1.5)))
        b('Glockenspiel', at, level).note(at, .5, int(rng.choice((86, 88, 93, 98))))


def morrow_score():
    """Morrow: the Valley Before Morning (56 bars at 60 bpm, 3 min 44 s, loops).
    1  bars 0-7    Frost: a high open fifth, tremolo, the basses' D, the glockenspiel ticking like ice; nothing moves.
    2  bars 8-19   The lullaby: the clarinet alone over the slow minor progression, then the flute and the oboe in
                   thirds, the harp turning each chord over.
    3  bars 20-27  The Rime: the tune held still, each of its notes sustained in the women's voices and the divided
                   strings; a timpani roll and a cymbal swell, and they stop.
    4  bars 28-35  Sitting with: very quiet. The solo cello plays the lullaby an octave down; nothing hurries it.
    5  bars 36-47  Morning: the progression turns major and the tune goes up in the horns and the violins, the trumpet
                   answers, the bells; the one forte in the piece.
    6  bars 48-55  The valley again: the major fades back to the open fifth, and the oboe remembers the first bar of
                   the morning tune over it; into bar 0."""
    score = muse.Score(tempo=TEMPO, title='Physis - Morrow')
    b = ha.Band(score)
    # 1. Frost (bars 0-7).
    frost(b, 0, 8, 0)
    ice(b, 0, 8, 0, 81)
    b('Harp', 16, 0).note(16, 4, (50, 57, 62))
    # 2. The lullaby (bars 8-19).
    for rep in range(2):
        for i, name in enumerate(MINOR[:6] if rep else MINOR):
            bar = 8 + rep * 8 + i
            if bar < 20:
                ha.bed(b, bar, 1, name, 1, cellos=True, basses=i % 2 == 0)
        ha.ripples(b, 8 + rep * 8, MINOR[:4], 0)
    ha.line(b, 'Clarinet in B♭', 8, LULLABY, 1)
    ha.line(b, 'Flute', 16, LULLABY[:4], 1, shift=12)
    ha.line(b, 'Oboe', 16, LULLABY[:4], 1, shift=8)
    # 3. The Rime (bars 20-27): each note of the tune held where it was.
    for i, row in enumerate(LULLABY):
        at = (20 + i) * 4
        b('Women', at, 1).note(at, 4, row[0][1])
        b('Violas', at, 0).note(at, 4, row[0][1] - 12, tremolo=3)
    b('Violoncellos', 80, 0).note(80, 32, 50)
    b('Contrabasses', 80, 0).note(80, 32, 38)
    b('Timpani', 96, 0).note(96, 12, 38, tremolo=3)
    b.swell('Timpani', 96, 108, 'crescendo')
    b('Suspended Cymbal', 100, 0).note(100, 8, 60, tremolo=3)
    b.swell('Suspended Cymbal', 100, 108, 'crescendo')
    ice(b, 24, 4, 0, 82)
    # 4. Sitting with (bars 28-35).
    ha.line(b, 'Violoncellos', 28, LULLABY, 1, shift=-12)
    for i, name in enumerate(MINOR):
        cb, vc, vla, v2 = CHORD[name]
        at = (28 + i) * 4
        b('Violas', at, 0).note(at, 4, vla)
        b('Contrabasses', at, 0).note(at, 4, cb)
    b('Harp', 140, 0).note(140, 4, (62, 69, 74))
    # 5. Morning (bars 36-47).
    for i in range(12):
        name = MAJOR[i % 8]
        bar = 36 + i
        ha.bed(b, bar, 1, name, 3 if 38 <= bar < 46 else 2)
    ha.ripples(b, 36, MAJOR, 1, high=True)
    ha.ripples(b, 44, MAJOR[:4], 2, high=True)
    ha.line(b, 'Horn in F', 36, MORNING, 2, shift=-12)
    ha.line(b, 'Violins 1', 40, MORNING, 3, shift=12)
    ha.line(b, 'Women', 40, MORNING[:4], 2)
    ha.line(b, 'Trumpet in B♭', 44, MORNING[4:], 3)
    b('Tubular Bells', 160, 2).note(160, 6, (62, 74))
    b('Tubular Bells', 176, 1).note(176, 6, (57, 69))
    b('Timpani', 160, 2).note(160, 1, 38, artic='accent')
    b('Suspended Cymbal', 160, 1).note(160, 4, 60)
    # 6. The valley again (bars 48-55).
    for k, name in enumerate(('D', 'D5', 'D5', 'D5')):
        ha.bed(b, 48 + k * 2, 2, name, 0, basses=k < 2)
    frost(b, 52, 4, 0)
    ha.line(b, 'Oboe', 50, MORNING[:2], 1)
    ice(b, 52, 4, 0, 83)
    return score


def morrow_music(excerpt=None, from_bar=0, profile='MuseSounds'):
    import soundfile
    WORK.mkdir(parents=True, exist_ok=True)
    score = morrow_score()
    assert score.bars() == BARS, score.bars()
    tag = 'Morrow' if profile == 'MuseSounds' else 'Morrow_basic'
    score.write(WORK / (tag + '.musicxml'))
    missing = muse.render(WORK / (tag + '.musicxml'), WORK / (tag + '_raw.wav'), profile=profile, keep_score=WORK / (tag + '.mscz'))
    print('Morrow: %d bars at %d bpm, profile %s; without a sound of the profile: %s' % (score.bars(), score.tempo, profile, missing), flush=True)
    audio, rate = soundfile.read(WORK / (tag + '_raw.wav'), dtype='float32')
    assert rate == RATE and audio.ndim == 2 and audio.shape[1] == 2, (rate, audio.shape)
    beat = 60 / TEMPO
    total = int((BARS * 4 * beat + 8.0) * RATE)
    mix = np.zeros((total, 2))
    mix[:min(total, len(audio))] = audio[:total]
    mix = hall(mix, 5.0, .6 * HALL, 81, 7000)
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
    write('S_Music_Morrow_Excerpt' if excerpt else 'S_Music_Morrow', mix, .9, MUSIC_LUFS)


# ---------------------------------------------------------------- ambience (loops) and effects

rng = np.random.default_rng(81)


def crack(seconds, bright=5000.0):
    """Ice settling: a short dry tick and its ring, the high band of a noise burst falling away fast."""
    n = int(seconds * RATE)
    t = t_(seconds)
    burst = np.random.default_rng(int(rng.integers(0, 1 << 30))).normal(size=n) * np.exp(-t / (seconds / 6))
    return band(burst, bright * .4, bright * 2.2)


def amb_morrow(seconds=60):
    """The valley in the hour before sunrise: almost nothing. A cold air moving very slowly down from the peaks, a
    hiss in the frozen grass when it stirs, the reservoir's ice settling now and then with a tick or a long creak far
    off, and under everything a stillness that is not quite silence."""
    n = int(seconds * RATE)
    air = (.5 + .5 * drift(n, 4, 811)) ** 2
    wind = noise_bed(n, 50, 240, 812) * (.4 + .6 * air)[:, None] + noise_bed(n, 400, 1600, 813) * (.05 + .95 * air)[:, None] * .3
    grass = noise_bed(n, 3500, 9000, 814) * (.05 + .95 * air ** 3)[:, None]
    ice_ = np.zeros((n, 2))
    at = rng.uniform(0, 2)
    while at < seconds:
        put(ice_, crack(rng.uniform(.04, .12), rng.uniform(2500, 6000)), at, rng.uniform(.05, .4), rng.uniform(-.9, .9))
        at += rng.uniform(1.5, 7.0)
    creak = np.zeros((n, 2))
    for k in range(3):
        start, dur = rng.uniform(0, seconds), rng.uniform(1.5, 3.0)
        t = t_(dur)
        f = 90 + 40 * np.sin(2 * np.pi * .7 * t + rng.uniform(0, 6))
        tone = np.sin(np.cumsum(2 * np.pi * f / RATE)) * np.sin(np.pi * t / dur) ** 2 * (.6 + .4 * np.sign(np.sin(2 * np.pi * 23 * t)))
        put(creak, band(tone, 60, 900), start, .4, rng.uniform(-.6, .6))
    room = noise_bed(n, 20, 120, 815)
    mix = blend((wind, -30), (grass, -40), (ring(ice_, 2.5, .45, 816, 7000), -38), (ring(creak, 3.0, .5, 817, 3000), -40), (room, -44))
    write('S_Amb_Morrow', ring(mix, 3.0, .25, 819, 5000), .7, -25)


def amb_lull(seconds=40):
    """The Lull, near: the Hold's cold engine. A low compressor hum with a slow beat in it, the hiss of refrigerant,
    frost crackling where the cold meets the air. It stops when the Unrisen is sat with (tag MorrowHush)."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    hum = np.zeros((n, 2))
    for h, amp in ((1, 1.0), (2, .5), (3, .25), (5, .1), (7, .05)):
        for ch in range(2):
            f = whole(49.0 * h * (1 + (.0011 if ch else -.0011)), n)
            hum[:, ch] += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 6))
    hum *= (.8 + .2 * np.stack([wobble(n, .2, .8, 821 + ch) for ch in range(2)], 1))
    hiss = noise_bed(n, 2500, 9000, 823) * (.6 + .4 * np.stack([wobble(n, .1, .6, 824 + ch) for ch in range(2)], 1))
    crackle = np.zeros((n, 2))
    at = 0.0
    while at < seconds:
        put(crackle, crack(rng.uniform(.01, .03), rng.uniform(4000, 8000)), at, rng.uniform(.05, .3), rng.uniform(-.9, .9))
        at += rng.uniform(.04, .5)
    mix = blend((hum, -23), (hiss, -36), (crackle, -34))
    write('S_Amb_Lull', ring(mix, 2.0, .3, 829, 4000), .75, -21)


def amb_morning(seconds=40):
    """Inside Maren's mind: a kitchen at dawn with the sound turned almost all the way down. A slow clock that ticks a
    little too far apart, the room's close hush, and very high and far a held shimmer, like a breath not let out."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    clock = np.zeros((n, 2))
    at = 0.0
    while at < seconds - .2:
        put(clock, crack(.03, 3000.0), at, .5, -.3)
        at += 1.6
    hush = noise_bed(n, 80, 500, 831) * .5
    shimmer = np.zeros((n, 2))
    for f, amp in ((whole(1760.0, n), 1.0), (whole(2637.0, n), .5)):
        for ch in range(2):
            shimmer[:, ch] += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * (.6 + .4 * wobble(n, .05, .3, 833 + ch))
    mix = blend((ring(clock, 1.2, .35, 834, 5000), -34), (hush, -40), (shimmer, -48))
    write('S_Amb_Morning', mix, .7, -27)


def sfx_sit():
    """She kneels and stays: a low warm chord (D, A, F sharp) swelling in over a second and a half, and a breath."""
    t = t_(3.0)
    env = np.clip(t / 1.5, 0, 1) ** 1.5 * np.exp(-np.clip(t - 1.5, 0, None) / .9)
    tone = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((146.8, 1.0), (220.0, .6), (370.0, .35), (587.3, .12))) * env
    breath = band(np.random.default_rng(841).normal(size=len(t)), 300, 2400) * np.sin(np.pi * np.clip(t / 2.2, 0, 1)) ** 2 * .15
    write('S_SitWith', hall(tone + breath, 3.0, .45, 842, 4000), .6)


def sfx_wake():
    """The Rime lets go of someone: a run of small cracks, then a warm open fifth that blooms and fades."""
    t = t_(4.0)
    out = np.zeros((len(t), 2))
    for k in range(9):
        put(out, crack(rng.uniform(.03, .08), rng.uniform(3000, 7000)), .05 + k * rng.uniform(.03, .09), rng.uniform(.3, .7), rng.uniform(-.7, .7))
    env = np.clip((t - .5) / .8, 0, 1) * np.exp(-np.clip(t - 1.3, 0, None) / 1.1)
    warm = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((293.7, 1.0), (440.0, .7), (587.3, .3), (880.0, .12))) * env * .5
    out += np.stack((warm, warm), 1)
    write('S_Wake', hall(out, 3.5, .5, 843, 6000), .7)


def sfx_inner():
    """The way into the Morning: everything drops away under a long low swell, and at its top a single clear note."""
    t = t_(6.0)
    swell = np.sin(np.pi * np.clip(t / 5.0, 0, 1)) ** 2
    low = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((73.4, 1.0), (110.0, .5), (146.8, .3))) * swell
    note = np.sin(2 * np.pi * 1174.7 * t) * np.clip((t - 3.5) / .2, 0, 1) * np.exp(-np.clip(t - 3.7, 0, None) / 1.4) * .25
    air = band(np.random.default_rng(844).normal(size=len(t)), 100, 1200) * swell * .2
    write('S_Inner', hall(low + note + air, 4.5, .55, 845, 5000), .7)


SOUNDS = {'S_Amb_Morrow': amb_morrow, 'S_Amb_Lull': amb_lull, 'S_Amb_Morning': amb_morning, 'S_SitWith': sfx_sit, 'S_Wake': sfx_wake,
          'S_Inner': sfx_inner}
PARTS = {'amb': ['S_Amb_Morrow', 'S_Amb_Lull', 'S_Amb_Morning'], 'sfx': ['S_SitWith', 'S_Wake', 'S_Inner']}


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
    names = [name for part in (args or ['music', 'amb', 'sfx']) for name in (['S_Music_Morrow'] if part == 'music' else PARTS.get(part, [part]))]
    for name in names:
        conclave.reseed(name)
        rng = np.random.default_rng(conclave.zlib.crc32(name.encode()) + 7)
        if name == 'S_Music_Morrow':
            morrow_music(float(options['--excerpt']) if '--excerpt' in options else None, int(options.get('--from-bar', 0)))
        elif name in SOUNDS:
            SOUNDS[name]()
        else:
            sys.exit('unknown part %s; parts: music, amb, sfx, %s' % (name, ', '.join(SOUNDS)))
