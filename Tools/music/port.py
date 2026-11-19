"""The old SoundFont scores played by Muse Sounds: their note events turned into a written score.

The Center, Temple, Awakening, Conclave and Grove music is composed in Tools/build_physis_center_audio.py,
build_physis_conclave_audio.py and build_physis_grove_audio.py as events (General MIDI program, key, start, length,
velocity, and for the Orchestra class a dynamics shape and a lead gain) and was rendered by perform() / render()
through the SoundFont. perform_muse() takes the same events and returns the same kind of signal from MuseScore, so
those scripts' own finishing (hall, loop fold, level ride, loudness, write) runs unchanged after it.

What a sampled orchestra needs written, and how it is read off the events:
  parts       by program and register: violin, viola, cello, bass, flute, oboe ... to their sections; the "string
              ensemble" pads spread over second violins, violas and cellos by pitch; "tremolo strings" become the
              same sections bowing a tremolo; "pizzicato strings" become pizzicato sections; choir aahs and oohs go
              to women and men by pitch; the celesta (no Muse Sounds library here) to the glockenspiel
  dynamics    one marking where a part's level changes: its loudest velocity in the bar (melodies the old score
              lifted with a lead gain read one step louder) on the scale pp < 38 <= p < 50 <= mp < 62 <= mf < 76 <= f
              < 90 <= ff
  hairpins    a note shaped 'cresc' or 'dim' two beats or longer carries a crescendo or diminuendo
  slurs       a melodic line (one note at a time, each starting where the last ended) is slurred in phrases of up
              to two bars, a note of three beats or more ending the phrase; brass tongue every note
  ringing     harp, glockenspiel, pizzicato and timpani notes are written only as long as the gap to the next
              (they ring on their own); a timpani note with a crescendo is a roll
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import muse  # noqa: E402

RATE = 44100
LEVELS = ('pp', 'p', 'mp', 'mf', 'f', 'ff')
SOLO = {40: 'Violins 1', 41: 'Violas', 42: 'Violoncellos', 43: 'Contrabasses', 46: 'Harp', 47: 'Timpani', 56: 'Trumpet in B♭', 57: 'Trombone', 58: 'Tuba',
        60: 'Horn in F', 68: 'Oboe', 69: 'English Horn', 70: 'Bassoon', 71: 'Clarinet in B♭', 73: 'Flute', 8: 'Glockenspiel', 9: 'Glockenspiel'}
RINGING = {46, 47, 8, 9, 45}
TONGUED = {56, 57, 58}


def seat(program, key):
    """(instrument, role) for a note."""
    if program in SOLO:
        return SOLO[program], 'celesta' if program == 8 else ''
    if program in (48, 49):
        return ('Violins 2' if key >= 67 else 'Violas' if key >= 55 else 'Violoncellos'), 'pad'
    if program == 44:
        return ('Violins 2' if key >= 60 else 'Violas' if key >= 48 else 'Violoncellos'), 'trem'
    if program == 45:
        return ('Violas' if key >= 55 else 'Violoncellos' if key >= 43 else 'Contrabasses'), 'pizz'
    if program in (52, 53):
        return ('Women' if key >= 60 else 'Men'), ''
    raise ValueError('no orchestral seat for General MIDI program %d' % program)


def to_muse(events, beat, title):
    score = muse.Score(tempo=round(60 / beat), title=title)
    rows = {}
    for event in events:
        program, key, start, length, velocity = event[:5]
        shape, gain = (event[5], event[6]) if len(event) > 5 else ('flat', 1.0)
        at, span = muse.grid(start / beat), max(1, muse.grid(length / beat))
        rows.setdefault(seat(program, key), []).append(dict(at=at, end=at + span, key=key, loud=velocity + (10 if gain > 1.5 else 0), shape=shape, program=program))
    order = list(muse.INSTRUMENTS)
    for (name, role), notes in sorted(rows.items(), key=lambda kv: (order.index(kv[0][0]), kv[0][1])):
        part = score.part(name, '%s (%s)' % (name, role) if role else name)
        notes.sort(key=lambda n: (n['at'], n['key']))
        program = notes[0]['program']
        onsets = sorted(set(n['at'] for n in notes))
        if program in RINGING:
            for n in notes:
                roll = program == 47 and n['shape'] == 'cresc' and n['end'] - n['at'] >= 2 * muse.DIV
                later = [o for o in onsets if o > n['at']]
                if not roll:
                    n['end'] = min(n['end'], later[0] if later else n['end'], n['at'] + muse.DIV)
                n['roll'] = roll
        if role == 'pizz':
            part.text(notes[0]['at'] / muse.DIV, 'pizz.')
        # Dynamics: the bar's loudest note, marked where it changes.
        have = None
        for bar in sorted(set(n['at'] // muse.BAR for n in notes)):
            inside = [n for n in notes if n['at'] // muse.BAR == bar]
            loud = max(n['loud'] for n in inside)
            mark = LEVELS[sum(loud >= edge for edge in (38, 50, 62, 76, 90))]
            if mark != have:
                part.dynamic(min(n['at'] for n in inside) / muse.DIV, mark)
                have = mark
        # Chords: notes of one part starting and ending together.
        chords = {}
        for n in notes:
            chords.setdefault((n['at'], n['end']), []).append(n)
        line = sorted(chords.items())
        # Slurs over a melodic line.
        slur = {}
        if role == '' and program not in RINGING and program not in TONGUED:
            run = []

            def close():
                if len(run) > 1:
                    slur[run[0]], slur[run[-1]] = 'start', 'stop'
                run.clear()
            for i, ((at, end), group) in enumerate(line):
                alone = len(group) == 1 and not any(a < end and e > at for (a, e), _ in line[:i] + line[i + 1:])
                if not alone or (run and (run[-1][1] != at or end - run[0][0] > 2 * muse.BAR)):
                    close()
                if alone:
                    run.append((at, end))
                    if end - at >= 3 * muse.DIV:
                        close()
            close()
        wedged = set()
        for (at, end), group in line:
            first = group[0]
            tremolo = 3 if role == 'trem' or first.get('roll') else 0
            part.note(at / muse.DIV, (end - at) / muse.DIV, [n['key'] for n in group], slur=slur.get((at, end)), tremolo=tremolo)
            shape = first['shape']
            if shape in ('cresc', 'dim') and end - at >= 2 * muse.DIV and not any(a < end and e > at for a, e in wedged):
                part.wedge(at / muse.DIV, end / muse.DIV, 'crescendo' if shape == 'cresc' else 'diminuendo')
                wedged.add((at, end))
    return score


def perform_muse(name):
    """A stand-in for the old perform(font, orch, tail) and render(font, score, tail): the same events through
    MuseScore, as a float32 stereo signal of the length the old function gave."""
    import numpy as np
    import soundfile

    def perform(font, orch, tail=8.0):
        work = ROOT / 'Saved/Music'
        work.mkdir(parents=True, exist_ok=True)
        score = to_muse(orch.events, orch.beat, 'Physis - ' + name)
        score.write(work / (name + '.musicxml'))
        missing = muse.render(work / (name + '.musicxml'), work / (name + '_raw.wav'), keep_score=work / (name + '.mscz'))
        print('%s: %d bars at %d bpm, parts: %s; without a Muse sound: %s' % (name, score.bars(), score.tempo, ', '.join(p.label for p in score.parts), missing), flush=True)
        audio, rate = soundfile.read(work / (name + '_raw.wav'), dtype='float32')
        assert rate == RATE, rate
        total = int((max(e[2] + e[3] for e in orch.events) + tail) * RATE)
        out = np.zeros((total, 2), np.float32)
        out[:min(total, len(audio))] = audio[:total]
        return out
    return perform
