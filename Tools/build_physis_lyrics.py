"""Speaks the main theme's lyric phrases with Kokoro, ready for build_physis_audio.py.

Run with the Kokoro venv: python build_physis_lyrics.py MODELS_DIR OUTPUT_DIR
Writes dry 44.1 kHz mono phrases; the song adds the rhythm, pitch and reverb.
"""
import pathlib
import subprocess
import sys

import soundfile
from kokoro_onnx import EspeakConfig, Kokoro

# Name, voice, speed, text. Original lyrics on the eternal search for peace and creation.
PHRASES = (
    ('star', 'af_heart', .82, 'Every star... is a door we open.'),
    ('peace', 'af_heart', .78, 'We keep on looking for peace.'),
    ('peace_low', 'am_michael', .8, 'We keep on looking for peace.'),
    ('nothing', 'af_bella', .82, 'Out of nothing... we begin again.'),
    ('gentle', 'af_heart', .8, 'Make the world... and make it gentle.'),
    ('searching', 'af_heart', .76, 'Still searching.'),
    ('creating', 'af_bella', .76, 'Still creating.'),
    ('hold', 'am_michael', .8, 'Hold the light... until it holds you.'),
    ('home', 'af_heart', .8, 'Every ending is a place to start.'),
)


def main():
    models, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    speech = EspeakConfig(lib_path='/usr/lib64/libespeak-ng.so.1', data_path='/usr/share/espeak-ng-data')
    engine = Kokoro(str(models / 'kokoro-v1.0.onnx'), str(models / 'voices-v1.0.bin'), espeak_config=speech)
    for name, voice, speed, text in PHRASES:
        audio, rate = engine.create(text, voice=voice, speed=speed, lang='en-us')
        raw = out / (name + '.raw.wav')
        soundfile.write(raw, audio, rate)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-af', 'highpass=f=90,loudnorm=I=-16:TP=-2', '-ar', '44100', '-ac', '1', '-c:a', 'pcm_s16le', str(out / (name + '.wav'))], check=True)
        raw.unlink()
        print(name, flush=True)


main()
