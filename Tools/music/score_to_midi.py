"""The main theme's notes (Tools/build_physis_score.py compose()) as a Standard MIDI File for a notation program.

Run with numpy on the path (the Kokoro venv's packages):
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/music/score_to_midi.py OUT.mid
One track per instrument (General MIDI program, named), 80 bpm in 4/4. The score's humanizing (a few ms on each
start, a little length over the beat) is taken out so the notes sit on a sixteenth-note grid and read as notation.
"""
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
source = (ROOT / 'Tools/build_physis_score.py').read_text().rsplit('\nmain()', 1)[0]
scope = {'__file__': str(ROOT / 'Tools/build_physis_score.py'), '__name__': 'score'}
exec(compile(source, 'build_physis_score.py', 'exec'), scope)
NAMES = {73: 'Flute', 68: 'Oboe', 46: 'Harp', 40: 'Violins', 48: 'Strings', 44: 'Tremolo Strings', 42: 'Violoncellos', 43: 'Contrabasses',
         60: 'Horn in F', 56: 'Trumpet', 57: 'Trombone', 58: 'Tuba', 52: 'Choir Aahs', 53: 'Voice Oohs', 47: 'Timpani'}
PPQ, GRID = 480, 120


def varlen(n):
    out = [n & 0x7F]
    while n >> 7:
        n >>= 7
        out.append(0x80 | n & 0x7F)
    return bytes(reversed(out))


def track(events):
    data, now = b'', 0
    for tick, _, message in sorted(events):
        data += varlen(tick - now) + message
        now = tick
    data += b'\x00\xff\x2f\x00'
    return b'MTrk' + struct.pack('>I', len(data)) + data


def main():
    score, bars = scope['compose']()
    beat = scope['BEAT']
    parts = {}
    for group, bank, program, key, start, length, velocity in (e for e in score.events if e[0] != 'vox'):
        on = round(start / beat * PPQ / GRID) * GRID
        ticks = max(GRID, round(length / beat * PPQ / GRID) * GRID)
        parts.setdefault((bank, program), []).append((on, ticks, key, velocity))
    meta = lambda kind, payload: b'\xff' + bytes([kind]) + varlen(len(payload)) + payload
    tracks = [track([(0, 0, meta(0x51, struct.pack('>I', round(60e6 / (60 / beat)))[1:])), (0, 0, meta(0x58, bytes([4, 2, 24, 8])))])]
    channel = 0
    for (bank, program), notes in sorted(parts.items()):
        drums = bank == 128
        ch = 9 if drums else channel
        if not drums:
            channel += 1 if channel != 8 else 2
        name = 'Cymbals' if drums else NAMES[program]
        events = [(0, 0, meta(0x03, name.encode()))]
        if not drums:
            events.append((0, 1, bytes([0xC0 | ch, program])))
        for on, ticks, key, velocity in notes:
            events.append((on, 3, bytes([0x90 | ch, key, velocity])))
            events.append((on + ticks, 2, bytes([0x80 | ch, key, 0])))
        tracks.append(track(events))
        print('%-16s %4d notes' % (name, len(notes)))
    out = pathlib.Path(sys.argv[1])
    out.write_bytes(b'MThd' + struct.pack('>IHHH', 6, 1, len(tracks), PPQ) + b''.join(tracks))
    print(out, bars, 'bars')


main()
