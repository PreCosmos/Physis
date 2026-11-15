"""Chatterbox venv (CPU): every spoken page of the Conclave's people, dry, into conclave_dry/<wav name>.wav.
Each take is transcribed (faster-whisper base.en) and compared with its text; a take that strays is redone with
another seed (up to 4 tries), and the best is kept. Writes report.json. Finished files are skipped on a rerun.
batch.py [--only NAME_SUBSTRING]"""
import difflib, json, pathlib, re, sys, time
import librosa, soundfile, torch
from chatterbox.tts import ChatterboxTTS
from faster_whisper import WhisperModel
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'Content/Python'))
import physis_conclave_lore as lore
from physis_lore import voice_name
OUT = HERE / 'conclave_dry'
only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else ''
# How the model should be given a few words (it reads plain English; Kokoro's espeak respellings are not used).
SPOKEN = ((r'\bAL\b', 'A.L.'), ('Orsolya', 'Orshoya'), ('Mechanoid', 'Meckanoid'), ('~', ' '))
NUMBERS = {'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'}


def words(text):
    text = re.sub(r"[^a-z0-9' ]", ' ', text.lower().replace('-', ' '))
    return [NUMBERS.get(w, w) for w in text.split()]


def score(want, heard):
    return difflib.SequenceMatcher(None, words(want), words(heard)).ratio()


jobs = []
for person in lore.PEOPLE:
    if person[3]:
        for k, page in enumerate(lore.conversation_pages(person)):
            jobs.append((voice_name(lore.person_key(person[0], k)), page, person[3], person[4]))
jobs = [j for j in jobs if only in j[0]]
model = ChatterboxTTS.from_pretrained(device='cpu')
ears = WhisperModel('base.en', device='cpu', compute_type='int8')
report_path = HERE / 'report.json'
report = json.loads(report_path.read_text()) if report_path.exists() else {}
t_all = time.time()
for index, (name, page, voice, kind) in enumerate(jobs):
    target = OUT / (name + '.wav')
    if target.exists() and name in report:
        continue
    text = page
    for old, new in SPOKEN:
        text = re.sub(old, new, text)
    best = None
    for attempt in range(4):
        torch.manual_seed(7 + 101 * attempt)
        wav = model.generate(text, audio_prompt_path=str(HERE / ('ref_%s.wav' % voice)), exaggeration=0.5, cfg_weight=0.5)
        audio = wav.squeeze(0).cpu().numpy()
        heard = ' '.join(s.text.strip() for s in ears.transcribe(librosa.resample(audio, orig_sr=model.sr, target_sr=16000))[0])
        match = score(page.replace('~', ' '), heard)
        seconds = len(audio) / model.sr
        # A take is also refused when it runs far too long or short for its text (a loop, or a cut-off line).
        pace = len(page) / max(seconds, .1)
        ok = match >= .9 and 8 <= pace <= 24
        if best is None or (ok, match) > (best['ok'], best['match']):
            best = {'ok': ok, 'match': round(match, 3), 'seconds': round(seconds, 2), 'pace': round(pace, 1), 'tries': attempt + 1, 'heard': heard, 'voice': voice, 'kind': kind, 'audio': audio}
        if ok:
            break
    soundfile.write(target, best.pop('audio'), model.sr)
    report[name] = best
    report_path.write_text(json.dumps(report, indent=1))
    print('%3d/%d %-28s %s match %.2f %.1fs tries %d  (%.0f s elapsed)' % (index + 1, len(jobs), name, 'ok ' if best['ok'] else 'BAD', best['match'], best['seconds'], best['tries'], time.time() - t_all), flush=True)
bad = [n for n, r in report.items() if not r['ok']]
print('done: %d takes, %d flagged: %s' % (len(report), len(bad), ', '.join(bad)), flush=True)
