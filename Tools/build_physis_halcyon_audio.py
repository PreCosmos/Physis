"""Music and ambience for Halcyon, the Drowned Harbour (level 6, Earth).

Run with the Kokoro venv's packages from the project folder (numpy and soundfile: nothing here speaks):
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/build_physis_halcyon_audio.py [music] [amb] [NAME ...]
--out DIR writes elsewhere; --excerpt SECONDS [--from-bar N] writes only that much, as S_Music_Halcyon_Excerpt, for
listening tests (it needs --out). --soundfont-profile renders with MuseScore's basic SoundFont (needs --out).

The music is a score for Tools/music/muse.py, rendered by MuseScore 4 with Muse Sounds without its window (the score
and the raw render stay in Saved/Music/Halcyon.*), then finished as Arche's is (build_physis_arche_audio.arche_music):
the Conclave's hall at HALL, the loop fold, the level ride round the loop, a soft knee and the common loudness.
Writes Art/Audio/Halcyon/S_Music_Halcyon.wav, 44.1 kHz stereo 16-bit; it loops without a seam.

The ambience beds (S_Amb_*) are synthesised with the Conclave's loop-safe helpers (circular filtering, whole cycles,
events and reverb that wrap round the loop), so they loop without a seam too: S_Amb_Halcyon the harbour everywhere,
S_Amb_HeldSea the standing water round the Bastion (it stops with the Keel), S_Amb_Quarter the drowned streets.
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'music')]
import build_physis_conclave_audio as conclave  # noqa: E402
import muse  # noqa: E402
from build_physis_center_audio import band, env, t_  # noqa: E402
from build_physis_conclave_audio import (MUSIC_LUFS, TUBE, blend, bubble, drift, fold, groan, hall, noise_bed, put, ride, ring,  # noqa: E402
                                         whole, wobble, write)

ROOT = HERE.parent
OUT = ROOT / 'Art/Audio/Halcyon'
WORK = ROOT / 'Saved/Music'
RATE = 44100
HALL = .45
KNEE = 2.0

# D Dorian: the Grove is E minor, Arche C Aeolian. The raised sixth (B natural) is the town's own colour, sung in its
# hymn; the one D major passage is the morning before the wave, remembered.
#
# The Litany (theme A), a hymn tune of three four-bar lines, one for each line of the Just's oath: "Hold the line"
# (steady, round the dominant), "Remember the drowned" (falling to the tonic), "Let no wave come again" (climbing and
# left hanging on B over G: no cadence, because the oath never ends). Themes give each bar's notes as (beat, key, beats).
LITANY = (((0, 69, 1), (1, 69, 1), (2, 74, 1.5), (3.5, 72, .5)), ((0, 69, 2), (2, 67, 1), (3, 69, 1)),
          ((0, 65, 1), (1, 67, 1), (2, 69, 1), (3, 72, 1)), ((0, 74, 4),),
          ((0, 74, 1), (1, 72, 1), (2, 71, 2)), ((0, 69, 1.5), (1.5, 67, .5), (2, 65, 2)),
          ((0, 64, 1), (1, 65, 1), (2, 67, 1), (3, 64, 1)), ((0, 62, 3), (3, 64, 1)),
          ((0, 65, 1), (1, 67, 1), (2, 69, 2)), ((0, 72, 1), (1, 74, 1), (2, 76, 2)),
          ((0, 77, 1.5), (1.5, 76, .5), (2, 74, 1), (3, 72, 1)), ((0, 71, 4),))
LITANY_CHORDS = ('Dm', 'Am', 'F', 'Dm', 'G', 'Dm', 'C', 'Dm', 'F', 'C', 'Dm7', 'G')
# The morning (theme B): what Trace Reading shows, in D major, light and high (flute and glockenspiel).
MORNING = (((0, 78, 1), (1, 81, 1), (2, 83, 2)), ((0, 81, 1.5), (1.5, 79, .5), (2, 78, 2)),
           ((0, 76, 1), (1, 78, 1), (2, 79, 1), (3, 81, 1)), ((0, 78, 4),))
MORNING_CHORDS = ('D', 'G', 'Em', 'D')
# The wave: the hymn's harmony pulled flat (B flat), then the dominant with its leading tone, the only one in the piece.
WAVE_CHORDS = ('Dm', 'Bbmaj7', 'C', 'Am', 'Dm', 'Bbmaj7', 'Gm', 'A')
# Chords as they are bowed: contrabasses, cellos, violas (two notes), second violins (two notes); sounding pitch.
CHORD = {'D5': (38, 45, (57, 62), (69, 74)), 'Dm': (38, 50, (57, 62), (65, 69)), 'Dm7': (38, 50, (57, 60), (65, 69)),
         'Am': (45, 52, (57, 64), (69, 72)), 'F': (41, 53, (57, 60), (65, 69)), 'C': (36, 48, (55, 64), (67, 72)),
         'G': (43, 50, (59, 62), (67, 71)), 'Gm': (43, 50, (58, 62), (67, 70)), 'Bbmaj7': (34, 46, (53, 57), (62, 65)),
         'A': (45, 52, (57, 61), (64, 69)), 'D': (38, 50, (57, 62), (66, 69)), 'Em': (40, 52, (55, 59), (64, 67)),
         'Asus': (45, 52, (57, 62), (64, 69))}
TEMPO, BARS = 60, 56
LEVELS = ('pp', 'p', 'mp', 'mf', 'f', 'ff')
ORCHESTRA = ('Flute', 'Oboe', 'Clarinet in B♭', 'English Horn', 'Horn in F', 'Trumpet in B♭', 'Trombone', 'Tuba', 'Timpani',
             'Suspended Cymbal', 'Tubular Bells', 'Vibraphone', 'Glockenspiel', 'Harp', 'Women',
             'Violins 1', 'Violins 2', 'Violas', 'Violoncellos', 'Contrabasses')


class Band:
    """Parts by name, each remembering its dynamic so a marking is written only on a change."""

    def __init__(self, score):
        self.score, self.level = score, {}
        self.parts = {name: score.part(name) for name in ORCHESTRA}

    def __call__(self, name, at=None, level=None):
        if level is not None and self.level.get(name) != level:
            self.parts[name].dynamic(at, LEVELS[level])
            self.level[name] = level
        return self.parts[name]

    def swell(self, name, start, end, kind):
        self.parts[name].wedge(start, end, kind)
        self.level[name] = None


def bed(b, bar, bars, name, level, tremolo=False, cellos=True, basses=True):
    cb, vc, vla, v2 = CHORD[name]
    at, beats = bar * 4, bars * 4
    if basses:
        b('Contrabasses', at, level).note(at, beats, cb)
    if cellos:
        b('Violoncellos', at, level).note(at, beats, vc)
    b('Violas', at, level).note(at, beats, vla, tremolo=3 if tremolo else 0)
    b('Violins 2', at, level).note(at, beats, v2, tremolo=3 if tremolo else 0)


def line(b, name, bar, theme, level, shift=0, phrase=2, slur=True):
    """A melody from `bar`, slurred in phrases of `phrase` bars."""
    for first in range(0, len(theme), phrase):
        notes = [((bar + first + i) * 4 + beat, beats, key + shift) for i, row in enumerate(theme[first:first + phrase]) for beat, key, beats in row]
        for k, (at, beats, key) in enumerate(notes):
            mark = None if not slur or len(notes) < 2 else 'start' if k == 0 else 'stop' if k == len(notes) - 1 else None
            b(name, at, level).note(at, beats, key, slur=mark)


def swell_sea(b, bar, bars, level):
    """The sea: cellos and basses rocking between D and A in half notes, each pair of bars one swell and its fall."""
    for k in range(bars):
        at = (bar + k) * 4
        b('Contrabasses', at, level).note(at, 2, 38)
        b('Contrabasses').note(at + 2, 2, 45)
        b('Violoncellos', at, level).note(at, 2, (50, 57))
        b('Violoncellos').note(at + 2, 2, (45, 52))
        if k % 2 == 0:
            for name in ('Contrabasses', 'Violoncellos'):
                b.swell(name, at, at + 4, 'crescendo')
                b.swell(name, at + 4, at + 8, 'diminuendo')


def ripples(b, bar, names, level, high=False):
    """The harp's water: each bar's chord spread up and back in eighth notes."""
    for i, name in enumerate(names):
        cb, vc, vla, v2 = CHORD[name]
        tones = (vc, vla[0], vla[1], v2[0], v2[1], v2[0], vla[1], vla[0])
        at = (bar + i) * 4
        for k, key in enumerate(tones):
            b('Harp', at, level).note(at + k * .5, .5, key + (12 if high else 0))


def shimmer(b, bar, names, level):
    """The past, read: the vibraphone turning over each chord's top notes in sixteenths, an octave up."""
    for i, name in enumerate(names):
        v2 = CHORD[name][3]
        vla = CHORD[name][2]
        cell = (v2[1] + 12, v2[0] + 12, vla[1] + 12, v2[0] + 12)
        at = (bar + i) * 4
        for k in range(16):
            b('Vibraphone', at, level).note(at + k * .25, .25, cell[k % 4])


def toll(b, bar, beat, level, key=50):
    """One stroke of the Clocktower's bell (D, low), let ring."""
    at = bar * 4 + beat
    b('Tubular Bells', at, level).note(at, 4, (key, key + 12))


def halcyon_score():
    """Halcyon: the Drowned Harbour (56 bars at 60 bpm, 3 min 44 s, loops).
    1  bars 0-7    The sea and the bell: the low strings rock between D and A in slow swells, the harp ripples, the
                   violas hold a high open fifth; the Clocktower strikes seven, one stroke a bar, the last left hanging.
    2  bars 8-19   The Litany, the town's hymn: its three lines on solo oboe, then clarinet and English horn, then
                   the horn, over the strings as a choir; the last line hangs on B over G.
    3  bars 20-27  The morning before the wave, as Trace Reading shows it: D major, the flute and glockenspiel on a
                   light tune, the vibraphone's shimmer and high tremolo violins, women's voices holding the chord.
    4  bars 28-35  The wave: the harmony pulled flat, the sea swell growing under tremolo strings, the trombones on
                   the Litany's first line, timpani and a cymbal swell into the one leading tone, on A.
    5  bars 36-47  The Litany in full: violins and horns in octaves, trumpet on the last line, forte, brass and
                   timpani as weight; it falls back and hangs on B over G again, quieter.
    6  bars 48-55  The sea lies down: the swell again, very soft, the bell once, the women's voices on the open fifth,
                   the oboe remembering the hymn's last line; into bar 0."""
    score = muse.Score(tempo=TEMPO, title='Physis - Halcyon')
    b = Band(score)
    # 1. The sea and the bell (bars 0-7).
    swell_sea(b, 0, 8, 1)
    b('Violas', 0, 0).note(0, 32, (62, 69), tremolo=3)
    b('Violins 2', 0, 0).note(16, 16, (74, 81))
    ripples(b, 1, ('D5',), 0)
    ripples(b, 3, ('Dm',), 0)
    ripples(b, 5, ('D5', 'Dm7'), 1)
    for k in range(7):
        toll(b, k, 0, 1 if k < 6 else 0)
    b('English Horn', 24, 1).note(24, 2, 69, slur='start')
    b('English Horn').note(26, 2, 74)
    b('English Horn').note(28, 4, 72, slur='stop')
    # 2. The Litany, plainly (bars 8-19).
    for i, name in enumerate(LITANY_CHORDS):
        bed(b, 8 + i, 1, name, 1 if i < 4 else 2)
    line(b, 'Oboe', 8, LITANY[0:4], 2)
    line(b, 'Clarinet in B♭', 12, LITANY[4:8], 2)
    line(b, 'English Horn', 12, LITANY[4:8], 1, shift=-12)
    line(b, 'Horn in F', 16, LITANY[8:12], 2)
    b('Flute', 76, 1).note(76, 4, 79)    # a single high answer over the hanging B
    ripples(b, 8, LITANY_CHORDS[:4], 0)
    ripples(b, 16, LITANY_CHORDS[8:12], 1)
    toll(b, 11, 0, 0)
    # 3. The morning before the wave (bars 20-27).
    for rep in range(2):
        for i, name in enumerate(MORNING_CHORDS):
            bar = 20 + rep * 4 + i
            bed(b, bar, 1, name, 1, tremolo=rep == 1)
            b('Violins 1', bar * 4, 0).note(bar * 4, 4, CHORD[name][3][1] + 12, tremolo=3)
            b('Women', bar * 4, 1).note(bar * 4, 4, CHORD[name][2][1] + 12)
        line(b, 'Flute', 20 + rep * 4, MORNING, 2 + rep)
        shimmer(b, 20 + rep * 4, MORNING_CHORDS, 1)
    line(b, 'Glockenspiel', 24, MORNING, 1)
    ripples(b, 20, MORNING_CHORDS, 1, high=True)
    b.swell('Violins 1', 104, 112, 'diminuendo')
    # 4. The wave (bars 28-35).
    for i, name in enumerate(WAVE_CHORDS):
        bed(b, 28 + i, 1, name, 2 if i < 4 else 3, tremolo=True, cellos=False, basses=False)
    swell_sea(b, 28, 8, 3)
    line(b, 'Trombone', 28, LITANY[0:4], 2, shift=-12)
    line(b, 'Horn in F', 32, LITANY[0:2], 3)
    for i, name in enumerate(WAVE_CHORDS[4:]):
        at = (32 + i) * 4
        b('Tuba', at, 2).note(at, 4, CHORD[name][0])
    b('Violins 1', 112, 2).note(112, 16, 74, tremolo=3)
    b('Violins 1').note(128, 8, 77, tremolo=3)
    b('Violins 1').note(136, 8, 76, tremolo=3)
    b.swell('Violins 1', 128, 144, 'crescendo')
    b('Timpani', 128, 1).note(128, 8, 45, tremolo=3)
    b('Timpani').note(136, 8, 45, tremolo=3)
    b.swell('Timpani', 128, 144, 'crescendo')
    b('Suspended Cymbal', 136, 0).note(136, 8, 60, tremolo=3)
    b.swell('Suspended Cymbal', 136, 144, 'crescendo')
    # 5. The Litany in full (bars 36-47).
    for i, name in enumerate(LITANY_CHORDS):
        bed(b, 36 + i, 1, name, 4 if i < 8 else 3)
        at = (36 + i) * 4
        b('Tuba', at, 3 if i < 8 else 2).note(at, 4, CHORD[name][0] if CHORD[name][0] >= 34 else CHORD[name][0] + 12)
        b('Trombone', at, 2).note(at, 4, CHORD[name][2])
    line(b, 'Violins 1', 36, LITANY, 4)
    line(b, 'Horn in F', 36, LITANY[:8], 3, shift=-12)
    line(b, 'Trumpet in B♭', 44, LITANY[8:], 2)
    line(b, 'Flute', 40, LITANY[4:8], 2, shift=12)
    line(b, 'Oboe', 40, LITANY[4:], 2)
    b.swell('Violins 1', 176, 192, 'diminuendo')
    ripples(b, 36, LITANY_CHORDS, 2)
    b('Timpani', 144, 3).note(144, 1, 38, artic='accent')
    b('Timpani').note(160, 1, 45, artic='accent')
    b('Timpani', 176, 2).note(176, 1, 43)
    b('Suspended Cymbal', 144, 1).note(144, 4, 60)
    toll(b, 44, 0, 2)
    # 6. The sea lies down (bars 48-55).
    swell_sea(b, 48, 8, 0)
    b('Violas', 192, 0).note(192, 32, (62, 69), tremolo=3)
    b('Women', 192, 0).note(192, 16, (62, 69))
    b('Women').note(208, 16, (62, 67))
    line(b, 'Oboe', 50, LITANY[8:12], 1)
    ripples(b, 49, ('Dm',), 0)
    ripples(b, 53, ('D5',), 0)
    toll(b, 52, 0, 0)
    b('Violins 2', 216, 0).note(216, 8, (69, 74))
    return score


def halcyon_music(excerpt=None, from_bar=0, profile='MuseSounds'):
    """Renders and finishes the score (as build_physis_arche_audio.arche_music does)."""
    import soundfile
    WORK.mkdir(parents=True, exist_ok=True)
    score = halcyon_score()
    assert score.bars() == BARS, score.bars()
    tag = 'Halcyon' if profile == 'MuseSounds' else 'Halcyon_basic'
    score.write(WORK / (tag + '.musicxml'))
    missing = muse.render(WORK / (tag + '.musicxml'), WORK / (tag + '_raw.wav'), profile=profile, keep_score=WORK / (tag + '.mscz'))
    print('Halcyon: %d bars at %d bpm, profile %s, parts: %s; without a sound of the profile: %s' % (
        score.bars(), score.tempo, profile, ', '.join(p.name for p in score.parts), missing), flush=True)
    audio, rate = soundfile.read(WORK / (tag + '_raw.wav'), dtype='float32')
    assert rate == RATE and audio.ndim == 2 and audio.shape[1] == 2, (rate, audio.shape)
    beat = 60 / TEMPO
    total = int((BARS * 4 * beat + 8.0) * RATE)
    mix = np.zeros((total, 2))
    mix[:min(total, len(audio))] = audio[:total]
    mix = hall(mix, 4.2, .6 * HALL, 61, 8000)
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
    write('S_Music_Halcyon_Excerpt' if excerpt else 'S_Music_Halcyon', mix, .9, MUSIC_LUFS)


# ---------------------------------------------------------------- ambience (loops)

rng = np.random.default_rng(61)


def wave(seconds=6.5):
    """One wave on the shingle, far off: the swell gathering (low and rising), the break (a broad burst), the
    wash running up the stones (hiss), and the drag back down (the shingle rattling, thinning as it goes)."""
    t = t_(seconds)
    n = len(t)
    swell = band(rng.normal(size=n), 50, 420) * np.clip(t / 2.2, 0, 1) ** 2 * np.exp(-np.clip(t - 2.2, 0, None) / .9)
    brk = band(rng.normal(size=n), 180, 3200) * np.exp(-np.clip(t - 2.1, 0, None) / .55) * (t > 2.1) * np.clip((t - 2.1) / .08, 0, 1)
    wash = band(rng.normal(size=n), 900, 6500) * np.clip((t - 2.2) / .5, 0, 1) * np.exp(-np.clip(t - 2.7, 0, None) / 1.3)
    clicks = (rng.uniform(size=n) < np.clip(.012 * np.exp(-np.clip(t - 3.3, 0, None) / 1.1) * (t > 3.0), 0, 1)) * rng.uniform(.3, 1, n)
    rattle = band(clicks, 2200, 8000)
    out = swell * 1.0 + brk * .9 + wash * .45 + rattle * 1.6
    return out * np.clip((seconds - t) / 1.6, 0, 1) ** 1.5   # the drag dies away; a wave never stops short


def gull(seed):
    """A herring gull's call far off: two or three gliding cries (up a little, then a long fall), each a reedy
    tone with harmonics and a quick flutter, the last longest."""
    local = np.random.default_rng(seed)
    calls = local.integers(2, 4)
    out = np.zeros(int((calls * .42 + .6) * RATE))
    for k in range(calls):
        length = local.uniform(.22, .3) if k < calls - 1 else local.uniform(.45, .6)
        tt = t_(length)
        x = tt / length
        f = local.uniform(1500, 1900) * (1 + .18 * np.sin(np.pi * np.clip(x / .3, 0, 1)) * (x < .3) - .35 * np.clip((x - .25) / .75, 0, 1))
        f = f * (1 + .012 * np.sin(2 * np.pi * 34 * tt))
        phase = np.cumsum(f) / RATE * 2 * np.pi
        tone = sum(a * np.sin(h * phase) for h, a in ((1, 1), (2, .55), (3, .35), (4, .18), (5, .08)))
        tone *= np.clip(x / .08, 0, 1) * np.clip((1 - x) / .25, 0, 1)
        at = int(k * .42 * RATE)
        out[at:at + len(tone)] += tone
    return band(out, 700, 6000)


def buoy(seed):
    """A bell buoy rocking out in the harbour mouth: two or three uneven strokes of a heavy bell."""
    local = np.random.default_rng(seed)
    f = 392.0 * local.uniform(.98, 1.02)
    out = np.zeros(int(9 * RATE))
    at = 0.0
    for k in range(local.integers(2, 4)):
        tt = t_(6.0)
        stroke = sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt * (1.1 + 1.6 * i)) for i, (r, a) in enumerate(TUBE))
        stroke *= np.clip(tt / .002, 0, 1) * local.uniform(.5, 1)
        i0 = int(at * RATE)
        out[i0:i0 + len(stroke)] += stroke[:len(out) - i0]
        at += local.uniform(1.1, 2.0)
    return out


def amb_halcyon(seconds=60):
    """The harbour everywhere: waves breaking on the shingle far off, one every seven to ten seconds from one
    side or the other; a cold wind off the sea that gusts slowly; gulls, far and few; the bell buoy in the
    harbour mouth twice a loop. Grey, wide and empty: a town nobody walks in."""
    n = int(seconds * RATE)
    surf = np.zeros((n, 2))
    at = rng.uniform(0, 2)
    while at < seconds:
        put(surf, wave(rng.uniform(8.5, 9.5)), at, rng.uniform(.55, 1.0), rng.uniform(-.75, .75))
        at += rng.uniform(6.8, 9.8)
    surf = ring(band(surf, 40, 7000), 2.8, .45, 701, 4500)   # far off: the cliffs and the houses give it back
    gust = (.5 + .5 * drift(n, 7, 702)) ** 1.5
    wind = noise_bed(n, 70, 320, 703) * (.55 + .45 * gust)[:, None] + noise_bed(n, 600, 2600, 704) * (.15 + .85 * gust)[:, None] * .5
    hiss = noise_bed(n, 3500, 9000, 705) * (.1 + .9 * gust ** 2)[:, None]
    gulls = np.zeros((n, 2))
    for k, when in enumerate((7.0, 19.0, 33.0, 46.0, 54.0)):
        put(gulls, gull(710 + k), when + rng.uniform(-2, 2), rng.uniform(.4, 1.0), rng.uniform(-.9, .9))
    gulls = ring(gulls, 2.2, .7, 718, 5000)
    bells = np.zeros((n, 2))
    for k, when in enumerate((11.0, 41.0)):
        put(bells, buoy(720 + k), when, 1.0, .35 if k == 0 else .2)
    bells = ring(band(bells, 150, 3000), 3.0, .8, 724, 3000)
    mix = blend((surf, -24), (wind, -31), (hiss, -38), (gulls, -36), (bells, -37))
    write('S_Amb_Halcyon', mix, .7, -23)


def amb_heldsea(seconds=40):
    """The Held Sea, near: a wall of water forced to stand. A deep churning roar that never breaks (the weight
    of it, low and turbulent), a rushing hiss of water climbing its own face, spray crashing off the crest now
    and then, and under it all the Undertow's pumps: a low throb that pulls every few seconds, its tone forced
    and slightly sour, two pitches that will not agree. It stops when the Keel falls (tag HalcyonScar)."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    churn = noise_bed(n, 25, 180, 731) * (.7 + .3 * np.stack([wobble(n, .2, 1.2, 732 + ch) for ch in range(2)], 1))
    rush = noise_bed(n, 300, 3800, 734) * (.75 + .25 * np.stack([wobble(n, 2, 9, 735 + ch) for ch in range(2)], 1))
    spray = np.zeros((n, 2))
    at = rng.uniform(0, 2)
    while at < seconds:
        tt = t_(rng.uniform(1.2, 2.0))
        burst = band(rng.normal(size=len(tt)), 1200, 9000) * np.clip(tt / .15, 0, 1) * np.exp(-tt / .45) * np.clip((tt[-1] - tt) / .6, 0, 1)
        put(spray, burst, at, rng.uniform(.4, 1), rng.uniform(-.9, .9))
        at += rng.uniform(2.5, 6.0)
    beats = 10   # the pumps pull ten times a loop (every four seconds)
    pull = (.5 - .5 * np.cos(2 * np.pi * beats * t / seconds)) ** 3
    pump = np.zeros((n, 2))
    for f, amp in ((whole(41.2, n), 1.0), (whole(82.4, n), .5), (whole(87.3, n), .28), (whole(123.5, n), .2)):
        for ch in range(2):
            pump[:, ch] += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.3))
    pump *= (.25 + .75 * pull)[:, None]
    strain = np.zeros((n, 2))
    for k in range(2):
        put(strain, groan(rng.uniform(55, 75), rng.uniform(4.0, 5.5), 740 + k), (k + .4) * seconds / 2, 1.0, rng.uniform(-.5, .5))
    mix = blend((churn, -24), (rush, -28), (ring(spray, 1.6, .3, 745, 7000), -31), (pump, -29), (band(strain, 30, 500), -35))
    write('S_Amb_HeldSea', ring(mix, 1.8, .25, 749, 6000), .75, -21)


def amb_quarter(seconds=40):
    """The Drowned Quarter: shallow water among the houses. It slaps and sucks at walls and doorways in small
    uneven waves, gurgles in through windows and drains out of them, a loose shutter knocks now and then, and
    the open sea's surf sounds far off past the roofs."""
    n = int(seconds * RATE)
    laps = np.zeros((n, 2))
    at = rng.uniform(0, 1)
    while at < seconds:
        tt = t_(rng.uniform(.5, 1.1))
        slap = band(rng.normal(size=len(tt)), 160, rng.uniform(1200, 2400)) * np.clip(tt / .04, 0, 1) * np.exp(-tt / rng.uniform(.12, .25)) * np.clip((tt[-1] - tt) / .2, 0, 1)
        pan = rng.uniform(-.85, .85)
        put(laps, slap, at, rng.uniform(.3, 1), pan)
        for _ in range(rng.integers(1, 5)):
            put(laps, bubble(rng.uniform(300, 1200), rng.uniform(.02, .06)), at + rng.uniform(.1, .7), rng.uniform(.05, .12), pan + rng.uniform(-.2, .2))
        at += rng.uniform(.6, 2.2)
    laps = ring(laps, 1.2, .35, 751, 6000)
    gurgle = noise_bed(n, 200, 900, 752) * np.clip(np.stack([wobble(n, 1, 5, 753 + ch) for ch in range(2)], 1), 0, 1) ** 2
    knocks = np.zeros((n, 2))
    for k, when in enumerate((9.0, 9.7, 27.0)):
        tt = t_(.25)
        knock = band(rng.normal(size=len(tt)), 150, 1400) * np.exp(-tt / .025) + np.sin(2 * np.pi * 210 * tt) * np.exp(-tt / .06)
        put(knocks, knock, when, rng.uniform(.5, 1), -.4)
    knocks = ring(knocks, 1.4, .5, 757, 3000)
    far = np.zeros((n, 2))
    at = rng.uniform(0, 3)
    while at < seconds:
        put(far, wave(rng.uniform(8.5, 9.5)), at, rng.uniform(.5, 1), rng.uniform(-.4, .4))
        at += rng.uniform(7.5, 10.0)
    far = ring(band(far, 40, 2500), 2.5, .6, 759, 2500)
    mix = blend((laps, -25), (gurgle, -34), (knocks, -33), (far, -31))
    write('S_Amb_Quarter', mix, .7, -23)


SOUNDS = {'S_Amb_Halcyon': amb_halcyon, 'S_Amb_HeldSea': amb_heldsea, 'S_Amb_Quarter': amb_quarter}
PARTS = {'amb': list(SOUNDS)}


if __name__ == '__main__':
    args, options = sys.argv[1:], {}
    for flag in ('--out', '--excerpt', '--from-bar'):
        if flag in args:
            at = args.index(flag)
            options[flag] = args[at + 1]
            del args[at:at + 2]
    profile = 'MuseSounds'
    if '--soundfont-profile' in args:
        args.remove('--soundfont-profile')
        profile = 'MuseScore Basic'
        if '--out' not in options:
            sys.exit('--soundfont-profile is a comparison render: give --out DIR (not the import folder)')
    if '--excerpt' in options and '--out' not in options:
        sys.exit('--excerpt writes a test file: give --out DIR (not the import folder)')
    OUT = pathlib.Path(options.get('--out', OUT))
    OUT.mkdir(parents=True, exist_ok=True)
    conclave.OUT = OUT   # write() is the Conclave's and looks its folder up there
    names = [name for part in (args or ['music', 'amb']) for name in (['S_Music_Halcyon'] if part == 'music' else PARTS.get(part, [part]))]
    for name in names:
        conclave.reseed(name)
        rng = np.random.default_rng(conclave.zlib.crc32(name.encode()) + 7)
        if name == 'S_Music_Halcyon':
            halcyon_music(float(options['--excerpt']) if '--excerpt' in options else None, int(options.get('--from-bar', 0)), profile)
        elif name in SOUNDS:
            SOUNDS[name]()
        else:
            sys.exit('unknown part %s; parts: music, amb, %s' % (name, ', '.join(SOUNDS)))
