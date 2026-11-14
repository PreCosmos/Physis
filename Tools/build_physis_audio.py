"""Synthesizes combat sounds, explosions and music, and exports the slash arc mesh.

Run: flatpak run org.blender.Blender -b --python Tools/build_physis_audio.py
Blender is only used for its numpy and FBX export. Output goes to Art/Audio/Game.
"""
import math
import os
import pathlib
import sys
import wave

import bpy
import numpy as np

ROOT = pathlib.Path(bpy.path.abspath(__file__)).resolve().parent.parent
OUT = ROOT / 'Art/Audio/Game'
RATE = 44100
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)


def write(name, left, right=None, peak=.9):
    right = left if right is None else right
    size = min(len(left), len(right))
    data = np.stack((left[:size], right[:size]), 1)
    data = data / max(np.abs(data).max(), 1e-6) * peak
    with wave.open(str(OUT / (name + '.wav')), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((data * 32767).astype('<i2').tobytes())


def times(seconds):
    return np.arange(int(seconds * RATE)) / RATE


def lowpass(signal, cutoff):
    """One-pole lowpass; cutoff may be a per-sample array, so it can sweep."""
    cutoff = np.broadcast_to(cutoff, signal.shape)
    gain = 1 - np.exp(-2 * np.pi * cutoff / RATE)
    out = np.empty_like(signal)
    state = 0.0
    for index in range(len(signal)):
        state += gain[index] * (signal[index] - state)
        out[index] = state
    return out


def fft_filter(signal, low, high):
    spectrum = np.fft.rfft(signal)
    freq = np.fft.rfftfreq(len(signal), 1 / RATE)
    spectrum *= (freq >= low) & (freq <= high)
    return np.fft.irfft(spectrum, len(signal))


def reverb(signal, seconds, wet):
    """Convolves with decaying filtered noise, for a large hall."""
    size = int(seconds * RATE)
    tail = rng.normal(size=size) * np.exp(-6.5 * np.arange(size) / size)
    tail = fft_filter(tail, 120, 5200)
    tail /= np.sqrt((tail ** 2).sum())
    padded = len(signal) + size
    wetted = np.fft.irfft(np.fft.rfft(signal, padded) * np.fft.rfft(tail, padded), padded)
    dry = np.zeros(padded)
    dry[:len(signal)] = signal
    return dry + wetted * wet


def stereo_hall(signal, seconds=2.4, wet=1.0):
    return reverb(signal, seconds, wet), reverb(signal, seconds, wet)


def explosion(seed, seconds, depth):
    """Sub thump, a roaring noise body whose brightness falls, then falling debris."""
    local = np.random.default_rng(seed)
    t = times(seconds)
    sweep = 26 + 80 * np.exp(-t * 7)
    thump = np.sin(2 * np.pi * np.cumsum(sweep) / RATE) * np.exp(-t * 2.4)
    noise = local.normal(size=t.size)
    crack = fft_filter(noise, 900, 9000) * np.exp(-t * 34) * 1.1
    roar = lowpass(noise, 120 + 2600 * np.exp(-t * 2.8)) * np.minimum(t * 45, 1) * np.exp(-t * (5.5 / seconds)) * 2.6
    rumble = lowpass(local.normal(size=t.size), 70) * np.exp(-t * (3.2 / seconds)) * 7
    debris = np.zeros(t.size)
    for _ in range(int(40 * seconds)):
        start = int(local.uniform(.12, seconds * .8) * RATE)
        size = int(local.uniform(.006, .05) * RATE)
        if start + size < t.size:
            grain = fft_filter(local.normal(size=size), 700, 6000) * np.hanning(size)
            debris[start:start + size] += grain * local.uniform(.05, .3) * math.exp(-start / RATE * 1.4)
    dry = thump * depth + roar + rumble + crack + debris
    return dry * np.tanh(1) / 1


def whoosh(seed, seconds, high):
    local = np.random.default_rng(seed)
    t = times(seconds)
    shape = np.sin(np.pi * np.minimum(t / seconds, 1)) ** 2.2
    centre = 500 + high * shape
    band = lowpass(local.normal(size=t.size), centre) - lowpass(local.normal(size=t.size), centre * .35)
    return band * shape


def clang(seed, seconds, base):
    """Inharmonic steel partials over a short bright strike."""
    local = np.random.default_rng(seed)
    t = times(seconds)
    out = np.zeros(t.size)
    for ratio, level, decay in ((1, 1, 7), (2.76, .8, 10), (5.4, .6, 15), (8.93, .45, 22), (13.3, .3, 30)):
        out += level * np.sin(2 * np.pi * base * ratio * t + local.uniform(0, 6)) * np.exp(-t * decay)
    return out + fft_filter(local.normal(size=t.size), 1500, 12000) * np.exp(-t * 90) * 1.6


def flesh_hit(seed):
    local = np.random.default_rng(seed)
    t = times(.42)
    thud = np.sin(2 * np.pi * np.cumsum(60 + 170 * np.exp(-t * 42)) / RATE) * np.exp(-t * 15)
    tear = fft_filter(local.normal(size=t.size), 500, 7000) * np.exp(-t * 26) * .9
    return thud * 1.5 + tear


# Music: D minor, 84 bpm. Detuned strings, low brass, choir and taiko over a pedal.
BPM = 84
BEAT = 60 / BPM
ROOTS = {'D': 36, 'Bb': 34, 'F': 41, 'C': 36, 'G': 31, 'A': 33}
CHORDS = {'D': (0, 3, 7), 'Bb': (0, 4, 7), 'F': (0, 4, 7), 'C': (0, 4, 7), 'G': (0, 3, 7), 'A': (0, 4, 7)}
ROOTS['C'] = 36


def note_hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def saw(hz, t, voices, detune):
    out = np.zeros(t.size)
    for index in range(voices):
        cents = (index - (voices - 1) / 2) * detune
        phase = (t * hz * 2 ** (cents / 1200) + rng.uniform(0, 1)) % 1
        out += 2 * phase - 1
    return out / voices


def strings(midi, seconds, brightness):
    t = times(seconds)
    body = saw(note_hz(midi), t, 7, 5) * (1 + .05 * np.sin(2 * np.pi * 5.1 * t))
    edge = np.minimum(t / .28, 1) * np.minimum((seconds - t) / .4, 1)
    return lowpass(body, brightness) * edge


def choir(midi, seconds):
    t = times(seconds)
    hz = note_hz(midi)
    out = sum(np.sin(2 * np.pi * hz * k * t + rng.uniform(0, 6)) / k ** 1.4 for k in range(1, 7))
    air = fft_filter(rng.normal(size=t.size), hz * 2, hz * 7) * .05
    edge = np.minimum(t / .9, 1) * np.minimum((seconds - t) / 1.1, 1)
    return (out + air) * edge * (1 + .08 * np.sin(2 * np.pi * 4.6 * t))


def taiko(level):
    t = times(1.3)
    body = np.sin(2 * np.pi * np.cumsum(58 + 90 * np.exp(-t * 30)) / RATE) * np.exp(-t * 4.6)
    skin = lowpass(rng.normal(size=t.size), 1500) * np.exp(-t * 38) * .8
    return (body * 2.2 + skin) * level


def brass(midi, seconds):
    t = times(seconds)
    swell = np.minimum(t / .1, 1) * np.minimum((seconds - t) / .18, 1)
    body = saw(note_hz(midi), t, 3, 3) + .6 * saw(note_hz(midi - 12), t, 3, 3)
    return lowpass(body, 300 + 2600 * swell ** 2) * swell


def place(track, sound, start):
    begin = int(start * RATE)
    end = min(begin + len(sound), len(track))
    if end > begin:
        track[begin:end] += sound[:end - begin]


def score(bars, progression, drive, seconds_extra=3.0):
    total = int((bars * 4 * BEAT + seconds_extra) * RATE)
    low, high, drums = np.zeros(total), np.zeros(total), np.zeros(total)
    for bar in range(bars):
        name = progression[bar % len(progression)]
        start = bar * 4 * BEAT
        root = ROOTS[name]
        grow = (bar + 1) / bars if drive == 'rise' else 1
        low_bar = strings(root, 4 * BEAT + .3, 420) + strings(root + 12, 4 * BEAT + .3, 700) * .6
        place(low, low_bar * .7, start)
        for offset, level in ((0, 1.2), (1.5, .8), (2, 1), (3, 1), (3.5, .7)):
            if grow > .25:
                place(drums, taiko(level * grow), start + offset * BEAT)
        if grow > .4:
            for tone in CHORDS[name]:
                place(high, choir(root + 24 + tone, 4 * BEAT + 1) * .34 * grow, start)
                place(high, strings(root + 24 + tone, 4 * BEAT + .3, 1800) * .32 * grow, start)
        if grow > .6 and bar % 2 == 1:
            place(high, brass(root + 12, BEAT * 1.5) * .9 * grow, start + 2 * BEAT)
            place(high, brass(root + 19, BEAT * 1.5) * .7 * grow, start + 2 * BEAT)
        if drive == 'fight':
            for step in range(8):
                pulse = strings(root + 12, BEAT * .42, 1500)
                place(high, pulse * (.34 if step % 2 else .5), start + step * BEAT / 2)
    return low, high, drums


def mix(parts, wet):
    low, high, drums = parts
    left_high, right_high = stereo_hall(high, 3.2, wet)
    left_low, right_low = stereo_hall(low, 2.0, wet * .4)
    left_drums, right_drums = stereo_hall(drums, 1.8, wet * .5)
    size = max(len(left_low), len(left_high), len(left_drums))
    left_low, right_low = [np.pad(track, (0, size - len(track))) for track in (left_low, right_low)]
    left_high, right_high = [np.pad(track, (0, size - len(track))) for track in (left_high, right_high)]
    left_drums, right_drums = [np.pad(track, (0, size - len(track))) for track in (left_drums, right_drums)]
    left = left_low + left_high * 1.05 + left_drums * .9
    right = right_low + right_high * .95 + right_drums * .9
    return np.tanh(left / np.abs(left).max() * 1.4), np.tanh(right / np.abs(right).max() * 1.4)


def loop_tail(left, right, seconds):
    """Folds the reverb tail back over the start, so the loop point stays seamless."""
    size = int(seconds * RATE)
    left, right = left.copy(), right.copy()
    extra = len(left) - size
    left[:extra] += left[size:]
    right[:extra] += right[size:]
    return left[:size], right[:size]


def export_arc():
    """A swept ribbon for the blade trail: 150 degrees of ring, UV.x runs along the sweep."""
    steps = 40
    vertices = []
    faces = []
    uvs = []
    for index in range(steps + 1):
        angle = math.radians(-75 + 150 * index / steps)
        for radius, v in ((60, 0), (170, 1)):
            vertices.append((math.cos(angle) * radius, math.sin(angle) * radius, 0))
            uvs.append((index / steps, v))
    for index in range(steps):
        a = index * 2
        faces.append((a, a + 2, a + 3, a + 1))
    mesh = bpy.data.meshes.new('SM_SlashArc')
    mesh.from_pydata(vertices, [], faces)
    layer = mesh.uv_layers.new(name='UV0')
    for loop in mesh.loops:
        layer.data[loop.index].uv = uvs[loop.vertex_index]
    item = bpy.data.objects.new('SM_SlashArc', mesh)
    bpy.context.collection.objects.link(item)
    bpy.ops.object.select_all(action='DESELECT')
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    bpy.ops.export_scene.fbx(filepath=str(ROOT / 'Art/Meshes/Props/SM_SlashArc.fbx'), use_selection=True, axis_forward='-Y', axis_up='Z',
                             bake_space_transform=False, mesh_smooth_type='FACE', add_leaf_bones=False)


def laser(seed):
    """A deep plasma shot: falling saw with a noise body, capped well below 2.6 kHz."""
    t = times(.42)
    hz = 120 + 780 * np.exp(-t * 15)
    phase = np.cumsum(hz) / RATE % 1
    body = lowpass(2 * phase - 1, 2200) * np.exp(-t * 7)
    hiss = lowpass(np.random.default_rng(seed).normal(size=t.size), 1600) * np.exp(-t * 24) * .5
    return body + hiss


def laser_hit(seed):
    t = times(.6)
    thud = np.sin(2 * np.pi * np.cumsum(70 + 240 * np.exp(-t * 30)) / RATE) * np.exp(-t * 9)
    return thud * 1.6 + lowpass(np.random.default_rng(seed).normal(size=t.size), 2200) * np.exp(-t * 20)


def battle():
    """Driving war music: 16th-note ostinato, double-time drums, brass stabs, choir and alarm."""
    global BEAT
    BEAT = 60 / 156
    step = BEAT / 4
    bars = 24
    keys = ('D', 'D', 'Bb', 'C', 'D', 'D', 'G', 'A')
    total = int((bars * 4 * BEAT + 4) * RATE)
    low, high, drums = np.zeros(total), np.zeros(total), np.zeros(total)
    cache = {}

    def stab(midi, seconds, cutoff):
        key = (midi, round(seconds, 3), cutoff)
        if key not in cache:
            size = int(seconds * RATE)
            body = saw(note_hz(midi), times(seconds), 5, 7)
            cache[key] = np.tanh(lowpass(body, cutoff) * 2.6) * np.minimum(np.arange(size) / 90, 1) * np.exp(-np.arange(size) / size * 2.2)
        return cache[key]

    kick = taiko(1.9)
    size = int(.3 * RATE)
    snare = (fft_filter(rng.normal(size=size), 900, 7000) * 1.7 + np.sin(2 * np.pi * 190 * times(.3)) * .9) * np.exp(-times(.3) * 17)
    pattern = (0, 0, 12, 0, 0, 12, 0, 7, 0, 0, 12, 0, 3, 0, 7, 12)
    theme = (14, 15, 17, 19, 17, 15, 14, 10, 12, 14, 12, 10, 7, 10, 12, 14)
    for bar in range(bars):
        name = keys[bar % len(keys)]
        root = ROOTS[name]
        start = bar * 4 * BEAT
        heat = .75 + .25 * min(bar / 8, 1)
        for index in range(16):
            when = start + index * step
            accent = 1.25 if index % 4 == 0 else .82
            place(low, stab(root + pattern[index], step * 1.15, 900) * accent, when)
            place(low, stab(root - 12, step * 1.05, 240) * .9 * accent, when)
            place(drums, kick * (.95 if index % 8 == 0 else .42 if index % 2 == 0 else .2), when)
            if bar % 4 == 3 and index >= 8:
                place(drums, snare * (.35 + .08 * (index - 8)), when)
        for beat in (1, 3):
            place(drums, snare * 1.25, start + beat * BEAT)
        for offset, length in ((0, 1.0), (.75, .5), (1.5, 1.5), (3, .75), (3.5, .75)):
            for tone in (12, 19, 24):
                place(high, brass(root + tone, BEAT * length) * .62 * heat, start + offset * BEAT)
        if bar >= 4:
            for index, degree in enumerate(theme):
                if index % 2 == 0:
                    place(high, stab(root + 24 + degree, BEAT * .62, 3000) * .62, start + index * step)
        if bar >= 8:
            for tone in CHORDS[name]:
                place(high, choir(root + 24 + tone, 4 * BEAT + .5) * .42, start)
        if bar % 8 == 7:
            t = times(4 * BEAT)
            place(high, lowpass(saw(180 + 240 * (t / t[-1]) ** 2, t, 3, 10), 2300) * .3 * t / t[-1], start)
    left, right = mix((low, high, drums), .38)
    left, right = np.tanh(left * 1.9), np.tanh(right * 1.9)
    return loop_tail(left, right, bars * 4 * BEAT)


def plasma_loop(seconds):
    """Deep molten roar with slow bubbling; the ends crossfade so it loops cleanly."""
    t = times(seconds + 1)
    hum = lowpass(rng.normal(size=t.size), 140) * 7
    hiss = fft_filter(rng.normal(size=t.size), 500, 2400) * .16 * (1 + .6 * np.sin(2 * np.pi * .7 * t))
    bubbles = np.zeros(t.size)
    for _ in range(int(9 * seconds)):
        start = int(rng.uniform(0, seconds) * RATE)
        size = int(rng.uniform(.04, .14) * RATE)
        hz = rng.uniform(70, 240)
        grain = np.sin(2 * np.pi * np.cumsum(hz * (1 + np.arange(size) / size)) / RATE) * np.hanning(size)
        bubbles[start:start + size] += grain[:len(bubbles[start:start + size])] * rng.uniform(.12, .4)
    body = hum + hiss + bubbles
    fade = int(RATE)
    size = int(seconds * RATE)
    out = body[:size].copy()
    out[:fade] = out[:fade] * np.linspace(0, 1, fade) + body[size:size + fade] * np.linspace(1, 0, fade)
    return out


def plasma_burn():
    t = times(1.1)
    hiss = fft_filter(rng.normal(size=t.size), 700, 2500) * np.exp(-t * 3.6) * 1.5
    crack = lowpass(rng.normal(size=t.size), 1800) * np.exp(-t * 38) * 2
    thump = np.sin(2 * np.pi * np.cumsum(50 + 150 * np.exp(-t * 26)) / RATE) * np.exp(-t * 7) * 1.6
    return hiss + crack + thump


def chime(notes, seconds, spread, bright):
    """Soft bell partials struck in a quick upward run."""
    out = np.zeros(int((seconds + .4) * RATE))
    for index, midi in enumerate(notes):
        t = times(seconds)
        tone = sum(np.sin(2 * np.pi * note_hz(midi) * ratio * t) * level for ratio, level in ((1, 1), (2, bright), (3.01, bright * .45)))
        place(out, tone * np.exp(-t * 5) * np.minimum(t * 300, 1), index * spread)
    return out


def epic():
    """The main theme: choir and strings open, a brass motif rises, the full orchestra answers."""
    global BEAT
    BEAT = 60 / 72
    keys = ('D', 'Bb', 'F', 'C', 'D', 'Bb', 'G', 'A')
    motif = ((0, 14, 2), (2, 17, 1), (3, 21, 1), (4, 19, 2), (6, 17, 1), (7, 16, 1),
             (8, 14, 3), (11, 12, 1), (12, 10, 2), (14, 12, 2))
    bars = 36
    total = int((bars * 4 * BEAT + 6) * RATE)
    low, high, drums = np.zeros(total), np.zeros(total), np.zeros(total)
    boom = taiko(2.2)
    for bar in range(bars):
        name = keys[bar % 8]
        root = ROOTS[name]
        start = bar * 4 * BEAT
        part = 0 if bar < 8 else 1 if bar < 16 else 2 if bar < 32 else 3
        swell = (bar % 8 + 1) / 8
        place(low, strings(root, 4 * BEAT + .4, 380) * (.5 + .3 * swell), start)
        place(low, strings(root + 12, 4 * BEAT + .4, 600) * .45, start)
        for tone in CHORDS[name]:
            place(high, choir(root + 24 + tone, 4 * BEAT + 1.2) * (.22 if part == 0 else .34), start)
        if part == 0:
            if bar % 2 == 0:
                place(drums, boom * .7, start)
            continue
        for tone in CHORDS[name]:
            place(high, strings(root + 24 + tone, 4 * BEAT + .3, 2200) * .26, start)
        if bar % 2 == 0 and part < 3:
            for when, degree, length in motif:
                if when < 16:
                    beat_at = (when % 8) * BEAT / 2 + (4 * BEAT if when >= 8 else 0)
                    if bar * 4 * BEAT + beat_at < total / RATE - 2:
                        lift = 12 if part == 2 else 0
                        place(high, brass(ROOTS['D'] + 12 + degree + lift, length * BEAT / 2 + .25) * (.75 if part == 1 else .95), start + beat_at)
        for offset, level in ((0, 1.3), (1, .5), (2, .9), (3, .55), (3.5, .7)):
            place(drums, boom * level * (1.1 if part == 2 else .8), start + offset * BEAT)
        if part >= 2:
            for step in range(8):
                place(low, strings(root + 12 + (7 if step % 4 == 2 else 0), BEAT * .45, 1400) * .4, start + step * BEAT / 2)
        if part == 3:
            place(high, brass(root + 12, 4 * BEAT) * (1 - swell) * .8, start)
    left, right = mix((low, high, drums), .75)
    return loop_tail(left, right, bars * 4 * BEAT)


def piano(midi, seconds, level=1.0):
    t = times(seconds)
    hz = note_hz(midi)
    tone = sum(np.sin(2 * np.pi * hz * k * (1 + .0004 * k * k) * t) * np.exp(-t * (1.2 + k * .9)) / k ** 1.3 for k in range(1, 8))
    hammer = lowpass(rng.normal(size=t.size), 3000) * np.exp(-t * 80) * .08
    return (tone + hammer) * np.minimum(t * 400, 1) * level


def kick():
    t = times(.45)
    return np.sin(2 * np.pi * np.cumsum(48 + 120 * np.exp(-t * 34)) / RATE) * np.exp(-t * 7) * 1.4


def snare():
    t = times(.35)
    return (fft_filter(rng.normal(size=t.size), 1200, 9000) * 1.2 * np.exp(-t * 16) + np.sin(2 * np.pi * 200 * t) * np.exp(-t * 26) * .7)


def hat(open_=False):
    t = times(.25 if open_ else .06)
    return fft_filter(rng.normal(size=t.size), 7000, 16000) * np.exp(-t * (14 if open_ else 70)) * .45


def load_voice(name):
    with wave.open(str(ROOT / 'Art/Audio/Vox' / (name + '.wav'))) as source:
        data = np.frombuffer(source.readframes(source.getnframes()), '<i2').astype(float) / 32768
    return fft_filter(data, 150, 7000)


def bell(midi, seconds, level=1.0):
    t = times(seconds)
    hz = note_hz(midi)
    tone = np.sin(2 * np.pi * hz * t + 1.2 * np.sin(2 * np.pi * hz * 2.01 * t) * np.exp(-t * 3)) * np.exp(-t * 2.2)
    return tone * np.minimum(t * 300, 1) * level


def riser(seconds):
    t = times(seconds)
    sweep = lowpass(rng.normal(size=t.size), 200 + 7000 * (t / t[-1]) ** 2)
    return sweep * (t / t[-1]) ** 2 * .6


def moby():
    """Eight sections: intro, half-time verse, pre-chorus, chorus, breakdown, build, key-change chorus, outro."""
    beat = 60 / 98
    major = (0, 4, 7, 12)
    minor = (0, 3, 7, 12)
    F, C, Dm, Bb, Am, G, D, Em, Cc = ((41, major), (36, major), (38, minor), (34, major), (33, minor),
                                      (43, major), (38, major), (40, minor), (36, major))
    # Name, bars, progression, drums, vocal lines by bar within the section.
    sections = (('intro', 8, (F, C, Dm, Bb), 'none', {2: 'star', 6: 'home'}),
                ('verse', 8, (F, C, Dm, Bb), 'half', {0: 'peace', 2: 'peace_low', 4: 'peace', 6: 'searching'}),
                ('pre', 4, (Dm, Bb, F, C), 'build', {0: 'nothing', 2: 'gentle'}),
                ('chorus', 8, (F, C, Dm, Bb), 'full', {0: 'peace', 2: 'creating', 4: 'peace', 6: 'searching', 7: 'creating'}),
                ('breakdown', 8, (Bb, Cc, Am, Dm), 'none', {1: 'hold', 4: 'nothing', 6: 'home'}),
                ('build', 4, (Bb, Cc, Am, Cc), 'four', {0: 'searching', 2: 'creating', 3: 'searching'}),
                ('lift', 16, (G, D, Em, Cc), 'full', {0: 'peace', 2: 'peace_low', 4: 'hold', 6: 'searching', 7: 'creating', 8: 'peace', 10: 'gentle', 12: 'peace', 14: 'searching', 15: 'creating'}),
                ('outro', 8, (F, C, Dm, Bb), 'fade', {1: 'home', 4: 'star', 6: 'searching'}))
    bars = sum(section[1] for section in sections)
    total = int((bars * 4 * beat + 6) * RATE)
    music, pads, drums, vox, lead = (np.zeros(total) for _ in range(5))
    voices = {name: load_voice(name) for name in ('star', 'peace', 'peace_low', 'nothing', 'gentle', 'searching', 'creating', 'hold', 'home')}
    kicks, snares = kick(), snare()
    hook = (7, 9, 12, 9, 7, 4, 2, 4)
    counter = (12, 11, 9, 7)
    bar = 0
    for name, length, progression, groove, lines in sections:
        for inner in range(length):
            root, chord = progression[inner % len(progression)]
            start = bar * 4 * beat
            last = inner == length - 1
            if name == 'intro':
                for tone in chord[:3]:
                    place(music, piano(root + 24 + tone, 3.0, .55), start)
                place(music, piano(root + 36 + chord[2], 1.5, .3), start + 2 * beat)
            elif name in ('breakdown', 'outro'):
                for step, tone in enumerate((0, 2, 1, 3, 2, 1)):
                    place(music, piano(root + 36 + chord[tone], 1.2, .28), start + step * beat * 2 / 3)
                if name == 'breakdown':
                    place(lead, bell(root + 48 + hook[inner % 8] - 12, 2.0, .35), start + beat)
            else:
                for offset in (0, 1.5, 3) if name != 'verse' else (0, 2):
                    for tone in chord:
                        place(music, piano(root + 24 + tone, 2.0, .62 if offset == 0 else .45), start + offset * beat)
                if name in ('chorus', 'lift'):
                    for step, degree in enumerate(hook):
                        if (inner + step) % 3 != 2:
                            place(lead, bell(root + 36 + degree + (12 if name == 'lift' else 0), .9, .32), start + step * beat / 2)
            for tone in chord[:3]:
                place(pads, strings(root + 24 + tone, 4 * beat + .4, 900 if name == 'breakdown' else 1600) * (.16 if name in ('intro', 'outro') else .3), start)
            if name == 'lift':
                place(pads, strings(root + 36 + counter[inner % 4], 4 * beat, 2400) * .22, start)
            if name in ('pre', 'build') and inner == length - 1:
                place(pads, riser(4 * beat), start)
            if groove != 'none':
                pattern = {'half': (0, 10), 'build': (0, 8), 'full': (0, 6, 10), 'four': (0, 4, 8, 12), 'fade': (0, 10)}[groove]
                fade = (1 - inner / length) if groove == 'fade' else 1.0
                for offset, span in ((0, 1.2), (1.5, .4), (2, 1.2), (3.5, .4)) if groove != 'half' else ((0, 3.5),):
                    tone = root + 12 + (7 if (groove == 'full' and offset == 3.5) else 0)
                    place(music, lowpass(saw(note_hz(tone), times(span * beat), 2, 4), 360) * np.exp(-times(span * beat) * 1.3) * 1.1 * fade, start + offset * beat)
                for step in range(16):
                    when = start + step * beat / 4 + (beat / 4) * (.12 if step % 2 else 0)
                    if step in pattern:
                        place(drums, kicks * fade, when)
                    if groove == 'half' and step == 8 or groove in ('full', 'four', 'fade') and step in (4, 12):
                        place(drums, snares * fade, when)
                    if groove == 'build' and step % 2 == 0:
                        place(drums, snares * (.2 + .05 * inner + .02 * step), when)
                    if groove != 'half' or step % 4 == 0:
                        place(drums, hat(step == 14 and groove == 'full') * (.85 if step % 4 == 2 else .5) * fade, when)
                    if last and groove == 'full' and step >= 12:
                        place(drums, snares * (.4 + .12 * (step - 12)), when)
            if inner in lines:
                phrase = lines[inner]
                place(vox, voices[phrase] * (.9 if 'low' in phrase else 1.0), start + .5 * beat)
                if name == 'lift' and phrase in ('peace', 'searching', 'creating'):
                    place(vox, voices['peace_low' if phrase == 'peace' else phrase] * .4, start + 2.5 * beat)
            bar += 1
    left_music, right_music = stereo_hall(music + pads, 2.2, .35)
    left_lead, right_lead = stereo_hall(lead, 1.6, .5)
    left_vox, right_vox = stereo_hall(vox, 2.8, .6)
    left_drums, right_drums = stereo_hall(drums, .8, .12)
    size = min(len(left_music), len(left_vox), len(left_drums), len(left_lead))
    left = left_music[:size] * .8 + left_lead[:size] * .55 + left_vox[:size] * 1.1 + left_drums[:size] * .9
    right = right_music[:size] * .8 + right_lead[:size] * .65 + right_vox[:size] * 1.1 + right_drums[:size] * .9
    level = max(np.abs(left).max(), np.abs(right).max())
    left, right = np.tanh(left / level * 1.3), np.tanh(right / level * 1.3)
    return loop_tail(left, right, bars * 4 * beat)


def pitched(voice, ratio):
    """Resamples a phrase to shift its pitch; ratio below one is lower and slower."""
    size = int(len(voice) / ratio)
    return np.interp(np.arange(size) * ratio, np.arange(len(voice)), voice)


def epic_vocal():
    """Orchestral and choral, with the peace and creation lyrics chanted over the climaxes."""
    global BEAT
    BEAT = 60 / 76
    D, Bb, F, C, G, A, Gm, Eb = (('D', 38), ('Bb', 34), ('F', 41), ('C', 36), ('G', 43), ('A', 33), ('Gm', 43), ('Eb', 39))
    minor = (0, 3, 7)
    major = (0, 4, 7)
    shape = {'D': minor, 'Gm': minor, 'Bb': major, 'F': major, 'C': major, 'G': major, 'A': major, 'Eb': major}
    # Name, bars, progression, intensity 0..3, lyric lines by bar.
    sections = (('dawn', 8, (D, Bb, F, C), 0, {2: 'star', 6: 'home'}),
                ('rise', 8, (D, Bb, F, A), 1, {0: 'peace', 4: 'peace_low'}),
                ('march', 8, (Gm, Eb, Bb, F), 2, {0: 'nothing', 2: 'gentle', 4: 'searching', 6: 'creating'}),
                ('hymn', 8, (Bb, F, Gm, D), 3, {0: 'peace', 2: 'hold', 4: 'peace', 6: 'searching', 7: 'creating'}),
                ('quiet', 4, (Eb, Bb, C, A), 0, {1: 'hold'}),
                ('crown', 12, (D, Bb, F, C, G, A), 3, {0: 'peace', 2: 'gentle', 4: 'nothing', 6: 'peace', 8: 'searching', 9: 'creating', 10: 'home'}),
                ('end', 4, (D, Bb, F, D), 1, {1: 'star'}))
    motif = ((0, 7, 2), (2, 10, 1), (3, 12, 1), (4, 14, 3), (7, 12, 1), (8, 10, 2), (10, 12, 2), (12, 7, 4))
    bars = sum(section[1] for section in sections)
    total = int((bars * 4 * BEAT + 8) * RATE)
    low, high, drums, vox = (np.zeros(total) for _ in range(4))
    voices = {name: load_voice(name) for name in ('star', 'peace', 'peace_low', 'nothing', 'gentle', 'searching', 'creating', 'hold', 'home')}
    boom, snap = taiko(2.4), snare()
    bar = 0
    for name, length, progression, heat, lines in sections:
        for inner in range(length):
            key, root = progression[inner % len(progression)]
            chord = shape[key]
            start = bar * 4 * BEAT
            place(low, strings(root, 4 * BEAT + .4, 300 + 120 * heat) * (.55 + .15 * heat), start)
            place(low, strings(root - 12, 4 * BEAT + .4, 220) * (.3 + .2 * heat), start)
            for tone in chord:
                place(high, choir(root + 24 + tone, 4 * BEAT + 1.2) * (.2 + .08 * heat), start)
                if heat:
                    place(high, strings(root + 24 + tone, 4 * BEAT + .3, 1600 + 600 * heat) * (.14 + .06 * heat), start)
            if heat >= 1:
                for offset, level in ((0, 1.3), (2, .9)) if heat == 1 else ((0, 1.4), (1, .5), (1.5, .45), (2, 1.0), (3, .7), (3.5, .8)):
                    place(drums, boom * level, start + offset * BEAT)
            if heat >= 2:
                for step in range(8):
                    place(low, strings(root + 12 + (7 if step % 4 == 3 else 0), BEAT * .45, 1500) * .45, start + step * BEAT / 2)
                if heat == 3 and inner % 2 == 1:
                    for step in (12, 13, 14, 15):
                        place(drums, snap * (.3 + .1 * (step - 12)), start + step * BEAT / 4)
            if heat >= 2 and inner % 2 == 0:
                for when, degree, span in motif:
                    lift = 12 if name == 'crown' else 0
                    place(high, brass(38 + 12 + degree + lift, span * BEAT / 2 + .3) * (.8 + .1 * heat), start + when * BEAT / 2)
            if name == 'quiet':
                place(high, bell(root + 48 + chord[inner % 3], 3.0, .4), start)
            if inner == length - 1 and name in ('rise', 'march', 'quiet'):
                place(high, riser(4 * BEAT) * 1.4, start)
            if inner in lines:
                phrase = voices[lines[inner]]
                place(vox, phrase * (1.1 if heat >= 2 else .9), start + .25 * BEAT)
                place(vox, pitched(phrase, .5) * (.55 if heat >= 2 else .35), start + .25 * BEAT)
                if heat == 3:
                    place(vox, pitched(phrase, 1.0) * .4, start + 2.25 * BEAT)
            bar += 1
    left_low, right_low = stereo_hall(low, 2.4, .45)
    left_high, right_high = stereo_hall(high, 3.4, .9)
    left_drums, right_drums = stereo_hall(drums, 2.0, .55)
    left_vox, right_vox = stereo_hall(vox, 3.8, 1.1)
    size = min(len(left_low), len(left_high), len(left_drums), len(left_vox))
    left = left_low[:size] * .9 + left_high[:size] * 1.05 + left_drums[:size] * .95 + left_vox[:size] * 1.2
    right = right_low[:size] * .9 + right_high[:size] * .95 + right_drums[:size] * .95 + right_vox[:size] * 1.2
    level = max(np.abs(left).max(), np.abs(right).max())
    left, right = np.tanh(left / level * 1.5), np.tanh(right / level * 1.5)
    return loop_tail(left, right, bars * 4 * BEAT)


if 'epicvox' in sys.argv:
    left, right = epic_vocal()
    write('S_Music_MainTheme', left, right, peak=.92)
    print('EPICVOX DONE', flush=True)
    os._exit(0)

if 'moby' in sys.argv:
    left, right = moby()
    write('S_Music_MainTheme', left, right, peak=.9)
    print('MOBY DONE', flush=True)
    os._exit(0)

if 'epic' in sys.argv:
    left, right = epic()
    write('S_Music_MainTheme', left, right, peak=.9)
    print('EPIC DONE', flush=True)
    os._exit(0)

if 'plasma' in sys.argv:
    left = plasma_loop(8)
    write('S_PlasmaLoop', left, np.roll(left, 900), peak=.8)
    left, right = stereo_hall(plasma_burn(), .7, .5)
    write('S_PlasmaBurn', left, right, peak=.9)
    for name, notes, spread, bright, peak in (('S_PickupHealth', (64, 69, 76), .07, .35, .6), ('S_PickupDivinity', (62, 69, 74, 81), .09, .25, .6),
                                              ('S_PickupAmmo', (50, 57), .05, .7, .7), ('S_PickupFuse', (57, 64, 69, 76), .1, .5, .7)):
        left, right = stereo_hall(chime(notes, .8, spread, bright), 1.1, .5)
        write(name, left, right, peak=peak)
    print('PLASMA DONE', flush=True)
    os._exit(0)

if 'battle' in sys.argv:
    for index in range(2):
        left, right = stereo_hall(laser(index), .5, .5)
        write('S_Laser%d' % (index + 1), left, right, peak=.7)
    left, right = stereo_hall(laser_hit(5), .4, .4)
    write('S_LaserHit', left, right, peak=.8)
    left, right = battle()
    write('S_Music_Combat', left, right, peak=.95)
    print('BATTLE DONE', flush=True)
    os._exit(0)

for index, (seconds, depth) in enumerate(((4.5, 2.4), (5.5, 2.8), (3.5, 2.0))):
    left, right = stereo_hall(explosion(index + 1, seconds, depth), 1.4, .8)
    write('S_Explosion%d' % (index + 1), left, right)
left, right = stereo_hall(explosion(9, 2.2, 1.6), .7, .5)
write('S_DroneExplosion', left, right)
for index, high in enumerate((2600, 3400, 1900)):
    write('S_SwordSwing%d' % (index + 1), whoosh(index, .36, high), peak=.7)
write('S_SwordHeavy', whoosh(8, .6, 1300) + lowpass(rng.normal(size=int(.6 * RATE)), 240) * np.hanning(int(.6 * RATE)) * 1.3, peak=.8)
for index in range(2):
    left, right = stereo_hall(flesh_hit(index + 20) + clang(index + 30, .42, 930 + index * 160) * .25, .35, .35)
    write('S_SwordHit%d' % (index + 1), left, right)
left, right = stereo_hall(clang(40, 1.6, 610) + clang(41, 1.6, 1187) * .6, 1.6, 1.0)
write('S_Parry', left, right)
left, right = stereo_hall(clang(44, .5, 780), .4, .4)
write('S_Block', left, right, peak=.6)
print('sounds done', flush=True)

left, right = mix(score(23, ('D', 'D', 'Bb', 'A', 'D', 'F', 'C', 'A'), 'rise', 4), .9)
write('S_Music_Theme', left, right, peak=.85)
print('theme done', flush=True)
bars = 16
left, right = mix(score(bars, ('D', 'Bb', 'F', 'A', 'D', 'G', 'Bb', 'A'), 'fight', 4), .55)
left, right = loop_tail(left, right, bars * 4 * BEAT)
write('S_Music_Combat', left, right, peak=.85)
print('combat done', flush=True)
export_arc()
print('ALL DONE', flush=True)
