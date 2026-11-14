"""Sound and music for the Center of the Universe (level 2).

Run with the Kokoro venv's Python (it has numpy) on the host, from the project folder:
  Saved/AudioTools/kokoro_venv/bin/python Tools/build_physis_center_audio.py [sfx] [music] [cine]
Music renders through Art/Audio/SoundFont/MuseScore_General.sf3 with Tools/physis_soundfont.py.
Writes Art/Audio/Center/*.wav, imported by `outfit_operation center:audio`.
"""
import pathlib
import random
import sys
import wave

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import physis_soundfont as sf  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'Art/Audio/Center'
RATE = 44100
rng = np.random.default_rng(11)
OUT.mkdir(parents=True, exist_ok=True)


def write(name, signal, peak=.9):
    if signal.ndim == 1:
        signal = np.stack((signal, signal), 1)
    signal = signal / max(np.abs(signal).max(), 1e-6) * peak
    with wave.open(str(OUT / (name + '.wav')), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((signal * 32767).astype('<i2').tobytes())
    print('wrote', name, round(len(signal) / RATE, 1), 's', flush=True)


def t_(seconds):
    return np.arange(int(seconds * RATE)) / RATE


def band(signal, low, high):
    spectrum = np.fft.rfft(signal, axis=0)
    freq = np.fft.rfftfreq(len(signal), 1 / RATE)
    shape = ((freq >= low) & (freq <= high)).astype(float)
    shape = np.convolve(shape, np.ones(64) / 64, 'same')
    if signal.ndim == 2:
        shape = shape[:, None]
    return np.fft.irfft(spectrum * shape, len(signal), axis=0)


def size_up(n):
    s = 1
    while s < n:
        s *= 2
    return s


def hall(signal, seconds=3.0, wet=.5, seed=1, bright=6000):
    if signal.ndim == 1:
        signal = np.stack((signal, signal), 1)
    local = np.random.default_rng(seed)
    n = int(seconds * RATE)
    out = np.zeros_like(signal)
    for ch in range(2):
        tail = local.normal(size=n) * np.exp(-6.0 * np.arange(n) / n)
        tail = band(tail, 80, bright)
        tail /= np.sqrt((tail ** 2).sum())
        L = size_up(len(signal) + n)
        w = np.fft.irfft(np.fft.rfft(signal[:, ch], L) * np.fft.rfft(tail, L), L)[:len(signal)]
        out[:, ch] = signal[:, ch] + w * wet
    return out


def env(n, attack, release, shape=1.0):
    t = np.arange(n) / RATE
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    r = np.clip((t[-1] - t) / max(release, 1e-4), 0, 1)
    return (a * r) ** shape


def bell(freq, seconds, decay=2.5, partials=((1, 1), (2.76, .45), (5.4, .25), (8.9, .12))):
    t = t_(seconds)
    out = np.zeros_like(t)
    for ratio, amp in partials:
        out += amp * np.sin(2 * np.pi * freq * ratio * t + rng.uniform(0, 6)) * np.exp(-t * decay * ratio ** .5)
    return out * np.clip(t / .004, 0, 1)


def place(track, sound, at, gain=1.0, pan=0.0):
    i = int(at * RATE)
    if sound.ndim == 1:
        sound = np.stack((sound * np.sqrt((1 - pan) / 2) * 1.414, sound * np.sqrt((1 + pan) / 2) * 1.414), 1)
    end = min(i + len(sound), len(track))
    if end > i:
        track[i:end] += sound[:end - i] * gain


def loopable(track, fade):
    """Crossfades the tail into the head so the file loops without a seam."""
    n = int(fade * RATE)
    ramp = np.linspace(0, 1, n)[:, None]
    head = track[:n] * ramp + track[-n:] * (1 - ramp)
    return np.concatenate([head, track[n:-n]])


# ---------------------------------------------------------------- ambience

def ambience():
    seconds = 64
    n = int(seconds * RATE)
    track = np.zeros((n, 2))
    # Wind: slow-breathing filtered noise, wide.
    for ch in range(2):
        noise = rng.normal(size=n)
        track[:, ch] += band(noise, 60, 520) * (.5 + .3 * np.sin(np.arange(n) / RATE * 2 * np.pi / (17 + ch * 3)))
    # Water lapping under reeds.
    lap = band(rng.normal(size=n), 300, 1800) * (.5 + .5 * np.sin(np.arange(n) / RATE * 2 * np.pi * .4)) ** 6
    track += np.stack((lap, np.roll(lap, 9000)), 1) * .5
    # Crystal crickets: tiny high pings in clusters, all over the stereo field.
    for k in range(900):
        at = rng.uniform(0, seconds - 1)
        f = rng.choice([3520, 3951, 4186, 4699, 5274]) * rng.uniform(.995, 1.005)
        ping = bell(f, .35, 14, ((1, 1), (2.01, .2)))
        for j in range(rng.integers(1, 4)):
            place(track, ping, at + j * .07, rng.uniform(.03, .09), rng.uniform(-1, 1))
    # Glass frogs: soft low glooping calls.
    for k in range(70):
        at = rng.uniform(0, seconds - 1)
        f0 = rng.uniform(140, 220)
        t = t_(.32)
        call = np.sin(2 * np.pi * (f0 * t + 60 * t * t)) * np.exp(-t * 9) * np.clip(t / .01, 0, 1)
        call += .3 * np.sin(2 * np.pi * 3 * (f0 * t + 60 * t * t)) * np.exp(-t * 14)
        for j in range(rng.integers(1, 3)):
            place(track, call, at + j * .4, rng.uniform(.12, .25), rng.uniform(-.8, .8))
    # Ethereal creature song, far off: gliding sine voices.
    for k in range(6):
        at = rng.uniform(2, seconds - 8)
        t = t_(5.5)
        glide = rng.uniform(380, 620) * (1 + .18 * np.sin(2 * np.pi * t / 5.5 * rng.uniform(.6, 1.2)))
        phase = np.cumsum(glide) / RATE * 2 * np.pi
        voice = (np.sin(phase) + .25 * np.sin(2 * phase) + .1 * np.sin(3 * phase)) * env(len(t), 1.8, 2.5, 1.5)
        place(track, voice, at, .1, rng.uniform(-.9, .9))
    track = hall(track, 3.5, .55, 3)
    write('S_Center_Ambience', loopable(track, 3), .55)


def temple_ambience():
    seconds = 48
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    drone = np.zeros(n)
    for f, a in ((55, 1), (82.5, .6), (110, .5), (164.8, .25), (220, .15)):
        drone += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * (.7 + .3 * np.sin(2 * np.pi * t / rng.uniform(9, 15)))
    track = np.stack((drone, np.roll(drone, 3000)), 1) * .3
    for k in range(40):
        place(track, bell(rng.choice([440, 554, 659, 880, 1109]), 4, 1.2), rng.uniform(0, seconds - 4), rng.uniform(.05, .12), rng.uniform(-1, 1))
    drip = bell(1800, .4, 22, ((1, 1),))
    for k in range(60):
        place(track, drip, rng.uniform(0, seconds - 1), .05, rng.uniform(-1, 1))
    write('S_Temple_Ambience', loopable(hall(track, 5, .8, 4, 4000), 3), .55)


# ---------------------------------------------------------------- effects

def breath():
    """Physis's first breath: a sudden sharp gasp, held, then released."""
    seconds = 2.6
    t = t_(seconds)
    noise = rng.normal(size=len(t))
    # Gasp: fast-rising airy inhale with a vocal formant edge.
    gasp_env = np.clip(t / .08, 0, 1) * np.exp(-np.clip(t - .15, 0, None) * 5.5) * (t < .9)
    air = band(noise, 900, 7200) * gasp_env
    form = np.zeros_like(t)
    f0 = 210 + 160 * np.clip(t / .25, 0, 1)
    ph = np.cumsum(f0) / RATE * 2 * np.pi
    for k, (fc, amp) in enumerate(((800, 1), (1250, .7), (2600, .4))):
        form += amp * np.sin(ph * max(1, round(fc / 300)))
    form *= gasp_env * .12
    # Release: a long shaky exhale.
    ex_env = np.clip((t - 1.35) / .2, 0, 1) * np.exp(-np.clip(t - 1.55, 0, None) * 1.8)
    shake = 1 + .25 * np.sin(2 * np.pi * 7 * t)
    exhale = band(noise, 250, 3200) * ex_env * shake * .55
    sig = air + form + exhale
    write('S_Awaken_Breath', hall(sig, 1.4, .25, 5), .8)


def resonator(signal, freq, bandwidth):
    """Two-pole resonant filter: one vocal-tract formant."""
    r = np.exp(-np.pi * bandwidth / RATE)
    a1, a2 = -2 * r * np.cos(2 * np.pi * freq / RATE), r * r
    out = np.zeros_like(signal)
    y1 = y2 = 0.0
    gain = 1 - r
    for i, x in enumerate(signal):
        y = gain * x - a1 * y1 - a2 * y2
        out[i] = y
        y2, y1 = y1, y
    return out


def gasp_synth():
    """(Superseded by gasp(), which uses real recordings.) Physis's first breath on waking. Real breath is broadband turbulent air, only gently coloured
    by the mouth, so it is built that way: pink-ish noise with a flickering, uneven flow, three wide
    formants of an open mouth, a lip-parting click, a sharp inhale that stops dead as the throat
    catches, a held beat, then a slower shaky exhale that ends in a faint voiced sigh."""
    seconds = 3.6
    t = t_(seconds)
    n = len(t)

    def pinkish(seed):
        local = np.random.default_rng(seed)
        white = local.normal(size=n)
        spec = np.fft.rfft(white)
        f = np.fft.rfftfreq(n, 1 / RATE)
        spec /= np.maximum(f, 150) ** .18
        return np.fft.irfft(spec, n) * 40

    def flicker(seed, rate, depth):
        # Uneven airflow: slow random wobble of the breath's strength.
        local = np.random.default_rng(seed)
        steps = local.normal(size=int(seconds * rate) + 2)
        return 1 + depth * np.interp(t * rate, np.arange(len(steps)), steps)

    def mouth(sig, formants):
        out = np.zeros_like(sig)
        for f, bw, g in formants:
            # Normalise each formant's peak so wide upper formants are not lost.
            out += g * resonator(sig, f, bw) * (bw / 300) ** .5
        return out * .4 + band(sig, 1100, 7500) * 1.1

    # Inhale: lips part (0.06 s), air rushes in for ~0.27 s, the throat catches and it stops.
    start, stop = .07, .36
    rise = np.clip((t - start) / .045, 0, 1) ** 1.5
    fall = np.clip((stop - t) / .018, 0, 1)
    swell = np.exp(-((t - .17) / .16) ** 2) * .55 + .45
    inhale_env = rise * fall * swell * (t < stop + .02)
    air = mouth(pinkish(1) * inhale_env * flicker(2, 40, .25), ((780, 420, 1.0), (1350, 520, .6), (2700, 700, .35)))
    click = np.zeros(n)
    k = int(.062 * RATE)
    click[k:k + 90] = np.hanning(90) * np.sin(np.arange(90) * 2 * np.pi * 2200 / RATE)
    catch = np.zeros(n)
    k = int(stop * RATE)
    catch[k:k + 140] = np.hanning(140) * np.sin(np.arange(140) * 2 * np.pi * 900 / RATE) * .6
    # A breathy edge of voice inside the gasp, uneven in pitch.
    pitch = 310 + 70 * np.clip((t - .1) / .18, 0, 1) + 12 * np.sin(2 * np.pi * 9 * t)
    phase = np.cumsum(pitch) / RATE * 2 * np.pi
    buzz = (np.sin(phase) + .5 * np.sin(2 * phase) + .25 * np.sin(3 * phase)) * np.exp(-((t - .22) / .07) ** 2)
    voice = mouth(buzz * (.5 + .5 * pinkish(3) / (np.abs(pinkish(3)).max() + 1e-9)), ((780, 300, 1.0), (1350, 400, .5))) * .5
    # Held breath, then a slower release from 1.15 s through a half-open mouth, shaking.
    release = np.clip((t - 1.15) / .18, 0, 1) ** 1.3 * np.exp(-np.clip(t - 1.4, 0, None) * 1.1)
    shake = flicker(4, 7, .35) * (1 + .12 * np.sin(2 * np.pi * 5.5 * t))
    exhale = mouth(pinkish(5) * release * shake, ((560, 450, 1.0), (1500, 650, .6), (2500, 900, .35))) * .28
    # It ends in a faint low sigh, more air than voice.
    sigh_pitch = 230 - 40 * np.clip((t - 1.6) / .9, 0, 1)
    sphase = np.cumsum(sigh_pitch) / RATE * 2 * np.pi
    sigh = (np.sin(sphase) + .4 * np.sin(2 * sphase)) * np.exp(-((t - 1.95) / .35) ** 2) * (.4 + .6 * np.abs(pinkish(6)) / (np.abs(pinkish(6)).max() + 1e-9))
    sigh = mouth(sigh, ((600, 250, 1.0), (1100, 350, .4))) * .22
    sig = air + voice + click * .15 + catch * .2 + exhale + sigh
    sig = sig / np.abs(sig).max()
    # Close to her: almost dry, a touch of the glade around it.
    write('S_Awaken_Gasp', hall(sig, .5, .08, 13, 8000), .85)


SOURCES = ROOT / 'Saved/AudioSources/freesound_cc0'


def load_source(name):
    # Freesound previews converted to 44.1 kHz mono WAV with ffmpeg.
    with wave.open(str(SOURCES / (name + '.wav'))) as w:
        return np.frombuffer(w.readframes(w.getnframes()), '<i2') / 32768


def denoise(x, strength=1.6, floor=.08):
    """Spectral gate: learn the room hiss from the quietest frames and subtract it."""
    hop, size = 512, 2048
    window = np.hanning(size)
    pad = np.concatenate((np.zeros(size), x, np.zeros(size)))
    frames = np.array([pad[i:i + size] * window for i in range(0, len(pad) - size, hop)])
    spec = np.fft.rfft(frames, axis=1)
    mag = np.abs(spec)
    energy = mag.sum(1)
    noise = np.median(mag[energy <= np.percentile(energy, 25)], 0)
    gain = np.clip(1 - strength * noise / (mag + 1e-9), floor, 1)
    # Smooth the gain over time so the gate does not warble.
    gain = np.apply_along_axis(lambda g: np.convolve(g, np.ones(5) / 5, 'same'), 0, gain)
    out = np.zeros(len(pad))
    norm = np.zeros(len(pad))
    for k, frame in enumerate(np.fft.irfft(spec * gain, size, axis=1)):
        out[k * hop:k * hop + size] += frame * window
        norm[k * hop:k * hop + size] += window ** 2
    return (out / np.maximum(norm, 1e-6))[size:size + len(x)]


def clip(x, start, end, fade_in=.01, fade_out=.04):
    seg = x[int(start * RATE):int(end * RATE)].copy()
    a, b = int(fade_in * RATE), int(fade_out * RATE)
    seg[:a] *= np.linspace(0, 1, a)
    seg[-b:] *= np.linspace(1, 0, b)
    return seg


def gasp():
    """Physis's first breath on waking, from real recordings (both CC0, freesound.org):
    #535243 "female sharp inhale sounds" by marythewitch (inhales recorded for surfacing from
    drowning) gives the gasp itself; #234335 "Breath" by mcroce gives the shaky breathing after it.
    The gasp is the deepest, loudest of the eight inhales; a held beat follows, then her breath
    settles in the second recording, fading out as she lies still."""
    inhales = denoise(band(load_source('535243_marythewitch_sharp_inhales'), 70, 16000))
    breaths = denoise(band(load_source('234335_mcroce_breath'), 70, 16000))
    gulp = clip(inhales, 8.97, 9.68, .006, .06)
    after = clip(breaths, 2.25, 8.85, .05, 1.8)
    gulp /= np.abs(gulp).max()
    # The breathing after it sits well under the gasp (about -9 dB at its peaks).
    after *= .36 / np.abs(after).max()
    hold = np.zeros(int(.55 * RATE))
    sig = np.concatenate((np.zeros(int(.02 * RATE)), gulp, hold, after))
    write('S_Awaken_Gasp', hall(sig, .5, .06, 13, 9000), .85)


def splash():
    """Entering deep water: a body-sized splash, then bubbles."""
    t = t_(1.6)
    burst = band(rng.normal(size=len(t)), 300, 9000) * np.exp(-t * 7) * np.clip(t / .01, 0, 1)
    low = band(rng.normal(size=len(t)), 60, 500) * np.exp(-t * 4) * .8
    track = np.stack((burst + low, burst * .9 + low), 1)
    for k in range(26):
        f = rng.uniform(500, 1600)
        tt = t_(.06)
        bubble = np.sin(2 * np.pi * f * (1 + 2.5 * tt) * tt) * np.exp(-tt * 60)
        place(track, bubble, rng.uniform(.08, .9), rng.uniform(.05, .18), rng.uniform(-.6, .6))
    write('S_Splash', hall(track, .8, .2, 14, 7000), .8)


def heartbeat():
    seconds = 3.0
    track = np.zeros((int(seconds * RATE), 2))
    t = t_(.25)
    thump = np.sin(2 * np.pi * (55 * t - 40 * t * t)) * np.exp(-t * 22)
    for at in (0, .32, 1.4, 1.72):
        place(track, thump, at + .1, 1.0 if at in (0, 1.4) else .6)
    write('S_Awaken_Heart', track, .9)


def settle():
    """Settle: a deep pulse that spreads out, then calm glass shimmer."""
    seconds = 3.5
    t = t_(seconds)
    sub = np.sin(2 * np.pi * (70 * t - 8 * t * t)) * np.exp(-t * 2.2)
    swell = band(rng.normal(size=len(t)), 200, 2400) * np.exp(-((t - .25) / .25) ** 2) * .5
    track = np.stack((sub + swell, sub + swell), 1)
    for k, f in enumerate((523.3, 659.3, 784, 1046.5, 1318.5)):
        place(track, bell(f, 2.8, 1.6), .18 + k * .06, .35, (k - 2) / 2.5)
    write('S_Settle', hall(track, 3, .7, 6), .9)


def mend():
    """Mend: warm healing bloom rising through a major chord."""
    seconds = 3.2
    track = np.zeros((int(seconds * RATE), 2))
    t = t_(2.8)
    for k, f in enumerate((392, 493.9, 587.3, 784, 987.8)):
        tone = (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * env(len(t), .35 + k * .05, 1.6, 1.4)
        place(track, tone, k * .07, .25, (k - 2) / 3)
    shimmer = band(rng.normal(size=len(t)), 5000, 12000) * env(len(t), .6, 1.8) * .12
    place(track, shimmer, 0, 1)
    write('S_Mend', hall(track, 2.5, .6, 7), .85)


def chime_set():
    # Lantern lit, Stillstone collected, puzzle solved, barrier dissolve, artifact bloom.
    track = np.zeros((int(2.4 * RATE), 2))
    place(track, bell(880, 2.2, 1.5), 0, .6, -.3)
    place(track, bell(1318.5, 2.0, 1.7), .05, .4, .3)
    write('S_Lantern', hall(track, 2, .5, 8), .8)

    track = np.zeros((int(2.6 * RATE), 2))
    for k, f in enumerate((659.3, 830.6, 987.8, 1318.5)):
        place(track, bell(f, 2.0, 2.2), k * .09, .5, (k - 1.5) / 2)
    write('S_Stillstone', hall(track, 2, .6, 9), .85)

    track = np.zeros((int(4.0 * RATE), 2))
    for k, f in enumerate((523.3, 587.3, 659.3, 784, 880, 1046.5)):
        place(track, bell(f, 3, 1.4), k * .12, .45, (k - 2.5) / 3)
    for f in (261.6, 392, 523.3):
        tt = t_(3.2)
        place(track, np.sin(2 * np.pi * f * tt) * env(len(tt), .3, 2.2), .7, .25)
    write('S_PuzzleSolved', hall(track, 3, .6, 10), .85)

    seconds = 2.2
    t = t_(seconds)
    track = np.zeros((len(t), 2))
    for k in range(70):
        place(track, bell(rng.uniform(2000, 6500), .5, rng.uniform(6, 12), ((1, 1), (1.6, .4))), rng.uniform(0, .9), rng.uniform(.05, .2), rng.uniform(-1, 1))
    hiss = band(rng.normal(size=len(t)), 1500, 9000) * np.exp(-t * 3) * .4
    place(track, hiss, 0, 1)
    write('S_BarrierDissolve', hall(track, 1.6, .5, 11), .85)

    seconds = 9
    track = np.zeros((int(seconds * RATE), 2))
    t = t_(7.5)
    for k, f in enumerate((130.8, 196, 261.6, 329.6, 392, 523.3, 659.3)):
        tone = sum(a * np.sin(2 * np.pi * f * m * t + rng.uniform(0, 6)) for m, a in ((1, 1), (2, .35), (3, .15)))
        place(track, tone * env(len(t), 1.2 + k * .25, 3.5, 1.4), k * .18, .2, (k - 3) / 4)
    for k in range(24):
        place(track, bell(rng.choice([1046.5, 1318.5, 1568, 2093]), 3, 1.2), 1.5 + k * .22, .12, rng.uniform(-1, 1))
    write('S_Artifact', hall(track, 4, .8, 12), .9)


def creature_calls():
    for v in range(3):
        seconds = 2.0
        t = t_(seconds)
        base = (520, 760, 330)[v]
        glide = base * (1 + .3 * np.sin(2 * np.pi * t * (.7 + v * .3)) * np.exp(-t))
        ph = np.cumsum(glide) / RATE * 2 * np.pi
        voice = (np.sin(ph) + .3 * np.sin(2.01 * ph) + .12 * np.sin(3.02 * ph)) * env(len(t), .12, 1.2, 1.3)
        write('S_Creature_Call%d' % v, hall(voice, 2.4, .7, 20 + v), .7)
    # The sky whale's song: very low, slow, enormous.
    seconds = 9
    t = t_(seconds)
    glide = 90 * (1 + .35 * np.sin(2 * np.pi * t / 9) + .1 * np.sin(2 * np.pi * t * .9))
    ph = np.cumsum(glide) / RATE * 2 * np.pi
    song = (np.sin(ph) + .5 * np.sin(2 * ph) + .3 * np.sin(3 * ph) + .2 * np.sin(5 * ph)) * env(len(t), 2.5, 3.5, 1.5)
    write('S_Whale_Song', hall(song, 6, 1.0, 30, 2500), .8)
    # Enemy cries for the crystal hunters (bright, dissonant) and the Sentinel (huge).
    t = t_(1.2)
    cry = sum(np.sin(2 * np.pi * f * t * (1 + .05 * np.sin(2 * np.pi * 30 * t))) for f in (880, 932, 1397)) * env(len(t), .02, .8)
    write('S_Shard_Cry', hall(cry, 1.2, .4, 31), .7)
    t = t_(3.5)
    roar = sum(a * np.sin(2 * np.pi * f * t + 3 * np.sin(2 * np.pi * 2.5 * t)) for f, a in ((55, 1), (58.3, .8), (110, .5), (164.8, .3)))
    roar += band(rng.normal(size=len(t)), 80, 900) * .6
    write('S_Sentinel_Roar', hall(roar * env(len(t), .3, 1.8), 3, .6, 32, 3000), .85)
    # Looping beds for ambient sound actors: a few calls spread over half a minute, then silence.
    for v in range(3):
        seconds = 30
        bed = np.zeros((int(seconds * RATE), 2))
        for k in range(4 + v):
            base = rng.uniform(300, 900)
            t = t_(rng.uniform(1.2, 2.4))
            glide = base * (1 + .25 * np.sin(2 * np.pi * t * rng.uniform(.5, 1.4)) * np.exp(-t))
            ph = np.cumsum(glide) / RATE * 2 * np.pi
            call = (np.sin(ph) + .3 * np.sin(2.01 * ph)) * env(len(t), .1, .9, 1.3)
            place(bed, call, rng.uniform(0, seconds - 3), rng.uniform(.4, 1.0), rng.uniform(-.7, .7))
        write('S_Creature_Loop%d' % v, loopable(hall(bed, 2.4, .7, 50 + v), 2), .6)
    seconds = 60
    bed = np.zeros((int(seconds * RATE), 2))
    t = t_(9)
    for at in (5, 31):
        glide = rng.uniform(75, 100) * (1 + .35 * np.sin(2 * np.pi * t / 9) + .1 * np.sin(2 * np.pi * t * .9))
        ph = np.cumsum(glide) / RATE * 2 * np.pi
        song = (np.sin(ph) + .5 * np.sin(2 * ph) + .3 * np.sin(3 * ph) + .2 * np.sin(5 * ph)) * env(len(t), 2.5, 3.5, 1.5)
        place(bed, song, at, 1.0, rng.uniform(-.4, .4))
    write('S_Whale_Loop', loopable(hall(bed, 6, 1.0, 60, 2500), 3), .8)


# ---------------------------------------------------------------- music (SoundFont)

FLUTE, OBOE, CLARINET, HARP, PIANO, CELESTA, VIOLIN, STRINGS, SLOW_STR, CELLO, BASS = 73, 68, 71, 46, 0, 8, 40, 48, 49, 42, 43
HORN, CHOIR, OOHS, PAD_WARM, PAD_HALO, TIMPANI = 60, 52, 53, 89, 94, 47


class Score:
    def __init__(self, beat):
        self.events, self.beat = [], beat
        self.r = random.Random(5)

    def note(self, program, key, start, beats, velocity):
        velocity = max(1, min(127, int(velocity + self.r.uniform(-5, 5))))
        self.events.append((program, int(key), start * self.beat + self.r.uniform(0, .015), beats * self.beat, velocity))


def render(font, score, tail=8.0):
    total = int((max(e[2] + e[3] for e in score.events) + tail) * RATE)
    out = np.zeros((total, 2), np.float32)
    cache = {}
    for program, key, start, length, velocity in score.events:
        token = (program, key, velocity // 8, round(length, 2))
        if token not in cache:
            cache[token] = sf.render_note(font, 0, program, key, velocity // 8 * 8 + 4, length)
        sound = cache[token]
        at = int(start * RATE)
        end = min(at + len(sound), total)
        out[at:end] += sound[:end - at]
    return out


# D Lydian: dreamy, bright, a little strange — the Center's own colour.
LYD = (0, 2, 4, 6, 7, 9, 11)
PROG = ((50, (0, 4, 7, 11)), (52, (0, 4, 7, 9)), (47, (0, 3, 7, 10)), (55, (0, 4, 7, 11)),
        (50, (0, 4, 7, 14)), (45, (0, 5, 7, 12)), (52, (0, 4, 7, 11)), (54, (0, 3, 7, 10)))
MELODY = (((0, 74, 3), (3, 76, 1)), ((0, 78, 2), (2, 81, .5), (2.5, 80, .5), (3, 76, 1)), ((0, 74, 4),), ((0, 71, 2), (2, 73, 2)),
          ((0, 74, 1.5), (1.5, 78, .5), (2, 81, 2)), ((0, 83, 3), (3, 81, 1)), ((0, 80, 2), (2, 78, 2)), ((0, 76, 4),))


def center_music():
    font = sf.SoundFont(str(ROOT / 'Art/Audio/SoundFont/MuseScore_General.sf3'))
    score = Score(60 / 66)
    bar = 0
    # 6 passes through the 8-bar cycle, each with a different colour; ~3.5 minutes, loops.
    plan = ((PAD_HALO, None, 0), (HARP, CELESTA, 1), (FLUTE, None, 2), (VIOLIN, CLARINET, 3), (OBOE, None, 2), (PIANO, None, 1))
    for cycle, (lead, double, heat) in enumerate(plan):
        for i, ((root, chord), notes) in enumerate(zip(PROG, MELODY)):
            start = bar * 4
            loud = (40, 52, 62, 74)[heat]
            for k, step in enumerate(chord):
                score.note(SLOW_STR if heat else OOHS, root + step, start, 4.1, loud - 14)
                if heat >= 2:
                    score.note(CHOIR, root + 12 + step, start, 4.1, loud - 24)
            score.note(CELLO, root - 12, start, 4, loud - 12)
            if heat >= 3:
                score.note(BASS, root - 24, start, 4, loud - 16)
                score.note(HORN, root + chord[1], start, 4, loud - 22)
            # Harp / celesta arpeggios carry the motion in every pass but the first.
            if cycle:
                pattern = [root + 12 + chord[j % len(chord)] + 12 * (j // len(chord)) for j in range(8)]
                for j, key in enumerate(pattern):
                    score.note(HARP if j % 2 == 0 else CELESTA, key, start + j * .5, 1.2, 46 + 4 * heat)
            if cycle not in (0,):
                for when, key, beats in notes:
                    score.note(lead, key, start + when, beats, loud + 6)
                    if double:
                        score.note(double, key - 12, start + when, beats, loud - 6)
            else:
                for when, key, beats in notes[:1]:
                    score.note(CELESTA, key + 12, start + when, 2, 40)
            bar += 1
    mix = render(font, score)
    mix = hall(mix, 4.0, .65, 40, 7000)
    mix = loopable(mix, 4)
    write('S_Music_Center', mix, .85)


# ---------------------------------------------------------------- orchestral exploration score

# General MIDI programs used as orchestra sections.
O_VLN, O_VLA, O_VC, O_CB, O_TREM, O_PIZZ, O_HARP, O_TIMP = 40, 41, 42, 43, 44, 45, 46, 47
O_STR, O_STR_SLOW, O_CHOIR, O_OOHS = 48, 49, 52, 53
O_TPT, O_TBN, O_TUBA, O_HORN = 56, 57, 58, 60
O_OBOE, O_ENG, O_BSN, O_CLAR, O_FLUTE, O_CEL, O_GLOCK = 68, 69, 70, 71, 73, 8, 9
# Concert seating, left (-1) to right (+1): violins left, cellos and basses right, winds centre.
SEAT = {O_VLN: -.5, O_STR: -.25, O_STR_SLOW: -.2, O_TREM: -.3, O_VLA: .15, O_VC: .4, O_CB: .55, O_PIZZ: .45,
        O_HARP: -.65, O_CEL: .6, O_GLOCK: .5, O_TIMP: .05, O_CHOIR: 0, O_OOHS: 0,
        O_HORN: -.35, O_TPT: .15, O_TBN: .35, O_TUBA: .45, O_FLUTE: -.1, O_OBOE: .05, O_CLAR: -.05, O_ENG: .1, O_BSN: .2}
# Sections played by many players get a second, slightly late copy so they sound like a section.
ENSEMBLE = {O_VLN, O_STR, O_STR_SLOW, O_TREM, O_VLA, O_VC, O_CB, O_CHOIR, O_OOHS, O_HORN}


class Orchestra:
    """A score with per-note dynamics shapes and stereo seating."""

    def __init__(self, bpm):
        self.beat = 60 / bpm
        self.events = []
        self.r = random.Random(17)

    def note(self, program, key, start, beats, velocity, shape='flat', gain=1.0):
        velocity = max(1, min(127, int(velocity + self.r.uniform(-3, 3))))
        self.events.append((program, int(key), start * self.beat + self.r.uniform(0, .012), beats * self.beat, velocity, shape, gain))


def dynamics(n, shape, length):
    x = np.linspace(0, 1, n)
    body = min(1, length * RATE / max(n, 1))
    x = np.clip(x / max(body, 1e-6), 0, 1)
    if shape == 'swell':      # a phrase that breathes: rises to the middle, eases off
        return .55 + .45 * np.sin(np.pi * np.clip(x, 0, 1)) ** .8
    if shape == 'cresc':
        return .35 + .65 * x ** 1.4
    if shape == 'dim':
        return 1 - .65 * x ** .8
    return np.ones(n)


def perform(font, orch, tail=8.0):
    total = int((max(e[2] + e[3] for e in orch.events) + tail) * RATE)
    out = np.zeros((total, 2), np.float32)
    cache = {}
    # The SoundFont's instruments differ in level by up to 10x; even them out so the score's
    # velocities alone set the balance.
    level = {}
    for program in set(e[0] for e in orch.events):
        probe = sf.render_note(font, 0, program, 45 if program == O_TIMP else 62, 84, 1.0)
        level[program] = .03 / max(float(np.sqrt((probe ** 2).mean())), 1e-4)
    for program, key, start, length, velocity, shape, lift in orch.events:
        token = (program, key, velocity // 8, round(length, 2))
        if token not in cache:
            stereo = sf.render_note(font, 0, program, key, velocity // 8 * 8 + 4, length)
            cache[token] = (stereo.mean(1) * level[program]).astype(np.float32)
        mono = cache[token] * dynamics(len(cache[token]), shape, length).astype(np.float32) * lift
        copies = ((0, SEAT.get(program, 0)),)
        if program in ENSEMBLE:
            copies = ((0, SEAT.get(program, 0) - .08), (int(.018 * RATE), SEAT.get(program, 0) + .08))
        for delay, pan in copies:
            angle = (np.clip(pan, -1, 1) + 1) * np.pi / 4
            at = int(start * RATE) + delay
            end = min(at + len(mono), total)
            gain = 1 / len(copies) ** .5
            out[at:end, 0] += mono[:end - at] * np.cos(angle) * gain
            out[at:end, 1] += mono[:end - at] * np.sin(angle) * gain
    return out


def level_ride(mix, keep_db):
    """Slow compression: loudness is measured over ~3 s and anything above the quietest
    passages by more than `keep_db` is drawn back, so the intro and the climax both carry in game."""
    hop = RATE // 4
    frames = len(mix) // hop + 1
    rms = np.array([np.sqrt((mix[i * hop:(i + 1) * hop] ** 2).mean() + 1e-12) for i in range(frames)])
    smooth = np.convolve(rms, np.ones(12) / 12, 'same')
    db = 20 * np.log10(smooth + 1e-9)
    floor = np.percentile(db, 10)
    over = np.clip(db - floor - keep_db, 0, None)
    under = np.clip(floor + 4 - db, 0, None)
    gain_db = -over * .75 + under * .6
    gain = 10 ** (np.interp(np.arange(len(mix)) / hop, np.arange(frames), gain_db) / 20)
    return mix * gain[:, None]


def voicing(root, chord, low, high, near):
    """Chord tones stacked upward from the tone nearest `near`, all within [low, high]."""
    tones = sorted(set(c % 12 for c in chord))
    pool = [k for k in range(low, high + 1) if (k - root) % 12 in tones]
    start = min(pool, key=lambda k: abs(k - near))
    chosen = [k for k in pool if k >= start][:len(tones)]
    while len(chosen) < len(tones):
        chosen.insert(0, max(k for k in pool if k < chosen[0]))
    return chosen


# The Center theme (D Lydian, the raised G# gives it its floating colour).
THEME_A = (((0, 62, 2), (2, 64, 1), (3, 66, 1)), ((0, 69, 3), (3, 68, 1)), ((0, 66, 2), (2, 64, 1), (3, 62, 1)), ((0, 64, 4),),
           ((0, 62, 1), (1, 66, 1), (2, 69, 2)), ((0, 71, 2), (2, 73, 1), (3, 69, 1)), ((0, 68, 2), (2, 66, 2)), ((0, 62, 4),))
CHORDS_A = ((50, (0, 4, 7, 11)), (52, (0, 4, 7, 14)), (47, (0, 3, 7, 10)), (45, (0, 4, 7, 14)),
            (50, (0, 4, 7, 16)), (43, (0, 4, 7, 11, 18)), (52, (0, 4, 7, 11)), (50, (0, 7, 11, 16)))
# The answering theme, higher and more open.
THEME_B = (((0, 69, 1), (1, 74, 1), (2, 76, 2)), ((0, 78, 3), (3, 76, .5), (3.5, 74, .5)), ((0, 73, 2), (2, 71, 2)), ((0, 68, 1), (1, 69, 1), (2, 71, 2)),
           ((0, 74, 1), (1, 78, 1), (2, 81, 2)), ((0, 80, 2), (2, 78, 1), (3, 76, 1)), ((0, 78, 1.5), (1.5, 76, .5), (2, 73, 2)), ((0, 74, 4),))
CHORDS_B = ((50, (0, 4, 7, 11)), (47, (0, 3, 7, 10)), (54, (0, 3, 7, 10)), (52, (0, 4, 7, 14)),
            (50, (0, 4, 7, 14)), (52, (0, 4, 7, 11)), (45, (0, 4, 7, 10)), (50, (0, 4, 7, 11, 18)))
# Night: the shadowed middle, B minor turning to the Lydian light again.
CHORDS_N = ((47, (0, 3, 7)), (43, (0, 4, 7, 11)), (40, (0, 3, 7, 10)), (42, (0, 4, 7, 10)),
            (47, (0, 3, 7, 14)), (43, (0, 4, 7, 18)), (45, (0, 5, 7)), (45, (0, 4, 7, 10)))
NIGHT_HORN = (((0, 59, 3), (3, 62, 1)), ((0, 66, 4),), ((0, 64, 2), (2, 62, 2)), ((0, 61, 4),),
              ((0, 59, 2), (2, 66, 2)), ((0, 68, 4),), ((0, 69, 2), (2, 71, 2)), ((0, 73, 4),))


def strings_bed(o, bar, chords, loud, shape='swell', program=O_STR_SLOW, top=79):
    near = 66
    for i, (root, chord) in enumerate(chords):
        at = (bar + i) * 4
        notes = voicing(root, chord, 57, top, near)
        near = notes[0]
        for k in notes:
            o.note(program, k, at, 4.05, loud, shape)
        o.note(O_VLA, voicing(root, chord, 50, 62, 55)[0], at, 4.05, loud - 8, shape)
        o.note(O_VC, root if root < 50 else root - 12, at, 4.05, loud, shape)
        o.note(O_CB, (root if root < 50 else root - 12) - 12, at, 4.05, loud - 10, shape)


def melody(o, bar, theme, program, loud, shift=0, double=None, double_shift=-12, shape='swell', lead=2.6):
    # `lead` lifts the tune above the accompaniment (measured: about +4 dB over the rest).
    for i, notes in enumerate(theme):
        for when, key, beats in notes:
            o.note(program, key + shift, (bar + i) * 4 + when, beats + .05, loud, shape if beats >= 2 else 'flat', lead)
            if double:
                o.note(double, key + shift + double_shift, (bar + i) * 4 + when, beats + .05, loud - 8, shape if beats >= 2 else 'flat', lead * .7)


def harp_rolls(o, bar, chords, loud, every=.5, octave=12):
    for i, (root, chord) in enumerate(chords):
        tones = voicing(root, chord, 50 + octave, 90, 62 + octave)
        run = tones + [t + 12 for t in tones]
        steps = int(4 / every)
        for j in range(steps):
            o.note(O_HARP, run[j % len(run)], (bar + i) * 4 + j * every, 1.6, loud - 6 * (j % 2))


def ostinato(o, bar, chords, program, loud, low=70):
    # Eighth-note arpeggio figure, rising and falling, the walking pulse of the explorer.
    for i, (root, chord) in enumerate(chords):
        tones = voicing(root, chord, low, low + 16, low + 4)
        figure = (tones + tones[-2:0:-1])
        for j in range(8):
            o.note(program, figure[j % len(figure)], (bar + i) * 4 + j * .5, .55, loud - (4 if j % 2 else 0))


def center_orchestral():
    """The Center's exploration music, a full orchestra (~3.7 min, loops):
    intro of tremolo strings, harp and celesta; theme A on solo horn; theme B on violins with an oboe
    answer; the night section (B minor, low horns, timpani); theme A again on cellos over a walking
    clarinet figure; the tutti climax; theme B in flutes and violins; and an oboe coda leading back."""
    font = sf.SoundFont(str(ROOT / 'Art/Audio/SoundFont/MuseScore_General.sf3'))
    o = Orchestra(70)
    # 1. Intro (bars 0-7): shimmering strings, harp, celesta glints, a flute hint of the theme.
    for i, (root, chord) in enumerate(CHORDS_A):
        at = i * 4
        for k in voicing(root, chord, 66, 86, 74):
            o.note(O_TREM, k, at, 4.05, 34 + 3 * (i % 4), 'swell')
        o.note(O_CB, root - 12 if root >= 47 else root, at, 4.05, 36, 'swell')
        o.note(O_CEL, voicing(root, chord, 81, 96, 86)[i % 3], at + 1.5, 2, 44)
        o.note(O_CEL, voicing(root, chord, 81, 96, 86)[(i + 2) % 3], at + 3, 1, 38)
    harp_rolls(o, 4, CHORDS_A[4:], 42, every=1)
    melody(o, 4, THEME_A[:3], O_FLUTE, 54, shift=12)
    # 2. Theme A, solo horn over strings and harp (bars 8-15).
    strings_bed(o, 8, CHORDS_A, 50)
    harp_rolls(o, 8, CHORDS_A, 46)
    melody(o, 8, THEME_A, O_HORN, 78)
    # 3. Theme B, violins with the oboe answering at phrase ends (bars 16-23).
    strings_bed(o, 16, CHORDS_B, 56)
    harp_rolls(o, 16, CHORDS_B, 48)
    melody(o, 16, THEME_B, O_VLN, 80, double=O_FLUTE, double_shift=12, lead=3.6)
    for i, key in ((3, 81), (7, 78)):
        o.note(O_OBOE, key, (16 + i) * 4 + 2, 2, 66, 'swell')
    o.note(O_CEL, 86, 23 * 4, 4, 46)
    # 4. Night (bars 24-31): tremolo low strings, horns, timpani, the choir far off.
    for i, (root, chord) in enumerate(CHORDS_N):
        at = (24 + i) * 4
        for k in voicing(root, chord, 47, 66, 54):
            o.note(O_TREM, k, at, 4.05, 50 + 2 * i, 'cresc' if i % 2 == 0 else 'swell')
        o.note(O_VC, root, at, 4.05, 58, 'swell')
        o.note(O_CB, root - 12, at, 4.05, 56, 'swell')
        for k in voicing(root, chord, 62, 76, 69):
            o.note(O_OOHS, k, at, 4.05, 40 + 3 * i, 'swell')
        if i % 2 == 0:
            o.note(O_TIMP, root if root >= 40 else root + 12, at, 1.5, 54 + 4 * i)
        o.note(O_BSN, voicing(root, chord, 45, 57, 50)[1], at + 2, 2, 48)
    melody(o, 24, NIGHT_HORN, O_HORN, 74, double=O_HORN, double_shift=-5)
    o.note(O_TIMP, 45, 31 * 4, 4, 70, 'cresc')
    o.note(O_TIMP, 45, 31 * 4 + 3.5, .5, 84)
    # 5. Theme A on cellos and bassoon over a walking clarinet figure and pizzicato (bars 32-39).
    for i, (root, chord) in enumerate(CHORDS_A):
        at = (32 + i) * 4
        for k in voicing(root, chord, 62, 78, 69):
            o.note(O_STR_SLOW, k, at, 4.05, 46, 'swell')
        o.note(O_PIZZ, root - 12 if root >= 47 else root, at, 1, 64)
        o.note(O_PIZZ, (root - 12 if root >= 47 else root) + 7, at + 2, 1, 56)
    ostinato(o, 32, CHORDS_A, O_CLAR, 56)
    melody(o, 32, THEME_A, O_VC, 82, shift=-12, double=O_BSN, double_shift=0, lead=3.8)
    # 6. Climax (bars 40-47): theme A in full, violins and flutes above, horns in harmony, brass,
    #    choir, timpani.
    strings_bed(o, 40, CHORDS_A, 74, program=O_STR, top=84)
    harp_rolls(o, 40, CHORDS_A, 60, every=.25, octave=12)
    melody(o, 40, THEME_A, O_VLN, 96, shift=12, double=O_FLUTE, double_shift=12)
    melody(o, 40, THEME_A, O_HORN, 86)
    for i, (root, chord) in enumerate(CHORDS_A):
        at = (40 + i) * 4
        for k in voicing(root, chord, 50, 64, 55):
            o.note(O_TBN, k, at, 4.05, 66, 'swell')
        o.note(O_TUBA, root - 12 if root >= 47 else root, at, 4.05, 64, 'swell')
        for k in voicing(root, chord, 69, 81, 74):
            o.note(O_CHOIR, k, at, 4.05, 66, 'swell')
        o.note(O_TIMP, 38 if root % 12 in (2, 9) else 45, at, 1, 80)
        if i % 2:
            o.note(O_TIMP, 45 if root % 12 in (2, 9) else 38, at + 2.5, .5, 66)
            o.note(O_TIMP, 45 if root % 12 in (2, 9) else 38, at + 3, 1, 72)
    o.note(O_TPT, 74, 44 * 4, 4, 74, 'swell')
    o.note(O_TPT, 78, 45 * 4, 4, 78, 'swell')
    o.note(O_TPT, 81, 46 * 4, 4, 82, 'swell')
    o.note(O_GLOCK, 86, 47 * 4, 3, 60)
    # 7. Theme B, flutes and violins, the orchestra settling (bars 48-55).
    strings_bed(o, 48, CHORDS_B, 60, program=O_STR)
    harp_rolls(o, 48, CHORDS_B, 50)
    melody(o, 48, THEME_B, O_FLUTE, 74, double=O_VLN, double_shift=0)
    ostinato(o, 48, CHORDS_B[:4], O_CLAR, 48, low=62)
    for i, (root, chord) in enumerate(CHORDS_B):
        o.note(O_HORN, voicing(root, chord, 57, 69, 62)[1], (48 + i) * 4, 4.05, 54, 'swell')
    # 8. Coda (bars 56-63): oboe sings the first phrase alone, strings fade, celesta, back to the start.
    for i, (root, chord) in enumerate(CHORDS_A):
        at = (56 + i) * 4
        fade = 50 - 2 * i
        for k in voicing(root, chord, 62, 81, 69):
            o.note(O_STR_SLOW, k, at, 4.05, fade, 'dim' if i == 7 else 'swell')
        o.note(O_CB, root - 12 if root >= 47 else root, at, 4.05, fade - 6, 'swell')
        o.note(O_CEL, voicing(root, chord, 81, 96, 86)[i % 3], at + 2, 2, 40)
    melody(o, 56, THEME_A[:4], O_OBOE, 70, lead=3.4)
    melody(o, 60, THEME_A[4:], O_ENG, 62, shape='dim', lead=3.4)
    mix = perform(font, o)
    # A large hall: the orchestra sounds far off in the night, not in a room.
    mix = hall(mix, 3.6, .55, 44, 8500)
    # Gentle bus glue: a soft limiter so the climax and the intro sit at a usable level together.
    mix = mix / np.abs(mix).max()
    mix = level_ride(mix, 9.0)
    mix = mix / np.abs(mix).max()
    mix = np.tanh(mix * 1.6) / np.tanh(1.6)
    mix = loopable(mix, 4)
    write('S_Music_Center', mix, .9)


def temple_music():
    font = sf.SoundFont(str(ROOT / 'Art/Audio/SoundFont/MuseScore_General.sf3'))
    score = Score(60 / 54)
    prog = ((38, (0, 7, 15)), (41, (0, 7, 14)), (36, (0, 7, 16)), (43, (0, 3, 7)))
    for bar in range(24):
        root, chord = prog[bar % 4]
        start = bar * 4
        for step in chord:
            score.note(OOHS, root + 12 + step, start, 4.1, 50)
            score.note(SLOW_STR, root + step, start, 4.1, 44)
        score.note(CELLO, root, start, 4, 50)
        if bar >= 4:
            for j in range(4):
                score.note(CELESTA, root + 36 + chord[j % 3], start + j + .5, 1.5, 38)
        if bar % 8 >= 4:
            score.note(FLUTE, root + 36 + chord[1], start, 3, 52)
        if bar % 4 == 0:
            score.note(TIMPANI, root, start, 2, 38)
    mix = hall(render(font, score), 6.0, .9, 41, 5000)
    write('S_Music_Temple', loopable(mix, 4), .8)


def awakening_music():
    """Cue for the 30 s awakening: silence and heartbeat, the breath, then the reveal swell."""
    font = sf.SoundFont(str(ROOT / 'Art/Audio/SoundFont/MuseScore_General.sf3'))
    score = Score(60 / 60)
    # 0-6 s: almost nothing. 6 s: breath (separate sfx). 9-30 s: rise and bloom on D Lydian.
    for k, key in enumerate((62, 69, 74)):
        score.note(OOHS, key, 1 + k, 7, 30)
    seq = ((50, (0, 7, 16, 18)), (55, (0, 4, 11, 16)), (52, (0, 4, 7, 14)), (50, (0, 4, 7, 11, 16, 19)))
    for b, (root, chord) in enumerate(seq):
        start = 8 + b * 5
        loud = 50 + b * 16
        for step in chord:
            score.note(SLOW_STR, root + step, start, 5.2, loud - 8)
            score.note(CHOIR, root + 12 + step, start, 5.2, loud - 16)
        score.note(CELLO, root - 12, start, 5, loud)
        score.note(BASS, root - 24, start, 5, loud - 6)
        for j in range(10):
            score.note(HARP, root + 12 + chord[j % len(chord)] + 12 * (j // len(chord)), start + j * .5, 1.5, 54 + b * 8)
        if b >= 2:
            score.note(HORN, root + chord[2], start, 5, loud - 10)
            score.note(TIMPANI, root - 12, start, 1, loud)
    for when, key, beats in ((18, 81, 2), (20, 83, 1), (21, 85, 1), (22, 86, 4), (26, 88, 4)):
        score.note(VIOLIN, key, when, beats, 92)
        score.note(FLUTE, key, when, beats, 80)
    mix = hall(render(font, score, 6), 4.5, .8, 42, 7500)
    write('S_Music_Awakening', mix, .9)


if __name__ == '__main__':
    parts = sys.argv[1:] or ['sfx', 'music', 'cine']
    if 'gasp' in parts:
        gasp()
    if 'splash' in parts:
        splash()
    if 'orchestra' in parts:
        center_orchestral()
    if 'sfx' in parts:
        ambience()
        temple_ambience()
        breath()
        gasp()
        heartbeat()
        settle()
        mend()
        chime_set()
        creature_calls()
    if 'cine' in parts:
        awakening_music()
    if 'music' in parts:
        center_orchestral()
        temple_music()
