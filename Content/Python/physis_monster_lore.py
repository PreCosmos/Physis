"""The elemental monsters: their meshes, numbers and Logbook text.

Author, 2026-11-17: "add monsters in all the levels with physical attacks and attacks like fire, ice, thunder, wind and
dark and light. I want you to give a scientific explanation in their scans of how they came to be and how to beat them."
Then: "We need new VERY impressive designs. AAA quality ... monster designs based on lions, dragons, mantises,
elephants, frogs, angels and demons", and, of the first two models: "Add fire and ice particles around them
respectively", and then, the same day: "fix the dragon if it's a thunder creature and instead of misty ice put some
thunders engulfing him" (so the dragon is the Storm Drake of the brief again, wrapped in lightning).

Each is a generated model (Art/Monsters/DESIGN_BRIEFS.md -> Tools/concept_art.py -> Tools/image_to_3d.py ->
Tools/build_physis_monsters.py -> physis_monster_models.py; since 2026-11-18 the models are made on this machine,
Tools/image_to_3d_local.py). All seven of the briefs exist; the earlier six
recoloured air-swimmers (Saved/Backup_2026-11-17_real_monsters) were refused by the author and are not placed.

Each fights with its body as the other animals do, and also looses a bolt of its element
(Tools/blueprint_logic/elements.py: BP_TrainingDrone.Element, BP_EnemyBolt, BP_Physis.PhysisElement):
  1 fire     burns: half a point of health a second for three seconds
  2 ice      her walking speed falls to 55 % for 3.5 s
  3 thunder  a fast bolt; she cannot act for 0.6 s
  4 wind     a slow gust that throws her back
  5 dark     takes 15 Divinity
  6 light    the fastest bolt; it cannot be blocked or parried, only avoided
A hit that is blocked or parried carries no element (light aside, which no guard stops).

The scans are Proposed, for the author to review. Every "how to beat it" line says only what the game does.

MONSTERS[name]: mesh, health, hover (cm from the ground to the model's middle, so its feet stand), EnemyKind (0 plain),
BP_TrainingDrone.Animal (the body plan whose lunge it uses: 5 for the four-legged, 6, the gentlest, for the
upright ones and the mammoth), Reach (cm), Logbook entry, how many stand together,
element, half size (cm: forward, sideways, up) for its clouds (physis_monster_models.aura), and for some a crown:
the middle and half size of a second cloud of fire or mist, in the body's axes (the lion's mane).
"""

MONSTERS = {
    'PyreLion': ('SM_MN_PyreLion', 24, 128, 0, 5, 330.0, ('Enemies', 'Pyre Lion',
        'Level 4. Fire. Glands at the root of each mane filament seep an oil that burns in air, and the lion lights it '
        'with a spark from a crystal plate under its tongue. Divinity in its blood carries the heat away, so the skin '
        'beneath never burns. Its fire sets you burning for three seconds. It rears before it strikes, and it must draw '
        'breath after every roar: parry or sidestep the flame, then strike while its chest is still heaving. '
        'Twenty-four health.'), 1, 1, (150, 66, 128), ((95, -10, 40), (70, 66, 70))),
    'StormDrake': ('SM_MN_StormDrake', 40, 198, 0, 5, 430.0, ('Enemies', 'Storm Drake',
        'Level 5. Thunder. Stacks of flat cells run the length of its back, each holding a small charge like the plates '
        'of a battery, and its spines are their terminals. A nerve thick with Divinity fires them all at once, and the '
        'charge leaves through the mouth as an arc. The shock locks your muscles for a little over half a second. It '
        'draws its neck back before every bolt and every bite: parry on the flash or keep stone between you, and '
        'strike while it charges again. Forty health.'), 1, 3, (218, 150, 198)),
    'GaleMantis': ('SM_MN_GaleMantis', 16, 148, 3, 5, 340.0, ('Enemies', 'Gale Mantis',
        'Level 3. Wind. Its forearms are latched and spring-loaded like a mantis shrimp\'s: muscle loads the spring '
        'slowly and the latch lets it go in a few thousandths of a second. The arm moves faster than the air can get '
        'out of its way, and the wave of air it pushes is the weapon. The blast throws you back, so keep clear of '
        'edges. It rears before it strikes: step aside as it rises, and cut it while it folds its arms again. '
        'Sixteen health.'), 1, 4, (165, 137, 148)),
    'RimeMammoth': ('SM_MN_RimeMammoth', 60, 156, 1, 6, 450.0, ('Enemies', 'Rime Mammoth',
        'Level 5. Ice. It cools brine in channels under its skin by letting it evaporate through the coat, the way '
        'sweat cools you, until the brine is far colder than freezing water. It sprays that brine from its trunk, and '
        'a hit slows your step to about half for three and a half seconds. Light blows are lost in the coat. It throws '
        'its head up before it brings the tusks down: keep moving, strike heavy, and come at it from behind, where '
        'neither trunk nor tusk can reach. Sixty health.'), 1, 2, (215, 80, 156)),
    'GloomToad': ('SM_MN_GloomToad', 20, 97, 0, 5, 300.0, ('Enemies', 'Gloom Toad',
        'Level 3. Dark. Its skin is packed with a pigment that takes in nearly all the light that falls on it and '
        'keeps it as heat. Glands in the warts make an alkaloid that binds Divinity the way some toad poisons bind to '
        'nerves, and it coats its spit with it. A hit takes fifteen Divinity from you, so do not count on your '
        'Divinity near it. It sinks on its haunches before it lunges or spits: strike while it gathers itself. '
        'Twenty health.'), 1, 5, (130, 105, 97)),
    'Seraph': ('SM_MN_Seraph', 30, 215, 0, 6, 330.0, ('Enemies', 'Seraph',
        'Level 5. Light. A glider that came to stand upright in the updrafts of the Center. Crystal cells in its '
        'feathers gather light all day, and channels of clear flesh carry it to a lens behind its brow. The beam '
        'passes a raised blade as if it were glass: it cannot be blocked or parried, only avoided. Its wings draw back '
        'before it fires. Step aside or stand behind something solid, then close in: its body is fragile, and the '
        'sweep of its wings can be parried. Thirty health.'), 1, 6, (58, 170, 164)),
    'NightFiend': ('SM_MN_NightFiend', 28, 150, 0, 6, 330.0, ('Enemies', 'Night Fiend',
        'Level 4. Dark. A cave hunter that sees by the Divinity in living things, not by light. Its body stores what '
        'it takes in the glowing membranes of its wings and chest, and it throws a little back out to stun its prey. '
        'A hit takes fifteen Divinity from you. It hunts by your Divinity, so it always knows where you are. Parry its '
        'claws, and strike its chest when it draws its arm back to throw: that is where it is weakest. '
        'Twenty-eight health.'), 1, 5, (63, 132, 150)),
}
# Which species live in which world. The author, 2026-11-18: "The Battle Station needs one of these enemies in it. The
# rest of the levels must have one of each in them."
EVERY = ('PyreLion', 'StormDrake', 'GaleMantis', 'RimeMammoth', 'GloomToad', 'Seraph', 'NightFiend')
WORLDS = {'ship': ('PyreLion',), 'center': EVERY, 'conclave': EVERY, 'grove': EVERY, 'arche': EVERY}


def entries():
    return [row[6] for row in MONSTERS.values()]
