"""Concept art for the elemental monsters (Art/Monsters/DESIGN_BRIEFS.md), rendered locally with Stable Diffusion XL.

  Saved/AudioTools/sdxl_venv/bin/python Tools/concept_art.py [NAME ...] [--view hero|side|front|head] [--steps N] [--seed N] [--count N]
Writes Art/Monsters/Concepts/<Name>_<view>_<seed>.png (1216 x 832). No name renders all seven.

The machine has no usable GPU for this (CPU only), so a picture takes several minutes: about 15 s a step. The model is
stabilityai/stable-diffusion-xl-base-1.0 (CreativeML Open RAIL++-M), in the Hugging Face cache; the environment
(Saved/AudioTools/sdxl_venv) holds a current diffusers and borrows PyTorch from the voice environment beside it.

Each prompt is the creature's brief cut down to what the model can read (77 tokens an encoder): the subject first, its
one focal feature, the look of the hide, then the shot. STYLE is the same for all, so the seven belong together.
"""
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'Art/Monsters/Concepts'
STYLE = 'photorealistic creature concept art, AAA game design, cinematic lighting, dark background'
NEGATIVE = ('cartoon, anime, toy, cute, lowres, blurry, deformed, extra limbs, extra heads, fused limbs, bad anatomy, text, caption, watermark, signature, frame, border, '
            'human, woman, man, pretty face, dress, robe, armor, clothing, weapon, saddle, multiple animals, city, buildings')
VIEWS = {'hero': 'full body, three-quarter view', 'side': 'full body, side view, plain grey background', 'front': 'full body, front view, plain grey background',
         'head': 'close-up portrait of the head'}
# Kept under 77 tokens with the view and the style: what does not fit is not read.
CREATURES = {
    'PyreLion': 'a huge male lion whose entire mane is roaring fire, mane made of flames, burning tail tuft, soot-black scarred hide with glowing ember cracks, coal-bright eyes, prowling',
    'StormDrake': 'a lean four-legged storm dragon, slate-blue scales, tall glowing glass spines along its back crackling with lightning, dark wings veined with lightning, white-blue eyes, glowing throat',
    'GaleMantis': 'a colossal praying mantis monster rearing up, triangular head, huge raptorial scythe forearms raised, serrated edges glowing sky-blue, pale jade armored exoskeleton, wings spread, storm wind and dust',
    'RimeMammoth': 'a woolly mammoth with enormous tusks of translucent blue glacier ice, long dark matted fur tipped with icicles, ice crystals along its back, pale blue glowing eyes, freezing mist, frost',
    'GloomToad': 'a giant monstrous toad, skin pitch black as coal, matte, covered in warts, some warts glowing violet from inside, magenta slit eyes, wide open mouth with a long tongue, squat heavy body, dark swamp at night',
    'Seraph': 'a biblically accurate angel creature, six huge feathered wings covered in glowing eyes, tall thin inhuman ivory body, smooth faceless head with a glowing vertical slit, floating halo of bone, eerie',
    'NightFiend': 'a hunched demonic predator, lean sinewy body, black burnt-leather hide, heavy curled ram horns, torn bat wings, long clawed arms, cloven hooves, glowing violet cracks across its chest, needle teeth',
}

# For image-to-3D: the animal alone, whole, on a plain ground, with nothing round it that a model builder would turn into
# geometry (no fire trails, mist, scenery). --view model uses these and MODEL_STYLE.
MODEL_STYLE = 'full body, three-quarter view, isolated on a plain white background, studio lighting, photorealistic creature, AAA game asset, entire animal in frame'
MODEL_SUBJECT = {
    # the author, of the first lion model: "doesn't have eyes and its mane is the same color as his body, it needs to be darker"
    'PyreLion': 'a huge muscular male lion, its entire mane pure jet black, black mane, tawny golden body, wide open glowing amber eyes, fierce face, standing still on four straight legs, side view',
    'StormDrake': 'a lean four-legged dragon, slate-blue scales, tall glowing yellow glass spines along its back, wings half folded, white-blue eyes, standing',
    'GaleMantis': 'a giant praying mantis monster, triangular head, huge raptorial scythe forearms raised, pale jade armored exoskeleton, wings half open, standing upright',
    'RimeMammoth': 'a woolly mammoth with enormous tusks of translucent blue ice, long dark matted fur tipped with icicles, ice crystals along its back, standing',
    'GloomToad': 'a giant monstrous toad, pitch-black warty skin, warts glowing violet, magenta slit eyes, wide mouth, squat heavy body, sitting',
    'Seraph': 'a tall thin faceless angelic creature, smooth ivory body, six feathered wings spread, glowing vertical slit for a face, halo ring above its head, standing',
    'NightFiend': 'a hunched demonic predator, lean sinewy body, black leathery hide, heavy curled ram horns, bat wings half open, long clawed arms, cloven hooves, glowing violet cracks on its chest, standing',
}


def main():
    args = sys.argv[1:]
    take = lambda flag, default: (args.pop(args.index(flag) + 1), args.remove(flag))[0] if flag in args else default
    view, steps, seed, count = take('--view', 'hero'), int(take('--steps', 26)), int(take('--seed', 7)), int(take('--count', 1))
    names = [n for n in CREATURES if not args or n in args]
    import torch
    from diffusers import DPMSolverMultistepScheduler, StableDiffusionXLPipeline
    torch.set_num_threads(24)
    began = time.time()
    gpu = torch.cuda.is_available()   # in the TRELLIS.2 environment (Saved/AudioTools/t2_run.sh) a picture takes seconds
    pipe = StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0', variant='fp16', torch_dtype=torch.float32, use_safetensors=True)
    if gpu:
        pipe.enable_sequential_cpu_offload()   # about 5 GB of the 8 are free: the whole UNet does not fit beside the desktop
        pipe.vae.enable_tiling()
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
    pipe.set_progress_bar_config(disable=True)
    print('model loaded in %.0f s' % (time.time() - began), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        for k in range(count):
            started = time.time()
            prompt = '%s, %s' % (MODEL_SUBJECT[name], MODEL_STYLE) if view == 'model' else '%s, %s, %s' % (CREATURES[name], VIEWS[view], STYLE)
            size = (1024, 1024) if view == 'model' else (1216, 832)
            image = pipe(prompt=prompt, negative_prompt=NEGATIVE + (', fire trail, smoke, mist, scenery, ground clutter, cropped, close-up, portrait, sketch, line art, drawing, walking, running, brown mane, orange mane' if view == 'model' else ''), width=size[0], height=size[1], num_inference_steps=steps, guidance_scale=6.5,
                         generator=torch.Generator('cpu').manual_seed(seed + k)).images[0]
            target = OUT / ('%s_%s_%d.png' % (name, view, seed + k))
            image.save(target)
            print('%s %.0f s' % (target.name, time.time() - started), flush=True)


if __name__ == '__main__':
    main()
