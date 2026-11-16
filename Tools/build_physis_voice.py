"""Generates Divinity's narration with Kokoro, then gives it her reverb.

Run with the Kokoro venv: python build_physis_voice.py MODELS_DIR OUTPUT_DIR [--samples] [--center] [--conclave] [--grove] [--arche]
Text comes from Content/Python/physis_lore.py. Output is 44.1 kHz stereo wav.
--conclave voices level 3 from Content/Python/physis_conclave_lore.py into OUTPUT_DIR (Art/Audio/Conclave/Voice):
Divinity's scans and arrival line, then every page of every person in that person's own voice, set in a
space that suits what they are (KINDS). For tests it takes --only NAME[,NAME...] (wav names, shell-style
patterns) and --limit N (at most N new files).
--grove voices level 4 the same way from Content/Python/physis_grove_lore.py into OUTPUT_DIR (Art/Audio/Grove/Voice);
its Director speaks over intercom posts (kind 'radio') until she is met in person (kind 'human').
"""
import fnmatch
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import soundfile
from kokoro_onnx import EspeakConfig, Kokoro

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Content/Python'))
from physis_lore import all_entries, voice_name  # noqa: E402

VOICE = 'bf_emma'
SPEED = .9
# Lowered a touch and set in a very large, soft space.
EFFECT = ('asetrate=24000*0.97,aresample=44100,atempo=1.03,'
          'aecho=0.8:0.55:70|140|260|430:0.26|0.2|0.14|0.09,apad=pad_dur=0.9,loudnorm=I=-12:TP=-1:LRA=9,aformat=channel_layouts=stereo')
SPOKEN = (('Q.', 'Q.'), ('AL ', 'A.L. '), ('Mecha', 'Mekka'), ('Mechanoid', 'Meck-anoid'), ('Divinity', 'Divinity'), ('4,015', 'four thousand and fifteen'))
# Conclave names as espeak (Kokoro's phonemes) reads them wrongly, checked phoneme by phoneme: Kairos
# rhymed with "rose", Orsolya as "Or-suh-lia" (it is Hungarian, OR-shoy-a), Iriel with a short "irr",
# Rhea as one syllable. Halden reads correctly. AL is respelt before these run (see conclave()).
CONCLAVE_SPOKEN = (('Kairos', 'Kaiross'), ('Orsolya', 'Orshoya'), ('Iriel', 'Iri-el'), ('Rhea', 'Reea')) + SPOKEN

# The Conclave's people by kind (physis_conclave_lore.PEOPLE[4]): Kokoro speed, the ffmpeg chain on
# Kokoro's 24 kHz take, and the space they speak in (room() arguments). Every chain then runs through
# its room's impulse response with afir and ends at Divinity's loudness.
KINDS = {
    # A person in a small warm room: a little more body in the low mids, sibilance eased, close walls
    # whose treble dies quickly. Nothing like Divinity's vast space.
    'human': (SPEED, 'aresample=44100,highpass=f=70,equalizer=f=210:t=q:w=1:g=1.5,highshelf=f=6500:g=-1.5',
              dict(rt60=.34, drr=12, damp=.3, share=.45, seed=11,
                   early=((3.1, 1), (5.3, .85), (7.9, .7), (11.2, .55), (14.6, .42), (19.8, .3)))),
    # A Robot: a voice box's narrow band, a quarter of the signal ring-modulated at 72 Hz (a buzz on
    # every vowel, every consonant still clear), a short tube resonance, a hard bright little room.
    'robot': (SPEED, 'aresample=44100,highpass=f=230,lowpass=f=5200,aeval=val(0)*(0.76+0.24*sin(2*PI*72*t)),'
                     'flanger=delay=1.6:depth=0:regen=-30:width=40:speed=0.1,equalizer=f=2000:t=q:w=1.4:g=2.5',
              dict(rt60=.45, drr=10, damp=.08, share=.5, seed=12, early=((2.2, 1), (3.9, .9), (6.1, .75), (8.4, .6), (12.5, .4)))),
    # A Mechanoid: a semitone and a half down (tempo kept), two inharmonic feedback combs for the ring of
    # a metal chest, more weight below and a little compression; it speaks in the Foundry's hall.
    'mechanoid': (SPEED, 'asetrate=24000*0.92,aresample=44100,atempo=1.087,highpass=f=80,'
                         'flanger=delay=2.3:depth=0:regen=45:width=35:speed=0.1,flanger=delay=3.9:depth=0:regen=30:width=25:speed=0.1,'
                         'lowshelf=f=170:g=3,acompressor=threshold=0.125:ratio=2.5:attack=8:release=160:makeup=1.4',
                  dict(rt60=1.1, drr=6, damp=.25, share=.3, seed=13, early=((9, 1), (17, .8), (26, .65), (38, .5)))),
    # A Mecha: slower speech, four semitones down, a comb at 7.5 ms (a body ringing near 133 Hz and its
    # harmonics) with two body resonances, dark and heavy, in a large space.
    'mecha': (.85, 'asetrate=24000*0.8,aresample=44100,atempo=1.15,highpass=f=40,'
                   'flanger=delay=7.5:depth=0:regen=50:width=40:speed=0.1,equalizer=f=110:t=q:w=1:g=4,equalizer=f=340:t=q:w=1.4:g=2,'
                   'lowpass=f=6000,acompressor=threshold=0.15:ratio=2:attack=15:release=250:makeup=1.3',
              dict(rt60=1.7, drr=4, damp=.35, share=.25, seed=14, early=((5, 1), (11, .85), (19, .7), (31, .55), (47, .4)))),
    # A Lightform: a soft three-voice chorus, air added above 5 kHz, and a gentle long reverb whose
    # treble lingers (little damping) after a short pre-delay.
    'light': (SPEED, 'aresample=44100,highpass=f=110,chorus=0.7:0.9:38|51|66:0.32|0.26|0.2:0.23|0.31|0.42:1.4|1.9|2.4,'
                     'aexciter=amount=1.1:drive=6:freq=5500:ceil=16000,highshelf=f=7500:g=2',
              dict(rt60=2.6, drr=2, damp=.12, share=.15, seed=15, predelay=.025, early=((12, 1), (19, .8), (29, .65), (41, .5)))),
}
# A person heard over an intercom post (level 4's Director Voss): a small speaker's band, hard compression and a
# little overdrive, a presence peak, and the post's own tiny metal box for a room.
KINDS['radio'] = (SPEED, 'aresample=44100,highpass=f=380,lowpass=f=3200,acompressor=threshold=0.09:ratio=6:attack=2:release=60:makeup=2,'
                         'asoftclip=type=tanh,equalizer=f=1800:t=q:w=1.2:g=4,highpass=f=300',
                  dict(rt60=.22, drr=14, damp=.5, share=.5, seed=16, early=((1.4, 1), (2.6, .7), (4.1, .5))))
GROVE_SPOKEN = (('Thessaly-4', 'Thessaly Four'), ('Verdance', 'Verdanss')) + SPOKEN
# Level 5's First Ones: unhurried, a tone and a half down with the tempo kept, a faint doubled voice a fifth of a
# second of shimmer behind the first (they speak as if from inside stone), in a tall stone hall. A speaking stone
# carries a voice the same way through rock: the band narrowed, a comb for the stone's ring, a small hard space.
KINDS['firstone'] = (.84, 'asetrate=24000*0.9,aresample=44100,atempo=1.111,highpass=f=60,'
                          'chorus=0.8:0.85:46|63:0.22|0.16:0.18|0.26:1.1|1.6,lowshelf=f=180:g=2,highshelf=f=7000:g=-1',
                     dict(rt60=1.9, drr=5, damp=.2, share=.2, seed=17, predelay=.012, early=((7, 1), (13, .8), (22, .65), (35, .5), (52, .35))))
KINDS['stone'] = (.84, 'asetrate=24000*0.9,aresample=44100,atempo=1.111,highpass=f=160,lowpass=f=4200,'
                       'flanger=delay=4.6:depth=0:regen=40:width=30:speed=0.1,equalizer=f=520:t=q:w=1.2:g=3',
                  dict(rt60=.6, drr=8, damp=.15, share=.45, seed=18, early=((2.4, 1), (4.3, .8), (6.9, .6), (10.2, .4))))
ARCHE_SPOKEN = (('Arche', 'Ar-kee'), ('Kathodos', 'Kathodoss'), ('Aeon', 'Ee-on'), ('Maruth', 'Maruth'), ('Oreth', 'Oreth'), ('Sael', 'Sah-el'),
                ('Ilun', 'Iloon')) + SPOKEN
# Kokoro's speech peaks sit 15-19 dB over its loudness, but -12 LUFS under -1 dBTP leaves room for 11, so
# loudnorm alone limits the peakiest kinds (the robot) to -14. Levelling every take to -20 LUFS first
# gives a voice-over compressor the same input everywhere; it eases the syllable peaks, and loudnorm then
# reaches Divinity's -12 (measured: -12.0 to -12.7 LUFS for every kind).
LOUDNESS = ('loudnorm=I=-20:TP=-1:LRA=20,acompressor=threshold=-28dB:ratio=3:attack=3:release=80:knee=6,'
            'loudnorm=I=-12:TP=-1:LRA=9,aformat=channel_layouts=stereo')


def speak(engine, text, voice, target, effect=EFFECT, spoken=SPOKEN, speed=SPEED, room=None, scratch=None):
    for old, new in spoken:
        text = text.replace(old, new)
    audio, rate = engine.create(text.replace('~', ' '), voice=voice, speed=speed, lang='en-gb' if voice[0] == 'b' else 'en-us')
    # With `scratch` the raw take and the finished wav are made there and the wav is moved into place last, so
    # a stopped run leaves nothing stray, and no half-written wav that the next run would skip as done.
    made = scratch / target.name if scratch else target
    raw = made.with_suffix('.raw.wav')
    soundfile.write(raw, audio, rate)
    # A room is an impulse response wav: the effect's second input, convolved by its afir.
    rooms = ['-i', str(room)] if room else []
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw)] + rooms + ['-filter_complex', effect, '-ar', '44100', '-c:a', 'pcm_s16le', str(made)], check=True)
    raw.unlink()
    if made != target:
        shutil.move(str(made), str(target))


def room(path, rt60, drr, damp, share, early, seed, predelay=0.0, rate=44100):
    """Writes a stereo impulse response and returns its length in seconds. The voice itself is a unit
    impulse in both ears; early reflections from the nearest walls follow (ms, relative gain; alternate
    sides, each answered faintly on the other); then a diffuse tail grows out of them and falls 60 dB in
    rt60 seconds at 500 Hz, a little slower in the bass and faster in each octave above by `damp`, as
    air and soft surfaces take a real room's treble first. `drr` is the direct-to-reverberant ratio in
    dB (how close the listener stands) and `share` the part of the reverberant energy in the early
    reflections."""
    local = np.random.default_rng(seed)
    seconds = predelay + rt60 * 1.3 + .05
    n = int(seconds * rate)
    t = np.arange(n) / rate
    reflections = np.zeros((n, 2))
    for k, (ms, gain) in enumerate(early):
        at = int((predelay + ms / 1000) * rate)
        sign = (-1) ** (k // 2)
        reflections[at, k % 2] += gain * sign
        reflections[at + int(local.uniform(.3, 1.1) / 1000 * rate), 1 - k % 2] += gain * .6 * sign
    # Octave bands from 63 Hz to 16 kHz with triangular weights in log frequency, so they sum flat.
    octave = np.log2(np.maximum(np.fft.rfftfreq(n, 1 / rate), 1) / 500)
    tail = np.zeros((n, 2))
    for centre in range(-3, 6):
        weight = np.clip(1 - np.abs(octave - centre), 0, 1)
        if centre == -3:
            weight[octave < -3] = 1
        if centre == 5:
            weight[octave > 5] = 1
        decay = rt60 * (1 + .08 * max(-centre, 0)) / (1 + damp * max(centre, 0))
        for ch in range(2):
            tail[:, ch] += np.fft.irfft(np.fft.rfft(local.normal(size=n)) * weight, n) * np.exp(-6.91 * t / decay)
    tail *= (1 - np.exp(-np.clip(t - predelay - early[0][0] / 1000, 0, None) / .015))[:, None]
    reverb = 10 ** (-drr / 10)
    reflections *= np.sqrt(reverb * share / (reflections ** 2).sum(0).mean())
    tail *= np.sqrt(reverb * (1 - share) / (tail ** 2).sum(0).mean())
    ir = reflections + tail
    ir[0] += 1.0
    soundfile.write(path, ir.astype(np.float32), rate, subtype='FLOAT')
    return seconds


def conclave(engine, out):
    """Level 3: Divinity's scans and arrival line in her voice and effect, then every page of every
    person in their own voice and their kind's chain and room. Patience has no voice until the Shepherd
    falls, so his silent entry makes no file."""
    import physis_conclave_lore as lore
    jobs = [(voice_name(title), text, VOICE, None) for _, title, text in lore.conclave_entries() + [('Story',) + lore.ARRIVAL_LINE]]
    for person in lore.PEOPLE:
        if person[3]:
            jobs += [(voice_name(lore.person_key(person[0], k)), page, person[3], person[4]) for k, page in enumerate(lore.conversation_pages(person))]
    # Patterns match the names with or without '.wav'.
    only = [re.sub(r'\.wav$', '', p) for p in sys.argv[sys.argv.index('--only') + 1].split(',')] if '--only' in sys.argv else None
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else len(jobs)
    with tempfile.TemporaryDirectory() as scratch:
        scratch = pathlib.Path(scratch)
        spaces = {}
        for name, text, voice, kind in jobs:
            target = out / (name + '.wav')
            if target.exists() or (only and not any(fnmatch.fnmatch(name, pattern) for pattern in only)):
                continue
            if limit <= 0:
                break
            limit -= 1
            # SPOKEN's 'AL ' misses "the AL." and reads "of A.L." as "of a L"; this spelling holds everywhere.
            text = re.sub(r'\bAL\b', 'Eigh-ell', text)
            if kind is None:
                speak(engine, text, VOICE, target, spoken=CONCLAVE_SPOKEN, scratch=scratch)
            else:
                speed, chain, space = KINDS[kind]
                if kind not in spaces:
                    path = scratch / ('Room_%s.wav' % kind)
                    spaces[kind] = (path, room(path, **space))
                path, seconds = spaces[kind]
                effect = '[0:a]%s,apad=pad_dur=%.2f,pan=stereo|c0=c0|c1=c0[v];[v][1:a]afir=irnorm=-1,%s' % (chain, seconds, LOUDNESS)
                speak(engine, text, voice, target, effect, CONCLAVE_SPOKEN, speed, path, scratch)
            print(name, flush=True)


def grove(engine, out):
    """Level 4: Divinity's scans and arrival line in her voice and effect, then every page of every person in their own
    voice and their kind's chain and room (conclave()'s method, with the grove's lore and spellings)."""
    import physis_grove_lore as lore
    jobs = [(voice_name(title), text, VOICE, None) for _, title, text in lore.grove_entries() + [('Story',) + lore.ARRIVAL_LINE]]
    for person in lore.PEOPLE:
        if person[3]:
            jobs += [(voice_name(lore.person_key(person[0], k)), page, person[3], person[4]) for k, page in enumerate(lore.conversation_pages(person))]
    only = [re.sub(r'\.wav$', '', p) for p in sys.argv[sys.argv.index('--only') + 1].split(',')] if '--only' in sys.argv else None
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else len(jobs)
    with tempfile.TemporaryDirectory() as scratch:
        scratch = pathlib.Path(scratch)
        spaces = {}
        for name, text, voice, kind in jobs:
            target = out / (name + '.wav')
            if target.exists() or (only and not any(fnmatch.fnmatch(name, pattern) for pattern in only)):
                continue
            if limit <= 0:
                break
            limit -= 1
            if kind is None:
                speak(engine, text, VOICE, target, spoken=GROVE_SPOKEN, scratch=scratch)
            else:
                speed, chain, space = KINDS[kind]
                if kind not in spaces:
                    path = scratch / ('Room_%s.wav' % kind)
                    spaces[kind] = (path, room(path, **space))
                path, seconds = spaces[kind]
                effect = '[0:a]%s,apad=pad_dur=%.2f,pan=stereo|c0=c0|c1=c0[v];[v][1:a]afir=irnorm=-1,%s' % (chain, seconds, LOUDNESS)
                speak(engine, text, voice, target, effect, GROVE_SPOKEN, speed, path, scratch)
            print(name, flush=True)


def arche(engine, out):
    """Level 5: grove()'s method with Arche's lore and spellings (the AL respelt as in the Conclave)."""
    import physis_arche_lore as lore
    jobs = [(voice_name(title), text, VOICE, None) for _, title, text in lore.arche_entries() + [('Story',) + lore.ARRIVAL_LINE]]
    for person in lore.PEOPLE:
        if person[3]:
            jobs += [(voice_name(lore.person_key(person[0], k)), page, person[3], person[4]) for k, page in enumerate(lore.conversation_pages(person))]
    only = [re.sub(r'\.wav$', '', p) for p in sys.argv[sys.argv.index('--only') + 1].split(',')] if '--only' in sys.argv else None
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else len(jobs)
    with tempfile.TemporaryDirectory() as scratch:
        scratch = pathlib.Path(scratch)
        spaces = {}
        for name, text, voice, kind in jobs:
            target = out / (name + '.wav')
            if target.exists() or (only and not any(fnmatch.fnmatch(name, pattern) for pattern in only)):
                continue
            if limit <= 0:
                break
            limit -= 1
            text = re.sub(r'\bAL\b', 'Eigh-ell', text)
            if kind is None:
                speak(engine, text, VOICE, target, spoken=ARCHE_SPOKEN, scratch=scratch)
            else:
                speed, chain, space = KINDS[kind]
                if kind not in spaces:
                    path = scratch / ('Room_%s.wav' % kind)
                    spaces[kind] = (path, room(path, **space))
                path, seconds = spaces[kind]
                effect = '[0:a]%s,apad=pad_dur=%.2f,pan=stereo|c0=c0|c1=c0[v];[v][1:a]afir=irnorm=-1,%s' % (chain, seconds, LOUDNESS)
                speak(engine, text, voice, target, effect, ARCHE_SPOKEN, speed, path, scratch)
            print(name, flush=True)


def main():
    models, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    # ESPEAK_LIB / ESPEAK_DATA point at another espeak-ng (e.g. copies of the host's, from inside a sandbox).
    speech = EspeakConfig(lib_path=os.environ.get('ESPEAK_LIB', '/usr/lib64/libespeak-ng.so.1'),
                          data_path=os.environ.get('ESPEAK_DATA', '/usr/share/espeak-ng-data'))
    engine = Kokoro(str(models / 'kokoro-v1.0.onnx'), str(models / 'voices-v1.0.bin'), espeak_config=speech)
    if '--samples' in sys.argv:
        line = 'Two fleets, eleven years, and between them the same living substance. Divinity takes no side. Neither, you realize, do you.'
        for voice in ('bf_emma', 'af_heart', 'bf_lily'):
            speak(engine, line, voice, out / ('Divinity_Sample_%s.wav' % voice))
        return
    if '--conclave' in sys.argv:
        conclave(engine, out)
        return
    if '--grove' in sys.argv:
        grove(engine, out)
        return
    if '--arche' in sys.argv:
        arche(engine, out)
        return
    rows = all_entries()
    if '--center' in sys.argv:
        # Level 2: every Center scan plus the awakening line.
        from physis_center_lore import AWAKEN_LINE, center_entries
        rows = center_entries() + [('Story', 'Awakening', AWAKEN_LINE)]
    for category, title, text in rows:
        if (out / (voice_name(title) + '.wav')).exists():
            continue
        speak(engine, text, VOICE, out / (voice_name(title) + '.wav'))
        print(voice_name(title), flush=True)


main()
