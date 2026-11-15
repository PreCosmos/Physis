"""Kokoro venv: every dry take in conclave_dry/ through its speaker's chain, room and loudness, exactly as
Tools/build_physis_voice.py does for Kokoro's takes (KINDS, room(), LOUDNESS), into conclave_wet/. wet.py"""
import json, pathlib, subprocess, sys, tempfile, types
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
source = (ROOT / 'Tools/build_physis_voice.py').read_text().split('\ndef main():')[0]
scope = {'__file__': str(ROOT / 'Tools/build_physis_voice.py'), '__name__': 'voice_defs'}
exec(compile(source, 'build_physis_voice.py', 'exec'), scope)
v = types.SimpleNamespace(**scope)
report = json.loads((HERE / 'report.json').read_text())
out = HERE / 'conclave_wet'
out.mkdir(exist_ok=True)
done = 0
with tempfile.TemporaryDirectory() as d:
    spaces = {}
    for name, row in sorted(report.items()):
        kind = row['kind']
        speed, chain, space = v.KINDS[kind]
        if kind not in spaces:
            path = pathlib.Path(d) / ('Room_%s.wav' % kind)
            spaces[kind] = (path, v.room(path, **space))
        path, seconds = spaces[kind]
        effect = '[0:a]%s,apad=pad_dur=%.2f,pan=stereo|c0=c0|c1=c0[v];[v][1:a]afir=irnorm=-1,%s' % (chain, seconds, v.LOUDNESS)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(HERE / 'conclave_dry' / (name + '.wav')), '-i', str(path),
                        '-filter_complex', effect, '-ar', '44100', '-c:a', 'pcm_s16le', str(out / (name + '.wav'))], check=True)
        done += 1
print('wet', done, 'kinds', sorted(spaces))
