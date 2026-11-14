"""Composes and renders the Physis main theme through an orchestral SoundFont.

Run with any Python that has numpy: python build_physis_score.py SOUNDFONT
Writes Art/Audio/Game/S_Music_MainTheme.wav. Lyric phrases come from Art/Audio/Vox.
"""
import pathlib
import random
import sys
import wave

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import physis_soundfont as sf  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RATE = sf.RATE
BEAT = 60 / 80
rng = random.Random(4)

# General MIDI programs.
FLUTE, OBOE, HARP, VIOLIN, STRINGS, TREMOLO, CELLO, BASS = 73, 68, 46, 40, 48, 44, 42, 43
HORN, TRUMPET, TROMBONE, TUBA, CHOIR, OOHS, TIMPANI = 60, 56, 57, 58, 52, 53, 47

# Theme A and B as (beat in bar, midi, beats), one list per bar, written in D major.
THEME_A = (((0, 69, 1.5), (1.5, 74, .5), (2, 76, 1), (3, 78, 1)), ((0, 79, 2), (2, 78, 1), (3, 76, 1)),
           ((0, 74, 1.5), (1.5, 76, .5), (2, 78, 1), (3, 81, 1)), ((0, 79, 3.5),),
           ((0, 83, 1.5), (1.5, 81, .5), (2, 79, 1), (3, 78, 1)), ((0, 76, 2), (2, 74, 1), (3, 76, 1)),
           ((0, 78, 1.5), (1.5, 79, .5), (2, 76, 1), (3, 73, 1)), ((0, 74, 4),))
THEME_B = (((0, 78, 2), (2, 74, 1), (3, 76, 1)), ((0, 79, 2), (2, 78, 1), (3, 76, 1)),
           ((0, 78, 1.5), (1.5, 81, .5), (2, 79, 1), (3, 78, 1)), ((0, 76, 4),),
           ((0, 78, 2), (2, 74, 1), (3, 76, 1)), ((0, 79, 2), (2, 81, 1), (3, 83, 1)),
           ((0, 81, 1.5), (1.5, 79, .5), (2, 78, 1), (3, 76, 1)), ((0, 76, 2), (2, 73, 1), (3, 76, 1)))
MAJOR, MINOR = (0, 4, 7), (0, 3, 7)
PROG_A = ((38, MAJOR), (43, MAJOR), (38, MAJOR), (43, MAJOR), (40, MINOR), (45, MAJOR), (45, MAJOR), (38, MAJOR))
PROG_B = ((35, MINOR), (43, MAJOR), (38, MAJOR), (45, MAJOR), (35, MINOR), (43, MAJOR), (40, MINOR), (45, MAJOR))
PROG_BRIDGE = ((43, MAJOR), (35, MINOR), (40, MINOR), (45, MAJOR), (43, MAJOR), (35, MINOR), (36, MAJOR), (45, MAJOR))
# Section, bars of melody, chords, intensity 0..4, transpose, melody instruments, lyrics by bar.
SECTIONS = (('intro', THEME_A, PROG_A, 0, 0, (FLUTE,), {}),
            ('statement', THEME_A, PROG_A, 1, 0, (VIOLIN, STRINGS), {5: 'star'}),
            ('rising', THEME_B, PROG_B, 2, 0, (HORN, TRUMPET), {0: 'peace', 4: 'peace_low'}),
            ('bridge', THEME_A[:8], PROG_BRIDGE, 0, 0, (OBOE,), {1: 'hold', 5: 'home'}),
            ('anthem', THEME_A, PROG_A, 4, 0, (VIOLIN, STRINGS, TRUMPET, CHOIR), {0: 'peace', 2: 'gentle', 4: 'nothing', 6: 'creating'}),
            ('ascent', THEME_B, PROG_B, 4, 2, (VIOLIN, STRINGS, TRUMPET, HORN, CHOIR), {0: 'peace', 2: 'searching', 4: 'hold', 6: 'creating'}),
            ('coda', (((0, 74, 8),), ((0, 74, 4),)), ((38, MAJOR), (38, MAJOR)), 3, 2, (CHOIR, STRINGS, HORN), {0: 'home'}))


class Score:
    def __init__(self):
        self.events = []

    def note(self, program, key, start, beats, velocity, bank=0, group='orch'):
        velocity = max(1, min(127, int(velocity + rng.uniform(-6, 6))))
        self.events.append((group, bank, program, int(key), start + rng.uniform(0, .012), beats * BEAT, velocity))


def compose():
    score = Score()
    bar = 0
    for name, melody, chords, heat, shift, leads, lines in SECTIONS:
        for inner, ((root, quality), notes) in enumerate(zip(chords * 4, melody)):
            start = bar * 4 * BEAT
            root += shift
            triad = [root + 24 + step for step in quality]
            loud = (45, 64, 82, 100, 112)[heat]
            # Melody, doubled an octave up at the big moments.
            for when, key, beats in notes:
                for lead in leads:
                    lift = 12 if (lead in (VIOLIN, TRUMPET) and heat >= 4) else 0
                    if lead == CHOIR:
                        lift = -12
                    score.note(lead, key + shift + lift, start + when * BEAT, beats * 1.02, loud + (8 if when == 0 else 0))
            # Sustained harmony: strings pad, horns and choir as the music grows.
            pad = STRINGS if heat else OOHS
            for key in triad:
                score.note(pad, key, start, 4.05, loud - 18)
            if heat >= 2:
                for key in triad[1:]:
                    score.note(HORN, key - 12, start, 4.0, loud - 20)
            if heat >= 3:
                for key in triad:
                    score.note(CHOIR, key + 12, start, 4.05, loud - 22)
            # Bass line.
            score.note(CELLO, root + 12, start, 4.0, loud - 10)
            score.note(BASS, root, start, 4.0, loud - 12)
            if heat >= 3:
                score.note(TROMBONE, root + 12, start, 2.0, loud - 14)
                score.note(TUBA, root, start + 2 * BEAT, 2.0, loud - 14)
            # Motion: harp arpeggios when quiet, tremolo strings and timpani when loud.
            if heat <= 1:
                for step, key in enumerate((triad + [triad[0] + 12, triad[1] + 12, triad[2] + 12])[:8]):
                    score.note(HARP, key, start + step * BEAT / 2, 1.5, 58)
            if heat >= 2:
                for step in range(8):
                    score.note(TREMOLO, triad[step % 3] + 12, start + step * BEAT / 2, .5, loud - 26)
                score.note(TIMPANI, root + 12, start, 1.0, loud - 4)
                score.note(TIMPANI, root + 12 + 7, start + 2 * BEAT, 1.0, loud - 14)
            if heat >= 4:
                for step in (1, 3):
                    score.note(TIMPANI, root + 12, start + step * BEAT, .5, loud - 18)
                for step in range(4):
                    score.note(TRUMPET, triad[2] + 12, start + (step + .5) * BEAT, .4, loud - 30)
            if heat >= 3 and inner % 2 == 0:
                score.note(0, 49, start, 2.0, loud - 6, bank=128)
            if inner == len(melody) - 1 and name in ('rising', 'bridge'):
                for roll in range(16):
                    score.note(TIMPANI, root + 12, start + roll * BEAT / 4, .25, 40 + roll * 4)
            if inner in lines:
                score.events.append(('vox', 0, 0, 0, start + .2 * BEAT, lines[inner], heat))
            bar += 1
    return score, bar


def render(font, score, bars):
    total = int((bars * 4 * BEAT + 8) * RATE)
    groups = {'orch': np.zeros((total, 2), np.float32), 'vox': np.zeros((total, 2), np.float32)}
    cache = {}
    for event in score.events:
        if event[0] == 'vox':
            continue
        group, bank, program, key, start, length, velocity = event
        token = (bank, program, key, velocity // 8, round(length, 2))
        if token not in cache:
            cache[token] = sf.render_note(font, bank, program, key, velocity // 8 * 8 + 4, length)
        sound = cache[token]
        at = int(start * RATE)
        end = min(at + len(sound), total)
        groups['orch'][at:end] += sound[:end - at]
    for event in score.events:
        if event[0] != 'vox':
            continue
        start, phrase, heat = event[4], event[5], event[6]
        with wave.open(str(ROOT / 'Art/Audio/Vox' / (phrase + '.wav'))) as source:
            voice = np.frombuffer(source.readframes(source.getnframes()), '<i2').astype(np.float32) / 32768
        low = np.interp(np.arange(len(voice) * 2) * .5, np.arange(len(voice)), voice)
        for signal, level in ((voice, .9), (low, .45 if heat >= 3 else .25)):
            at = int(start * RATE)
            end = min(at + len(signal), total)
            groups['vox'][at:end] += np.stack((signal[:end - at], signal[:end - at]), 1) * level
    return groups


def fast_size(n):
    size = 1
    while size < n:
        size *= 2
    return size


def hall(signal, seconds, wet, seed):
    local = np.random.default_rng(seed)
    size = int(seconds * RATE)
    out = np.zeros_like(signal)
    for channel in range(2):
        tail = local.normal(size=size) * np.exp(-6.5 * np.arange(size) / size)
        tail /= np.sqrt((tail ** 2).sum())
        length = fast_size(len(signal) + size)
        wetted = np.fft.irfft(np.fft.rfft(signal[:, channel], length) * np.fft.rfft(tail, length), length)[:len(signal)]
        out[:, channel] = signal[:, channel] + wetted * wet
    return out


def main():
    font = sf.SoundFont(sys.argv[1])
    score, bars = compose()
    groups = render(font, score, bars)
    orch = hall(groups['orch'], 2.8, .45, 1)
    # The lyrics are carried by the choir; spoken phrases are left out of the mix.
    mix = orch / max(np.abs(orch).max(), 1e-6)
    # Gentle compression: quiet passages come up, the climax keeps its weight.
    window = int(.5 * RATE)
    energy = np.concatenate(([0.0], np.cumsum((mix ** 2).mean(1), dtype=np.float64)))
    index = np.arange(len(mix))
    low, high = np.clip(index - window // 2, 0, len(mix)), np.clip(index + window // 2, 0, len(mix))
    power = (energy[high] - energy[low]) / np.maximum(high - low, 1)
    level = np.sqrt(np.maximum(power, 1e-8))
    target = np.percentile(level, 90)
    gain = np.clip((target / level) ** .55, .6, 6.0)
    mix = mix * gain[:, None]
    mix = np.tanh(mix / np.abs(mix).max() * 1.25)
    mix = mix / np.abs(mix).max() * .92
    out = ROOT / 'Art/Audio/Game/S_Music_MainTheme.wav'
    with wave.open(str(out), 'wb') as target:
        target.setnchannels(2)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes((mix * 32767).astype('<i2').tobytes())
    print('SCORE DONE', flush=True); print('SCORE DONE', bars, 'bars', round(len(mix) / RATE, 1), 's', flush=True)


main()
