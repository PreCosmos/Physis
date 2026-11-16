"""Divinity's narration with Chatterbox (every scan and story line she speaks, all five levels), then her reverb.

Chatterbox takes her timbre and pace from a dry Kokoro take of her voice (bf_emma), made once by
Saved/AudioTools/divinity_voice/make_ref.py, and speaks each line in sentence groups short enough to stay stable.
Every group is transcribed (faster-whisper base.en) and compared with its text; one that strays, loops or is cut off
is redone with another seed (up to 4 tries) and the best is kept. Groups are joined with a speaker's pauses.

Run from the project folder with the Chatterbox venv (CPU, about 2.5 times the audio's length):
  Saved/AudioTools/chatterbox_venv/bin/python Tools/build_physis_divinity_voice.py dry [SET...] [--only PATTERN[,..]]
      dry takes into Saved/AudioTools/divinity_voice/dry/<set>/ and report.json; finished lines are skipped.
  Saved/AudioTools/chatterbox_venv/bin/python Tools/build_physis_divinity_voice.py wet [SET...] [--only PATTERN[,..]]
      every dry take through her effect (build_physis_voice.EFFECT) into the game's folders, 44.1 kHz stereo; the wav
      it replaces is first copied to Saved/Backup_2026-11-15_divinity_kokoro/<set>/ if no copy is there yet.
Sets: ship (Art/Audio/Voice), center (Art/Audio/Voice/Center), conclave (Art/Audio/Conclave/Voice), grove
(Art/Audio/Grove/Voice), arche (Art/Audio/Arche/Voice). Only Divinity's files are touched; the people's pages belong to build_physis_voice.py.
"""
import difflib
import fnmatch
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / 'Saved/AudioTools/divinity_voice'
BACKUP = ROOT / 'Saved/Backup_2026-11-15_divinity_kokoro'
sys.path.insert(0, str(ROOT / 'Content/Python'))
from physis_lore import all_entries, voice_name  # noqa: E402

FOLDERS = {'ship': 'Art/Audio/Voice', 'center': 'Art/Audio/Voice/Center', 'conclave': 'Art/Audio/Conclave/Voice', 'grove': 'Art/Audio/Grove/Voice',
           'arche': 'Art/Audio/Arche/Voice'}
# The model's own middle: the widest pitch movement of the settings tried, at her Kokoro takes' pace (16 chars/s).
EXAGGERATION, CFG = .5, .5
# Her effect, as build_physis_voice.py gives it to Kokoro's takes (both models speak at 24 kHz).
EFFECT = ('asetrate=24000*0.97,aresample=44100,atempo=1.03,'
          'aecho=0.8:0.55:70|140|260|430:0.26|0.2|0.14|0.09,apad=pad_dur=0.9,loudnorm=I=-12:TP=-1:LRA=9,aformat=channel_layouts=stereo')
# What the model is given for words it would read wrongly (it reads plain English, not espeak respellings).
SPOKEN = ((r'\bAL\b', 'A.L.'), (r'\b2296\b', 'twenty-two ninety-six'), (r'-(\d)\b', r' \1'), ('Mechanoid', 'Meckanoid'), (r'\bMecha\b', 'Mekka'),
          ('Verdance', 'Verdanss'), ('Orsolya', 'Orshoyah'), (r'\bsteles?\b', lambda m: 'steelee' + m.group(0)[5:]), (r'\bV or D-pad', 'Vee, or D-pad'),
          # Arche's names: AR-kee, KATH-o-doss, EE-on, SAH-el, ih-LOON.
          (r'\bArche\b', 'Arkee'), ('Kathodos', 'Kathodoss'), (r'\bAeon\b', 'Eon'), (r'\bSael\b', 'Sah-el'), (r'\bIlun\b', 'Iloon'))
DIGITS = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')
NUMBERS = {word: str(k) for k, word in enumerate(DIGITS)}
NAMES = 'Physis, Divinity, the First Ones, the Serene, the Vigil, the Just, the Wise, Kairos, Thessaly, Conclave, Stillstone, Heartbloom, Reweave, Settle, Mend, A.L., Arche, Kathodos, Aeon, Sael, Ilun, Maruth, Oreth, the Sunderer'
GROUP = 250           # most characters spoken in one go
PAUSE, BREAK = .42, .7  # seconds between sentence groups, and at a line break ('~')


def lines(which):
    if which == 'ship':
        rows = all_entries()
    elif which == 'center':
        import physis_center_lore as lore
        rows = lore.center_entries() + [('Story', 'Awakening', lore.AWAKEN_LINE)]
    elif which == 'conclave':
        import physis_conclave_lore as lore
        rows = lore.conclave_entries() + [('Story',) + lore.ARRIVAL_LINE]
    elif which == 'grove':
        import physis_grove_lore as lore
        rows = lore.grove_entries() + [('Story',) + lore.ARRIVAL_LINE]
    else:
        import physis_arche_lore as lore
        rows = lore.arche_entries() + [('Story',) + lore.ARRIVAL_LINE]
    return [(voice_name(title), text) for _, title, text in rows]


def spoken(text):
    for old, new in SPOKEN:
        text = re.sub(old, new, text)
    text = re.sub(r'\b(\d)\b', lambda m: DIGITS[int(m.group(1))], text)
    if re.search(r'\d', text):
        raise ValueError('a number with no spelling: ' + text)
    return text


def groups(text):
    """[(text, pause after it)]: whole sentences gathered up to GROUP characters, so each has its neighbours for
    intonation and none is long enough for the model to drift."""
    out = []
    for paragraph in [p.strip() for p in text.split('~') if p.strip()]:
        current = ''
        for sentence in re.split(r'(?<=[.!?])\s+', paragraph):
            if current and len(current) + 1 + len(sentence) > GROUP:
                out.append([current, PAUSE])
                current = sentence
            else:
                current = (current + ' ' + sentence).strip()
        out.append([current, BREAK])
    out[-1][1] = 0
    return out


def words(text):
    text = re.sub(r'\ba\.l\.', 'al', text.lower())
    text = re.sub(r"[^a-z0-9' ]", ' ', text.replace('-', ' '))
    return [NUMBERS.get(w, w) for w in text.split()]


def selection():
    sets = [a for a in sys.argv[2:] if a in FOLDERS] or list(FOLDERS)
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    return [(which, name, text) for which in sets for name, text in lines(which)
            if not only or any(fnmatch.fnmatch(name, pattern) for pattern in only)]


def dry():
    import librosa
    import numpy as np
    import soundfile
    import torch
    torch.set_num_threads(12)  # another voice run may share the machine
    from chatterbox.tts import ChatterboxTTS
    from faster_whisper import WhisperModel
    model = ChatterboxTTS.from_pretrained(device='cpu')
    assert model.sr == 24000
    ears = WhisperModel('base.en', device='cpu', compute_type='int8')
    report_path = WORK / 'report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    jobs = selection()
    began = time.time()
    for index, (which, name, text) in enumerate(jobs):
        key = which + '/' + name
        target = WORK / 'dry' / which / (name + '.wav')
        if target.exists() and key in report:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        parts, rows = [], []
        for group, pause in groups(text):
            best = None
            for attempt in range(4):
                torch.manual_seed(7 + 101 * attempt)
                audio = model.generate(spoken(group), audio_prompt_path=str(WORK / 'ref_divinity.wav'), exaggeration=EXAGGERATION, cfg_weight=CFG)
                audio, _ = librosa.effects.trim(audio.squeeze(0).cpu().numpy(), top_db=38)
                heard = ' '.join(s.text.strip() for s in ears.transcribe(librosa.resample(audio, orig_sr=model.sr, target_sr=16000), initial_prompt=NAMES)[0])
                match = difflib.SequenceMatcher(None, words(group), words(heard)).ratio()
                pace = len(group) / max(len(audio) / model.sr, .1)
                ok = match >= .9 and 10 <= pace <= 22
                if best is None or (ok, match) > (best['ok'], best['match']):
                    best = {'ok': ok, 'match': round(match, 3), 'pace': round(pace, 1), 'tries': attempt + 1, 'text': group, 'heard': heard, 'audio': audio}
                if ok:
                    break
            audio = best.pop('audio')
            fade = int(.008 * model.sr)
            audio[:fade] *= np.linspace(0, 1, fade)
            audio[-fade:] *= np.linspace(1, 0, fade)
            parts += [audio, np.zeros(int(pause * model.sr), dtype=audio.dtype)]
            rows.append(best)
        take = np.concatenate(parts)
        soundfile.write(target, take, model.sr)
        report[key] = {'ok': all(r['ok'] for r in rows), 'seconds': round(len(take) / model.sr, 2), 'groups': rows}
        report_path.write_text(json.dumps(report, indent=1))
        print('%3d/%d %-44s %s match %.2f %5.1fs tries %s  (%.0f min)' % (index + 1, len(jobs), key, 'ok ' if report[key]['ok'] else 'BAD',
              min(r['match'] for r in rows), report[key]['seconds'], '+'.join(str(r['tries']) for r in rows), (time.time() - began) / 60), flush=True)
    bad = [k for k, r in report.items() if not r['ok']]
    print('done: %d lines, %d flagged: %s' % (len(report), len(bad), ', '.join(bad)), flush=True)


def wet():
    done = 0
    for which, name, _ in selection():
        source = WORK / 'dry' / which / (name + '.wav')
        if not source.exists():
            print('no dry take:', which, name)
            continue
        target = ROOT / FOLDERS[which] / (name + '.wav')
        kept = BACKUP / which / target.name
        if target.exists() and not kept.exists():
            kept.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, kept)
        made = WORK / 'wet.tmp.wav'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(source), '-filter_complex', EFFECT, '-ar', '44100', '-c:a', 'pcm_s16le', str(made)], check=True)
        shutil.move(str(made), str(target))
        done += 1
    print('wet:', done, 'lines')


if __name__ == '__main__':
    {'dry': dry, 'wet': wet}[sys.argv[1]]()
