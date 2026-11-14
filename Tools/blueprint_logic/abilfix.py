# Rewrites only PageAbilities from physis_lore.ABILITIES. It writes BP_PhysisHUD, so it must be the only HUD write of
# a fresh editor launch (see rebuild2.sh's warning).
# 2026-11-09: it took pause.py's lines by number (222 and 387-388), which had drifted onto other code; it now finds
# them by their content: the colour constants, the lore loader and the PageAbilities block.
import sys
sys.path.insert(0,'Tools')
SCRATCH='/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/'
hf=open(SCRATCH+'hudfont.py').read()
exec(hf[:hf.index("var(H,'LineY','float')")])
pz=open(SCRATCH+'pause.py').read()
lines=pz.split('\n')
exec(next(l for l in lines if l.startswith("GOLD='")))
i=lines.index('import importlib.util')
exec('\n'.join(lines[i:i+2]))
a=pz.index("rows=[];cols="); b=pz.index("comp(H)",a)
exec(pz[a:b]); comp(H)
