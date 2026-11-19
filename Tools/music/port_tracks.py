"""Re-render the SoundFont tracks with Muse Sounds: each old script composes and finishes its track as before, with
its SoundFont player replaced by Tools/music/port.py.

  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/music/port_tracks.py [center temple awakening conclave grove]
Each wav it replaces under Art/Audio is first copied to Saved/Backup_2026-11-16_music_soundfont/ (once).
The sampled sections are recorded in a room and MuseScore adds its own reverb, so the old scripts' hall is mixed in
at HALL of its former amount.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'Tools/music'), str(ROOT / 'Tools')]
import port  # noqa: E402

HALL = .4
BACKUP = ROOT / 'Saved/Backup_2026-11-16_music_soundfont'
TRACKS = {'center': ('build_physis_center_audio', 'center_orchestral', 'Art/Audio/Center/S_Music_Center.wav'),
          'temple': ('build_physis_center_audio', 'temple_music', 'Art/Audio/Center/S_Music_Temple.wav'),
          'awakening': ('build_physis_center_audio', 'awakening_music', 'Art/Audio/Center/S_Music_Awakening.wav'),
          'conclave': ('build_physis_conclave_audio', 'conclave_music', 'Art/Audio/Conclave/S_Music_Conclave.wav'),
          'grove': ('build_physis_grove_audio', 'grove_music', 'Art/Audio/Grove/S_Music_Grove.wav')}


def main():
    for track in sys.argv[1:] or list(TRACKS):
        module_name, function, target = TRACKS[track]
        module = __import__(module_name)
        kept = BACKUP / target
        if not kept.exists():
            kept.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / target, kept)
        name = pathlib.Path(target).stem.replace('S_Music_', '')
        module.sf.SoundFont = lambda path: None
        module.perform = module.render = port.perform_muse(name)
        if not getattr(module.hall, 'lighter', False):   # the Grove's hall is the Conclave's, already made lighter
            def hall(signal, seconds=3.0, wet=.5, *rest, old=module.hall, **more):
                return old(signal, seconds, wet * HALL, *rest, **more)
            hall.lighter = True
            module.hall = hall
        if hasattr(module, 'conclave'):   # the Grove writes with the Conclave's write(), which looks its folder up there
            module.conclave.OUT = module.OUT
        getattr(module, function)()
        print('MUSIC', target, flush=True)


main()
