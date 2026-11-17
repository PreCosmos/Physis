"""Music, sound effects and ambience for Arche, the City of the Descent (level 5).

Run with the Kokoro venv's packages from the project folder (numpy and soundfile: nothing here speaks):
  cd ~/PhysisProject && PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages \
  python3 Tools/build_physis_arche_audio.py [parts]
Parts: music, sfx, amb (all three when none is given) or single sounds by name (S_Weave ...).
--out DIR writes elsewhere; --excerpt SECONDS [--from-bar N] writes only that much of the music, as
S_Music_Arche_Excerpt, for listening tests (it needs --out, so the import folder stays clean).
The music is written as a score for Tools/music/muse.py and rendered by MuseScore 4 with Muse Sounds, without
its window (the score and the raw render stay in Saved/Music/Arche.*); it is then finished as the ported
tracks are (Tools/music/port_tracks.py): the Conclave's hall at 0.4 of a SoundFont track's amount, the loop
fold, the Center's level ride taken round the loop, a soft knee and the common loudness. --soundfont-profile
renders the same score with MuseScore's basic SoundFont instead (a fallback, and the comparison that shows
which parts got a Muse sound).
Effects and beds use the Conclave's and the Grove's helpers (build_physis_conclave_audio.py: write() with its
loudness hold, put/ring/fold/drift/whole/noise_bed/blend, sweep/chime/glow/bubble/groan;
build_physis_grove_audio.py: finish() with its cap, sway()).
Writes Art/Audio/Arche/*.wav, 44.1 kHz stereo 16-bit. The music and the S_Amb_* beds loop without a seam; the
effects ring out and end in silence. Each sound draws from its own seed, so building one alone gives the same
file as building all.
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'music')]
import build_physis_conclave_audio as conclave  # noqa: E402
import muse  # noqa: E402
from build_physis_center_audio import band, env, place, t_  # noqa: E402
from build_physis_conclave_audio import (GLASS, MUSIC_LUFS, TUBE, blend, bubble, chime, drift, fold, glow, groan, hall,  # noqa: E402
                                         noise_bed, put, ride, ring, sweep, whole, wobble, write)
from build_physis_grove_audio import finish, sway  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / 'Art/Audio/Arche'
WORK = ROOT / 'Saved/Music'
RATE = 44100
HALL = .4   # Tools/music/port_tracks.py: the sampled sections bring their own room
rng = np.random.default_rng(31)


def reseed(name):
    """The Conclave's reseed (its generator and the Center's, which bell() draws from) and this module's
    generator from the same name, so a sound is the same built alone or after others."""
    global rng
    conclave.reseed(name)
    rng = np.random.default_rng(conclave.zlib.crc32(name.encode()) + 3)


# ---------------------------------------------------------------- effects

def stone(f0, seconds=.16, hard=1.0):
    """One piece of stone striking another: a few inharmonic modes, heavily damped (stone does not ring),
    under a tick of contact noise. `hard` < 1 softens the tick (a piece seating, not struck)."""
    t = t_(seconds)
    out = np.zeros_like(t)
    for ratio in np.concatenate(([1.0], rng.uniform(1.4, 6.5, 5))):
        out += rng.uniform(.4, 1) / ratio ** .7 * np.sin(2 * np.pi * f0 * ratio * t + rng.uniform(0, 6.3)) * np.exp(-t * rng.uniform(35, 70) * ratio ** .4)
    out += band(rng.normal(size=len(t)), 900, 6500) * np.exp(-t / .0035) * .7 * hard
    return out * np.clip(t / .0006, 0, 1) * np.clip((seconds - t) / .02, 0, 1)


def grind(seconds, seed, low=140, high=1900):
    """Stone dragged over stone: a band of noise broken into grains by a fast uneven flutter."""
    n = int(seconds * RATE)
    grain = np.clip(.15 + wobble(n, 18, 90, seed), 0, None) ** 1.5
    return band(np.random.default_rng(seed + 1).normal(size=n), low, high) * grain


def gather(track, count, span, low, high, gain, wide=.95):
    """`count` stone pieces arriving over `span` seconds, thicker towards the end, from the sides to the
    middle, the later ones higher (smaller pieces close the last gaps)."""
    for at in np.sort(span * rng.uniform(.02, 1, count) ** .6):
        x = at / span
        place(track, stone(rng.uniform(low, high) * (1 + .8 * x), hard=rng.uniform(.5, 1)), at, gain * rng.uniform(.45, 1) * (.5 + .5 * x),
              float(np.clip(rng.uniform(-wide, wide) * (1 - .85 * x), -1, 1)))


def weave():
    """Reweave on one of the city's bones, for good: stone pieces drawn together out of the air (knocks
    thickening and closing in from both sides over a rising drag of stone and air), the low thud of the
    whole thing settling into place, and over it a warm chime, pearl gold: a tube at E flat with glass on
    the major chord above it, which is the key the music's second theme gathers in."""
    track = np.zeros((int(1.8 * RATE), 2))
    span = .98
    t = t_(span)
    x = t / span
    drag = grind(span, 501) * x ** 1.6 * np.clip((span - t) / .03, 0, 1)
    place(track, sway(drag, .7 * np.sin(2 * np.pi * 1.4 * t) * (1 - x)), 0, .5)
    air = sweep(260 * 9 ** x ** 1.2, 1.2, 502) * x ** 2 * np.clip((span - t) / .04, 0, 1)
    place(track, np.stack((air, np.roll(air, 260)), 1), 0, .45)
    gather(track, 26, span, 130, 420, .5)
    tt = t_(.75)
    thud = np.sin(2 * np.pi * np.cumsum(44 + 26 * np.exp(-tt / .05)) / RATE) * np.exp(-tt / .17) * np.clip(tt / .004, 0, 1)
    place(track, thud, span, 1.0)
    place(track, band(rng.normal(size=len(tt)), 50, 600) * np.exp(-tt / .06) * np.clip(tt / .003, 0, 1), span, .5)
    place(track, stone(82, .3), span, .8)
    place(track, chime(311.1, 4.6, TUBE), span + .03, .6, -.1)
    for k, (f, pan) in enumerate(((622.3, .15), (784, -.3), (932.3, .35), (1244.5, 0))):
        place(track, chime(f, 5.2 + .6 * k, GLASS), span + .04 + .035 * k, .36 - .04 * k, pan)
    for k, f in enumerate((155.6, 311.1, 466.2)):
        place(track, glow(f, .78, .05, .6, 510 + k), span + .02, .07, (k - 1) / 2)
    finish('S_Weave', track, 35, 10000, .7, .28, 81, 7000, .9, cap=1.85)


def weave_restless():
    """Reweave on restless stone: fewer, lighter pieces gather, and a thin glass fifth (E flat and B flat,
    no third, no tube) answers where the thud and the chord would be. It holds, for now."""
    track = np.zeros((int(1.0 * RATE), 2))
    span = .6
    t = t_(span)
    x = t / span
    drag = grind(span, 521, 300, 2600) * x ** 1.6 * np.clip((span - t) / .03, 0, 1)
    place(track, sway(drag, .6 * np.sin(2 * np.pi * 2 * t) * (1 - x)), 0, .3)
    air = sweep(400 * 7 ** x ** 1.2, 1.1, 522) * x ** 2 * np.clip((span - t) / .04, 0, 1)
    place(track, np.stack((air, np.roll(air, 260)), 1), 0, .35)
    gather(track, 13, span, 260, 620, .4, wide=.8)
    place(track, chime(1244.5, 9.5, GLASS), span + .01, .5, -.15)
    place(track, chime(1864.7, 11, GLASS), span + .04, .3, .25)
    finish('S_WeaveRestless', track, 90, 11000, .4, .2, 82, 8000, .75, cap=1.05)


def unweave():
    """A woven thing letting go: a glassy shimmer falling down a cold scale (C minor with its flat second)
    as the weave's light goes out, and the stone sliding apart, its pieces knocking fewer and further to the
    sides. No thud: nothing lands."""
    track = np.zeros((int(1.2 * RATE), 2))
    span = .85
    t = t_(span)
    x = t / span
    scale = (2793.8, 2489, 2217.5, 2093, 1864.7, 1661.2, 1568, 1396.9, 1244.5, 1108.7, 1046.5, 932.3, 830.6, 784, 698.5, 622.3)
    for k, f in enumerate(scale):
        at = .55 * (k / (len(scale) - 1)) ** .85
        place(track, chime(f, 15 - .4 * k, GLASS), at, .16 * (1 - .035 * k), float(np.clip((k % 2 * 2 - 1) * (.15 + .05 * k), -.9, .9)))
    shimmer = sweep(7000 * .16 ** x, .9, 531) * np.clip(t / .02, 0, 1) * (1 - x) ** 1.3
    place(track, np.stack((shimmer, np.roll(shimmer, 180)), 1), 0, .35)
    slide = grind(span, 532, 120, 1500) * np.clip(t / .05, 0, 1) * (1 - x) ** .8
    place(track, sway(slide, np.clip(-.1 - .8 * x, -1, 1)), 0, .3)
    place(track, sway(np.roll(grind(span, 534, 120, 1500), 900) * np.clip(t / .05, 0, 1) * (1 - x) ** .8, np.clip(.1 + .8 * x, -1, 1)), 0, .3)
    for at in np.sort(span * (1 - rng.uniform(0, 1, 11) ** .6)):
        far = at / span
        place(track, stone(rng.uniform(150, 380) * (1.5 - .6 * far), hard=rng.uniform(.4, .9)), at,
              .3 * (1 - .6 * far), float(rng.choice((-1, 1)) * (.2 + .75 * far)))
    finish('S_Unweave', track, 70, 11000, .5, .25, 83, 8500, .8, cap=1.25)


def animal_cry():
    """An air-swimmer about to strike: a short sung call that rises and breaks, with breath in it. Nothing in it
    is metal or glass: two soft voices a fifth apart, a slow wobble, a little air."""
    seconds = .62
    t = t_(seconds)
    x = t / seconds
    pitch = 260 * (1 + .9 * np.sin(np.pi * np.clip(x * 1.25, 0, 1)) ** 1.5) * (1 + .025 * np.sin(2 * np.pi * 11 * t))
    phase = 2 * np.pi * np.cumsum(pitch) / RATE
    voice = np.sin(phase) + .45 * np.sin(2 * phase + .6) + .22 * np.sin(3 * phase + 1.1) + .3 * np.sin(1.5 * phase)
    shape = np.clip(t / .05, 0, 1) * np.clip((seconds - t) / .22, 0, 1) ** 1.4
    breath = band(rng.normal(size=len(t)), 900, 5200) * (.25 + .5 * x) * .35
    one = (voice * .5 + breath) * shape
    track = np.zeros((int(.8 * RATE), 2))
    place(track, sway(one, np.clip(-.25 + .5 * x, -1, 1)), 0, .8)
    finish('S_AnimalCry', track, 90, 9000, .5, .25, 83, 8500, .8, cap=1.25)


def animal_strike():
    """A body thrown through the air and landing its blow: a rush of displaced air, then a soft heavy slap. No
    ring and no click: flesh, not a machine."""
    track = np.zeros((int(.7 * RATE), 2))
    seconds = .2
    t = t_(seconds)
    x = t / seconds
    rush = sweep(500 + 2600 * x ** 2, .7, 611) * np.sin(np.pi * x) ** 1.5
    place(track, sway(rush, np.clip(-.6 + 1.2 * x, -1, 1)), 0, .7)
    seconds = .34
    t = t_(seconds)
    thump = np.sin(2 * np.pi * (95 * np.exp(-t * 9) + 48) * t) * np.exp(-t / .07)
    slap = band(rng.normal(size=len(t)), 180, 2400) * np.exp(-t / .022)
    hit = (thump * .9 + slap * .6) * np.clip(t / .002, 0, 1)
    place(track, np.stack((hit, hit), 1), .17, 1.0)
    finish('S_AnimalStrike', track, 40, 9000, .5, .25, 83, 8500, .8, cap=1.25)


def current_travel():
    """Stepping into a Divinity current on Arche: thin air rising and turning around her, a stack of open
    fifths (C, G, D: no third, so no warmth) swelling under it, and glass notes climbing in fifths and
    seconds until they close over her. Colder and clearer than the Grove's: the air is an octave higher
    and narrower, the chord is hollow, the hall is brighter."""
    seconds = 2.45
    t = t_(seconds)
    build = np.clip(t / 1.6, 0, 1)
    after = np.exp(-np.clip(t - 1.65, 0, None) / .2)
    rush = sweep(480 * 11 ** build ** 1.15, .9, 541) * build ** 1.6 * after
    track = sway(rush, np.sin(np.cumsum(2 * np.pi * (.6 + 1.5 * build)) / RATE) * .8)
    hiss = sweep(3000 * 3 ** build, .6, 542) * build ** 2.5 * after
    place(track, np.stack((hiss, np.roll(hiss, 150)), 1), 0, .35)
    phase = np.cumsum(98 * 1.5 ** build) / RATE * 2 * np.pi
    place(track, np.sin(phase) * build ** 2 * np.exp(-np.clip(t - 1.65, 0, None) / .25), 0, .1)
    for k, f in enumerate((261.6, 392, 587.3, 880)):
        place(track, glow(f, 2.3, 1.4, .7, 550 + k), 0, .08, (k - 1.5) / 2.5)
    scale = (1046.5, 1174.7, 1568, 1760, 2093, 2349.3, 3136, 3520, 4186)
    for at in np.sort(1.9 * np.sqrt(rng.uniform(.02, 1, 24))):
        step = int(np.clip(at / 1.9 * 7 + rng.uniform(-1.5, 1.5), 0, len(scale) - 1))
        place(track, chime(scale[step], 15, GLASS), at, .035 + .055 * at / 1.9, rng.uniform(-.8, .8))
    finish('S_CurrentTravel', track, 70, 12500, 1.0, .4, 84, 9500, .9, cap=2.55)


# ---------------------------------------------------------------- ambience (loops)

def whistle(n, centre, width, seed):
    """Wind finding an edge: a narrow band of noise (it loops: band() is circular), one take per ear."""
    return noise_bed(n, centre - width / 2, centre + width / 2, seed)


def amb_arche(seconds=48):
    """Kathodos in the open: wind high over pale stone (thin air, a hiss that comes and goes in long slow
    gusts, two faint whistles where it crosses an edge), a handful of crystal ticks far off, each with a
    long cold ring, and twice a loop a hanging stone groaning very low. No music, no birds, nothing alive."""
    n = int(seconds * RATE)
    shared = drift(n, 6, 601)
    gust = np.stack([(.5 + .5 * np.clip(.75 * shared + .45 * drift(n, 9, 602 + ch), -1, 1)) ** 1.8 for ch in range(2)], 1)
    air = noise_bed(n, 90, 380, 604) * (.5 + .5 * gust)
    thin = noise_bed(n, 1500, 5200, 605) * (.12 + .88 * gust)
    hiss = noise_bed(n, 5200, 11000, 606) * (.05 + .95 * gust ** 1.6) * np.stack([.7 + .3 * wobble(n, 2, 9, 607 + ch) for ch in range(2)], 1)
    edge = (whistle(n, 1320, 70, 609) * (np.clip(drift(n, 7, 610), 0, 1) ** 2)[:, None] * np.array([1.0, .5])
            + whistle(n, 1975, 90, 611) * (np.clip(drift(n, 8, 612), 0, 1) ** 2)[:, None] * np.array([.45, 1.0])) * gust
    ticks = np.zeros((n, 2))
    for k, at in enumerate((4.5, 12.0, 17.5, 26.0, 33.5, 39.0, 45.0)):
        f = rng.uniform(2300, 5200)
        when, pan = at + rng.uniform(-1.5, 1.5), rng.uniform(-.85, .85)
        put(ticks, chime(f, rng.uniform(16, 28), GLASS), when, rng.uniform(.5, 1), pan)
        if rng.uniform() < .45:   # now and then a second sliver answers the first
            put(ticks, chime(f * rng.choice((1.335, 1.498, .749)), rng.uniform(18, 28), GLASS), when + rng.uniform(.12, .35), rng.uniform(.3, .6), pan + rng.uniform(-.2, .2))
    ticks = ring(band(ticks, 1200, 9000), 4.5, 1.6, 620, 8000)   # far off: mostly their echo off the canyon walls
    groans = np.zeros((n, 2))
    for k in range(2):
        put(groans, groan(rng.uniform(42, 68), rng.uniform(4.5, 6.5), 625 + k), (k + rng.uniform(.2, .7)) * seconds / 2, 1.0, rng.uniform(-.6, .6))
    groans = ring(band(groans, 30, 420), 3.5, .8, 628, 1500)
    mix = blend((air, -33), (thin, -29), (hiss, -34), (edge, -33), (ticks, -36), (groans, -37))
    write('S_Amb_Arche', ring(mix, 1.6, .2, 629, 9000), .6, -23)


def drip(freq, deep):
    """A drop into still water: the tick of the surface, then the pocket of air it makes sounding (a short
    sine rising in pitch, Minnaert), and for a heavy drop a second, lower one after it."""
    out = np.zeros(int(.2 * RATE))
    out[:int(.05 * RATE)] += bubble(freq, .05) * 1.0
    tick = t_(.012)
    out[:len(tick)] += band(rng.normal(size=len(tick)), 2500, 9000) * np.exp(-tick / .0015) * .25
    if deep:
        at = int(rng.uniform(.035, .06) * RATE)
        out[at:at + int(.09 * RATE)] += bubble(freq * rng.uniform(.5, .65), .09) * .7
    return out


def amb_cistern(seconds=40):
    """The Cisterns: still water in a stone bowl. The water barely moves (slow, soft lapping against the
    rim, a low breath of the chamber's air), and drops fall into it at long uneven intervals, each answered
    by the far wall and then by the whole cold vault for seconds."""
    n = int(seconds * RATE)
    room = noise_bed(n, 60, 320, 641) * (.8 + .2 * drift(n, 5, 642))[:, None]
    laps = np.zeros((n, 2))
    at = rng.uniform(0, 2)
    while at < seconds - .5:
        lt = t_(rng.uniform(1.4, 2.4))
        wash = band(rng.normal(size=len(lt)), 140, rng.uniform(700, 1200)) * np.clip(lt / rng.uniform(.35, .6), 0, 1) ** 1.5 * np.exp(-lt / rng.uniform(.4, .6))
        pan = rng.uniform(-.7, .7)
        put(laps, wash * np.clip((lt[-1] - lt) / .2, 0, 1), at, rng.uniform(.5, 1), pan)
        for _ in range(rng.integers(0, 3)):
            put(laps, bubble(rng.uniform(380, 1100), rng.uniform(.015, .04)), at + rng.uniform(.3, 1.1), rng.uniform(.03, .07), pan + rng.uniform(-.2, .2))
        at += rng.uniform(2.6, 5.2)
    laps = np.tanh(2 * laps / np.abs(laps).max())
    drips = np.zeros((n, 2))
    at = rng.uniform(1, 3)
    while at < seconds - .3:
        sound, gain, pan = drip(rng.uniform(900, 2300), rng.uniform() < .4), rng.uniform(.4, 1), rng.uniform(-.8, .8)
        put(drips, sound, at, gain, pan)
        # The far wall: the same drop again, darker, from the other side, then once more, fainter.
        delay = rng.uniform(.26, .38)
        put(drips, band(np.concatenate((sound, np.zeros(RATE // 8))), 300, 3200), at + delay, gain * .4, -pan * .8)
        put(drips, band(np.concatenate((sound, np.zeros(RATE // 8))), 300, 2000), at + delay * 2.1, gain * .18, pan * .5)
        at += rng.uniform(1.6, 5.5) if rng.uniform() > .2 else rng.uniform(.35, .6)
    drips = ring(drips, 5.5, 1.1, 650, 5500)
    mix = blend((room, -34), (laps, -29), (drips, -26))
    write('S_Amb_Cistern', ring(mix, 2.2, .3, 651, 5000), .7, -23)


def amb_lens(seconds=40):
    """The Sundering Lens: a cold hum on F sharp whose every partial has a neighbour a fraction of a hertz
    away, so the whole thing beats slowly (eight swells a loop, the upper partials a little faster, never
    quite together), with the tritone, C, inside it; a faint whine of two high tones a few hertz apart
    hangs over it, and thin cold air moves around it. It does not pulse or strike: it waits. Uneasy."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    step = RATE / n   # one cycle per loop: the smallest difference two looping tones can have
    hum = np.zeros((n, 2))
    for k, amp in ((1, 1), (2, .55), (3, .3), (4, .2), (6, .1), (8, .05)):
        f = whole(92.5 * k, n)
        for ch in range(2):
            beat = (8 + 3 * (k - 1) + ch) * step
            hum[:, ch] += amp * (np.sin(2 * np.pi * f * t + rng.uniform(0, 6.3)) + np.sin(2 * np.pi * (f + beat) * t + rng.uniform(0, 6.3)))
    for f, amp in ((130.8, .32), (261.6, .12), (138.6, .1)):   # the tritone, and a fifth that does not agree with it
        for ch in range(2):
            hum[:, ch] += amp * (np.sin(2 * np.pi * whole(f, n) * t + rng.uniform(0, 6.3)) + np.sin(2 * np.pi * (whole(f, n) + (5 + ch) * step) * t))
    sub = noise_bed(n, 28, 110, 661) * (.7 + .3 * drift(n, 4, 662))[:, None]
    violet = np.zeros((n, 2))   # the cold edge of the light: high partials that shimmer in and out
    for k, f in enumerate((1108.7, 1480, 1661.2, 2217.5)):
        for ch in range(2):
            swell = np.clip(drift(n, 6, 664 + 2 * k + ch), 0, 1) ** 1.5
            violet[:, ch] += (np.sin(2 * np.pi * whole(f, n) * t + rng.uniform(0, 6.3)) + np.sin(2 * np.pi * (whole(f, n) + (30 + 9 * k) * step) * t)) * swell / (k + 1)
    whine = np.zeros((n, 2))
    for f, amp in ((5919.9, 1), (5926.5, .9), (8372, .35)):
        for ch in range(2):
            whine[:, ch] += amp * np.sin(2 * np.pi * whole(f, n) * t + rng.uniform(0, 6.3)) * (.6 + .4 * drift(n, 5, 680 + ch))
    air = noise_bed(n, 2400, 8000, 685) * (.5 + .5 * drift(n, 7, 686))[:, None]
    mix = blend((hum, -24), (sub, -32), (violet, -37), (whine, -45), (air, -40))
    write('S_Amb_Lens', ring(mix, 4.0, .5, 689, 3500), .6, -22)


# ---------------------------------------------------------------- music (Muse Sounds)

# C Aeolian, far from the Grove's E minor and G major. No leading tone anywhere: the dominant is G minor or a
# suspended G, so nothing ever pushes; the home chord is mostly an open fifth with its ninth. Theme A (the
# city's grief) enters on G after a beat of silence and falls; theme B (things coming home) climbs from E flat
# over A flat and E flat harmony and ends on C over the open fifth: home, with no major third to call it a
# victory. Themes give each bar's notes as (beat, key, beats).
THEME_A = (((1, 67, 3),), ((0, 72, 2), (2, 70, 2)), ((0, 68, 3), (3, 67, 1)), ((0, 65, 2), (2, 67, 2)),
           ((1, 67, 1), (2, 72, 2)), ((0, 75, 3), (3, 74, 1)), ((0, 72, 2), (2, 70, 1), (3, 68, 1)), ((0, 67, 4),))
THEME_B = (((0, 63, 1), (1, 65, 1), (2, 70, 2)), ((0, 72, 3), (3, 70, 1)), ((0, 67, 1), (1, 68, 1), (2, 72, 2)), ((0, 74, 4),),
           ((0, 75, 1), (1, 77, 1), (2, 79, 2)), ((0, 82, 2), (2, 79, 1), (3, 77, 1)), ((0, 75, 2), (2, 77, 1), (3, 74, 1)), ((0, 72, 4),))
# Chords as they are bowed: contrabasses, cellos, violas (two notes), second violins (two notes); sounding pitch.
CHORD = {'C5': (36, 43, (55, 62), (67, 74)), 'Cm9': (36, 43, (55, 63), (62, 67)), 'Cm7/Eb': (39, 46, (55, 60), (63, 67)),
         'Fm': (41, 48, (56, 60), (65, 68)), 'Gm7': (43, 50, (55, 58), (62, 65)), 'Abmaj7': (32, 51, (55, 60), (63, 67)),
         'Fm9': (41, 48, (56, 63), (67, 72)), 'Ab': (44, 51, (56, 60), (63, 68)), 'Gsus': (43, 50, (55, 60), (62, 67)),
         'Ab9': (32, 51, (58, 60), (63, 70)), 'Eb/G': (43, 51, (58, 63), (67, 70)), 'Fm7': (41, 48, (56, 63), (65, 68)),
         'Bb': (34, 46, (53, 58), (62, 65))}
CHORDS_A = ('Cm9', 'Cm7/Eb', 'Fm', 'Gm7', 'Abmaj7', 'Fm9', 'Ab', 'Gsus')
CHORDS_B = ('Ab9', 'Eb/G', 'Fm7', 'Bb', 'Abmaj7', 'Eb/G', 'Fm7', 'C5')
STILL = ('C5', 'Abmaj7', 'Fm9', 'Gsus')   # two bars each, over which the piece begins and ends
TEMPO, BARS = 54, 48
LEVELS = ('pp', 'p', 'mp', 'mf', 'f', 'ff')
ORCHESTRA = ('Flute', 'Oboe', 'English Horn', 'Horn in F', 'Trombone', 'Tuba', 'Timpani', 'Glockenspiel', 'Harp',
             'Violins 1', 'Violins 2', 'Violas', 'Violoncellos', 'Contrabasses')


class Band:
    """Parts by name, each remembering its dynamic so a marking is written only on a change (the one in
    Tools/music/build_game_music.py)."""

    def __init__(self, score):
        self.score, self.level = score, {}
        self.parts = {name: score.part(name) for name in ORCHESTRA}

    def __call__(self, name, at=None, level=None):
        if level is not None and self.level.get(name) != level:
            self.parts[name].dynamic(at, LEVELS[level])
            self.level[name] = level
        return self.parts[name]

    def swell(self, name, start, end, kind):
        """A hairpin; the part's next entry writes its dynamic again."""
        self.parts[name].wedge(start, end, kind)
        self.level[name] = None


def bed(b, bar, bars, name, level, tremolo=False, bass=None, cellos=True):
    """A chord held by the strings for `bars` bars (long notes are tied over the bar lines); `tremolo` makes
    the violas and second violins shiver; `bass` keeps a pedal under it; without `cellos` they are free to sing."""
    cb, vc, vla, v2 = CHORD[name]
    at, beats = bar * 4, bars * 4
    b('Contrabasses', at, level).note(at, beats, cb if bass is None else bass)
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


def rolls(b, bar, names, level, twice=False):
    """The harp spreading each bar's chord upward in eighth notes and letting it ring; `twice` answers it
    from the top on the third beat."""
    for i, name in enumerate(names):
        cb, vc, vla, v2 = CHORD[name]
        tones, at = (vc, vla[0], vla[1], v2[0], v2[1]), (bar + i) * 4
        for k, key in enumerate(tones):
            b('Harp', at, level).note(at + k * .5, .5, key)
        if twice:
            for k, key in enumerate((v2[1] + 12, v2[0] + 12, v2[1], vla[1])):
                b('Harp', at, level).note(at + 2.5 + k * .25, .25, key)


def points(b, level, *marks):
    """Single glockenspiel notes, (bar, beat, key): points of crystal light."""
    for bar, beat, key in marks:
        b('Glockenspiel', bar * 4 + beat, level).note(bar * 4 + beat, 1, key)


def stonework(b, bar, bars, name, level):
    """The weight of stone: tuba on the bass, trombones on the fifth above it."""
    cb, vc, vla, v2 = CHORD[name]
    at = bar * 4
    b('Tuba', at, level).note(at, bars * 4, cb if cb >= 29 else cb + 12)
    b('Trombone', at, level).note(at, bars * 4, (vc, vc + 7) if vc + 7 <= 58 else (vc - 5, vc))


def arche_score():
    """Arche: the City of the Descent (48 bars at 54 bpm, 3 min 33 s, loops).
    1  bars 0-7    The city standing still: an open fifth on C held by muted-quiet strings over a pedal, the
                   first violins on one high G, single glockenspiel notes and a harp chord now and then;
                   tuba and trombones come in under the second half; an English horn sounds two notes.
    2  bars 8-15   Theme A, the grief, on the first violins, plainly; the English horn joins its second half.
    3  bars 16-23  The cellos take it an octave down under shivering high violins, the low brass under them,
                   a horn holding the middle, the flute answering the long notes.
    4  bars 24-31  Scattered things: theme B arrives in pieces, a bar each: harp, flute, English horn, horn,
                   glockenspiel and harp, flute and oboe, violins, horn.
    5  bars 32-39  The pieces come home: theme B whole on the first violins with the horn an octave under,
                   the fullest the piece gets (mezzo forte to a brief forte), brass and timpani as weight, not
                   fanfare; it settles on C over the open fifth, with no third.
    6  bars 40-47  Stillness again: shivering strings, the English horn and flute remembering theme A, the
                   violins theme B's first two bars, very quietly; a suspended G that falls into bar 0."""
    score = muse.Score(tempo=TEMPO, title='Physis - Arche')
    b = Band(score)
    # 1. The city standing still (bars 0-7).
    bed(b, 0, 2, 'C5', 0)
    bed(b, 2, 2, 'Abmaj7', 0, bass=36)
    bed(b, 4, 2, 'Fm9', 1)
    bed(b, 6, 2, 'Gsus', 1)
    b('Violins 1', 0, 0).note(0, 16, 79)
    b('Violins 1').note(16, 8, 75)
    b('Violins 1').note(24, 8, 74)
    points(b, 1, (0, 2, 91), (1, 3, 86), (2, 1.5, 87), (3, 2.5, 84), (5, 1, 91), (6, 2, 86), (7, 3, 79))
    rolls(b, 1, ('C5',), 0)
    rolls(b, 3, ('Abmaj7',), 0)
    rolls(b, 4, ('Fm9', 'Fm9', 'Gsus', 'Gsus'), 1)
    stonework(b, 4, 2, 'Fm9', 0)
    b.swell('Tuba', 16, 22, 'crescendo')
    b.swell('Trombone', 16, 22, 'crescendo')
    stonework(b, 6, 2, 'Gsus', 1)
    b.swell('Tuba', 26, 32, 'diminuendo')
    b.swell('Trombone', 26, 32, 'diminuendo')
    line(b, 'English Horn', 6, (((0, 62, 2), (2, 67, 2)), ((0, 62, 4),)), 1)
    # 2. Theme A on the first violins (bars 8-15).
    for i, name in enumerate(CHORDS_A):
        bed(b, 8 + i, 1, name, 1 if i < 4 else 2)
    line(b, 'Violins 1', 8, THEME_A, 2)
    rolls(b, 8, CHORDS_A, 1)
    points(b, 1, (11, 2, 86), (15, 2, 91))
    line(b, 'English Horn', 12, THEME_A[4:], 1)
    for i, name in enumerate(CHORDS_A[4:]):
        b('Horn in F', (12 + i) * 4, 0).note((12 + i) * 4, 4, CHORD[name][2][1])
    # 3. The cellos take it; high violins shiver, the low brass carries the bass (bars 16-23).
    for i, name in enumerate(CHORDS_A):
        at = (16 + i) * 4
        bed(b, 16 + i, 1, name, 2, cellos=False)
        b('Violins 1', at, 0).note(at, 4, CHORD[name][3][1] + 12, tremolo=3)
        b('Horn in F', at, 1).note(at, 4, CHORD[name][2][1])
        stonework(b, 16 + i, 1, name, 1)
    line(b, 'Violoncellos', 16, THEME_A, 3, shift=-12)
    rolls(b, 16, CHORDS_A, 1)
    line(b, 'Flute', 19, (((1, 74, 1), (2, 77, 2)),), 2)
    line(b, 'Flute', 23, (((1, 79, 1), (2, 74, 2)),), 2)
    points(b, 1, (17, 3, 87), (21, 3, 91))
    b('Timpani', 64, 1).note(64, 2, 48)
    # 4. Scattered things: theme B in pieces (bars 24-31).
    for i, name in enumerate(CHORDS_B):
        bed(b, 24 + i, 1, name, 1 if i < 4 else 2)
    for k, key in enumerate((63, 65, 70)):   # the harp's piece rings: three plucked notes
        b('Harp', 96, 2).note(96 + k, 1, key)
    line(b, 'Flute', 25, THEME_B[1:2], 2)
    line(b, 'English Horn', 26, THEME_B[2:3], 2)
    line(b, 'Horn in F', 27, THEME_B[3:4], 2, shift=-12)
    for k, key in enumerate((75, 77, 79)):
        b('Glockenspiel', 112, 2).note(112 + k, 1, key + 12)
        b('Harp', 112, 2).note(112 + k, 1, key)
    line(b, 'Flute', 29, THEME_B[5:6], 2)
    line(b, 'Oboe', 29, THEME_B[5:6], 1, shift=-12)
    line(b, 'Violins 1', 30, THEME_B[6:7], 2)
    b.swell('Violins 1', 120, 128, 'crescendo')
    line(b, 'Horn in F', 31, THEME_B[7:8], 2, shift=-12)
    line(b, 'English Horn', 31, THEME_B[7:8], 1)
    rolls(b, 25, CHORDS_B[1:4], 1)
    rolls(b, 29, CHORDS_B[5:8], 1)
    for i in range(4):
        stonework(b, 28 + i, 1, CHORDS_B[4 + i], 1)
    b('Timpani', 124, 0).note(124, 4, 43, tremolo=3)
    b.swell('Timpani', 124, 128, 'crescendo')
    # 5. The pieces come home: theme B whole (bars 32-39).
    for i, name in enumerate(CHORDS_B):
        bed(b, 32 + i, 1, name, 2 if i < 4 else 3 if i < 6 else 2)
        stonework(b, 32 + i, 1, name, 2 if i < 6 else 1)
    line(b, 'Violins 1', 32, THEME_B[:4], 3)
    line(b, 'Violins 1', 36, THEME_B[4:6], 4)
    line(b, 'Violins 1', 38, THEME_B[6:], 3)
    b.swell('Violins 1', 156, 160, 'diminuendo')
    line(b, 'Horn in F', 32, THEME_B, 2, shift=-12)
    line(b, 'Flute', 36, THEME_B[4:], 2, shift=12)
    line(b, 'Oboe', 36, THEME_B[4:], 2)
    rolls(b, 32, CHORDS_B, 2, twice=True)
    points(b, 2, (32, 0, 87), (36, 0, 87), (36, 2, 91), (39, 2, 91))
    b('Timpani', 128, 2).note(128, 2, 44)
    b('Timpani', 144, 2).note(144, 2, 44)
    b('Timpani', 156, 1).note(156, 2, 48)
    # 6. Stillness again (bars 40-47).
    bed(b, 40, 2, 'C5', 0, tremolo=True)
    bed(b, 42, 2, 'Abmaj7', 0, tremolo=True, bass=36)
    bed(b, 44, 2, 'Fm9', 0)
    bed(b, 46, 2, 'Gsus', 0)
    line(b, 'English Horn', 40, THEME_A[:2], 1)
    line(b, 'Flute', 42, THEME_A[2:4], 1)
    line(b, 'Violins 1', 44, THEME_B[:2], 0)
    b('Violins 1').note(184, 8, 74)
    b('Horn in F', 184, 0).note(184, 4, 60)
    b('Horn in F').note(188, 4, 62)
    stonework(b, 46, 2, 'Gsus', 0)
    rolls(b, 41, ('C5',), 0)
    rolls(b, 43, ('Abmaj7', 'Fm9', 'Fm9', 'Gsus'), 0)
    points(b, 1, (40, 2, 91), (41, 3, 86), (43, 1, 87), (45, 2, 84), (46, 2, 86), (47, 2.5, 91))
    return score


def arche_music(excerpt=None, from_bar=0, profile='MuseSounds'):
    """Renders the score with MuseScore and finishes it as the ported tracks are: the Conclave's hall at HALL
    of a SoundFont track's amount (a long, bright, cold one), the last ringing seconds laid over the first so
    the loop has no seam, the Center's level ride taken round the loop, a soft knee, and the common loudness.
    `excerpt` seconds from `from_bar` make a test file."""
    import soundfile
    WORK.mkdir(parents=True, exist_ok=True)
    score = arche_score()
    assert score.bars() == BARS, score.bars()
    tag = 'Arche' if profile == 'MuseSounds' else 'Arche_basic'
    score.write(WORK / (tag + '.musicxml'))
    missing = muse.render(WORK / (tag + '.musicxml'), WORK / (tag + '_raw.wav'), profile=profile, keep_score=WORK / (tag + '.mscz'))
    print('Arche: %d bars at %d bpm, profile %s, parts: %s; without a sound of the profile: %s' % (
        score.bars(), score.tempo, profile, ', '.join(p.name for p in score.parts), missing), flush=True)
    audio, rate = soundfile.read(WORK / (tag + '_raw.wav'), dtype='float32')
    assert rate == RATE and audio.ndim == 2 and audio.shape[1] == 2, (rate, audio.shape)
    beat = 60 / TEMPO
    total = int((BARS * 4 * beat + 8.0) * RATE)   # the piece and eight seconds of its ringing, as perform() gave
    mix = np.zeros((total, 2))
    mix[:min(total, len(audio))] = audio[:total]
    mix = hall(mix, 4.6, .6 * HALL, 53, 9000)
    if excerpt:
        mix = mix[int(from_bar * 4 * beat * RATE):][:int(excerpt * RATE)]
        mix[-int(1.5 * RATE):] *= np.linspace(1, 0, int(1.5 * RATE))[:, None]
        mix = ride(mix / np.abs(mix).max())
    else:
        mix = fold(mix, BARS * 4 * beat)
        pad = 12 * RATE
        mix = ride(np.concatenate((mix[-pad:], mix, mix[:pad])) / np.abs(mix).max())[pad:-pad]
    mix = mix / np.abs(mix).max()
    # The knee is the Grove's: a patient score has a high crest, and write() draws the result back to the
    # common level (it only ever turns down, so the knee has to bring the piece to that level or above).
    mix = np.tanh(mix * KNEE) / np.tanh(KNEE)
    write('S_Music_Arche_Excerpt' if excerpt else 'S_Music_Arche', mix, .9, MUSIC_LUFS)


KNEE = 2.0
SOUNDS = {'S_Music_Arche': arche_music, 'S_Weave': weave, 'S_WeaveRestless': weave_restless, 'S_Unweave': unweave,
          'S_CurrentTravel': current_travel, 'S_AnimalCry': animal_cry, 'S_AnimalStrike': animal_strike, 'S_Amb_Arche': amb_arche, 'S_Amb_Cistern': amb_cistern, 'S_Amb_Lens': amb_lens}
PARTS = {'music': ['S_Music_Arche'], 'sfx': ['S_Weave', 'S_WeaveRestless', 'S_Unweave', 'S_CurrentTravel', 'S_AnimalCry', 'S_AnimalStrike'],
         'amb': ['S_Amb_Arche', 'S_Amb_Cistern', 'S_Amb_Lens']}


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
    names = [name for part in (args or ['music', 'sfx', 'amb']) for name in PARTS.get(part, [part])]
    unknown = [name for name in names if name not in SOUNDS]
    if unknown:
        sys.exit('unknown part %s; parts: %s' % (', '.join(unknown), ', '.join(list(PARTS) + list(SOUNDS))))
    for name in names:
        reseed(name)
        if name == 'S_Music_Arche':
            arche_music(float(options['--excerpt']) if '--excerpt' in options else None, int(options.get('--from-bar', 0)), profile)
        else:
            SOUNDS[name]()
