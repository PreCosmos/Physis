"""Music, sound effects and ambience for the Wounded Grove (level 4).

Run with the Kokoro venv's packages from the project folder (numpy only: nothing here speaks):
  cd ~/PhysisProject && PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages \
  python3 Tools/build_physis_grove_audio.py [parts]
Parts: music, sfx, amb (all three when none is given) or single sounds by name (S_LinkPull ...).
--out DIR writes elsewhere; --excerpt SECONDS [--from-bar N] renders only that much of the music, as
S_Music_Grove_Excerpt, for listening tests (it needs --out, so the import folder stays clean).
Music renders through Art/Audio/SoundFont/MuseScore_General.sf3 with the Center's orchestra
(Tools/build_physis_center_audio.py: Orchestra, perform, the score helpers) and the Conclave's finishing
(Tools/build_physis_conclave_audio.py: its fixed hall(), write() with its loudness hold, the loop helpers
put/ring/fold/drift/whole/noise_bed/blend and the sound sources sweep/chime/glow/bubble/mallet/groan), and is
held to the same loudness as the other levels' music.
Writes Art/Audio/Grove/*.wav, 44.1 kHz stereo 16-bit, which physis_grove_tools.import_audio imports. The
music and the S_Amb_* beds loop without a seam; the effects ring out and end in silence. Each sound draws
from its own seed, so building one alone gives the same file as building all.
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_physis_conclave_audio as conclave  # noqa: E402
import physis_soundfont as sf  # noqa: E402
from build_physis_center_audio import (O_CB, O_CLAR, O_FLUTE, O_HARP, O_HORN, O_OBOE, O_STR, O_TIMP, O_TREM, O_VC,  # noqa: E402
                                       O_VLN, Orchestra, band, env, harp_rolls, melody, ostinato, perform, place,
                                       strings_bed, t_, voicing)
from build_physis_conclave_audio import (GLASS, MUSIC_LUFS, TUBE, blend, bubble, chime, drift, fold, glow, groan, hall,  # noqa: E402
                                         mallet, noise_bed, put, ride, ring, sweep, trim, whole, wobble, write)

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'Art/Audio/Grove'
SOUNDFONT = ROOT / 'Art/Audio/SoundFont/MuseScore_General.sf3'
RATE = 44100
rng = np.random.default_rng(29)


def reseed(name):
    """The Conclave's reseed (its own generator and the Center's, which bell() draws from) and this
    module's generator from the same name, so a sound is the same built alone or after others."""
    global rng
    conclave.reseed(name)
    rng = np.random.default_rng(conclave.zlib.crc32(name.encode()) + 2)


def finish(name, track, low, high, seconds, wet, seed, bright, peak, cap=None):
    """The Conclave's finish() (band-limited with silence either side, room for the hall to ring out,
    trimmed once it has died away) with a `cap`: the link's sounds are short cues, so what still rings
    after `cap` seconds (the hall's last -40 dB) is faded out over 120 ms instead of kept."""
    lead = int(.05 * RATE)
    padded = np.concatenate((np.zeros((lead, 2)), track, np.zeros((int((seconds + .5) * RATE), 2))))
    out = trim(hall(band(padded, low, high)[lead:], seconds, wet, seed, bright))
    if cap and len(out) > cap * RATE:
        out = out[:int(cap * RATE)].copy()
        fade = int(.12 * RATE)
        out[-fade:] *= (np.linspace(1, 0, fade) ** 2)[:, None]
    write(name, out, peak)


def sway(mono, pan):
    """A mono sound whose place between the ears follows `pan` (-1..1 per sample)."""
    return np.stack((mono * np.sqrt((1 - pan) / 2), mono * np.sqrt((1 + pan) / 2)), 1) * 1.414


# ---------------------------------------------------------------- effects

BAR = ((1, 1), (2.76, .4), (5.4, .15))   # a small metal bar: bell()'s modes without those over 20 kHz


def link_pull():
    """Resonance Link drawing her to an anchor: a wooden knock as the link catches, a thrumming string
    whose pitch climbs an octave and a half as it draws tight, air rushing up and across with her, and
    two quick glass notes where she lands. Green-gold: wood and glass, no metal."""
    seconds = .56
    t = t_(seconds)
    rise = np.clip(t / .38, 0, 1)
    phase = np.cumsum(146.8 * 2 ** (1.585 * rise ** 1.4)) / RATE * 2 * np.pi
    thrum = sum(np.sin(k * phase + rng.uniform(0, 6.3)) / k ** 1.2 for k in range(1, 9))
    thrum *= (.6 + .4 * np.sin(2 * np.pi * 28 * t)) * np.clip(t / .012, 0, 1) * np.exp(-np.clip(t - .36, 0, None) / .045)
    air = sweep(500 * 9 ** rise, 1.2, 5) * rise ** 1.5 * np.exp(-np.clip(t - .38, 0, None) / .05)
    track = sway(air, np.clip(t / .4, 0, 1) * 1.2 - .6) * .8
    place(track, thrum, 0, .3)
    place(track, mallet(293.7, .45), 0, .55, -.2)
    place(track, chime(1174.7, 22, GLASS), .35, .22, .2)
    place(track, chime(1760, 26, GLASS), .375, .14, .45)
    finish('S_LinkPull', track, 60, 9500, .3, .2, 71, 7000, .85, cap=.62)


def link_take():
    """Taking up a flow from a source: a soft swell of held tones and air as it gathers into her hand,
    and a low chime (a tube at G below middle C) as it comes away."""
    seconds = .8
    t = t_(seconds)
    air = sweep(700 * 3 ** np.clip(t / .45, 0, 1), 1.3, 7) * env(len(t), .3, .4, 1.4)
    track = np.stack((air, np.roll(air, 300)), 1) * .3
    for k, f in enumerate((196, 293.7, 392)):
        place(track, glow(f, .72, .26, .38, 300 + k), 0, .12, (k - 1) / 2)
    place(track, chime(196, 11, TUBE), .25, .5, -.1)
    place(track, chime(392, 13, GLASS), .26, .16, .25)
    finish('S_LinkTake', track, 50, 8000, .4, .28, 72, 6000, .8, cap=.82)


def link_feed():
    """A flow delivered to a relay or a socket: two notes, the fifth and then the keynote above it (D to
    G), glass over soft wood, and a warm G chord held under them as the flow settles in. Solved, quietly."""
    track = np.zeros((int(1.65 * RATE), 2))
    for k, (f, at) in enumerate(((587.3, 0), (784, .17))):
        place(track, chime(f, 4.2 - .4 * k, GLASS), at, .5, -.25 + .5 * k)
        place(track, mallet(f / 2, 1.1), at, .32, -.15 + .3 * k)
    for k, f in enumerate((196, 293.7, 493.9)):
        place(track, glow(f, 1.4, .18, 1.1, 310 + k), .17, .07, (k - 1) / 2)
    finish('S_LinkFeed', track, 60, 9000, .8, .35, 73, 6500, .85, cap=1.65)


def string_snap(freq, seconds):
    """A taut string let go: it starts sharp and falls to its pitch in a few milliseconds, its stiff upper
    harmonics die first, and the snap itself is a tick of bright noise."""
    t = t_(seconds)
    phase = np.cumsum(freq * (1 + .35 * np.exp(-t / .012))) / RATE * 2 * np.pi
    out = sum(np.sin(k * phase * np.sqrt(1 + .0006 * k * k) + rng.uniform(0, 6.3)) / k * np.exp(-t * (7 + 2.2 * k)) for k in range(1, 15))
    out += band(rng.normal(size=len(t)), 1500, 8000) * np.exp(-t / .004) * .8
    return out * np.clip(t / .0005, 0, 1) * np.clip((seconds - t) / .03, 0, 1)


def link_tether():
    """Two enemies tied together: two strings pulled taut and snapping a fifth apart, one each side,
    and the tie's metal shimmer ringing between them."""
    seconds = .62
    t = t_(seconds)
    track = np.zeros((len(t), 2))
    place(track, string_snap(329.6, .55), 0, .7, -.55)
    place(track, string_snap(493.9, .5), .025, .6, .55)
    place(track, chime(2637, 11, BAR), .03, .1, -.2)
    place(track, chime(3520, 13, BAR), .05, .08, .25)
    shimmer = band(rng.normal(size=len(t)), 5000, 9500) * np.exp(-t / .12) * np.clip(t / .01, 0, 1)
    place(track, np.stack((shimmer, np.roll(shimmer, 200)), 1), .02, .07)
    finish('S_LinkTether', track, 70, 10000, .35, .22, 74, 8000, .85, cap=.72)


def current_travel():
    """Stepping into a Divinity current in the Grove: air rising and turning around her, a warm G chord
    swelling under it, and a shimmer of small glass notes that thickens and climbs until it closes over
    her. Warmer than the Conclave's: no plunge, lower air, the chord carries it."""
    seconds = 2.4
    t = t_(seconds)
    build = np.clip(t / 1.6, 0, 1)
    rush = sweep(220 * 10 ** build ** 1.2, 1.4, 6) * build ** 1.6 * np.exp(-np.clip(t - 1.65, 0, None) / .22)
    track = sway(rush, np.sin(np.cumsum(2 * np.pi * (.5 + 1.3 * build)) / RATE) * .8)
    phase = np.cumsum(73.4 * 1.5 ** build) / RATE * 2 * np.pi
    place(track, (np.sin(phase) + .35 * np.sin(2 * phase)) * build ** 2 * np.exp(-np.clip(t - 1.65, 0, None) / .3), 0, .2)
    for k, f in enumerate((196, 293.7, 392, 493.9)):
        place(track, glow(f, 2.3, 1.35, .75, 320 + k), 0, .11, (k - 1.5) / 2.5)
    scale = (784, 880, 987.8, 1174.7, 1318.5, 1568, 1760, 1975.5, 2349.3)
    for at in np.sort(1.9 * np.sqrt(rng.uniform(.02, 1, 26))):
        step = int(np.clip(at / 1.9 * 7 + rng.uniform(-1.5, 1.5), 0, len(scale) - 1))
        place(track, chime(scale[step], 14, GLASS), at, .04 + .06 * at / 1.9, rng.uniform(-.7, .7))
    finish('S_CurrentTravel', track, 40, 9000, 1.0, .45, 75, 6500, .9, cap=2.55)


# ---------------------------------------------------------------- ambience (loops)

def bird(kind, seed):
    """One call of a small bird: a few short whistled notes, each gliding a little."""
    local = np.random.default_rng(seed)
    notes = []   # (start, seconds, from Hz, to Hz)
    if kind == 'tit':        # two pitches see-sawing
        high, low, at = local.uniform(3400, 4200), local.uniform(2700, 3200), 0
        for j in range(local.integers(4, 7)):
            notes.append((at, .09, (high, low)[j % 2], (high, low)[j % 2] * .97))
            at += .16
    elif kind == 'warble':   # a quick run of glides
        at = 0
        for j in range(local.integers(5, 9)):
            f = local.uniform(2400, 4800)
            notes.append((at, local.uniform(.05, .09), f, f * local.uniform(.8, 1.25)))
            at += local.uniform(.08, .13)
    elif kind == 'thrush':   # slow fluting notes
        at = 0
        for j in range(3):
            f = local.uniform(1700, 2600)
            notes.append((at, local.uniform(.16, .24), f, f * local.uniform(.92, 1.1)))
            at += local.uniform(.28, .4)
    else:                    # dove: three soft low coos
        f = local.uniform(430, 500)
        notes = [(0, .32, f, f * .96), (.5, .22, f * 1.04, f), (.8, .4, f, f * .93)]
    out = np.zeros(int((notes[-1][0] + notes[-1][1] + .05) * RATE))
    for at, seconds, f0, f1 in notes:
        t = t_(seconds)
        phase = np.cumsum(f0 + (f1 - f0) * t / seconds) / RATE * 2 * np.pi
        tone = (np.sin(phase) + .15 * np.sin(2 * phase)) * np.hanning(len(t)) ** .7
        out[int(at * RATE):int(at * RATE) + len(t)] += tone
    return out


def amb_forest(seconds=48):
    """The grove in late afternoon: wind moving through the canopy in slow gusts (a low breath of air,
    the body of the leaves, their bright rustle fluttering on top, a little different in each ear as the
    gust crosses), and a few birds far off, each calling once or twice a loop. No music."""
    n = int(seconds * RATE)
    shared = drift(n, 8, 201)
    gust = np.stack([(.5 + .5 * np.clip(.7 * shared + .5 * drift(n, 11, 202 + ch), -1, 1)) ** 1.6 for ch in range(2)], 1)
    flutter = np.stack([.65 + .35 * wobble(n, 3, 14, 204 + ch) for ch in range(2)], 1)
    air = noise_bed(n, 70, 420, 206) * (.35 + .65 * gust)
    body = noise_bed(n, 420, 2200, 207) * (.2 + .8 * gust)
    rustle = noise_bed(n, 2200, 9000, 208) * (.08 + .92 * gust ** 1.4) * flutter
    birds = np.zeros((n, 2))
    calls = (('thrush', 3.5, -.6), ('tit', 9.0, .5), ('dove', 15.5, -.2), ('warble', 22.0, .7), ('thrush', 27.5, -.55),
             ('tit', 33.0, -.8), ('warble', 39.5, .3), ('dove', 44.0, .6))
    for k, (kind, at, pan) in enumerate(calls):
        put(birds, bird(kind, 210 + k), at + rng.uniform(-1.2, 1.2), rng.uniform(.5, 1.0), pan)
    # Distance: the calls lose their edge and arrive mostly as the wood's own reverberation.
    birds = ring(band(birds, 350, 5200), 2.4, 1.5, 220, 4000)
    mix = blend((air, -29), (body, -27), (rustle, -25), (birds, -34))
    write('S_Amb_Forest', ring(mix, 1.2, .2, 221, 7000), .6, -21)


def amb_water(seconds=40):
    """The Drowned Campus's lake: small waves lapping a soft shore at uneven intervals (a wash that swells
    and drains, a few bubbles after it), a wide quiet bed of open water, and to one side the Weir far off:
    a steady rush of falling water with its low rumble under it."""
    n = int(seconds * RATE)
    bed = noise_bed(n, 90, 900, 231) * (.75 + .25 * drift(n, 6, 232))[:, None]
    rush = noise_bed(n, 260, 2400, 233) * (.85 + .15 * drift(n, 9, 234))[:, None] * (.9 + .1 * wobble(n, 1, 6, 235))[:, None]
    weir = (rush + noise_bed(n, 35, 160, 236) * 1.6) * np.array([1.0, .55])
    laps = np.zeros((n, 2))
    at = 0.0
    while at < seconds - .4:
        near = rng.uniform() < .55
        lt = t_(rng.uniform(.7, 1.3))
        wash = band(rng.normal(size=len(lt)), 160, 2400 if near else 1300) * np.clip(lt / .14, 0, 1) ** 1.5 * np.exp(-lt / rng.uniform(.18, .32))
        wash += band(rng.normal(size=len(lt)), 500, 3200) * np.clip(lt / .006, 0, 1) * np.exp(-lt / .025) * .12
        pan = rng.uniform(-.3, .85)
        put(laps, wash, at, 1.0 if near else .45, pan)
        for _ in range(rng.integers(2, 7)):
            put(laps, bubble(rng.uniform(450, 1900), rng.uniform(.012, .035)), at + rng.uniform(.08, .6), rng.uniform(.03, .09), pan + rng.uniform(-.15, .15))
        at += rng.uniform(1.5, 3.6) if rng.uniform() > .2 else rng.uniform(.45, .7)
    laps = np.tanh(2 * laps / np.abs(laps).max())   # a soft knee, as on the Conclave's laps
    write('S_Amb_Water', ring(blend((bed, -30), (weir, -26), (laps, -23)), 1.4, .22, 237, 6000), .7, -21)


def amb_array(seconds=40):
    """The Deeproot Array forcing the roots: a low hum on A with a neighbour a semitone above and a
    tritone inside it (it beats and never settles), swelling in eight slow pulses a loop; each pulse
    lands with a sub thump and a rasp of current, a thin whine hangs over it, and now and then a root
    groans under the strain."""
    n = int(seconds * RATE)
    x = np.arange(n) / n
    t = np.arange(n) / RATE
    pulses = 8
    pulse = (.5 + .5 * np.sin(2 * np.pi * (pulses * x - .25))) ** 3
    hum = np.zeros(n)
    for k in range(1, 9):
        for detune in (0, .13 * k):
            hum += np.sin(2 * np.pi * whole(55 * k + detune, n) * t + rng.uniform(0, 6.3)) / k ** 1.3
    hum += .45 * np.sin(2 * np.pi * whole(58.27, n) * t) + .3 * np.sin(2 * np.pi * whole(77.78, n) * t) + .15 * np.sin(2 * np.pi * whole(155.6, n) * t)
    track = np.stack((hum, np.roll(hum, 1300)), 1) * ((.5 + .5 * pulse) * .09)[:, None]
    track += noise_bed(n, 25, 260, 241) * (.6 + .4 * pulse)[:, None] * .45
    rasp = band(sum(np.sin(2 * np.pi * whole(110 * k, n) * t + rng.uniform(0, 6.3)) / k for k in range(1, 30)), 700, 2600)
    rasp *= (.15 + .85 * pulse ** 2) * (.8 + .2 * wobble(n, 20, 60, 242)) * .012
    track += np.stack((rasp, np.roll(rasp, 500)), 1)
    whine = sum(np.sin(2 * np.pi * whole(f, n) * t + rng.uniform(0, 6.3)) for f in (1975.5, 1981, 2794)) * (.55 + .45 * drift(n, 5, 243)) * .0035
    track += np.stack((whine, np.roll(whine, 700)), 1)
    tt = t_(1.6)
    thump = np.sin(2 * np.pi * 38 * tt) * np.clip(tt / .09, 0, 1) * np.exp(-tt / .4)
    for k in range(pulses):
        put(track, thump, (k + .42) * seconds / pulses, .13, 0)
    for k in range(3):
        put(track, groan(rng.uniform(60, 105), rng.uniform(3.5, 5.5), 245 + k), (k + rng.uniform(.15, .8)) * seconds / 3, .045, rng.uniform(-.7, .7))
    write('S_Amb_Array', ring(track, 3.5, .6, 249, 2500), .6, -22)


# ---------------------------------------------------------------- music (SoundFont)

# E minor with the grove's old sadness (theme A, falling from B), which turns to G major when the hope
# arrives (theme B, rising from D). Themes give each bar's notes as (beat, key, beats); chords are
# (root, intervals) with the root where strings_bed's cellos play it (below 50 as written, else an octave
# down). Theme A ends on a suspended B that can fall back to E minor or open, deceptively, into G.
THEME_A = (((0, 71, 3), (3, 69, 1)), ((0, 67, 2), (2, 64, 2)),
           ((0, 69, 1.5), (1.5, 71, .5), (2, 72, 2)), ((0, 71, 3), (3, 66, 1)),
           ((0, 67, 1), (1, 71, 1), (2, 76, 2)), ((0, 74, 1.5), (1.5, 72, .5), (2, 71, 2)),
           ((0, 69, 2), (2, 66, 1), (3, 69, 1)), ((0, 66, 4),))
CHORDS_A = ((52, (0, 3, 7, 14)), (48, (0, 4, 7, 11)), (45, (0, 3, 7, 10)), (47, (0, 3, 7, 10)),
            (52, (0, 3, 7)), (48, (0, 4, 7, 11)), (50, (0, 4, 7, 14)), (47, (0, 5, 7, 10)))
THEME_B = (((0, 62, 1), (1, 67, 1), (2, 71, 2)), ((0, 74, 3), (3, 71, 1)),
           ((0, 72, 1.5), (1.5, 71, .5), (2, 67, 2)), ((0, 69, 3), (3, 71, 1)),
           ((0, 74, 1), (1, 76, 1), (2, 79, 2)), ((0, 78, 1.5), (1.5, 76, .5), (2, 74, 1), (3, 71, 1)),
           ((0, 72, 2), (2, 74, 1), (3, 69, 1)), ((0, 71, 4),))
CHORDS_B = ((43, (0, 4, 7)), (47, (0, 3, 7, 10)), (48, (0, 4, 7, 14)), (50, (0, 4, 7)),
            (52, (0, 3, 7, 10)), (48, (0, 4, 7, 11)), (45, (0, 3, 7, 10)), (43, (0, 4, 7, 14)))
# The valley before she moves: E minor with its ninth, C major leaning on its seventh; the bar before
# the theme hangs on the suspended B.
INTRO = ((52, (0, 3, 7, 14)), (48, (0, 4, 7, 11)), (52, (0, 3, 7, 14)), (48, (0, 4, 7, 11)),
         (45, (0, 3, 7, 10)), (43, (0, 4, 7, 9)), (48, (0, 4, 7, 11)), (47, (0, 5, 7, 10)))
CODA_DUSK = ((52, (0, 3, 7, 10)), (48, (0, 4, 7, 11)), (52, (0, 3, 7, 10)), (48, (0, 4, 7, 11)))
CODA_TURN = ((45, (0, 3, 7, 10)), (50, (0, 4, 7, 14)), (48, (0, 4, 7, 11)), (47, (0, 5, 7, 10)))
TEMPO, BARS = 63, 56


def inner(o, bar, chords, program, loud, low=55, high=67, near=60):
    """One held chord tone a bar in the middle of the texture (horn or clarinet), breathing with it."""
    for i, (root, chord) in enumerate(chords):
        o.note(program, voicing(root, chord, low, high, near)[1], (bar + i) * 4, 4.05, loud, 'swell')


def grove_score():
    """The Wounded Grove (~3.6 min at 63 bpm, 56 bars, loops): the valley waiting, on low strings, a
    shiver of tremolo and harp, with the flute low down and a far horn; the grove's sad theme on clarinet;
    the cellos take it and the oboe answers; the hope arrives on the horn, in G; violins and oboe carry
    it, the fullest the piece gets; the sad theme again, lighter, shared by oboe and flute; and a dusk
    coda in which the flute remembers the hope before the harmony leans back to the beginning."""
    o = Orchestra(TEMPO)
    # 1. The valley waiting (bars 0-7).
    strings_bed(o, 0, INTRO, 38)
    harp_rolls(o, 0, INTRO, 40, every=1)
    for i, (root, chord) in enumerate(INTRO[:4]):
        for k in voicing(root, chord, 64, 79, 71)[:2]:
            o.note(O_TREM, k, i * 4, 4.05, 30, 'swell')
    melody(o, 2, (((0, 64, 1), (1, 66, 1), (2, 71, 2)), ((0, 67, 4),)), O_FLUTE, 56, lead=1.8)
    melody(o, 6, (((0, 59, 2), (2, 64, 2)), ((0, 66, 4),)), O_HORN, 52, lead=1.9)
    # 2. The grove's theme on clarinet over strings and harp (bars 8-15).
    strings_bed(o, 8, CHORDS_A, 48)
    harp_rolls(o, 8, CHORDS_A, 46)
    melody(o, 8, THEME_A, O_CLAR, 76, lead=2.2)
    # 3. The cellos take it an octave down; the oboe answers their long notes, a horn holds the middle (bars 16-23).
    strings_bed(o, 16, CHORDS_A, 54)
    harp_rolls(o, 16, CHORDS_A, 48)
    melody(o, 16, THEME_A, O_VC, 84, shift=-12, lead=2.5)
    melody(o, 16, ((), (), (), ((1, 74, 1), (2, 78, 2)), (), (), (), ((1, 76, 1), (2, 78, 2))), O_OBOE, 62, lead=1.7)
    inner(o, 16, CHORDS_A, O_HORN, 46)
    # 4. The hope arrives: the horn in G major, the flute answering low (bars 24-31).
    strings_bed(o, 24, CHORDS_B, 54)
    harp_rolls(o, 24, CHORDS_B, 50)
    melody(o, 24, THEME_B, O_HORN, 80, shift=-12, lead=2.6)
    melody(o, 24, ((), (), (), ((2, 74, 1), (3, 78, 1)), (), (), (), ((1, 74, 1), (2, 79, 2))), O_FLUTE, 62, lead=1.7)
    o.note(O_TIMP, 43, 24 * 4, 2, 40)
    # 5. Violins and oboe carry it; horns in the middle, a clarinet figure moving beneath, harp in
    #    quicker rolls: full and warm, never loud (bars 32-39).
    strings_bed(o, 32, CHORDS_B, 64, program=O_STR, top=84)
    harp_rolls(o, 32, CHORDS_B, 52, every=.25)
    ostinato(o, 32, CHORDS_B, O_CLAR, 44, low=60)
    melody(o, 32, THEME_B, O_VLN, 88, double=O_OBOE, double_shift=0, lead=2.1)
    melody(o, 36, THEME_B[4:], O_FLUTE, 66, shift=12, lead=1.2)
    inner(o, 32, CHORDS_B, O_HORN, 56)
    o.note(O_TIMP, 43, 32 * 4, 2, 46)
    o.note(O_TIMP, 40, 36 * 4, 2, 44)
    # 6. The sad theme again, lighter for what she has heard: oboe, then the flute (bars 40-47).
    strings_bed(o, 40, CHORDS_A, 46)
    harp_rolls(o, 40, CHORDS_A, 44, every=1)
    melody(o, 40, THEME_A[:4], O_OBOE, 68, lead=2.0)
    melody(o, 44, THEME_A[4:], O_FLUTE, 66, lead=2.0)
    inner(o, 40, CHORDS_A, O_CLAR, 44)
    # 7. Dusk (bars 48-55): tremolo while the flute, then the clarinet below it, remember the hope; then
    #    harp, oboe and a horn over the suspended B that falls into bar 0.
    for i, (root, chord) in enumerate(CODA_DUSK):
        at = (48 + i) * 4
        for k in voicing(root, chord, 57, 76, 64):
            o.note(O_TREM, k, at, 4.05, 42, 'swell')
        o.note(O_VC, root - 12, at, 4.05, 44, 'swell')
        o.note(O_CB, root - 24, at, 4.05, 40, 'swell')
    melody(o, 48, THEME_B[:2], O_FLUTE, 62, lead=2.0)
    melody(o, 50, THEME_B[:2], O_CLAR, 60, shift=-12, lead=2.0)
    strings_bed(o, 52, CODA_TURN, 42)
    harp_rolls(o, 52, CODA_TURN, 42)
    melody(o, 52, (((0, 72, 2), (2, 74, 1), (3, 69, 1)), ((0, 66, 4),)), O_OBOE, 58, lead=1.8)
    o.note(O_HORN, 60, 54 * 4, 4.05, 48, 'swell')
    o.note(O_HORN, 59, 55 * 4, 4.05, 46, 'swell')
    return o


def grove_music(excerpt=None, from_bar=0):
    """Renders the score and finishes it as the Conclave's music is finished: a hall, its last ringing
    seconds laid over its first so the loop has no seam, the Center's level ride taken round the loop, a
    soft knee, and the same loudness. `excerpt` seconds from `from_bar` make a test file."""
    font = sf.SoundFont(str(SOUNDFONT))
    o = grove_score()
    if excerpt:
        start = from_bar * 4 * o.beat
        o.events = [(e[0], e[1], e[2] - start) + e[3:] for e in o.events if start <= e[2] < start + excerpt]
    mix = perform(font, o)
    # A wide, soft room: music heard through trees, a little longer and darker than the Conclave's plaza.
    mix = hall(mix, 3.8, .55, 52, 7000)
    if excerpt:
        mix = mix[:int(excerpt * RATE)]
        mix[-int(1.5 * RATE):] *= np.linspace(1, 0, int(1.5 * RATE))[:, None]
        mix = ride(mix / np.abs(mix).max())
    else:
        mix = fold(mix, BARS * 4 * o.beat)
        pad = 12 * RATE
        mix = ride(np.concatenate((mix[-pad:], mix, mix[:pad])) / np.abs(mix).max())[pad:-pad]
    mix = mix / np.abs(mix).max()
    # A patient score has a higher crest than the Conclave's: with that piece's knee (1.6) it reached only
    # -11.2 LUFS under the 0.9 peak; at 2.0 it measures -9.9 (0.3 % of samples past the knee) and write()
    # draws it back to the common level.
    mix = np.tanh(mix * 2.0) / np.tanh(2.0)
    write('S_Music_Grove_Excerpt' if excerpt else 'S_Music_Grove', mix, .9, MUSIC_LUFS)


SOUNDS = {'S_Music_Grove': grove_music, 'S_LinkPull': link_pull, 'S_LinkTake': link_take, 'S_LinkFeed': link_feed,
          'S_LinkTether': link_tether, 'S_CurrentTravel': current_travel,
          'S_Amb_Forest': amb_forest, 'S_Amb_Water': amb_water, 'S_Amb_Array': amb_array}
PARTS = {'music': ['S_Music_Grove'], 'sfx': ['S_LinkPull', 'S_LinkTake', 'S_LinkFeed', 'S_LinkTether', 'S_CurrentTravel'],
         'amb': ['S_Amb_Forest', 'S_Amb_Water', 'S_Amb_Array']}


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
    conclave.OUT = OUT   # write() is the Conclave's and looks its folder up there
    names = [name for part in (args or ['music', 'sfx', 'amb']) for name in PARTS.get(part, [part])]
    unknown = [name for name in names if name not in SOUNDS]
    if unknown:
        sys.exit('unknown part %s; parts: %s' % (', '.join(unknown), ', '.join(list(PARTS) + list(SOUNDS))))
    for name in names:
        reseed(name)
        if name == 'S_Music_Grove' and '--excerpt' in options:
            grove_music(float(options['--excerpt']), int(options.get('--from-bar', 0)))
        else:
            SOUNDS[name]()
