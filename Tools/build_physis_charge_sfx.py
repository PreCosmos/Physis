"""Synthesizes the sidearm's charged-shot sounds.

Run with any Python that has numpy: python build_physis_charge_sfx.py
Writes Art/Audio/Game/S_ChargeReady.wav (a rising chime when the charge is full)
and Art/Audio/Game/S_ChargedShot.wav (a heavy plasma blast).
"""
import pathlib
import wave

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
RATE = 44100
rng = np.random.default_rng(7)


def write(name, signal):
    signal = signal / max(np.abs(signal).max(), 1e-6) * .89
    stereo = np.stack((signal, np.roll(signal, 18)), 1)
    with wave.open(str(ROOT / 'Art/Audio/Game' / (name + '.wav')), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((stereo * 32767).astype('<i2').tobytes())


def sweep(start, end, seconds, curve=2.0):
    t = np.arange(int(seconds * RATE)) / RATE
    freq = start + (end - start) * (t / seconds) ** curve
    return np.sin(2 * np.pi * np.cumsum(freq) / RATE), t


def lowpass(signal, amount):
    out = np.empty_like(signal)
    level = 0.0
    for i, value in enumerate(signal):
        level += amount * (value - level)
        out[i] = level
    return out


def charge_ready():
    """A short rising shimmer that lands on a bright two-note ping."""
    rise, t = sweep(420, 1680, .32, 1.6)
    rise *= np.minimum(t / .02, 1) * (.35 + .65 * t / .32)
    ping_t = np.arange(int(.55 * RATE)) / RATE
    ping = sum(np.sin(2 * np.pi * f * ping_t) * a for f, a in ((1760, 1), (2637, .55), (3520, .25)))
    ping *= np.exp(-ping_t * 7.5) * np.minimum(ping_t / .004, 1)
    shimmer = np.sin(2 * np.pi * 7 * ping_t) * .15 + .85
    sound = np.zeros(len(rise) + len(ping))
    sound[:len(rise)] += rise * .55
    sound[len(rise) - 600:len(rise) - 600 + len(ping)] += ping * shimmer
    return sound


def charged_shot():
    """Deep thump, a bright electric crack and a ringing, falling plasma tail."""
    seconds = 1.6
    t = np.arange(int(seconds * RATE)) / RATE
    thump_freq = 140 * np.exp(-t * 9) + 38
    thump = np.sin(2 * np.pi * np.cumsum(thump_freq) / RATE) * np.exp(-t * 5.5)
    noise = rng.normal(size=len(t))
    crack = (noise - lowpass(noise, .08)) * np.exp(-t * 38) * .9
    zap_freq = 2400 * np.exp(-t * 6) + 180
    zap = np.sign(np.sin(2 * np.pi * np.cumsum(zap_freq) / RATE)) * np.exp(-t * 4.2) * .22
    zap = lowpass(zap, .35)
    ring = sum(np.sin(2 * np.pi * f * t * (1 - .06 * t)) * a for f, a in ((310, .4), (465, .25), (930, .12))) * np.exp(-t * 2.4)
    rumble = lowpass(noise, .015) * np.exp(-t * 2.2) * 3.0
    attack = np.minimum(t / .002, 1)
    sound = (thump * 1.1 + crack + zap + ring * .5 + rumble) * attack
    return np.tanh(sound * 1.6)


def main():
    write('S_ChargeReady', charge_ready())
    write('S_ChargedShot', charged_shot())
    print('wrote S_ChargeReady, S_ChargedShot')


main()
