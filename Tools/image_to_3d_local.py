"""A concept image to a textured 3D model with TRELLIS.2 (Microsoft, MIT licence) on this machine's GPU.

  Saved/AudioTools/t2_run.sh Tools/image_to_3d_local.py IMAGE.png [IMAGE.png ...] [--seed N] [--type 512|1024_cascade] [--faces N] [--texture N]
Writes Art/Monsters/Models/<name>.glb for each image, <name> being the file name up to its first underscore
(PyreLion_model_31.png -> PyreLion.glb), and the cut-out picture it was made from beside it.

The same model as Tools/image_to_3d.py reaches through its Hugging Face Space, without the daily quota. Set up by
Saved/AudioTools/t2_install.sh into a micromamba environment at ~/.local/share/physis_t2 (Python 3.11, PyTorch for
CUDA 12.8, the CUDA toolkit and compilers; outside the project because a space in its path breaks the builds). It needs the proprietary NVIDIA driver (the laptop's other boot,
nova/NVK, has no CUDA).

Memory: the card has 8 GB and the model's page asks for 24. The pipeline's low-VRAM mode keeps every part in main
memory and moves one to the card while it works (each flow model is 2.6 GB), so close the Unreal editor first.
--type 512 is the lighter setting; 1024_cascade is the Space's.

Two changes from the stock pipeline, both about licences:
  - the background is cut with rembg's isnet-general-use (Apache 2.0), or taken from the picture's own alpha; the
    stock BRIA RMBG-2.0 is for non-commercial use only and is never loaded;
  - the image encoder, facebook/dinov3-vitl16-pretrain-lvd1689m, is gated: the author accepted its licence on
    Hugging Face (2026-11-17) and the login from `hf auth login` fetches it.
"""
import gc
import os
import pathlib
import sys
import time

os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR', '1')
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Saved/AudioTools/TRELLIS.2'))
OUT = ROOT / 'Art/Monsters/Models'


def cut_out(path):
    """The picture with its background made transparent."""
    from PIL import Image
    import numpy as np
    image = Image.open(path)
    if image.mode == 'RGBA' and not (np.array(image)[:, :, 3] == 255).all():
        return image
    from rembg import new_session, remove
    return remove(image.convert('RGB'), session=new_session('isnet-general-use'))


class NoBackgroundModel:
    """Stands where the pipeline would load BRIA RMBG-2.0; pictures reach it already cut out."""
    def __init__(self, **_):
        pass

    def to(self, *_):
        return self

    cuda = cpu = to

    def __call__(self, image):
        raise RuntimeError('the picture has no transparent background: cut_out() should have made one')


def main():
    args = sys.argv[1:]
    take = lambda flag, default: (args.pop(args.index(flag) + 1), args.remove(flag))[0] if flag in args else default
    seed, kind, faces, texture = int(take('--seed', 0)), take('--type', '1024_cascade'), int(take('--faces', 200000)), int(take('--texture', 2048))
    import torch
    import o_voxel
    from trellis2.pipelines import Trellis2ImageTo3DPipeline, rembg
    rembg.BiRefNet = NoBackgroundModel
    began = time.time()
    pipeline = Trellis2ImageTo3DPipeline.from_pretrained('microsoft/TRELLIS.2-4B')
    pipeline.low_vram = True
    encoder = pipeline.image_cond_model.model
    if not hasattr(encoder, 'layer'):   # newer transformers keep DINOv3's blocks one level down; TRELLIS.2 reads them here
        encoder.layer = encoder.model.layer
    pipeline.cuda()
    print('pipeline loaded %.0f s' % (time.time() - began), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for path in args:
        started = time.time()
        name = pathlib.Path(path).stem.split('_')[0]
        image = cut_out(path)
        image.save(OUT / (name + '_input.png'))
        torch.cuda.reset_peak_memory_stats()
        # A detailed creature overfills the card where a plain one fits (the lion, 2026-11-17): on running out of
        # memory the same picture is tried with fewer tokens (less surface detail), and last at the 512 setting.
        mesh = None
        for how, tokens in ((kind, 49152), (kind, 32768), (kind, 22000), ('512', 49152)):
            gc.collect()
            torch.cuda.empty_cache()
            try:
                mesh = pipeline.run(image, seed=seed, pipeline_type=how, max_num_tokens=tokens)[0]
                print('%s sampled as %s with up to %d tokens' % (name, how, tokens), flush=True)
                break
            except RuntimeError as problem:
                if 'out of memory' not in str(problem).lower():
                    raise
                print('%s: out of memory as %s with %d tokens, trying lighter' % (name, how, tokens), flush=True)
                for part in pipeline.models.values():   # whatever was on the card when it failed
                    part.cpu()
        if mesh is None:
            print('FAILED %s: does not fit in memory at any setting' % name, flush=True)
            continue
        made = torch.cuda.max_memory_allocated() / 2 ** 30
        # Turning the result into a GLB is the step that overfills an 8 GB card (the remesh at full detail, 2026-11-17):
        # the sampling's leftovers are released first, and if it still does not fit it is written without the remesh
        # (the remesh works at the model's full grid whatever the face count), from a thinner mesh if need be.
        glb = None
        for limit, remesh in ((16777216, True), (8000000, False), (2000000, False)):
            gc.collect()
            torch.cuda.empty_cache()
            try:
                mesh.simplify(limit)   # 16777216 is nvdiffrast's limit
                glb = o_voxel.postprocess.to_glb(vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs, coords=mesh.coords, attr_layout=mesh.layout,
                                                 voxel_size=mesh.voxel_size, aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]], decimation_target=faces, texture_size=texture,
                                                 remesh=remesh, remesh_band=1, remesh_project=0, verbose=False)
                print('glb made from %d faces, remesh %s' % (limit, remesh), flush=True)
                break
            except RuntimeError as problem:   # torch's own, and CuMesh's "CUDA error ... out of memory"
                if 'out of memory' not in str(problem).lower():
                    raise
                print('out of memory making the glb from %d faces (remesh %s), trying lighter' % (limit, remesh), flush=True)
        if glb is None:
            print('FAILED %s: no glb fits in memory' % name, flush=True)
            continue
        target = OUT / (name + '.glb')
        if target.exists():
            target.replace(OUT / (name + '_before.glb'))
        glb.export(str(target), extension_webp=False)
        print('MODEL %s %.1f MB in %.0f s, peak %.1f GB on the card' % (target.name, target.stat().st_size / 1e6, time.time() - started, made), flush=True)
        del mesh, glb
        torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
