"""The battle music and the short rising theme for a real orchestra (Muse Sounds, Tools/music/muse.py).

  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/music/build_game_music.py [combat] [theme]
Writes Art/Audio/Game/S_Music_Combat.wav and S_Music_Theme.wav (the wavs they replace are first copied once to
Saved/Backup_2026-11-16_music_soundfont/), and the scores to Saved/Music/.

Both were synthesizer pieces in Tools/build_physis_audio.py (detuned saws for strings and brass, sine choir, a
synthetic taiko); their notes, keys, tempo, form and length are kept and given to instruments:
  combat  battle(): D minor, 156 bpm, 24 bars, loops. The sixteenth-note ostinato goes to cellos and violas (staccato,
          accented on the beat) over basses and tuba; the brass stabs to trombone, horns and trumpet; the theme that
          enters at bar 5 to violins and flute; the choir from bar 9 to women and men; kick and snare to bass drum,
          timpani and snare drum, with the snare's run into every fourth bar; the rising siren every eighth bar is a
          timpani and cymbal roll with a crescendo. It opens f and is ff from bar 5.
  theme   score(..., 'rise'): D minor, 84 bpm, 23 bars, a slow build over a pedal, 72.9 s like the sound asset it replaces
          (the wav that lay in Art/Audio/Game was an older 42.6 s take; the game had this longer one). It plays quietly
          under the 40 s cinematic at the end of the station. Basses and cellos hold the pedal, drums enter
          at a quarter of the way, choir and strings at 40 %, brass swells from 60 %, pp rising to ff.
"""
import pathlib
import re
import shutil
import subprocess
import sys

import numpy as np
import soundfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import muse  # noqa: E402

WORK = ROOT / 'Saved/Music'
BACKUP = ROOT / 'Saved/Backup_2026-11-16_music_soundfont'
ROOTS = {'D': 36, 'Bb': 34, 'F': 41, 'C': 36, 'G': 31, 'A': 33}
CHORDS = {'D': (0, 3, 7), 'Bb': (0, 4, 7), 'F': (0, 4, 7), 'C': (0, 4, 7), 'G': (0, 3, 7), 'A': (0, 4, 7)}
LEVELS = ('pp', 'p', 'mp', 'mf', 'f', 'ff')


class Band:
    """Parts by name, made when first used, each remembering its dynamic so a marking is written only on a change."""

    def __init__(self, score):
        self.score, self.parts, self.level = score, {}, {}

    def __call__(self, name, at=None, level=None):
        if name not in self.parts:
            self.parts[name] = self.score.part(name)
        if level is not None and self.level.get(name) != level:
            self.parts[name].dynamic(at, LEVELS[max(0, min(5, level))])
            self.level[name] = level
        return self.parts[name]


def combat():
    score = muse.Score(tempo=156, title='Physis - Combat')
    band = Band(score)
    for name in ('Flute', 'Horn in F', 'Trumpet in B♭', 'Trombone', 'Tuba', 'Timpani', 'Snare Drum', 'Bass Drum', 'Suspended Cymbal', 'Women', 'Men',
                 'Violins 1', 'Violins 2', 'Violas', 'Violoncellos', 'Contrabasses'):
        band(name)
    keys = ('D', 'D', 'Bb', 'C', 'D', 'D', 'G', 'A')
    pattern = (0, 0, 12, 0, 0, 12, 0, 7, 0, 0, 12, 0, 3, 0, 7, 12)
    theme = (14, 15, 17, 19, 17, 15, 14, 10, 12, 14, 12, 10, 7, 10, 12, 14)
    for bar in range(24):
        name = keys[bar % len(keys)]
        root, at = ROOTS[name], bar * 4
        loud = 4 if bar < 4 else 5   # it loops: a softer opening would dip every 37 s in the middle of a fight
        build = bar % 8 == 7
        for index in range(16):
            when = at + index / 4
            beat = index % 4 == 0
            band('Violoncellos', at, loud).note(when, .25, root + 12 + pattern[index], artic='accent' if beat else 'staccato')
            band('Violas', at, loud - 1).note(when, .25, root + 24 + pattern[index], artic='accent' if beat else 'staccato')
            if index % 2 == 0:
                band('Contrabasses', at, loud).note(when, .5, root, artic='accent' if beat else 'staccato')
            if bar % 4 == 3 and index >= 8:
                band('Snare Drum', at, loud - 1).note(when, .25, 38)
        if bar % 4 == 3:
            band('Snare Drum').wedge(at + 2, at + 4, 'crescendo')
        for beat in (0, 2):
            band('Bass Drum', at, loud).note(at + beat, 1, 60, artic='accent')
            band('Tuba', at, loud - 1).note(at + beat, 1, root, artic='accent')
        if bar % 4 != 3:
            for beat in (1, 3):
                band('Snare Drum', at, loud - 1).note(at + beat, .5, 38, artic='accent')
        else:
            band('Snare Drum', at, loud - 1).note(at + 1, .5, 38, artic='accent')
        if build:
            # Where the synthesizer had a rising siren: rolls growing into the next phrase.
            band('Timpani', at, 2).note(at, 4, root + 12, tremolo=3)
            band('Timpani').wedge(at, at + 4, 'crescendo')
            band.level['Timpani'] = None
            band('Suspended Cymbal', at, 1).note(at, 4, 60, tremolo=3)
            band('Suspended Cymbal').wedge(at, at + 4, 'crescendo')
            band.level['Suspended Cymbal'] = None
        else:
            band('Timpani', at, loud - 1).note(at, 1, root + 12, artic='accent')
        for offset, length in ((0, 1.0), (.75, .5), (1.5, 1.5), (3, .5), (3.5, .5)):
            band('Trombone', at, loud - 1).note(at + offset, length, root + 12, artic='accent')
            band('Horn in F', at, loud - 1).note(at + offset, length, root + 19, artic='accent')
            band('Trumpet in B♭', at, loud - 1).note(at + offset, length, root + 24, artic='accent')
        if bar >= 4:
            for index in range(0, 16, 2):
                key = root + 24 + theme[index]
                band('Violins 1', at, loud).note(at + index / 4, .5, key, artic='accent' if index % 8 == 0 else 'staccato')
                band('Violins 2', at, loud - 1).note(at + index / 4, .5, key - 12, artic='accent' if index % 8 == 0 else 'staccato')
                band('Flute', at, loud - 1).note(at + index / 4, .5, key + 12 if key + 12 <= 96 else key, artic='staccato')
        if bar >= 8:
            tones = [root + 24 + tone for tone in CHORDS[name]]
            band('Women', at, loud - 1).note(at, 4, [k for k in tones if k >= 60] or [tones[-1] + 12])
            band('Men', at, loud - 1).note(at, 4, [k for k in tones if k < 60] or [root + 12])
    return score, 24 * 4 * 60 / 156


def theme():
    score = muse.Score(tempo=84, title='Physis - Rising Theme')
    band = Band(score)
    for name in ('Horn in F', 'Trombone', 'Timpani', 'Bass Drum', 'Women', 'Men', 'Violins 1', 'Violins 2', 'Violas', 'Violoncellos', 'Contrabasses'):
        band(name)
    progression = ('D', 'D', 'Bb', 'A', 'D', 'F', 'C', 'A')
    bars = 23
    for bar in range(bars):
        name = progression[bar % len(progression)]
        root, at = ROOTS[name], bar * 4
        grow = (bar + 1) / bars
        loud = min(5, int(grow * 5.2))
        band('Contrabasses', at, max(loud, 1)).note(at, 4, root)
        band('Violoncellos', at, max(loud, 1)).note(at, 4, root + 12)
        if grow > .25:
            for offset in (0, 2):
                band('Bass Drum', at, loud).note(at + offset, 1, 60, artic='accent' if offset == 0 else None)
            for offset, length in ((1.5, .5), (3, .5), (3.5, .5)):
                band('Timpani', at, loud - 1).note(at + offset, length, root + 12)
        if grow > .4:
            tones = [root + 24 + tone for tone in CHORDS[name]]
            band('Women', at, loud - 1).note(at, 4, [k for k in tones if k >= 60] or [tones[-1] + 12])
            band('Men', at, loud - 1).note(at, 4, [k for k in tones if k < 60] or [root + 12])
            band('Violas', at, loud - 1).note(at, 4, tones[:2])
            band('Violins 2', at, loud - 1).note(at, 4, tones[2])
            band('Violins 1', at, loud - 1).note(at, 4, tones[0] + 12)
        if grow > .6 and bar % 2 == 1:
            band('Trombone', at, loud).note(at + 2, 1.5, root + 12, artic='accent')
            band('Horn in F', at, loud).note(at + 2, 1.5, root + 19, artic='accent')
    return score, None


def finish(raw, out, lufs, loop=None, seconds=None, squeeze=None):
    """MuseScore's float mix to the game: a loop's ringing tail laid over its start, an optional compressor (the
    battle music was a wall of sound, and has to stay over the fight), one fixed gain to `lufs`, a limiter at -1 dB."""
    audio, rate = soundfile.read(raw, dtype='float32')
    if loop:
        size = int(round(loop * rate))
        extra = min(len(audio) - size, size)
        audio[:extra] += audio[size:size + extra]
        audio = audio[:size]
    if seconds:
        size = int(round(seconds * rate))
        audio = np.concatenate((audio, np.zeros((max(size - len(audio), 0), 2), np.float32)))[:size]
        fade = int(1.5 * rate)
        audio[-fade:] *= np.linspace(1, 0, fade)[:, None]
    folded = raw.with_name(raw.stem.replace('_raw', '_folded') + '.wav')
    soundfile.write(folded, audio * .25, rate, subtype='FLOAT')
    chain = squeeze + ',' if squeeze else ''
    seen = subprocess.run(['ffmpeg', '-i', str(folded), '-af', chain + 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    loudness = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', seen)[-1])
    chain += 'volume=%.2fdB,alimiter=limit=0.89:attack=5:release=60:level=false' % (lufs - loudness)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(folded), '-af', chain, '-ar', '44100', '-c:a', 'pcm_s16le', str(out)], check=True)
    folded.unlink()


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[1:] or ['combat', 'theme']
    jobs = {'combat': (combat, 'Combat', -11.0, 'acompressor=threshold=-26dB:ratio=3:attack=15:release=220:knee=6:makeup=1', None),
            'theme': (theme, 'Theme', -13.7, 'acompressor=threshold=-46dB:ratio=2:attack=400:release=2500:knee=6:makeup=1', 72.9)}
    for key in wanted:
        compose, name, lufs, squeeze, seconds = jobs[key]
        target = ROOT / 'Art/Audio/Game' / ('S_Music_%s.wav' % name)
        kept = BACKUP / 'Art/Audio/Game' / target.name
        if not kept.exists():
            kept.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, kept)
        score, loop = compose()
        score.write(WORK / (name + '.musicxml'))
        missing = muse.render(WORK / (name + '.musicxml'), WORK / (name + '_raw.wav'), keep_score=WORK / (name + '.mscz'))
        print('%s: %d bars at %d bpm, %d parts; without a Muse sound: %s' % (name, score.bars(), score.tempo, len(score.parts), missing), flush=True)
        finish(WORK / (name + '_raw.wav'), target, lufs, loop, seconds, squeeze)
        print('MUSIC', target, flush=True)


if __name__ == '__main__':
    main()
