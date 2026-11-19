"""The Physis main theme for a real orchestra: Tools/build_physis_score.py's melody, harmony and form, scored for
Muse Sounds (Tools/music/muse.py) and rendered by MuseScore 4.

Run from the project folder (numpy and soundfile from the Kokoro venv):
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/music/build_main_theme.py [OUT.wav]
Writes Saved/Music/MainTheme.musicxml, MainTheme.mscz (opens in MuseScore) and the mixed wav (default
Saved/Music/S_Music_MainTheme.wav; it does not touch Art/Audio until the track is approved).

The notes are the old score's: themes A and B in D major, the same chords, the same seven sections and their
intensity (0..4). What changed is who plays them, because a sampled orchestra plays what is written:
  melody     flute (intro), oboe (bridge), first and second violins (statement), horns and trumpet (rising); at the
             anthem and ascent first violins and trumpet an octave up, second violins, flute and oboe with them, and
             the women of the choir an octave below; each bar's melody is one slurred phrase for winds and strings
  harmony    women humming (quiet sections), violas and violins (statement, rising), horns from intensity 2, full
             choir from 3 (the old choir chords, an octave lower where they passed a soprano's range)
  bass       cellos and basses; trombone and tuba from intensity 3
  motion     harp arpeggios when quiet; the old "tremolo strings" patch is now a real bowed tremolo (second
             violins, or violas when the seconds have the melody); timpani; cymbals at the big downbeats; the
             trumpet's offbeat notes go to a second trumpet; the timpani build-ups are one roll with a crescendo
  dynamics   written per section from the intensity: p, mp, mf, f, ff for the melody, one step under for the rest
"""
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import muse  # noqa: E402

old = {'__file__': str(ROOT / 'Tools/build_physis_score.py'), '__name__': 'score'}
exec(compile((ROOT / 'Tools/build_physis_score.py').read_text().rsplit('\nmain()', 1)[0], 'build_physis_score.py', 'exec'), old)
SECTIONS = old['SECTIONS']
FLUTE, OBOE, VIOLIN, STRINGS, HORN, TRUMPET, CHOIR = (old[n] for n in ('FLUTE', 'OBOE', 'VIOLIN', 'STRINGS', 'HORN', 'TRUMPET', 'CHOIR'))
LEVELS = ('pp', 'p', 'mp', 'mf', 'f', 'ff')


def compose():
    score = muse.Score(tempo=80, title='Physis - Main Theme')
    names = ('Flute', 'Oboe', 'Horn in F', 'Trumpet in B♭', 'Trumpet 2', 'Trombone', 'Tuba', 'Timpani', 'Cymbals', 'Harp', 'Women', 'Men',
             'Violins 1', 'Violins 2', 'Violas', 'Violoncellos', 'Contrabasses')
    part = {n: score.part('Trumpet in B♭' if n == 'Trumpet 2' else n, n) for n in names}
    level = {}

    def dynamic(name, beat, steps):
        mark = LEVELS[max(0, min(5, steps))]
        if level.get(name) != mark:
            part[name].dynamic(beat, mark)
            level[name] = mark

    def phrase(name, at, notes, lift, slurred=True, artic=None):
        for i, (when, key, beats) in enumerate(notes):
            slur = None
            if slurred and len(notes) > 1:
                slur = 'start' if i == 0 else 'stop' if i == len(notes) - 1 else None
            part[name].note(at + when, beats, key + lift, slur=slur, artic=artic)

    bar = 0
    for name, melody, chords, heat, shift, leads, _ in SECTIONS:
        for inner, ((root, quality), notes) in enumerate(zip(chords * 4, melody)):
            at = bar * 4
            root += shift
            triad = [root + 24 + step for step in quality]
            lead, under = heat + 1, heat        # indices into LEVELS: melody p..ff, the rest one step under
            high = 12 if heat >= 4 else 0
            # Melody.
            if FLUTE in leads or heat >= 4:
                dynamic('Flute', at, lead if FLUTE in leads else under)
                phrase('Flute', at, notes, shift + high)
            if OBOE in leads or heat >= 4:
                dynamic('Oboe', at, lead if OBOE in leads else under)
                phrase('Oboe', at, notes, shift)
            if VIOLIN in leads:
                dynamic('Violins 1', at, lead)
                phrase('Violins 1', at, notes, shift + high)
            if STRINGS in leads:
                dynamic('Violins 2', at, lead)
                phrase('Violins 2', at, notes, shift)
            if HORN in leads:
                dynamic('Horn in F', at, lead)
                phrase('Horn in F', at, notes, shift, slurred=False, artic='tenuto')
            if TRUMPET in leads:
                dynamic('Trumpet in B♭', at, lead)
                phrase('Trumpet in B♭', at, notes, shift + high, slurred=False, artic='tenuto')
            if CHOIR in leads:
                dynamic('Women', at, lead)
                phrase('Women', at, notes, shift - 12)
            # Harmony.
            tremolo = 'Violins 2' if STRINGS not in leads else 'Violas'
            if heat == 0:
                dynamic('Women', at, under)
                part['Women'].note(at, 4, triad)
            else:
                if tremolo != 'Violas':
                    dynamic('Violas', at, under)
                    part['Violas'].note(at, 4, triad[:2])
                if VIOLIN not in leads:
                    dynamic('Violins 1', at, under)
                    part['Violins 1'].note(at, 4, triad[2] if heat < 3 else triad[2] + 12)
                elif heat == 1:
                    dynamic('Violas', at, under)
                    part['Violas'].note(at, 4, triad)
            if heat >= 2:
                dynamic('Horn in F', at, lead if HORN in leads else under)
                part['Horn in F'].note(at, 4, [key - 12 for key in triad[1:]])
            if heat >= 3:
                top = [key + 12 for key in triad]
                dynamic('Men', at, under)
                part['Men'].note(at, 4, [key - 12 for key in triad])
                if CHOIR not in leads:
                    dynamic('Women', at, under)
                    part['Women'].note(at, 4, top if max(top) <= 81 else triad)
            # Bass.
            dynamic('Violoncellos', at, under)
            dynamic('Contrabasses', at, under)
            part['Violoncellos'].note(at, 4, root + 12)
            part['Contrabasses'].note(at, 4, root)
            if heat >= 3:
                dynamic('Trombone', at, under)
                dynamic('Tuba', at, under)
                part['Trombone'].note(at, 2, root + 12)
                part['Tuba'].note(at + 2, 2, root)
            # Motion.
            if heat <= 1:
                dynamic('Harp', at, 3)
                for step, key in enumerate((triad + [triad[0] + 12, triad[1] + 12, triad[2] + 12])[:8]):
                    part['Harp'].note(at + step / 2, .5, key)
            build = inner == len(melody) - 1 and name in ('rising', 'bridge')
            if heat >= 2:
                dynamic(tremolo, at, under - 1)
                drop = 0 if tremolo == 'Violins 2' else -12
                for step in range(8):
                    part[tremolo].note(at + step / 2, .5, triad[step % 3] + 12 + drop, tremolo=3)
                if not build:
                    dynamic('Timpani', at, under)
                    part['Timpani'].note(at, 1, root + 12, artic='accent')
                    part['Timpani'].note(at + 2, 1, root + 19)
            if heat >= 4:
                if not build:
                    for step in (1, 3):
                        part['Timpani'].note(at + step, .5, root + 12)
                dynamic('Trumpet 2', at, under - 1)
                for step in range(4):
                    part['Trumpet 2'].note(at + step + .5, .5, triad[2] + 12, artic='staccato')
            if heat >= 3 and inner % 2 == 0:
                dynamic('Cymbals', at, under)
                part['Cymbals'].note(at, 2, 60)
            if build:
                # One roll growing into the next section, where the old score had sixteen separate strokes.
                part['Timpani'].dynamic(at, 'p')
                level['Timpani'] = None
                part['Timpani'].note(at, 4, root + 12, tremolo=3)
                part['Timpani'].wedge(at, at + 4, 'crescendo')
            bar += 1
    return score


def mix(raw, out):
    """MuseScore's float mix (it can pass full scale) to the game's music level. The orchestra's own range is about
    20 dB from the quiet opening to the climax, too wide for music under play, so a slow 2:1 levelling halves it
    (the old track's sections spanned 9 dB); then one fixed gain brings the whole to -13 LUFS and a limiter catches
    the few peaks over -1 dB. No loudness-chasing filter: that made the opening as loud as the anthem."""
    level = 'volume=-12dB,acompressor=threshold=-46dB:ratio=2:attack=400:release=2500:knee=6:makeup=1'
    seen = subprocess.run(['ffmpeg', '-i', str(raw), '-af', level + ',ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    loudness = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', seen)[-1])
    seconds = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(raw)], capture_output=True, text=True).stdout)
    chain = '%s,volume=%.2fdB,alimiter=limit=0.89:attack=5:release=80:level=false,afade=t=out:st=%.2f:d=1.5' % (level, -13 - loudness, seconds - 1.5)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-af', chain, '-ar', '44100', '-c:a', 'pcm_s16le', str(out)], check=True)


def main():
    work = ROOT / 'Saved/Music'
    work.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else work / 'S_Music_MainTheme.wav'
    score = compose()
    score.write(work / 'MainTheme.musicxml')
    print(score.bars(), 'bars;', ', '.join('%s %d' % (p.label, len(p.notes)) for p in score.parts))
    missing = muse.render(work / 'MainTheme.musicxml', work / 'MainTheme_raw.wav', keep_score=work / 'MainTheme.mscz')
    print('parts without a Muse sound:', missing)
    mix(work / 'MainTheme_raw.wav', out)
    print('MUSIC', out)


if __name__ == '__main__':
    main()
