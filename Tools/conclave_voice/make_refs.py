"""Kokoro venv: a raw, dry reference take of a Kokoro voice, for a cloning model to take its timbre from.
make_refs.py VOICE [VOICE...] -> Saved/AudioTools/voice_test/ref_<voice>.wav"""
import os, pathlib, sys
import soundfile
from kokoro_onnx import EspeakConfig, Kokoro
ROOT = pathlib.Path(__file__).resolve().parents[3]
models = ROOT / 'Saved/AudioTools/kokoro_models'
speech = EspeakConfig(lib_path=os.environ['ESPEAK_LIB'], data_path=os.environ['ESPEAK_DATA'])
engine = Kokoro(str(models / 'kokoro-v1.0.onnx'), str(models / 'voices-v1.0.bin'), espeak_config=speech)
TEXT = ('I have kept these shelves for longer than I care to count. Every morning I open the shutters, light the lamp, '
        'and read the last page again, to be sure the ink has not changed its mind in the night.')
for voice in sys.argv[1:]:
    audio, rate = engine.create(TEXT, voice=voice, speed=.95, lang='en-gb' if voice[0] == 'b' else 'en-us')
    out = pathlib.Path(__file__).parent / ('ref_%s.wav' % voice)
    soundfile.write(out, audio, rate)
    print(out.name, round(len(audio) / rate, 1), 's')
