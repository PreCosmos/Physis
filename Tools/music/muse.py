"""Write an orchestral score as MusicXML and render it with MuseScore 4 and Muse Sounds, without its window.

  score = Score(tempo=80)                       # 4/4, beats are quarter notes, everything on a sixteenth-note grid
  violins = score.part('Violins 1')             # a name from INSTRUMENTS
  violins.dynamic(0, 'mp')
  violins.note(0, 1.5, 69, slur='start')        # start beat, length in beats, MIDI pitch (or a tuple: a chord)
  violins.note(1.5, .5, 74, slur='stop')
  violins.wedge(12, 16, 'crescendo')
  score.write('Theme.musicxml')
  render('Theme.musicxml', 'Theme.wav')         # MuseScore -> 44.1 kHz float wav, Muse Sounds profile

Muse Sounds plays from what is written: dynamics (pp..ff, hairpins), slurs (legato), staccato, accents and tremolo
strokes, not from note velocities. Pitches are written at concert pitch for every instrument (measured: MuseScore
keeps them as written for the horn, trumpet and contrabass parts it makes from these names).

Needs ~/Applications/MuseScore-Studio-*.AppImage (official release) and the Muse Sounds libraries (Muse Sounds
Manager: Strings, Brass, Woodwinds, Percussion, Choir, Harp). Every name in INSTRUMENTS was checked on 2026-11-16 to
get a Muse sound (its render differs from the basic SoundFont's); 'Choir' (voice.choir) does not, so it is not here.
Unpitched percussion is written as plain notes: cymbals, bass drum and tam-tam sound on MIDI 60, the snare drum only on
38; the taiko made no sound on any pitch written this way, so it is not here either.
"""
import glob
import json
import os
import pathlib
import subprocess
import tempfile

# Part name -> (MusicXML instrument-sound, clef sign, clef line). MuseScore picks its instrument from these.
INSTRUMENTS = {
    'Piccolo': ('wind.flutes.flute.piccolo', 'G', 2), 'Flute': ('wind.flutes.flute', 'G', 2), 'Oboe': ('wind.reed.oboe', 'G', 2),
    'English Horn': ('wind.reed.english-horn', 'G', 2), 'Clarinet in B♭': ('wind.reed.clarinet.bflat', 'G', 2), 'Bassoon': ('wind.reed.bassoon', 'F', 4),
    'Horn in F': ('brass.french-horn', 'G', 2), 'Trumpet in B♭': ('brass.trumpet.bflat', 'G', 2), 'Trombone': ('brass.trombone', 'F', 4), 'Tuba': ('brass.tuba', 'F', 4),
    'Timpani': ('drum.timpani', 'F', 4), 'Cymbals': ('metal.cymbal.crash', 'G', 2), 'Suspended Cymbal': ('metal.cymbal.suspended', 'G', 2),
    'Bass Drum': ('drum.bass-drum', 'G', 2), 'Snare Drum': ('drum.snare-drum', 'G', 2),   # write the snare as MIDI 38: it is silent elsewhere
    'Tam-tam': ('metal.tamtam', 'G', 2), 'Glockenspiel': ('pitched-percussion.glockenspiel', 'G', 2),
    'Tubular Bells': ('pitched-percussion.tubular-bells', 'G', 2), 'Vibraphone': ('pitched-percussion.vibraphone', 'G', 2), 'Harp': ('pluck.harp', 'G', 2),
    'Sopranos': ('voice.soprano', 'G', 2), 'Alto': ('voice.alto', 'G', 2), 'Women': ('voice.female', 'G', 2), 'Tenor': ('voice.tenor', 'G', 2),
    'Men': ('voice.male', 'F', 4), 'Bass': ('voice.bass', 'F', 4),
    'Violins 1': ('strings.violin', 'G', 2), 'Violins 2': ('strings.violin', 'G', 2), 'Violin': ('strings.violin', 'G', 2), 'Violas': ('strings.viola', 'C', 3),
    'Violoncellos': ('strings.cello', 'F', 4), 'Contrabasses': ('strings.contrabass', 'F', 4),
}
DIV = 4                                   # divisions per quarter note: a sixteenth-note grid
BAR = 4 * DIV
VALUES = ((16, 'whole', 0), (12, 'half', 1), (8, 'half', 0), (6, 'quarter', 1), (4, 'quarter', 0), (3, 'eighth', 1), (2, 'eighth', 0), (1, '16th', 0))
STEPS = (('C', 0), ('C', 1), ('D', 0), ('D', 1), ('E', 0), ('F', 0), ('F', 1), ('G', 0), ('G', 1), ('A', 0), ('A', 1), ('B', 0))
grid = lambda beats: int(round(beats * DIV))


class Part:
    def __init__(self, name, label=None):
        self.name, self.label = name, label or name
        self.sound, self.clef, self.line = INSTRUMENTS[name]
        self.notes, self.marks = [], []

    def note(self, start, beats, pitch, slur=None, artic=None, tremolo=0):
        """slur: 'start' or 'stop'; artic: 'staccato', 'accent', 'tenuto' or 'marcato'; tremolo: strokes (3 = unmeasured)."""
        pitches = tuple(sorted(pitch)) if isinstance(pitch, (tuple, list)) else (int(pitch),)
        if grid(beats) > 0:
            self.notes.append(dict(at=grid(start), end=grid(start) + grid(beats), pitches=pitches, slur=slur, artic=artic, tremolo=tremolo))

    def dynamic(self, beat, mark):
        self.marks.append((grid(beat), 'dynamic', mark))

    def text(self, beat, words):
        """A playing technique: 'pizz.' or 'arco'."""
        self.marks.append((grid(beat), 'text', words))

    def wedge(self, start, end, kind='crescendo'):
        self.marks += [(grid(start), 'wedge', kind), (grid(end), 'wedge', 'stop')]

    def voices(self):
        """Notes that sound together with different lengths go to separate voices (at most four)."""
        out, ends = [[] for _ in range(4)], [0, 0, 0, 0]
        for note in sorted(self.notes, key=lambda n: (n['at'], -n['end'])):
            free = [v for v in range(4) if ends[v] <= note['at']]
            if free:
                v = free[0]
            else:  # a fifth line: the one ending soonest gives way
                v = min(range(4), key=lambda k: ends[k])
                out[v][-1]['end'] = note['at']
            out[v].append(dict(note))
            ends[v] = note['end']
        return [v for v in out if v]


def pieces(at, end):
    """(start, length, name, dots) for a stretch of time, cut at bar lines and into writable note values."""
    out = []
    while at < end:
        room = min(end, (at // BAR + 1) * BAR) - at
        length, name, dots = next(v for v in VALUES if v[0] <= room)
        out.append((at, length, name, dots))
        at += length
    return out


class Score:
    def __init__(self, tempo=80, title='Physis'):
        self.tempo, self.title, self.parts = tempo, title, []

    def part(self, name, label=None):
        self.parts.append(Part(name, label))
        return self.parts[-1]

    def bars(self):
        return max(1, -(-max((n['end'] for p in self.parts for n in p.notes), default=BAR) // BAR))

    def write(self, path):
        bars = self.bars()
        x = ['<?xml version="1.0" encoding="UTF-8"?>', '<score-partwise version="4.0">', '<work><work-title>%s</work-title></work>' % self.title, '<part-list>']
        for k, p in enumerate(self.parts):
            x.append('<score-part id="P%d"><part-name>%s</part-name><score-instrument id="P%d-I1"><instrument-name>%s</instrument-name>'
                     '<instrument-sound>%s</instrument-sound></score-instrument></score-part>' % (k + 1, p.name, k + 1, p.name, p.sound))
        x.append('</part-list>')
        for k, p in enumerate(self.parts):
            x.append('<part id="P%d">' % (k + 1))
            lines = []
            for voice in p.voices():
                # Each voice as (start, length, name, dots, note or None, first piece?, last piece?), rests between notes.
                row, now = [], 0
                for note in voice:
                    row += [piece + (None, False, False) for piece in pieces(now, note['at'])]
                    cut = pieces(note['at'], note['end'])
                    row += [piece + (note, i == 0, i == len(cut) - 1) for i, piece in enumerate(cut)]
                    now = note['end']
                row += [piece + (None, False, False) for piece in pieces(now, bars * BAR)]
                lines.append(row)
            for bar in range(bars):
                x.append('<measure number="%d">' % (bar + 1))
                if bar == 0:
                    x.append('<attributes><divisions>%d</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time>'
                             '<clef><sign>%s</sign><line>%d</line></clef></attributes>' % (DIV, p.clef, p.line))
                    if k == 0:
                        x.append('<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>%d</per-minute></metronome>'
                                 '</direction-type><sound tempo="%d"/></direction>' % (self.tempo, self.tempo))
                for at, kind, value in sorted(m for m in p.marks if bar * BAR <= m[0] < (bar + 1) * BAR or (m[0] == bars * BAR and bar == bars - 1)):
                    body = {'dynamic': '<dynamics><%s/></dynamics>', 'wedge': '<wedge type="%s"/>', 'text': '<words>%s</words>'}[kind] % value
                    sound = '<sound pizzicato="%s"/>' % ('yes' if value.startswith('pizz') else 'no') if kind == 'text' else ''
                    offset = at - bar * BAR
                    x.append('<direction placement="%s"><direction-type>%s</direction-type>%s%s</direction>' % ('above' if kind == 'text' else 'below', body, '<offset>%d</offset>' % offset if offset else '', sound))
                for v, row in enumerate(lines):
                    if v:
                        x.append('<backup><duration>%d</duration></backup>' % BAR)
                    for at, length, name, dots, note, first, last in (r for r in row if bar * BAR <= r[0] < (bar + 1) * BAR):
                        shape = '<duration>%d</duration><voice>%d</voice><type>%s</type>%s' % (length, v + 1, name, '<dot/>' * dots)
                        if note is None:
                            x.append('<note><rest/>%s</note>' % shape)
                            continue
                        marks = ('<tied type="stop"/>' if not first else '') + ('<tied type="start"/>' if not last else '')
                        if note['slur'] == 'start' and first or note['slur'] == 'stop' and last:
                            marks += '<slur type="%s" number="1"/>' % note['slur']
                        if note['tremolo']:
                            marks += '<ornaments><tremolo type="single">%d</tremolo></ornaments>' % note['tremolo']
                        if note['artic'] and first:
                            marks += '<articulations><%s/></articulations>' % {'marcato': 'strong-accent'}.get(note['artic'], note['artic'])
                        ties = ('<tie type="stop"/>' if not first else '') + ('<tie type="start"/>' if not last else '')
                        for i, pitch in enumerate(note['pitches']):
                            step, alter = STEPS[pitch % 12]
                            x.append('<note>%s<pitch><step>%s</step>%s<octave>%d</octave></pitch>%s%s%s</note>' % (
                                '<chord/>' if i else '', step, '<alter>1</alter>' if alter else '', pitch // 12 - 1,
                                shape.replace('</duration>', '</duration>' + ties, 1), '', '<notations>%s</notations>' % marks if marks else ''))
                x.append('</measure>')
            x.append('</part>')
        x.append('</score-partwise>')
        pathlib.Path(path).write_text('\n'.join(x))


def musescore():
    found = sorted(glob.glob(os.path.expanduser('~/Applications/MuseScore-Studio-*.AppImage')))
    if not found:
        raise RuntimeError('no MuseScore AppImage in ~/Applications')
    return found[-1]


def render(source, target, profile='MuseSounds', keep_score=None):
    """MusicXML (or .mscz) -> wav through MuseScore's command line with the given sound profile. Returns the log's
    count of tracks that found no sound of the profile beyond the one MuseScore always reports."""
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    source, target = pathlib.Path(source).resolve(), pathlib.Path(target).resolve()
    logs = os.path.expanduser('~/.local/share/MuseScore/MuseScore4/logs/*.log')
    with tempfile.TemporaryDirectory() as scratch:
        score = pathlib.Path(keep_score).resolve() if keep_score else pathlib.Path(scratch) / 'score.mscz'
        subprocess.run([musescore(), '-o', str(score), str(source)], env=env, capture_output=True, timeout=600, check=True)
        job = pathlib.Path(scratch) / 'job.json'
        job.write_text(json.dumps([{'in': str(score), 'out': str(target)}]))
        before = set(glob.glob(logs))
        subprocess.run([musescore(), '-j', str(job), '--sound-profile', profile], env=env, capture_output=True, timeout=3600, check=True)
        new = sorted(set(glob.glob(logs)) - before)
    if not target.exists():
        raise RuntimeError('MuseScore wrote no audio: ' + str(target))
    return max(open(new[-1]).read().count('invalid audio source') - 1, 0) if new else None
