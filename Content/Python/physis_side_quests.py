"""Every side quest in the game, for the pause menu's Quests page (Tools/blueprint_logic/side_quests.py draws them).

Author, 2026-11-17: "scan the whole game for sidequest. Then make a Side Quests submenu under the Quests menu and make the
quests appear there with a description as they are given. We also need a Completed quests section".

What the scan found: nine requests, each asked by a person and paid by the same person (the PEOPLE tables of
physis_conclave_lore.py, physis_grove_lore.py and physis_arche_lore.py: a row <Key> who asks, and a row <Key>Thanks who
appears once the thing is held). The station and the Center have none: nobody there asks for anything (the Center's
vaults and caches are optional, but they are found, not given).

How the game already marks them, in BP_Physis.Flags:
  given    the asker's own token (',orsolya,'), set at the end of their greeting
  held     the thing's token (',seedpod,'; for three-part things ',pages,' once ',page1,' ',page2,' ',page3,' are held)
  done     ',met_<Key>Thanks,', set by BP_NPC.TalkReward when the person thanks her
A quest shows under Side Quests from `given` (or from the first part found, if she finds one before she is asked)
until `done`, then under Completed.

Row: world, title, given, held, parts (the tokens of a three-part thing, else ()), done, description, what to do once
it is held, reward. Text lines are split with '~' and kept under 62 characters, the width of a column.
"""

QUESTS = (
    ('The Conclave', 'The Starlace Seed Pod', ',orsolya,', ',seedpod,', (), ',met_OrsolyaThanks,',
     'Orsolya Fenn, at the Wellspring, left her best seed pod~drying on the Reservoir island when the swarm came.~Bring it back to her.',
     'You have the seed pod. Return to Orsolya at the Wellspring.', 'Health Augmentation'),
    ('The Conclave', 'The Ledger\'s Lost Pages', ',petra,', ',pages,', (',page1,', ',page2,', ',page3,'), ',met_PetraThanks,',
     'Three pages of the Ledger of Names blew out of the Archive:~one toward the Terraces, one toward the Reservoir, one into~the Old Quarter. Bring them to Petra Lune at the Archive.',
     'You have all three. Return to Petra at the Archive.', 'Pistol Augmentation'),
    ('The Conclave', 'Tamsin\'s Kite', ',tamsin,', ',kite,', (), ',met_TamsinThanks,',
     'Tamsin\'s kite is stuck at the top of the Terraces, past the~red walls the AL made. She has promised her jar of crystals.',
     'You have the kite. Return to Tamsin in the Commons.', '60 Divinity'),
    ('The Conclave', 'Halden-7\'s Memory Core', ',halden,', ',core,', (), ',met_HaldenThanks,',
     'Halden-7 left his memory core in a socket by the Foundry~furnaces when the swarm came. It holds forty years of the~Conclave.',
     'You have the core. Return to Halden-7 at the Mendery.', 'Defense Augmentation'),
    ('The Wounded Grove', 'The Seed Canisters', ',wick,', ',cans,', (',can1,', ',can2,', ',can3,'), ',met_WickThanks,',
     'Three canisters of the seed bank were out when the wall~sealed: one in Old Town, one on a roof in the drowned campus,~one up in the great trees. Bring them to Wick at the camp.',
     'You have all three. Return to Wick at the field camp.', 'Agility Augmentation'),
    ('The Wounded Grove', 'Burr\'s Coupling Pin', ',burr,', ',pin,', (), ',met_BurrThanks,',
     'Burr has held up the fallen overpass for nine years. His~coupling pin went into the lake with his hauler, on the~campus side.',
     'You have the pin. Return to Burr under the overpass.', 'Defense Augmentation'),
    ('Arche', 'Ilun\'s Chime', ',ilun,', ',chime,', (), ',met_IlunThanks,',
     'Ilun, keeper of the Cisterns, hung a chime on the pinnacle~by the Crystal Garden\'s Mirror. It fell when the stair went.',
     'You have the chime. Return to Ilun at the Hearthold.', 'Defense Augmentation'),
    ('Arche', 'The Leaves of the Record', ',oreth,', ',tablets,', (',tab1,', ',tab2,', ',tab3,'), ',met_OrethThanks,',
     'Three leaves of the city\'s record were lost with the Makers\'~Row: one by the Ossuary, one on the Middle Tier, one on top~of the Galleries. Bring them to Oreth at the Hearthold.',
     'You have all three. Return to Oreth at the Hearthold.', 'Agility Augmentation'),
    ('Arche', 'The Last Seedstone', ',sael,', ',seedstone,', (), ',met_SaelThanks,',
     'One seedstone of the Crystal Garden is left, on the Mirror\'s~island in the Cisterns. Sael wants to plant it at the~Hearthold.',
     'You have the seedstone. Return to Sael at the Hearthold.', 'Pistol Augmentation'),
)
