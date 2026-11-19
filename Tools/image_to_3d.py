"""A concept image to a textured 3D model with TRELLIS.2 (Microsoft, MIT licence), on its free Hugging Face Space.

  Saved/AudioTools/gpu_test_venv/bin/python Tools/image_to_3d.py IMAGE.png [OUT.glb] [--seed N] [--faces N] [--texture N]
Writes Art/Monsters/Models/<image stem>.glb by default. The image is uploaded to the Space (a public service run by
Hugging Face); the Space removes its background, builds the shape and the texture, and returns a GLB. Anonymous use is
limited by a daily GPU quota: when it is spent the call fails with a quota message, and the quota returns the next day
(a Hugging Face account, set as the HF_TOKEN environment variable by the user, raises it).
"""
import os
import pathlib
import shutil
import sys
import time

from gradio_client import Client, handle_file

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPACE = 'microsoft/TRELLIS.2'


def main():
    args = sys.argv[1:]
    take = lambda flag, default: (args.pop(args.index(flag) + 1), args.remove(flag))[0] if flag in args else default
    seed, faces, texture = int(take('--seed', 0)), int(take('--faces', 200000)), int(take('--texture', 2048))
    image = pathlib.Path(args[0]).resolve()
    out = pathlib.Path(args[1]).resolve() if len(args) > 1 else ROOT / 'Art/Monsters/Models' / (image.stem + '.glb')
    began = time.time()
    token = os.environ.get('HF_TOKEN')
    client = Client(SPACE, verbose=False, **({'token': token} if token else {}))
    client.predict(api_name='/start_session')
    clean = client.predict(handle_file(str(image)), api_name='/preprocess_image')
    print('background removed %.0f s' % (time.time() - began), flush=True)
    client.predict(handle_file(clean if isinstance(clean, str) else clean['path']), seed, '1024', 7.5, 0.7, 12, 5.0, 7.5, 0.5, 12, 3.0, 1.0, 0.0, 12, api_name='/image_to_3d')
    print('shape and texture %.0f s' % (time.time() - began), flush=True)
    result = client.predict(faces, texture, api_name='/extract_glb')
    glb = result[1] if isinstance(result, (list, tuple)) else result
    glb = glb if isinstance(glb, str) else glb.get('path') or glb.get('value')
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(glb, out)
    shutil.copy(clean if isinstance(clean, str) else clean['path'], out.with_name(out.stem + '_input.png'))
    print('MODEL %s %.1f MB in %.0f s' % (out, out.stat().st_size / 1e6, time.time() - began), flush=True)


if __name__ == '__main__':
    main()
