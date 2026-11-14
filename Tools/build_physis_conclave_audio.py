"""Music, sound effects and ambience for the Conclave (level 3).

Run with the Kokoro venv's packages from the project folder; the Commons ambience speaks its distant
murmur with Kokoro, so give it the espeak of the voice memory (kokoro-voice-workaround):
  E=~/PhysisProject/Saved/AudioTools/espeak; cd ~/PhysisProject && ESPEAK_DATA_PATH=$E/espeak-ng-data \
  ESPEAK_LIB=$E/lib/libespeak-ng.so.1 ESPEAK_DATA=$E/espeak-ng-data LD_LIBRARY_PATH=$E/lib \
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/build_physis_conclave_audio.py [parts]
Parts: music, sfx, amb (all three when none is given) or single sounds by name (S_LightStep ...).
--out DIR writes elsewhere; --excerpt SECONDS [--from-bar N] renders only that much of the music, as
S_Music_Conclave_Excerpt, for listening tests (it needs --out, so the import folder stays clean).
Music renders through Art/Audio/SoundFont/MuseScore_General.sf3 with the Center's orchestra
(Tools/build_physis_center_audio.py: Orchestra, perform with its per-program level normalisation, the
score helpers and level_ride; hall() is a copy with its echo fixed) and is held to the Center's loudness.
Writes Art/Audio/Conclave/*.wav, 44.1 kHz stereo 16-bit, which `conclave:audio` imports to
/Game/Conclave/Audio. The music and the S_Amb_* beds loop without a seam; the effects ring out and end in
silence. Each sound draws from its own seed, so building one alone gives the same file as building all.
"""
import os
import pathlib
import re
import subprocess
import sys
import wave
import zlib

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_physis_center_audio as center  # noqa: E402
import physis_soundfont as sf  # noqa: E402
from build_physis_center_audio import (O_BSN, O_CB, O_CEL, O_CHOIR, O_CLAR, O_FLUTE, O_GLOCK, O_HARP, O_HORN, O_OBOE,  # noqa: E402
                                       O_OOHS, O_PIZZ, O_STR, O_STR_SLOW, O_TBN, O_TIMP, O_TREM, O_TUBA, O_VC, O_VLA, O_VLN,
                                       Orchestra, band, bell, env, harp_rolls, level_ride, melody, ostinato, perform,
                                       place, size_up, strings_bed, t_, voicing)

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'Art/Audio/Conclave'
SOUNDFONT = ROOT / 'Art/Audio/SoundFont/MuseScore_General.sf3'
RATE = 44100
rng = np.random.default_rng(23)


def reseed(name):
    """Gives each sound its own random draws (noise, phases, timings; bell() draws from the Center module's
    generator), so a sound comes out the same whether it is built alone or after others."""
    global rng
    seed = zlib.crc32(name.encode())
    rng = np.random.default_rng(seed)
    center.rng = np.random.default_rng(seed + 1)


def hall(signal, seconds=3.0, wet=.5, seed=1, bright=6000):
    """The Center's hall() (same noise, decay and so the same room) with its impulse response band-limited
    with silence after it: band() filters circularly, and on the bare response it wraps the loud onset onto
    the last 40 ms, a ghost of every sound `seconds` later at about -27 dB, 20 dB over the tail around it."""
    if signal.ndim == 1:
        signal = np.stack((signal, signal), 1)
    local = np.random.default_rng(seed)
    n = int(seconds * RATE)
    size = size_up(len(signal) + n)
    out = np.zeros_like(signal)
    for ch in range(2):
        tail = local.normal(size=n) * np.exp(-6.0 * np.arange(n) / n)
        tail = band(np.concatenate((tail, np.zeros(RATE // 4))), 80, bright)[:n]
        tail /= np.sqrt((tail ** 2).sum())
        out[:, ch] = signal[:, ch] + np.fft.irfft(np.fft.rfft(signal[:, ch], size) * np.fft.rfft(tail, size), size)[:len(signal)] * wet
    return out


def loudness(signal):
    """Integrated loudness (LUFS, ITU-R BS.1770) of a stereo signal, measured by ffmpeg's ebur128."""
    run = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-f', 'f32le', '-ar', str(RATE), '-ac', '2', '-i', 'pipe:0', '-af', 'ebur128', '-f', 'null', '-'],
                         input=np.ascontiguousarray(signal, '<f4').tobytes(), capture_output=True, check=True)
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', run.stderr.decode())[-1])


def write(name, signal, peak=.9, lufs=None):
    """Scales to `peak`, or for a bed to `lufs` integrated loudness as long as its peak stays under `peak`
    (beds differ in crest factor, so a common peak would leave them at very different loudness)."""
    if not np.isfinite(signal).all():
        # A NaN reaches the wav as full-scale clicks (level_ride once made one, see ride()): stop instead.
        sys.exit('%s: the signal holds NaN or inf, nothing written' % name)
    if signal.ndim == 1:
        signal = np.stack((signal, signal), 1)
    signal = signal / max(np.abs(signal).max(), 1e-9) * peak
    if lufs is not None:
        signal = signal * min(10 ** ((lufs - loudness(signal)) / 20), 1.0)
    with wave.open(str(OUT / (name + '.wav')), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((np.clip(signal, -1, 1) * 32767).astype('<i2').tobytes())
    print('wrote', name, round(len(signal) / RATE, 1), 's', round(loudness(signal), 1), 'LUFS',
          round(20 * np.log10(np.abs(signal).max()), 1), 'dBFS peak', flush=True)


def trim(signal, floor=-60):
    """Cuts the silence after a sound has rung below `floor` dB of its peak, with a short fade."""
    level = np.abs(signal).max(1) if signal.ndim == 2 else np.abs(signal)
    end = int(np.nonzero(level > level.max() * 10 ** (floor / 20))[0][-1]) + int(.05 * RATE)
    out = signal[:end].copy()
    fade = np.linspace(1, 0, min(int(.05 * RATE), len(out)))
    out[-len(fade):] *= fade[:, None] if out.ndim == 2 else fade
    return out


def finish(name, track, low, high, seconds, wet, seed, bright, peak):
    """Writes a one-shot effect: band-limited with silence either side (band() filters circularly, which would
    lay the attack's ringing over the tail), given room for its hall to ring out (hall() keeps its input's
    length, which cut the effects off while they still rang, 28 to 43 dB under their peak), and trimmed once
    the reverb has died away."""
    lead = int(.05 * RATE)
    padded = np.concatenate((np.zeros((lead, 2)), track, np.zeros((int((seconds + .5) * RATE), 2))))
    write(name, trim(hall(band(padded, low, high)[lead:], seconds, wet, seed, bright)), peak)


# ---------------------------------------------------------------- loops without seams

# The music and the beds are made exactly periodic instead of crossfaded: noise is filtered over the
# whole loop with the FFT (band() is circular), slow movement uses whole cycles per loop, events and
# reverb tails that run past the end come back in at the start.

def put(track, sound, at, gain=1.0, pan=0.0):
    """place() on a loop (same pan law): whatever runs past the end comes back in at the start."""
    if sound.ndim == 1:
        sound = np.stack((sound * np.sqrt((1 - pan) / 2), sound * np.sqrt((1 + pan) / 2)), 1) * 1.414
    i = int(at * RATE) % len(track)
    head = min(len(sound), len(track) - i)
    track[i:i + head] += sound[:head] * gain
    track[:len(sound) - head] += sound[head:] * gain


def ring(track, seconds, wet, seed, bright=6000):
    """hall() on a loop: the reverb that rings past the end folds back onto the start."""
    n = int(seconds * RATE)
    tail = hall(np.concatenate((track, np.zeros((n, 2)))), seconds, wet, seed, bright)
    out = tail[:len(track)].copy()
    out[:n] += tail[len(track):]
    return out


def fold(mix, length):
    """A rendered piece cut to `length` seconds, its tail (releases and reverb) laid over its start."""
    n = int(round(length * RATE))
    out = mix[:n].copy()
    out[:len(mix) - n] += mix[n:]
    return out


def drift(n, cycles, seed, slope=1.0):
    """A slow random curve in [-1, 1] that loops: whole cycles 1..`cycles` over n samples, random
    phases, amplitudes falling as 1/k**slope."""
    local = np.random.default_rng(seed)
    x = np.arange(n) / n
    curve = sum(local.uniform(.4, 1) / k ** slope * np.sin(2 * np.pi * k * x + local.uniform(0, 6.3)) for k in range(1, cycles + 1))
    return curve / np.abs(curve).max()


def whole(freq, n):
    """`freq` moved to the nearest whole number of cycles in n samples, so a held tone loops."""
    return max(round(freq * n / RATE), 1) * RATE / n


def noise_bed(n, low, high, seed):
    """Independent filtered noise in each ear: a wide bed that loops (band() filters circularly)."""
    local = np.random.default_rng(seed)
    return np.stack([band(local.normal(size=n), low, high) for _ in range(2)], 1)


def blend(*layers):
    """Mixes (signal, LUFS) layers at those loudnesses, so a balance holds whatever their peaks: a
    sparse chime and a steady stream differ by 15 dB in crest factor."""
    return sum(layer * 10 ** ((level - loudness(layer)) / 20) for layer, level in layers)


def wobble(n, low, high, seed):
    """Random movement between `low` and `high` Hz (flicker, gurgle, friction), scaled to [-1, 1]."""
    curve = band(np.random.default_rng(seed).normal(size=n), low, high)
    return curve / np.abs(curve).max()


# ---------------------------------------------------------------- sound sources

def sweep(path, width, seed):
    """Noise through a band-pass `width` octaves wide whose centre follows `path` (Hz per sample):
    the moving air of a whoosh. Short-time FFT frames, each with its own Gaussian band."""
    local = np.random.default_rng(seed)
    n, size, hop = len(path), 2048, 512
    window = np.hanning(size)
    noise = local.normal(size=n + 2 * size)
    octave = np.log2(np.maximum(np.fft.rfftfreq(size, 1 / RATE), 20))
    out, norm = np.zeros(len(noise)), np.zeros(len(noise))
    for i in range(0, len(noise) - size, hop):
        centre = np.log2(path[int(np.clip(i - size // 2, 0, n - 1))])
        mask = np.exp(-.5 * ((octave - centre) / (width / 2)) ** 2)
        out[i:i + size] += np.fft.irfft(np.fft.rfft(noise[i:i + size] * window) * mask, size) * window
        norm[i:i + size] += window ** 2
    return (out / np.maximum(norm, 1e-6))[size:size + n]


GLASS = ((1, 1), (2.32, .3), (4.25, .1), (6.63, .035))   # a struck crystal rod, its upper modes kept low
TUBE = ((1, 1), (2.756, .55), (5.404, .26), (8.933, .1))  # a hanging metal tube (free-free bar modes)


def chime(freq, decay, partials):
    """bell() rung until its fundamental has fallen 48 dB, then faded over 30 ms: a bell cut off while it
    still rings ends in a click."""
    seconds = 48 / 8.686 / decay
    return bell(freq, seconds, decay, partials) * np.clip((seconds - t_(seconds)) / .03, 0, 1)


def glow(freq, seconds, attack, release, seed):
    """A held tone of light: soft harmonics in two voices a few cents apart, beating slowly."""
    local = np.random.default_rng(seed)
    t = t_(seconds)
    out = np.zeros_like(t)
    for detune in (-.0016, .0016):
        for k, amp in ((1, 1), (2, .3), (3, .12), (4, .05)):
            out += amp * np.sin(2 * np.pi * freq * (1 + detune) * k * t + local.uniform(0, 6.3))
    return out * env(len(t), attack, release, 1.3)


def bubble(freq, seconds):
    """One air bubble in water (Minnaert resonance): a short sine whose pitch rises as it surfaces."""
    t = t_(seconds)
    phase = np.cumsum(freq * (1 + 1.4 * t / seconds)) / RATE * 2 * np.pi
    return np.sin(phase) * np.exp(-t / (seconds / 4)) * np.clip(t / .0015, 0, 1)


def clank(f0, seconds, seed, near=1.0):
    """Struck iron: a click of contact and a few inharmonic modes ringing down, the higher ones
    first, as plates and beams ring at irregular ratios. Far ones (`near` < 1) lose their treble."""
    local = np.random.default_rng(seed)
    t = t_(seconds)
    out = np.zeros_like(t)
    for ratio in np.concatenate(([1.0], local.uniform(1.3, 7.5, 6))):
        out += local.uniform(.3, 1) / ratio ** .8 * np.sin(2 * np.pi * f0 * ratio * t + local.uniform(0, 6.3)) * np.exp(-t * local.uniform(3, 8) * ratio ** .6)
    out += band(local.normal(size=len(t)), 700, 7000) * np.exp(-t / .003) * .5
    out *= np.clip(t / .0008, 0, 1)
    return band(out, 60, 1500 + 7000 * near)


def groan(f0, seconds, seed):
    """A huge structure flexing far off: a stiff, slowly bending resonance with a grain of friction."""
    local = np.random.default_rng(seed)
    t = t_(seconds)
    bend = f0 * (1 + .035 * np.sin(2 * np.pi * t / seconds * local.uniform(.6, 1.2) + local.uniform(0, 6.3)))
    phase = np.cumsum(bend) / RATE * 2 * np.pi
    tone = sum(amp * np.sin(ratio * phase) for ratio, amp in ((1, 1), (2.03, .45), (3.12, .25), (4.41, .12)))
    return tone * (1 + .4 * wobble(len(t), 6, 40, seed)) * env(len(t), seconds * .35, seconds * .45, 1.5)


def mallet(freq, seconds=1.8):
    """A soft wooden bar under a felt mallet: its marimba-like modes (1, 3.9, 9.2) with a rounded attack,
    ringing until the fundamental has fallen about 48 dB (0.9 s stopped it at -24 dB, a click)."""
    t = t_(seconds)
    out = sum(amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t / tau) for ratio, amp, tau in ((1, 1, .32), (3.93, .22, .09), (9.2, .04, .03)))
    return out * np.clip(t / .004, 0, 1) ** 2 * np.clip((seconds - t) / .03, 0, 1)


# ---------------------------------------------------------------- effects

def light_step():
    """Light Step: she is light for 0.15 s and her trail fades in 0.35 s. A quick airy whoosh sweeping
    up through the mids and across the stereo field, a soft breath of body as she leaves, and three
    glass notes in the middle register: crystalline, never a laser (the author rejected shrill)."""
    seconds = 1.1   # long enough for the last glass note to ring down
    t = t_(seconds)
    n = len(t)
    air = sweep(520 * 6.5 ** np.clip(t / .3, 0, 1), 1.3, 1)
    air *= np.clip(t / .045, 0, 1) ** 2 * np.exp(-np.clip(t - .09, 0, None) / .11)
    pan = np.clip((t - .02) / .24, 0, 1) * 1.3 - .65
    track = np.stack((air * np.sqrt((1 - pan) / 2), air * np.sqrt((1 + pan) / 2)), 1) * 1.414
    body = band(rng.normal(size=n), 70, 320) * np.exp(-t / .045) * np.clip(t / .006, 0, 1)
    place(track, body, 0, .5)
    for k, f in enumerate((1046.5, 1568, 2093)):
        place(track, chime(f, 5.5, GLASS), .035 + k * .028, .1 - k * .02, -.3 + k * .3)
    finish('S_LightStep', track, 50, 8500, .9, .22, 61, 7000, .85)


def pylon_wake():
    """A Spine Pylon waking: a deep hum spinning up an octave with a turbine's whirr inside it, which
    opens into a bright F major chord of glass and held light, ringing out over the drum."""
    seconds = 9.0   # the chord's glass rings to 7.5 s and the hum dies away by 9 s (it was cut off at 7 s)
    t = t_(seconds)
    n = len(t)
    rise = np.clip(t / 2.7, 0, 1)
    hum = np.zeros(n)
    for detune in (0, .6):
        phase = np.cumsum(43.65 * 2 ** (rise ** 1.6) + detune) / RATE * 2 * np.pi
        hum += sum(np.sin(k * phase + rng.uniform(0, 6.3)) / k ** 1.1 for k in range(1, 10))
    hum *= rise ** 1.5 * np.exp(-np.clip(t - 2.8, 0, None) / 1.4) * np.clip((seconds - t) / 1.5, 0, 1) * .3
    spin = np.cumsum(2 + 16 * rise ** 1.3) / RATE * 2 * np.pi
    whirr = band(rng.normal(size=n), 250, 1500) * (.5 + .5 * np.sin(spin)) ** 2 * rise ** 2 * np.exp(-np.clip(t - 2.8, 0, None) / .6) * .25
    track = np.stack((hum + whirr, hum + np.roll(whirr, 400)), 1)
    at = 2.75
    thump = np.sin(2 * np.pi * 55 * t_(1.2)) * np.exp(-t_(1.2) / .22)
    place(track, thump, at, .5)
    for k, f in enumerate((174.6, 261.6, 349.2, 440, 523.3, 698.5)):
        place(track, glow(f, 4.2, .2 + .05 * k, 3.0, 70 + k), at, .16, (k - 2.5) / 3.5)
    for k, f in enumerate((698.5, 880, 1046.5, 1396.9)):
        place(track, chime(f, 1.2, GLASS), at + .02 + k * .05, .16, (k - 1.5) / 2)
    shimmer = band(rng.normal(size=int(3.5 * RATE)), 3500, 8000) * env(int(3.5 * RATE), .4, 2.6) * .05
    place(track, shimmer, at, 1)
    finish('S_PylonWake', track, 30, 10000, 4.0, .6, 62, 7000, .9)


def spine_wake():
    """The Spine burning whole again: a vast warm swell. The orchestra rises for six and a half seconds
    on F major (basses, cellos, violas and violins, horns, choir, trombones, a timpani roll) and arrives
    on a wider chord with a harp sweep and bells, over a sub swell and a breath of air, in a vast hall."""
    font = sf.SoundFont(str(SOUNDFONT))
    o = Orchestra(60)
    peak, hold = 6.5, 4.5
    sections = ((O_CB, (29,)), (O_VC, (41, 48)), (O_VLA, (53, 57, 60)), (O_STR_SLOW, (65, 69, 72, 79)),
                (O_HORN, (57, 60, 65)), (O_CHOIR, (65, 69, 72)), (O_TBN, (41, 48, 53)))
    for program, keys in sections:
        start = 1.5 if program in (O_HORN, O_CHOIR) else 3.0 if program == O_TBN else 0
        for k in keys:
            o.note(program, k, start, peak - start, 64, 'cresc')
            o.note(program, k + (12 if program in (O_STR_SLOW, O_CHOIR) and k < 70 else 0), peak, hold, 84, 'dim')
    roll = np.arange(0, peak, .075)
    for when in roll:
        o.note(O_TIMP, 41, when, .2, 26 + 64 * (when / peak) ** 1.6)
    o.note(O_TIMP, 41, peak, 2, 96)
    for j, k in enumerate(voicing(53, (0, 4, 7, 14), 53, 96, 53) + voicing(53, (0, 4, 7, 14), 65, 96, 65) + voicing(53, (0, 4, 7, 14), 77, 96, 77)):
        o.note(O_HARP, k, peak - .35 + j * .04, 2.5, 72)
    o.note(O_GLOCK, 89, peak + .1, 3, 64)
    o.note(O_CEL, 84, peak + .25, 3, 60)
    mix = perform(font, o, tail=6)
    t = np.arange(len(mix)) / RATE
    swell = np.clip(t / peak, 0, 1) ** 2 * np.exp(-np.clip(t - peak, 0, None) / 2.2)
    sub = np.sin(2 * np.pi * 43.65 * t) * swell * .012
    air = band(rng.normal(size=len(t)), 2000, 7000) * swell * .004
    mix += np.stack((sub + air, sub + np.roll(air, 500)), 1)
    write('S_SpineWake', trim(hall(mix, 5.0, .75, 63, 7000)), .9)


def current_travel():
    """Carried by a Divinity current: a rising rush of air that turns around her, the deep pull of the
    current beneath, a soft plunge, then light closing over her in falling glass notes and a held chord."""
    seconds = 6.0   # room for the last glass note to ring down (4.4 s cut the fall of notes off)
    t = t_(seconds)
    n = len(t)
    build = np.clip(t / 1.8, 0, 1)
    rush = sweep(180 * 16 ** build ** 1.3, 1.2, 2) * build ** 2 * np.exp(-np.clip(t - 1.85, 0, None) / .25)
    turn = np.sin(np.cumsum(2 * np.pi * (.6 + 1.6 * build)) / RATE)
    track = np.stack((rush * np.sqrt((1 - turn) / 2), rush * np.sqrt((1 + turn) / 2)), 1) * 1.414
    phase = np.cumsum(55 * 2 ** build) / RATE * 2 * np.pi
    pull = (np.sin(phase) + .4 * np.sin(2 * phase) + .15 * np.sin(3 * phase)) * build ** 2 * np.exp(-np.clip(t - 1.85, 0, None) / .35)
    place(track, pull, 0, .25)
    plunge = t_(2.2)
    place(track, np.sin(2 * np.pi * (62 - 14 * plunge) * plunge) * np.exp(-plunge / .3), 1.85, .45)
    place(track, band(rng.normal(size=len(plunge)), 200, 4000) * np.exp(-plunge / .35) * np.clip(plunge / .02, 0, 1), 1.85, .3)
    for k, f in enumerate((1396.9, 1046.5, 880, 698.5, 523.3)):
        place(track, chime(f, 1.6, GLASS), 1.95 + k * .11, .14, (2 - k) / 2.5)
    for k, f in enumerate((349.2, 440, 523.3)):
        place(track, glow(f, 2.4, .35, 1.8, 80 + k), 1.95, .1, (k - 1) / 2)
    finish('S_CurrentTravel', track, 30, 9000, 3.0, .55, 64, 7000, .9)


def talk_open():
    """A conversation opens: two soft wooden notes a fifth apart under a felt mallet, close and gentle."""
    track = np.zeros((int(1.9 * RATE), 2))
    place(track, mallet(349.2), 0, .8, -.15)
    place(track, mallet(523.3), .075, .6, .15)
    finish('S_TalkOpen', track, 80, 6000, .6, .12, 65, 6000, .7)


def lattice_open():
    """A Light Lattice opens as she steps through it: its bars let go in a quick fall of glass notes,
    a soft release of air, and a low warm resonance as the frame's light settles."""
    seconds = 3.1   # room for the lowest glass note to ring down
    t = t_(seconds)
    track = np.zeros((len(t), 2))
    for k, f in enumerate((1396.9, 1174.7, 1046.5, 880, 698.5, 523.3)):
        place(track, chime(f, 2.0, GLASS), .02 + k * .045, .2 - k * .015, (2.5 - k) / 3)
    release = sweep(3000 * (700 / 3000) ** np.clip(t / .45, 0, 1), 1.0, 3) * np.clip(t / .02, 0, 1) * np.exp(-t / .2)
    place(track, release, 0, .5)
    place(track, glow(87.3, 1.6, .12, 1.2, 90) + .5 * glow(174.6, 1.6, .12, 1.0, 91), .05, .18)
    finish('S_LatticeOpen', track, 40, 9500, 2.2, .5, 66, 7000, .85)


# ---------------------------------------------------------------- ambience (loops)

def murmur_takes():
    """Short sentences from the Commons' own people (physis_conclave_lore.PEOPLE, humans only), two from
    each voice, spoken by Kokoro: mono takes at 44.1 kHz for the distant crowd."""
    from kokoro_onnx import EspeakConfig, Kokoro
    sys.path.insert(0, str(ROOT / 'Content/Python'))
    import physis_conclave_lore as lore
    models = ROOT / 'Saved/AudioTools/kokoro_models'
    speech = EspeakConfig(lib_path=os.environ.get('ESPEAK_LIB', '/usr/lib64/libespeak-ng.so.1'),
                          data_path=os.environ.get('ESPEAK_DATA', '/usr/share/espeak-ng-data'))
    engine = Kokoro(str(models / 'kokoro-v1.0.onnx'), str(models / 'voices-v1.0.bin'), espeak_config=speech)
    lines = {}
    for person in lore.PEOPLE:
        if person[4] != 'human' or not person[3]:
            continue
        sentences = [s for page in lore.conversation_pages(person) for s in re.split(r'(?<=[.?!])\s+', page) if 14 <= len(s) <= 64]
        lines.setdefault(person[3], []).extend(sentences)
    takes = []
    for voice, sentences in sorted(lines.items()):
        for sentence in sentences[:2]:
            audio, rate = engine.create(sentence, voice=voice, speed=1.0, lang='en-gb' if voice[0] == 'b' else 'en-us')
            takes.append(np.interp(np.arange(int(len(audio) * RATE / rate)) * rate / RATE, np.arange(len(audio)), audio))
    return takes


def amb_commons(seconds=64):
    """Gentle town life in the Commons: the drum's air moving in gusts, water running in the canals and
    the Orrery's basin, two sets of wind chimes stirred by the gusts, and the people talking far off:
    their own sentences in many voices (murmur_takes), mixed far back, dark and reverberant, so that no
    word can be made out."""
    n = int(seconds * RATE)
    gust = (.5 + .5 * drift(n, 9, 101)) ** 2
    air = noise_bed(n, 60, 650, 102) * (.3 + .7 * gust)[:, None]
    # Water: a running channel (noise that gurgles) and its bubbles, right of centre.
    water = noise_bed(n, 450, 4200, 103) * (.6 + .4 * wobble(n, 2, 11, 106))[:, None] * np.array([.6, 1.0]) * .1
    for _ in range(int(seconds * 70)):
        put(water, bubble(rng.uniform(380, 1700), rng.uniform(.015, .05)), rng.uniform(0, seconds), rng.uniform(.006, .03), rng.uniform(.1, .7))
    # Wind chimes: strikes come in clusters with the gusts (tubes knocking each other).
    chimes = np.zeros((n, 2))
    for pitches, pan, level in (((698.5, 784, 880, 1046.5, 1174.7), -.4, 1.0), ((349.2, 392, 440, 523.3, 587.3), .55, .6)):
        for _ in range(1400):
            at = rng.uniform(0, seconds)
            if rng.uniform() < .22 * gust[int(at * RATE) % n] ** 1.5:
                put(chimes, bell(rng.choice(pitches) * rng.uniform(.998, 1.002), 5.0, .55, TUBE), at, level * rng.uniform(.4, 1), pan + rng.uniform(-.12, .12))
    # The town talking far off: overlapping fragments, a few at a time, darkened by distance.
    takes = murmur_takes()
    voices = np.zeros((n, 2))
    for _ in range(int(seconds * 1.15)):
        take = takes[rng.integers(len(takes))]
        length = min(len(take), int(rng.uniform(1.2, 3.2) * RATE))
        start = rng.integers(0, len(take) - length + 1)
        piece = take[start:start + length] * env(length, .08, .25)
        stretch = rng.uniform(.94, 1.06)
        piece = np.interp(np.arange(0, length - 1, stretch), np.arange(length), piece)
        put(voices, band(piece, 170, 2300), rng.uniform(0, seconds), rng.uniform(.35, 1.0), rng.uniform(-.85, .85))
    voices = ring(voices, 2.6, 1.3, 104, 3000)
    # The water carries the bed, the air sits under it, the chimes ring over it, the voices stay far back.
    mix = blend((water, -23), (air, -26), (chimes, -26), (voices, -29))
    write('S_Amb_Commons', ring(mix, 1.4, .22, 105, 7000), .6, -19)


def amb_drum(seconds=48):
    """The drum itself: a deep slow hum of the station's machinery breathing with the drum's turn (three
    slow swells a loop), moving air, the Spine's faint high tone, and now and then the structure
    groaning far off as it flexes."""
    n = int(seconds * RATE)
    x = np.arange(n) / n
    t = np.arange(n) / RATE
    turn = .75 + .25 * np.sin(2 * np.pi * 3 * x)
    hum = np.zeros(n)
    for k in range(1, 9):
        for detune in (0, .17 * k):
            hum += np.sin(2 * np.pi * whole(41.2 * k + detune, n) * t + rng.uniform(0, 6.3)) / k ** 1.3
    track = np.stack((hum, np.roll(hum, 1200)), 1) * (turn * .09)[:, None]
    track += noise_bed(n, 25, 320, 111) * (turn * .5)[:, None]
    spine = sum(np.sin(2 * np.pi * whole(f, n) * t + rng.uniform(0, 6.3)) for f in (220, 220.4, 330, 440.3)) * (.6 + .4 * drift(n, 5, 112)) * .006
    track += np.stack((spine, np.roll(spine, 800)), 1)
    for k in range(4):
        put(track, groan(rng.uniform(70, 140), rng.uniform(3.5, 6), 113 + k), (k + rng.uniform(.1, .8)) * seconds / 4, .05, rng.uniform(-.7, .7))
    for k in range(3):
        knock = clank(rng.uniform(60, 110), 1.6, 120 + k, near=.1) + np.sin(2 * np.pi * 48 * t_(1.6)) * np.exp(-t_(1.6) / .2)
        put(track, knock, (k + rng.uniform(.2, .8)) * seconds / 3, .06, rng.uniform(-.6, .6))
    write('S_Amb_Drum', ring(track, 5.0, .8, 114, 2500), .6, -22)


def amb_foundry(seconds=48):
    """The Foundry: furnace roar flickering in its draught, the floors' slow pulse of burning gas, a press
    thudding somewhere in the halls, crackle, and clanks of iron near and far in a big metal space."""
    n = int(seconds * RATE)
    flicker = .65 + .35 * wobble(n, 1.5, 9, 125)
    slow = .75 + .25 * drift(n, 7, 121)
    track = noise_bed(n, 30, 170, 122) * slow[:, None] * .9 + noise_bed(n, 120, 1400, 123) * (flicker * slow)[:, None] * .35
    for k in range(6):
        burst = t_(3.2)
        whoomph = band(rng.normal(size=len(burst)), 60, 900) * np.clip(burst / .25, 0, 1) * np.exp(-burst / 1.0)
        whoomph += np.sin(2 * np.pi * 41 * burst) * np.clip(burst / .3, 0, 1) * np.exp(-burst / .9) * .6
        put(track, whoomph, k * seconds / 6 + rng.uniform(0, 1.5), .5, rng.uniform(-.5, .5))
    for k in range(16):
        thud = np.sin(2 * np.pi * 58 * t_(.6)) * np.exp(-t_(.6) / .09) + clank(170, .6, 130 + k, near=.15) * .4
        put(track, thud, k * seconds / 16, .22, .35)
    for k in range(42):
        near = rng.uniform(.1, 1)
        put(track, clank(rng.uniform(180, 900), rng.uniform(.6, 1.8), 140 + k, near), rng.uniform(0, seconds), .05 + .2 * near ** 2, rng.uniform(-.9, .9))
    for k in range(8):
        at = rng.uniform(0, seconds)
        for j in range(rng.integers(4, 8)):
            put(track, clank(rng.uniform(900, 2200), rng.uniform(.1, .3), 200 + k * 10 + j, .5), at + j * rng.uniform(.04, .09), .05, rng.uniform(-.8, .8))
    # Crackle: tiny ticks cut from one second of bright noise (band() needs more than a tick to filter).
    sparks = band(rng.normal(size=RATE), 2000, 7000)
    for _ in range(int(seconds * 9)):
        at = rng.integers(0, RATE - 120)
        put(track, sparks[at:at + 120] * np.hanning(120), rng.uniform(0, seconds), rng.uniform(.03, .15), rng.uniform(-.8, .8))
    # The clanks keep their snap (no soft knee), which holds the hall a little under the Center's beds.
    write('S_Amb_Foundry', ring(track, 2.8, .55, 124, 5000), .7, -19)


def amb_water(seconds=40):
    """The Reservoir's edge: small waves lapping the stones and the pier posts at uneven intervals, each a
    wash of water with a slap, a hollow knock and a few bubbles after it, over a soft wide bed of open water."""
    n = int(seconds * RATE)
    bed = noise_bed(n, 90, 1100, 131) * (.75 + .25 * drift(n, 6, 132))[:, None]
    laps = np.zeros((n, 2))
    at = 0.0
    while at < seconds:
        near = rng.uniform() < .65
        lt = t_(rng.uniform(.6, 1.1))
        # The wash swells in over 90 ms (the water piles up before it breaks on the stone), then drains.
        wash = band(rng.normal(size=len(lt)), 180, 2600 if near else 1500) * np.clip(lt / .09, 0, 1) ** 1.5 * np.exp(-lt / rng.uniform(.15, .28))
        wash += band(rng.normal(size=len(lt)), 400, 3500) * np.clip(lt / .004, 0, 1) * np.exp(-lt / .02) * .22
        wash += np.sin(2 * np.pi * rng.uniform(90, 150) * lt) * np.exp(-lt / .06) * .18
        pan = rng.uniform(-.75, .75)
        put(laps, wash, at, 1.0 if near else .45, pan)
        for _ in range(rng.integers(3, 9)):
            put(laps, bubble(rng.uniform(500, 2200), rng.uniform(.012, .035)), at + rng.uniform(.05, .5), rng.uniform(.03, .1), pan + rng.uniform(-.2, .2))
        at += rng.uniform(1.3, 3.4) if rng.uniform() > .2 else rng.uniform(.35, .6)
    # Noise bursts peak 19 dB over their loudness; a soft knee on the laps lets the bed reach its level.
    laps = np.tanh(2 * laps / np.abs(laps).max())
    write('S_Amb_Water', ring(blend((bed, -27), (laps, -21)), 1.2, .2, 133, 6000), .7, -20)


# ---------------------------------------------------------------- music (SoundFont)

# F major, plain and warm: the town's own key (the Center floats in D Lydian). Themes give each bar's
# notes as (beat, key, beats); chords are (root, intervals) with the root where strings_bed's cellos
# play it (below 50 as written, else an octave down), so the basses stay between F1 and D2.
THEME = (((0, 72, 1), (1, 77, 3)), ((0, 76, 1), (1, 77, 1), (2, 79, 1), (3, 81, 1)),
         ((0, 77, 1.5), (1.5, 79, .5), (2, 77, 1), (3, 74, 1)), ((0, 72, 2), (2, 70, 1), (3, 69, 1)),
         ((0, 72, 1), (1, 77, 2), (3, 81, 1)), ((0, 84, 2), (2, 82, 1), (3, 81, 1)),
         ((0, 79, 1.5), (1.5, 77, .5), (2, 76, 2)), ((0, 77, 4),))
CHORDS = ((53, (0, 4, 7)), (57, (0, 3, 7, 10)), (46, (0, 4, 7, 14)), (48, (0, 4, 7, 10)),
          (53, (0, 4, 7, 14)), (62, (0, 3, 7, 10)), (48, (0, 4, 7, 10, 14)), (53, (0, 4, 7)))
# The bridge, more noble, climbing to the high B flat and leaning on the dominant.
BRIDGE = (((0, 65, 1), (1, 70, 2), (3, 72, 1)), ((0, 74, 1.5), (1.5, 72, .5), (2, 69, 2)),
          ((0, 67, 1), (1, 70, 1), (2, 74, 2)), ((0, 72, 3), (3, 74, 1)),
          ((0, 77, 2), (2, 76, 1), (3, 74, 1)), ((0, 74, 1), (1, 77, 1), (2, 82, 2)),
          ((0, 81, 1.5), (1.5, 79, .5), (2, 77, 1), (3, 76, 1)), ((0, 79, 4),))
CHORDS_BRIDGE = ((46, (0, 4, 7, 11)), (53, (0, 4, 7)), (55, (0, 3, 7, 10)), (48, (0, 4, 7, 14)),
                 (62, (0, 3, 7)), (46, (0, 4, 7, 14)), (55, (0, 3, 7, 10)), (48, (0, 4, 7, 10)))
# Market day: a light tune for the flute over pizzicato.
DANCE = (((0, 81, .5), (.5, 79, .5), (1, 77, 1), (2, 72, 1), (3, 77, 1)), ((0, 74, .5), (.5, 77, .5), (1, 82, 1), (2, 81, .5), (2.5, 79, .5), (3, 77, 1)),
         ((0, 81, .5), (.5, 79, .5), (1, 77, 1), (2, 84, 1.5), (3.5, 81, .5)), ((0, 79, 2), (2, 76, 1), (3, 72, 1)),
         ((0, 74, .5), (.5, 77, .5), (1, 81, 1), (2, 77, .5), (2.5, 74, .5), (3, 69, 1)), ((0, 70, .5), (.5, 74, .5), (1, 77, 1), (2, 82, 1), (3, 81, .5), (3.5, 79, .5)),
         ((0, 77, 1), (1, 79, .5), (1.5, 77, .5), (2, 74, 1), (3, 70, 1)), ((0, 72, 2), (2, 76, 1), (3, 79, 1)))
CHORDS_DANCE = ((53, (0, 4, 7)), (46, (0, 4, 7)), (53, (0, 4, 7)), (48, (0, 4, 7)),
                (62, (0, 3, 7)), (46, (0, 4, 7)), (55, (0, 3, 7, 10)), (48, (0, 4, 7, 10)))
# Morning opens on F with an added ninth and leans into the theme on a suspended dominant; the coda
# ends on the dominant too, so the last bar leads straight back into the first.
INTRO = ((53, (0, 4, 7, 14)), (46, (0, 4, 7, 11)), (55, (0, 3, 7, 10)), (48, (0, 5, 7, 10)))
CODA = ((62, (0, 3, 7, 10)), (55, (0, 3, 7, 10)), (48, (0, 7, 10, 14, 17)), (48, (0, 4, 7, 10)))
TEMPO, BARS = 76, 68
MUSIC_LUFS = -10.4   # Art/Audio/Center/S_Music_Center.wav, measured with ffmpeg ebur128
# Timpani tuned to the chord's root (F and C, as in the key, plus the others the progression needs).
TIMPANI = {5: 41, 0: 48, 10: 46, 2: 50, 7: 43, 9: 45}


def bass(root):
    return root if root < 50 else root - 12


def pizz(o, bar, chords, loud, bounce=False):
    """The town walking: pizzicato bass on beats one and three (root, then the fifth); with `bounce`
    the upper strings answer on two and four, an easy market-day lilt."""
    for i, (root, chord) in enumerate(chords):
        at = (bar + i) * 4
        low = bass(root)
        o.note(O_PIZZ, low, at, 1, loud)
        o.note(O_PIZZ, low + 7 if low + 7 <= 55 else low - 5, at + 2, 1, loud - 8)
        if bounce:
            for beat in (1, 3):
                for k in voicing(root, chord, 60, 72, 64)[:3]:
                    o.note(O_PIZZ, k, at + beat, .5, loud - 16)


def glints(o, bar, chords, loud, beat=2.5):
    """Celesta catching the light once a bar, a chord tone high up."""
    for i, (root, chord) in enumerate(chords):
        o.note(O_CEL, voicing(root, chord, 84, 98, 88)[i % 3], (bar + i) * 4 + beat, 1.5, loud)


def conclave_score():
    """The Conclave's town theme (~3.6 min at 76 bpm, 68 bars, loops): morning on strings and harp with
    the horn's call; the theme on clarinet over pizzicato; violins take it with the flute answering; the
    bridge on the horn; market day (a flute dance over pizzicato and clarinets); the whole town in
    tutti; the bridge again on violins and oboe; evening (flute and oboe share the theme); and a coda that
    remembers the bridge and turns back to the morning."""
    o = Orchestra(TEMPO)
    # 1. Morning (bars 0-3).
    strings_bed(o, 0, INTRO, 40)
    harp_rolls(o, 0, INTRO, 40, every=1)
    melody(o, 0, THEME[:2], O_HORN, 60, shift=-12, lead=2.2)
    o.note(O_HORN, 55, 3 * 4, 4.05, 52, 'swell')
    glints(o, 0, INTRO, 40)
    # 2. The theme on clarinet over pizzicato and harp (bars 4-11).
    strings_bed(o, 4, CHORDS, 52)
    harp_rolls(o, 4, CHORDS, 48)
    pizz(o, 4, CHORDS, 62)
    melody(o, 4, THEME, O_CLAR, 78, lead=2.2)
    # 3. Violins take the theme; horns hold the middle, a clarinet figure walks beneath, the flute answers (bars 12-19).
    strings_bed(o, 12, CHORDS, 58)
    harp_rolls(o, 12, CHORDS, 50)
    ostinato(o, 12, CHORDS, O_CLAR, 50, low=62)
    melody(o, 12, THEME, O_VLN, 82, lead=2.3)
    for i, (root, chord) in enumerate(CHORDS):
        o.note(O_HORN, voicing(root, chord, 57, 69, 62)[1], (12 + i) * 4, 4.05, 54, 'swell')
    melody(o, 12, ((), (), (), ((2, 79, 2),), (), (), (), ((1, 81, 1), (2, 84, 2))), O_FLUTE, 62, lead=1.6)
    # 4. The bridge on the horn, the oboe answering its long notes (bars 20-27).
    strings_bed(o, 20, CHORDS_BRIDGE, 56)
    harp_rolls(o, 20, CHORDS_BRIDGE, 50)
    melody(o, 20, BRIDGE, O_HORN, 80, shift=-12, lead=2.6)
    for i, key in ((3, 79), (7, 76)):
        o.note(O_OBOE, key, (20 + i) * 4 + 2, 2, 64, 'swell')
    o.note(O_TIMP, TIMPANI[10], 20 * 4, 2, 48)
    o.note(O_TIMP, TIMPANI[0], 27 * 4, 2, 54)
    # 5. Market day (bars 28-35): pizzicato oom-pah, clarinet figures, the flute's dance, glockenspiel.
    strings_bed(o, 28, CHORDS_DANCE, 44)
    pizz(o, 28, CHORDS_DANCE, 70, bounce=True)
    ostinato(o, 28, CHORDS_DANCE, O_CLAR, 56, low=60)
    melody(o, 28, DANCE, O_FLUTE, 74, lead=1.7)
    for i, (root, chord) in enumerate(CHORDS_DANCE):
        if i % 2 == 0:
            o.note(O_GLOCK, voicing(root, chord, 84, 96, 89)[0], (28 + i) * 4, 1.5, 52)
    # 6. The whole town (bars 36-43): violins and flutes an octave apart, horns in unison below,
    #    trombones and tuba, the choir, timpani on every chord.
    strings_bed(o, 36, CHORDS, 70, program=O_STR, top=84)
    harp_rolls(o, 36, CHORDS, 56, every=.25)
    melody(o, 36, THEME, O_VLN, 92, double=O_FLUTE, double_shift=12, lead=1.9)
    melody(o, 36, THEME, O_HORN, 82, shift=-12, lead=1.9)
    for i, (root, chord) in enumerate(CHORDS):
        at = (36 + i) * 4
        for k in voicing(root, chord, 50, 64, 55):
            o.note(O_TBN, k, at, 4.05, 58, 'swell')
        o.note(O_TUBA, bass(root), at, 4.05, 56, 'swell')
        for k in voicing(root, chord, 60, 72, 65):
            o.note(O_OOHS, k, at, 4.05, 58, 'swell')
        o.note(O_TIMP, TIMPANI[root % 12], at, 1, 70)
        if i in (3, 7):
            o.note(O_TIMP, TIMPANI[root % 12], at + 3, .5, 62)
            o.note(O_TIMP, TIMPANI[root % 12], at + 3.5, .5, 68)
    o.note(O_GLOCK, 89, 43 * 4, 3, 56)
    # 7. The bridge again on violins with the oboe, settling (bars 44-51).
    strings_bed(o, 44, CHORDS_BRIDGE, 58)
    harp_rolls(o, 44, CHORDS_BRIDGE, 50)
    ostinato(o, 44, CHORDS_BRIDGE[:4], O_CLAR, 48, low=62)
    melody(o, 44, BRIDGE, O_VLN, 78, double=O_OBOE, double_shift=0, lead=2.2)
    for i, (root, chord) in enumerate(CHORDS_BRIDGE):
        o.note(O_HORN, voicing(root, chord, 57, 69, 62)[1], (44 + i) * 4, 4.05, 50, 'swell')
    o.note(O_BSN, 46, 50 * 4, 4, 50, 'dim')
    # 8. Evening (bars 52-59): the flute sings the first phrase, the oboe the second.
    strings_bed(o, 52, CHORDS, 46)
    harp_rolls(o, 52, CHORDS, 44, every=1)
    melody(o, 52, THEME[:4], O_FLUTE, 66, lead=1.9)
    melody(o, 56, THEME[4:], O_OBOE, 64, lead=1.9)
    glints(o, 52, CHORDS, 38)
    # 9. Coda (bars 60-67): tremolo strings while the clarinet remembers the bridge low down; then harp
    #    and celesta over a suspended dominant that resolves into the morning of bar 0.
    for i, (root, chord) in enumerate(CHORDS_BRIDGE[:4]):
        at = (60 + i) * 4
        for k in voicing(root, chord, 57, 76, 64):
            o.note(O_TREM, k, at, 4.05, 46, 'swell')
        o.note(O_CB, bass(root) - 12, at, 4.05, 44, 'swell')
    melody(o, 60, BRIDGE[:4], O_CLAR, 64, shift=-12, lead=2.1)
    strings_bed(o, 64, CODA, 44)
    harp_rolls(o, 64, CODA, 44)
    glints(o, 64, CODA, 38, beat=1.5)
    melody(o, 64, (((0, 72, 1), (1, 77, 3)),), O_OBOE, 58, lead=1.8)
    o.note(O_HORN, 53, 66 * 4, 4.05, 50, 'swell')
    o.note(O_HORN, 52, 67 * 4, 4.05, 48, 'swell')
    return o


def ride(mix, keep_db=9.0):
    """level_ride() reads one frame past a signal that fills a whole number of its quarter-second frames,
    and that empty frame turns every gain into NaN; a sample of silence gives it something to read."""
    if len(mix) % (RATE // 4) == 0:
        return level_ride(np.concatenate((mix, np.zeros((1, 2), mix.dtype))), keep_db)[:-1]
    return level_ride(mix, keep_db)


def conclave_music(excerpt=None, from_bar=0):
    """Renders the score, lays its last ringing seconds over its first so the loop has no seam, and
    evens the level as the Center's music does. `excerpt` seconds from `from_bar` make a test file."""
    font = sf.SoundFont(str(SOUNDFONT))
    o = conclave_score()
    if excerpt:
        start = from_bar * 4 * o.beat
        o.events = [(e[0], e[1], e[2] - start) + e[3:] for e in o.events if start <= e[2] < start + excerpt]
    mix = perform(font, o)
    # A warm hall: the town's music heard across the plaza, nearer than the Center's night music.
    mix = hall(mix, 3.4, .5, 51, 8000)
    if excerpt:
        mix = mix[:int(excerpt * RATE)]
        mix[-int(1.5 * RATE):] *= np.linspace(1, 0, int(1.5 * RATE))[:, None]
        mix = ride(mix / np.abs(mix).max())
    else:
        mix = fold(mix, BARS * 4 * o.beat)
        # The level ride sees the loop as a circle, so its gain meets itself at the seam.
        pad = 12 * RATE
        mix = ride(np.concatenate((mix[-pad:], mix, mix[:pad])) / np.abs(mix).max())[pad:-pad]
    mix = mix / np.abs(mix).max()
    mix = np.tanh(mix * 1.6) / np.tanh(1.6)
    # PhysisMusicPick plays this and the Center's S_Music_Center at the same 0.1 x Music volume, so it is held
    # to the Center's -10.4 LUFS: peak-normalised alone the excerpts measured -8.3 to -8.7, 2 dB louder.
    write('S_Music_Conclave_Excerpt' if excerpt else 'S_Music_Conclave', mix, .9, MUSIC_LUFS)


SOUNDS = {'S_Music_Conclave': conclave_music, 'S_LightStep': light_step, 'S_PylonWake': pylon_wake, 'S_SpineWake': spine_wake,
          'S_CurrentTravel': current_travel, 'S_TalkOpen': talk_open, 'S_LatticeOpen': lattice_open,
          'S_Amb_Commons': amb_commons, 'S_Amb_Drum': amb_drum, 'S_Amb_Foundry': amb_foundry, 'S_Amb_Water': amb_water}
PARTS = {'music': ['S_Music_Conclave'], 'sfx': ['S_LightStep', 'S_PylonWake', 'S_SpineWake', 'S_CurrentTravel', 'S_TalkOpen', 'S_LatticeOpen'],
         'amb': ['S_Amb_Commons', 'S_Amb_Drum', 'S_Amb_Foundry', 'S_Amb_Water']}


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
    names = [name for part in (args or ['music', 'sfx', 'amb']) for name in PARTS.get(part, [part])]
    unknown = [name for name in names if name not in SOUNDS]
    if unknown:
        sys.exit('unknown part %s; parts: %s' % (', '.join(unknown), ', '.join(list(PARTS) + list(SOUNDS))))
    for name in names:
        reseed(name)
        if name == 'S_Music_Conclave' and '--excerpt' in options:
            conclave_music(float(options['--excerpt']), int(options.get('--from-bar', 0)))
        else:
            SOUNDS[name]()
