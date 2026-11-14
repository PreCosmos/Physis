"""A small offline SoundFont (SF2/SF3) player for rendering the game's orchestral score.

Only what the score needs: preset and instrument zones by key and velocity, sample pitch,
looping, a volume envelope, attenuation and pan. SF3 samples are Ogg Vorbis and are decoded
with the system's ffmpeg.
"""
import struct
import subprocess

import numpy as np

RATE = 44100
GEN = {'startOffset': 0, 'endOffset': 1, 'startLoop': 2, 'endLoop': 3, 'pan': 17, 'attack': 34, 'hold': 35, 'decay': 36, 'sustain': 37,
       'release': 38, 'instrument': 41, 'keyRange': 43, 'velRange': 44, 'attenuation': 48, 'coarse': 51, 'fine': 52, 'sampleID': 53,
       'sampleModes': 54, 'rootKey': 58}


def chunks(data, start, end):
    while start < end:
        tag, size = data[start:start + 4], struct.unpack('<I', data[start + 4:start + 8])[0]
        yield tag, start + 8, size
        start += 8 + size + (size & 1)


class SoundFont:
    def __init__(self, path):
        data = open(path, 'rb').read()
        self.data = data
        top = {}
        for tag, at, size in chunks(data, 12, len(data)):
            if tag == b'LIST':
                kind = data[at:at + 4]
                for sub, sat, ssize in chunks(data, at + 4, at + size):
                    top[(kind, sub)] = (sat, ssize)
        self.smpl = top[(b'sdta', b'smpl')]
        get = lambda name: data[top[(b'pdta', name)][0]:top[(b'pdta', name)][0] + top[(b'pdta', name)][1]]
        self.phdr = [struct.unpack('<20sHHHIII', get(b'phdr')[i:i + 38]) for i in range(0, len(get(b'phdr')), 38)]
        self.pbag = [struct.unpack('<HH', get(b'pbag')[i:i + 4]) for i in range(0, len(get(b'pbag')), 4)]
        self.pgen = [struct.unpack('<Hh', get(b'pgen')[i:i + 4]) for i in range(0, len(get(b'pgen')), 4)]
        self.inst = [struct.unpack('<20sH', get(b'inst')[i:i + 22]) for i in range(0, len(get(b'inst')), 22)]
        self.ibag = [struct.unpack('<HH', get(b'ibag')[i:i + 4]) for i in range(0, len(get(b'ibag')), 4)]
        self.igen = [struct.unpack('<Hh', get(b'igen')[i:i + 4]) for i in range(0, len(get(b'igen')), 4)]
        self.shdr = [struct.unpack('<20sIIIIIBbHH', get(b'shdr')[i:i + 46]) for i in range(0, len(get(b'shdr')), 46)]
        self.cache = {}

    @staticmethod
    def zones(bags, gens, first, last):
        out = []
        for index in range(first, last):
            items = {}
            for g in range(bags[index][0], bags[index + 1][0]):
                op, amount = gens[g]
                items[op] = amount
            out.append(items)
        return out

    def preset(self, bank, number):
        for index, row in enumerate(self.phdr[:-1]):
            if row[1] == number and row[2] == bank:
                return self.zones(self.pbag, self.pgen, row[3], self.phdr[index + 1][3])
        raise KeyError((bank, number))

    def sample(self, index):
        if index not in self.cache:
            name, start, end, loop_start, loop_end, rate, pitch, correction, link, kind = self.shdr[index]
            base = self.smpl[0]
            if kind & 0x10:
                blob = self.data[base + start:base + end]
                raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', 'pipe:0', '-f', 'f32le', '-ac', '1', '-ar', str(rate), 'pipe:1'],
                                     input=blob, capture_output=True, check=True).stdout
                wave = np.frombuffer(raw, '<f4').astype(np.float32)
            else:
                wave = np.frombuffer(self.data[base + start * 2:base + end * 2], '<i2').astype(np.float32) / 32768
                loop_start, loop_end = loop_start - start, loop_end - start
            self.cache[index] = (wave, loop_start, loop_end, rate, pitch, correction)
        return self.cache[index]

    def voices(self, bank, number, key, velocity):
        """Every (generators, sample) pair that should sound for this key."""
        found = []
        pzones = self.preset(bank, number)
        pglobal = pzones[0] if pzones and GEN['instrument'] not in pzones[0] else {}
        for pzone in pzones:
            if GEN['instrument'] not in pzone or not in_range(pzone, key, velocity):
                continue
            row = self.inst[pzone[GEN['instrument']]]
            izones = self.zones(self.ibag, self.igen, row[1], self.inst[pzone[GEN['instrument']] + 1][1])
            iglobal = izones[0] if izones and GEN['sampleID'] not in izones[0] else {}
            for izone in izones:
                if GEN['sampleID'] not in izone or not in_range(izone, key, velocity):
                    continue
                gens = dict(iglobal)
                gens.update(izone)
                for op, amount in list(pglobal.items()) + list(pzone.items()):
                    if op not in (GEN['instrument'], GEN['keyRange'], GEN['velRange']):
                        gens[op] = gens.get(op, 0) + amount
                found.append((gens, izone[GEN['sampleID']]))
        return found


def in_range(zone, key, velocity):
    for op, value in ((GEN['keyRange'], key), (GEN['velRange'], velocity)):
        if op in zone:
            low, high = zone[op] & 0xFF, (zone[op] >> 8) & 0xFF
            if not low <= value <= high:
                return False
    return True


def seconds(timecents):
    return 2 ** (timecents / 1200) if timecents > -12000 else 0.0


def render_note(font, bank, number, key, velocity, length):
    """Returns a stereo float array for one note of `length` seconds plus its release."""
    out = None
    for gens, index in font.voices(bank, number, key, velocity):
        wave, loop_start, loop_end, rate, pitch, correction = font.sample(index)
        root = gens.get(GEN['rootKey'], pitch)
        root = pitch if root < 0 or root > 127 else root
        cents = (key - root) * 100 + gens.get(GEN['coarse'], 0) * 100 + gens.get(GEN['fine'], 0) - correction
        step = 2 ** (cents / 1200) * rate / RATE
        attack, hold = seconds(gens.get(GEN['attack'], -12000)), seconds(gens.get(GEN['hold'], -12000))
        decay, release = seconds(gens.get(GEN['decay'], -12000)), max(seconds(gens.get(GEN['release'], -12000)), .06)
        sustain = 10 ** (-max(gens.get(GEN['sustain'], 0), 0) / 200)
        total = int((length + min(release, 3.0)) * RATE)
        position = np.arange(total) * step
        looping = gens.get(GEN['sampleModes'], 0) & 1 and loop_end > loop_start + 8
        if looping:
            span = loop_end - loop_start
            beyond = position >= loop_end
            position[beyond] = loop_start + np.mod(position[beyond] - loop_start, span)
        else:
            position = position[position < len(wave) - 1]
        signal = np.interp(position, np.arange(len(wave)), wave).astype(np.float32)
        t = np.arange(len(signal)) / RATE
        envelope = np.where(t < attack, t / max(attack, 1e-4), 1.0)
        after = t - attack - hold
        decayed = np.where(after > 0, sustain + (1 - sustain) * np.exp(-after / max(decay / 5, 1e-3)), 1.0)
        envelope = envelope * np.where(t < attack, 1.0, decayed)
        fade = np.clip(1 - (t - length) / release, 0, 1) ** 2
        envelope *= np.where(t > length, fade, 1.0)
        gain = 10 ** (-gens.get(GEN['attenuation'], 0) / 200) * (velocity / 127) ** 1.6
        pan = np.clip(gens.get(GEN['pan'], 0) / 500, -1, 1)
        mono = signal * envelope * gain
        stereo = np.stack((mono * np.sqrt((1 - pan) / 2), mono * np.sqrt((1 + pan) / 2)), 1)
        if out is None or len(stereo) > len(out):
            grown = np.zeros((len(stereo), 2), np.float32)
            if out is not None:
                grown[:len(out)] += out
            out = grown
        out[:len(stereo)] += stereo
    return out if out is not None else np.zeros((1, 2), np.float32)
