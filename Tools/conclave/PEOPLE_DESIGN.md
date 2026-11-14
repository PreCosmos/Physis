# Conclave people redesign: design spec (2026-11-09)

This pass was read-only. Nothing was launched and no project, engine or Blender file was edited.

The only files I wrote are 58 JPEG preset thumbnails, copied byte for byte out of the preset .uasset thumbnail tables into `/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/118dfceb-aea3-45c9-9a8a-7af9dd0bddc6/scratchpad/designer_presets/`. They are temporary and can be deleted.

**Path shorthands**
- PRJ = `/var/home/precosmos/Έγγραφα/Unreal Projects/Physis`
- MHC = `/home/precosmos/Unreal Engine/Linux_Unreal_Engine_5.8.4/Engine/Plugins/MetaHuman/MetaHumanCharacter`
- ENG = `/home/precosmos/Unreal Engine/Linux_Unreal_Engine_5.8.4/Engine`
- MEM = `/home/precosmos/.claude/projects/-var-home-precosmos---------Unreal-Projects-Physis/memory`
- TS = `MHC/Content/Optional/TextureSynthesis/TS-1.3-F_UE_res-1024_nchr-153`

**Confidence tags**
- [V] verified in files.
- [I] inferred.
- [U] unknown.
- [S#] the spike test that settles it (section 3.4).

## 0. New evidence found in this pass

1. **The cloud has worked from this machine before.** On 2026-10-30 a `-nullrhi` assembly of MH_Physis got past the build gate, which requires both face DNA and high-resolution textures (MHC/Source/MetaHumanCharacterEditor/Private/MetaHumanCharacterEditorSubsystem.cpp:2239-2275 and 2296-2310). It failed only at the Texture Graph bake: PRJ/Saved/Logs/CharacterAssembly.log:29 shows the `-nullrhi` flag, line 2241 "TextureGraph engine is not initialised", line 2280 "assembly failed".
   - So the auto-rig and texture services answered this account from here [V].
   - Assembly needs a real GPU [V].
2. **The project already scripts every MetaHuman step**, so most of the pipeline reuses code that worked:
   - Preset coefficients: PRJ/Content/Python/physis_character_tools.py:45-60
   - Body shape: :62-70
   - Eye colour: :71-74
   - Skin: :76-86
   - Grooms with Melanin and Redness: :87-101
   - Auto-rig and textures: PRJ/Content/Python/physis_outfit_tools.py:1119-1138
   - Low-memory OPTIMIZED assembly: :1082-1101
   - Landmark sculpting: :302-360
   - A skeletal wardrobe item whose `principal_asset` and `pipeline` are set from Python: :155-178. This settles researcher 1's open question [V].
   - Outfit component with leader pose: :1036-1053
   - Skin hidden under clothes via a ClothMask: PRJ/Content/Python/physis_animation_tools.py:111-135 and :197-215
3. **`get_face_landmarks` returns 79 points, not 100** (PRJ/Art/Characters/Physis/face-identity-baseline.json). The researcher assumed 100.
   - I identified the indices from their coordinates [I]:

     | Region | Indices |
     |---|---|
     | Nose | 64 tip, 65 columella, 6 mid-bridge, 59 nasion, 40/57 bridge sides, 45/67 nostril wings, 70/74 nose–cheek |
     | Eyes | 19/33 inner corners, 18/22 outer corners, 20/44 upper lid, 37/53 lower lid |
     | Brows | 24/77 heads, 10/26 middle, 25/78 tails |
     | Cheeks and jaw | 23/66 cheekbones, 2/29 lower cheek, 1/28 jaw angles, 3/30 chin sides |
     | Mouth and chin | 62 chin, 4 lower lip, 5 upper lip, 48/32 corners |
     | Skull and ears | 7 forehead, 60 crown, 13 back of skull, 38/54 and 39/56 ears |
   - The face model applies only about 25-40% of a requested move (MEM/physis-author-direction.md:15; physis_outfit_tools.py:336-337). Every delta below is the change wanted on the mesh, in cm. Request about 2.5 times as much.
4. **Preset choices are grounded.** I chose the face bases by looking at all 29 presets' clay thumbnails, and parsed their stored skin and groom data read-only. I avoid Ada, because Physis is built on Ada (physis_character_tools.py:48).
5. **Each face texture variant is chosen to fit the person's tone and age.**
   - The variant (`face_texture_index`) is one whose native tone `v_ui_chr_0` (TS/ts_params.json) is within 0.05 of the person's skin U value. Synthesis interpolates a variant's colour gains away from that native point (MetaHumanCoreTechLib/.../texture_model.cpp:253-258; ts_utils.cpp:142-168) [I].
   - Its wrinkle, stubble and mark tags (TS/texture_attributes.json) match the person's age.
   - All 12 picks are different variants.
6. **Two settings are UI-only.** HeadScale (range 0.8-1.3) sits on a property that is read-only to Python (MHC/Source/MetaHumanCharacter/Public/MetaHumanCharacter.h:98-99 and 386-387). Cornea Size is clamped to 0.145-0.185 (MetaHumanCharacterEyes.h:196-198).

## 1. The cast

> **Superseded values (2026-11-09):** the author then chose natural eye and hair colours. The live values, the iris and hair spread included, are in `Content/Python/physis_conclave_cast.py` `MH`; the entries below keep the original reasoning.

**Rules for the whole cast**
- **Palette.** The body is exempt (author, 2026-11-09): natural skin (U/V), lips, gums, nails, irises and hair
  (brows, lashes, beards, peachfuzz). Makeup, clothes, headwear and props stay in gold, light blue, red, green, black and
  white (Tools/conclave_meshes/palette.py).
  - The author chose natural eye and hair colours after this spec was written, so the iris and hair values below are
    palette-bound first drafts. Revise them in Phase 0 toward a natural, varied cast: brown irises for most (hazel,
    grey, blue and green for some), and brown, dark-brown, black, auburn, fair and grey hair, each fitting the person's
    age and skin.
  - The render audit [S9/S12] then checks only makeup, clothes and props; skin, eyes and hair are masked out of it.
- **Costumes.** Each person keeps their CAST costume (PRJ/Content/Python/physis_conclave_cast.py:22-91; the builders' docstrings in Tools/conclave_meshes/people.py:896-2210).
  - Each costume becomes one skinned mesh on `metahuman_base_skel`.
  - It gains what the Mannequin skin used to stand in for: sleeves (tops are sleeveless today, people.py:9-13 and README:154-155), plus legwear and footwear.
  - Rigid parts (hats, helmet, spectacles, pins, clip, ring, vambraces) are vertices weighted 100% to a single bone.
  - Skin under the clothes is masked out.
- **Height** comes from the body. CAST `scale` is never applied (look() does not read it, and person() spawns BP_NPC at actor scale 1). The one exception is a child, an adult body shown smaller: MH `look_scale` scales BP_NPC's Look (Tamsin 0.9; physis_conclave_scenario.py wear()).
- **Grooms.** Paths are `/MetaHumanCharacter/Optional/Grooms/Bindings/{Hair,Eyebrows,Beards,Mustaches,Peachfuzz}/WI_*`. Everyone gets `WI_Peachfuzz_M_Thin` in their hair colour. Eyelash enum names are SHORT_FINE and so on (MetaHumanCharacterEyes.h:256-266).

**How to read the entries**
- **Body:** height, then masculine/feminine (MF, 0 masculine, 1 feminine), fat and muscle, each 0-1 of its range.
- **Skin:** U (lightness) and V (redness); face texture variant with its wrinkle/stubble/marks tags (W/S/M) and native tone v; body texture index (bti).
- **Eyes:** iris (U warmth, V brightness).
- Sculpt deltas use the landmark indices above, in cm.

### Orsolya Fenn (rows Orsolya, OrsolyaThanks)
- **Who:** the gardener at the Wellspring, about 55. Sturdy, with strong forearms.
- **Body:** 164 cm. MF 0.92, fat 0.50, muscle 0.45.
- **Skin:** light and sun-weathered, U 0.20, V 0.78. Variant 14 (W1 S0 M2, v 0.21), bti 7. Cheek and nose redness 0.6. No freckles, so she doesn't echo Physis, who has U 0.22 with type-2 freckles (physis_character_tools.py:77-85).
- **Face:** Vivian 0.6 + Lani 0.4.
  - Lift the cheekbones (23/66 up 0.15, forward 0.1).
  - Fill the lower cheeks (2/29 out 0.2).
  - Widen the nostrils (45/67 out 0.15).
  - Round the chin (62 forward 0.1).
- **Hair:** `WI_Hair_S_LowPonytail` stands in for the plait at her nape and sits tight under the hat. Fair going grey: Melanin 0.22, Redness 0.05, Whiteness 0.25. Brows `WI_Eyebrows_M_Natural` in the same colour; lashes SHORT_FINE.
- **Eyes:** amber (0.80, 0.70).
- **Clothes:** CAST: long black skirt, white apron with a trowel in the pocket, light-blue scoop-neck blouse, white knitted shawl, straw hat (GOLD_STRAW) with a black ribbon. New: blouse sleeves rolled to the elbow, black ankle boots.
- **Change from CAST:** the plait becomes fair instead of black. The author should confirm.

### Kairos (rows Kairos, KairosSpire, KairosDone)
- **Who:** keeper of the Archive, about 68. Lean.
- **Body:** 181 cm. MF 0.08, fat 0.28, muscle 0.30.
- **Skin:** cool olive, U 0.52, V 0.32. Variant 109 (W2 S0 M1, v 0.49), bti 8, roughness 1.10.
- **Face:** Walter 0.6 + Lorenzo 0.4.
  - Higher forehead (7 up 0.2).
  - Longer, straight nose (6 forward 0.1, 64 down 0.1).
  - Deeper-set eyes (19/33 and 18/22 back 0.1).
  - Hollow temples (41/58 in 0.1).
  - A dry half-smile (48/32 up 0.08).
- **Hair:** `WI_Hair_M_BobSlick`, combed back to the collar, white (Whiteness 1.0). Beard `WI_Beard_L_Full` + `WI_Mustache_L_Full`, white. Brows `WI_Eyebrows_M_Unruly`, white. Lashes SHORT_SPARSE.
- **Eyes:** grey-blue (0.18, 0.55).
- **Clothes:** CAST: long black coat with gold buttons, white pocket square, gold watch chain. New: full black sleeves with gold cuff buttons, white collar and cuffs, black trousers and shoes.

### Petra Lune (rows Petra, PetraThanks)
- **Who:** archivist, about 34. Slim.
- **Body:** 170 cm. MF 0.95, fat 0.30, muscle 0.25.
- **Skin:** golden tan, U 0.48, V 0.58. Variant 78 (W0 S0 M0, v 0.48), bti 3.
- **Face:** Jelena 0.5 + Sunita 0.5.
  - Narrower jaw (1/28 in 0.2).
  - Smaller mouth (48/32 in 0.1).
  - Level brows (25/78 down 0.1).
  - Eyes slightly wider apart (19/33 out 0.08).
- **Hair:** `WI_Hair_S_Updo` for the low bun, neutral black (Melanin 1, Redness 0). Brows `WI_Eyebrows_M_Fine`; lashes LONG_SLIGHT_CURL. Gold wire spectacles with light-blue lenses on the head bone (people.py:1919-1921).
- **Eyes:** grey-green (0.28, 0.62).
- **Clothes:** CAST: red A-line skirt, black satchel, ivory blouse with a black-ribbon collar. New: long ivory sleeves with buttoned cuffs, black ankle boots.

### Tamsin (rows Tamsin, TamsinThanks) — an adult body scaled down (author, 2026-11-09)
- **Who:** a child, designed as about ten. MetaHuman has no child body. Height is 135-220 cm in the body model itself (the Height contour of MHC/Content/Body/IdentityTemplate/body_model.dna; the toolset's clamp, ENG/Plugins/Experimental/Toolsets/MetaHumanGenerator/Content/Python/metahuman_toolset/metahuman.py:126, repeats it) [V, S13]. So she is built as an adult body at 135 cm and shown smaller in the level.
- **Body:** 135 cm. MF 0.55, fat 0.32, muscle 0.18. Chest, bust span and hip at their minimum (75, 14 and 76 cm). Underbust 0.1 (72 cm) for a flat chest, waist 0.07 (62 cm) for a straight torso [I]. Across Shoulder 0.2 (28 cm) and Hand Circumference 0.12 (14.5 cm). Neck Length 0.29 (8 cm, the most at 135 cm): at the body model's default her shoulders rose to within 2 cm of her adult-size chin, and costumes.measure() refused the guide, finding no neck [V, 2026-11-09].
- **In the level:** `look_scale` 0.9 on BP_NPC's Look: 135 x 0.9 = 121.5 cm to the crown, about 123 cm with hair, eyes about 112 cm up. The head is about 22-23 cm at 135 cm (the built women measure 21.0-22.4 cm, the men 24.1-24.9 cm), so about 20 cm in the level. A uniform scale keeps proportions: about six heads tall at any scale, a child's proportion [I]. The guides, the costume and the studio portraits stay at 135 cm. 0.95 (128 cm) is the alternative if she reads too young.
- **Skin:** U 0.42, V 0.60. Variant 103 (W0 S0 M0, v 0.42), bti 1. Freckles type 1, density 0.35.
- **Face:** Mikel 0.6 + Vivian 0.4.
  - Shorter nose (64 back 0.25 and up 0.15; 6 back 0.15).
  - Shorter lower face (62 up 0.25 and back 0.2; 4, 5 and 50 up 0.15).
  - Rounder cheeks (23/66 out 0.2, forward 0.15).
  - Bigger eyes (20/44 up 0.12, 37/53 down 0.08).
  - Fuller forehead (7 forward 0.15).
  - HeadScale 1 (MH head_scale), not 1.05: Python cannot set it (section 0, item 6), and the 135 cm body already carries an adult-size head.
- **Hair:** `WI_Hair_S_Messy`, chestnut (Melanin 0.62, Redness 0.4: natural colours, author 2026-11-09), with a red clip on the right. Brows M_Fine; lashes SHORT_FINE.
- **Eyes:** green (0.36, 0.55), as MH builds them.
- **Clothes:** CAST: light-blue tunic, white collar, belt and gold buttons, kite spool in the pocket. New: short sleeves, white knee socks, black lace-up shoes. Built 2026-11-09 with strap shoes first: their low vamp left the toes bare, the toes came through the socks and the socks through the shoes, so the shoes are closed lace-ups and the socks sit 1.5 mm off the foot inside them, 4 mm off the leg, ending 5 cm under the knee joint (costumes.py SOCK_TOP, SOCK_LIFT) [V].
- **Fit (author, 2026-11-10: "her clothes are oversized"):** the pieces are drawn in metres for grown-ups, so on her 135 cm body their ease, folds, collar, belt and buttons hung off her. costumes.costume() now builds a child's costume (age under 18) on her guide grown to the Mannequins' 1.80 m (Guide.scaled) and shrinks it back, so all of it scales with her; adults are unchanged. Her tunic is also cut closer: the skirt falls nearly straight (hem .214 instead of the A-line's .238, folds .011 deep), the bodice's ease is about half, and the Peter Pan collar is .046/.032 wide. Measured on her guide: skirt 39 cm wide (was 46.5), bodice 31.5 (was 36), 1.6 cm off the body (was 2.2) [V]. The bodice still squares off at her shoulders, which rise close to her chin.

### Old Wen (rows Wen, WenDone)
- **Who:** an elder, about 82. Small and frail.
- **Body:** 152 cm. MF 0.95, fat 0.40, muscle 0.12.
- **Skin:** U 0.28, V 0.30. Variant 90 (W2 S0 M2, v 0.28), bti 8, roughness 1.12.
- **Face:** Sook-ja 0.7 + Grace 0.3.
  - Slightly hooded eyes (20/44 down 0.05).
  - Thin lips (5 down 0.05, 4 up 0.05).
  - Mouth corners up 0.05.
- **Hair:** `WI_Hair_S_Updo`, white, with two crossed gold pins. Brows `WI_Eyebrows_S_FlatThin`, white. Lashes SHORT_SPARSE.
- **Eyes:** pale grey (0.22, 0.45), saturation 0.6, with a grey limbal ring at 0.6 as an age ring.
- **Clothes:** CAST: white wrapped robe, black sash, black stole with gold fringe. New: long wide sleeves, black slippers.

### Marek Duran (row Marek)
- **Who:** foundry worker, about 45. Heavy-shouldered.
- **Body:** 178 cm. MF 0.05, fat 0.45, muscle 0.72.
- **Skin:** golden tan, U 0.62, V 0.66. Variant 6 (W1 S3 M1, v 0.49), the nearest heavy-stubble variant. bti 6.
- **Face:** Orlando 0.5 + Victor 0.5.
  - Heavier jaw (1/28 out 0.25).
  - An old broken nose (6 sideways 0.15, 64 sideways 0.1). The Python path allows asymmetric moves.
  - Heavier brow (59 forward 0.1).
- **Hair:** `WI_Hair_S_BuzzCut`, black, plus `WI_Beard_S_Stubble` and `WI_Mustache_S_Stubble`. Brows M_FlatThick; lashes SHORT_SPARSE.
- **Eyes:** green (0.32, 0.55).
- **Clothes:** CAST: light-blue chambray shirt, black canvas apron with gold rivets and red ties, red flat cap. New: sleeves rolled to the elbow, black trousers and boots.

### Sefa Moreno (row Sefa)
- **Who:** fruit seller, about 41. Full-figured.
- **Body:** 161 cm. MF 0.92, fat 0.62, muscle 0.35.
- **Skin:** U 0.70, V 0.74. Variant 141 (W1 S0 M1, v 0.74), bti 3.
- **Face:** Zuri 0.6 + Sunita 0.4.
  - High round cheeks (23/66 forward 0.15, up 0.1).
  - Wider mouth (48/32 out 0.12).
  - Fuller lips (5 and 4 forward 0.05).
- **Hair:** `WI_Hair_S_PulledBack`, black, with the hairline showing under the scarf. Brows M_Thick; lashes LONG_CURL.
- **Eyes:** amber (0.78, 0.68).
- **Clothes:** CAST: tiered gold skirt, red sash, white blouse with a red, gold and light-blue border, gold coins and hoops, red headscarf. New: three-quarter sleeves, red sandals.

### Teodor Vass (rows Teodor, TeodorDone)
- **Who:** guard at the north gate, about 33. Powerful build.
- **Body:** 187 cm. MF 0.03, fat 0.28, muscle 0.78.
- **Skin:** very dark and cool, U 0.93, V 0.16. Variant 146 (W0 S1 M1, v 0.91), bti 5.
- **Face:** Omari 0.6 + Victor 0.4.
  - Square jaw (1/28 out 0.2, 62 forward 0.1).
  - Level brows (25/78 down 0.08).
- **Hair:** `WI_Hair_S_CoilBuzzCut`, black, sized to fit the helmet, plus `WI_Beard_S_Stubble`. Brows M_Dense; lashes SHORT_FINE.
- **Eyes:** amber (0.76, 0.66).
- **Clothes:** CAST: black gambeson, white breastplate and backplate with gold edges, red sash, duty belt, crested white helmet. New: quilted sleeves with white vambraces (rigid), black trousers, knee boots.

### Doctor Ama Okafor (row Ama)
- **Who:** the doctor, about 47. Trim.
- **Body:** 171 cm. MF 0.90, fat 0.35, muscle 0.38.
- **Skin:** dark and neutral, U 0.86, V 0.46. Variant 73 (W1 S0 M0, v 0.86), bti 5.
- **Face:** Asha 0.5 + Celeste 0.5.
  - Defined cheekbones (23/66 out and up 0.1).
  - Tired, slightly hooded eyes (20/44 down 0.05).
- **Hair:** `WI_Hair_M_BobBangs`, black with Whiteness 0.08, and a thin gold band across the crown. Brows M_SlightArch; lashes LONG_SLIGHT_CURL.
- **Eyes:** green (0.35, 0.50).
- **Clothes:** CAST: white coat with two pens and a stethoscope. New: long sleeves, a light-blue top under the coat, black trousers and flat shoes.

### Dov Pell (row Dov)
- **Who:** fisher at the Reservoir, about 61. Thickset.
- **Body:** 176 cm. MF 0.08, fat 0.55, muscle 0.55.
- **Skin:** wind-burned, U 0.16, V 0.86. Variant 4 (W2 S2 M2, v 0.20), bti 7. Cheek redness 0.7, nose 0.65.
- **Face:** Bruce 0.6 + Walter 0.4.
  - A squint (37/53 up 0.05).
  - Broad nose (45/67 out 0.15).
  - Heavy brow (59 forward 0.1).
- **Hair:** `WI_Hair_S_Clean`, black going grey (Whiteness 0.3), plus `WI_Beard_S_Full` and `WI_Mustache_S_Full` in the same colour. Brows M_Messy.
- **Eyes:** pale blue (0.08, 0.90).
- **Clothes:** CAST: light-blue oilskin, black knit cap. New: oilskin sleeves with black cuffs, black trousers, black rubber boots (CN_Lacquer).

### Rhea Sato (row Rhea)
- **Who:** terrace farmer, about 26. Compact and strong.
- **Body:** 158 cm. MF 0.88, fat 0.30, muscle 0.55.
- **Skin:** U 0.36, V 0.50. Variant 119 (W0 S0 M1, v 0.36), bti 2. Freckles type 1, density 0.2.
- **Face:** Etta 0.5 + Tuya 0.5.
  - Rounder cheeks (2/29 out 0.1).
  - Determined chin (62 forward 0.1).
- **Hair:** `WI_Hair_S_PulledBack`, black, sized to fit under the neck curtain. Brows M_Natural; lashes SHORT_THIN.
- **Eyes:** amber (0.78, 0.70).
- **Clothes:** CAST: black skirt and blouse, gold apron with bib, white field hat with gold band and neck curtain. New: sleeves rolled to the forearm, black boots to mid-calf.

**Spread across the cast**
- **Skin lightness (U):** Dov 0.16, Orsolya 0.20, Wen 0.28, Rhea 0.36, Tamsin 0.42, Petra 0.48, Kairos 0.52, Marek 0.62, Sefa 0.70, Ama 0.86, Teodor 0.93.
- **Eyes:** 4 amber, 3 green, 2 grey, 2 light blue.
- **Hair:** 1 fair, 2 white, 2 greying black, the rest black.

## 2. The Listener (First One)

**Sources:** the lore row at physis_conclave_lore.py:199-202 and CAST at physis_conclave_cast.py:73-75. The roadmap describes First Ones as "native form" humans (GAME_ROADMAP.md:224), gives them their own designs (:677-679), and their home a look of "cool palettes … luminous edges" (:258).

**Concept:** a Serene listener. Human in every structure, but tall, narrow, long-necked, hairless and browless, with large pale eyes ringed in gold. The motif is "rings that listen": the gold ring behind the hood, gold limbal rings, a gold line around each eye, and gold nails.

- **Proportions:** 203 cm. MF 0.35, fat 0.15, muscle 0.30.
  - Neck Length at 85% of its range.
  - Across Shoulder 30%.
  - Upper and lower arm length 75%.
  - Hand Circumference 25%, Waist 25%, Inseam 70%.
  - The ranges are read at run time, as `slim_identity` does (physis_outfit_tools.py:943-953).
- **Face:** Jelena 0.55 + Asha 0.45, with the shape weights pushed 1.15 times further from the template [I, S3]. Sculpt, in cm of wanted change:
  - Larger, wider-set eyes: 20/44 up 0.15; 37/53 down 0.10; 19/33 out 0.10; 18/22 out 0.15 and up 0.05.
  - A bridge with no dip at the eyes: 59 forward 0.2; 6 forward 0.1; 64 down 0.15.
  - Narrow nostrils: 45/67 in 0.15.
  - High, flat cheekbones (23/66 out and up 0.15), hollowed below (2/29 in 0.15).
  - Small mouth with thin lips: 48/32 in 0.15; corners up 0.05 for a serene look.
  - Long, tapering chin: 62 down 0.2; 3/30 in 0.1; 1/28 in 0.2.
  - Small, flat ears: 38/54 in 0.2.
  - A longer skull under the hood: 60 up 0.5; 13 back 0.6.
- **Skin, natural but uncommon:** "ashen cool", U 0.45, V 0.03.
  - This is the least red tone at mid lightness. Every U/V pair lies inside the synthesis model's natural tone map (MetaHumanCharacterSkin.h:18-22).
  - Variant 112 (W0 S0 M0, v 0.46): unlined and unmarked. bti 1, roughness 0.95.
  - Lips at saturation 0.2; no flush on the cheeks.
  - Finger and toe nails tinted GOLD (1.0, 0.766, 0.336): intensity 0.7, metallic 0.5 (MetaHumanCharacterSkin.h:54-77).
  - Fallback tone: deep cool, U 0.95, V 0.05.
- **Eyes:**
  - Iris ice blue: primary (0.03, 0.97), secondary (0.08, 0.85).
  - Gold limbal ring, size 0.80.
  - Cornea Size 0.185, the maximum, for large irises.
  - Pupil dilation 0.88; sclera tint (0.95, 0.95, 0.97); vascularity 0.1.
- **Hair:** none. No hair, brow or beard grooms. Peachfuzz in white to catch rim light. Lashes LONG_SLIGHT_CURL in white (Melanin 0, Lightness 1) [S9].
- **Markings:** FullThinLiner eye makeup (CatEye as the alternative) in GOLD, metalness 1, roughness 0.25, opacity 0.95. Assembly bakes makeup (MetaHumanCharacterAssemblySettings.h:56-57). Whether the metallic finish survives the bake is unknown [U, S9].
- **Robe, hood and ring:** kept from CAST (people.py:1029-1030, 1752-1754, 2122-2124): white robe over a light-blue under-robe, gold orphrey, hem band and cord, deep hood with a gold edge, gold listening ring with light-blue lights (CN_Glow at 0.5 brightness, README:250-259).
  - New: long white bell sleeves lined in BLUE_PALE, ending at the wrist so the gold-nailed hands show.
  - New: the hood is lined in BLUE_PALE instead of shaded dark, so his face reads under the Spine's top light.
  - Floor length, so no shoes; the body mask hides everything under the robe.
- **How it reads:** at 30 m, the height, narrow robe and halo-like ring. At talk range, the browless smooth face, oversized pale irises in gold rings, ashen skin and long neck. It stays anatomically human because both face and body are MetaHuman models. The same rules can later define First One warriors.

## 3. Build plan

### 3.1 Integration: design (c)
BP_NPC keeps talking, tokens, facing and the talk icon. A new ChildActorComponent named **Look** holds the person's assembled Blueprint `/Game/Conclave/People/<Key>/BP_<Key>`, at relative yaw -90 like Body (physis_conclave_tools.py:2193) [I, S7].

Why this design:
- **Hiding works.** Hiding BP_NPC hides its child actor (ENG/Source/Runtime/Engine/Private/Actor.cpp:6352-6367; Components/SceneComponent.cpp:3498-3506) [V].
- **Swapping looks works.** Setting the class on a placed instance respawns the child (ChildActorComponent.cpp:597-615) [V].
- **Bounds need one change.** Bounds include the child only with `bIncludeFromChildActors` (Classes/GameFramework/Actor.h:1603-1611) [V].
- **Epic's own wiring is kept:** LODSync, groom bindings, the MetaHuman component.
- **Rebuilds are safe.** A rebuild resets Face, Body and grooms by name, deletes extra SkeletalMesh and ChaosCloth components, and keeps static ones (MHC/Source/MetaHumanDefaultEditorPipeline/Private/MetaHumanDefaultEditorPipelineLegacy.cpp:293-349) [V]. So the post-pass re-adds the costume after every rebuild.
- **No name clash** with BP_NPC's bool named `Face`.

Rejected:
- **(a) attached actors** do not hide with BP_NPC: overlapping people at shared spots, and Marek never leaves.
- **(b) copying the parts into BP_NPC** re-implements Epic's assembly wiring for every actor.

### 3.2 Quality settings
- **Pipeline:** OPTIMIZED + HIGH. The best face LOD is LOD1. MEDIUM's best is LOD3; 5.8 has a Medium card-hair bug (https://dev.epicgames.com/documentation/metahuman/metahuman-known-issues-5-8-in-unreal-engine). If the spike's VRAM figure is over budget, use MEDIUM for minor people. Never CINEMATIC; Epic says it "is silently treated as HIGH" on this pipeline (https://dev.epicgames.com/documentation/metahuman/metahuman-creator-python-scripting-in-unreal-engine).
- **Rig:** JOINTS_ONLY (`EMetaHumanRigType`, MetaHumanCharacterEditorSubsystem.h:131-133). HIGH strips face LOD0, which is the only LOD with blendshapes [I].
- **Cloud:** 2K texture sources, the default (MetaHumanCharacterSkin.h:275-297). Set `MetaHuman.Cloud.Autorig.UseDdc 1` so reruns reuse cached rigs (MetaHumanSDK/.../MetaHumanARServiceRequest.cpp:36-37, 200).
- **Post-pass, per person:**
  - Texture caps: 2048 for face LOD1; 1024 for other face LODs, eyes and covered body; 512 for teeth. MH_Physis came out with an 8K body basecolor (researcher 4).
  - Grooms: `bUseCards = true` (HairStrands/.../GroomComponent.h:275-277), out of ray tracing, no simulation. Use per-component settings, never global cvars, because Physis shares the hair cvars.
  - MetaHuman component: body correctives, neck correctives and the neck rig off.
  - People's meshes out of ray tracing by default [I]. Decide after S10.

### 3.3 Steps

#### Phase 0: offline, no editor and no Blender
1. **Back up first**, with the editor closed. .uasset files are untracked (.gitignore:63).
   - Copy these to `~/PhysisBackups/people-<date>/`: Content/MetaHumans, MH_Physis.uasset, BP_NPC.uasset, L_Conclave.umap (and its BuiltData), M_CNSurface.uasset.
   - Put all code changes on a git branch.
2. **Cast data**, in `physis_conclave_cast.py`:
   - Keep today's table as `CAST_MANNEQUIN`.
   - Change the 19 human rows to `{'mh': '<Key>', ...}`.
   - Add a pure-literal `MH` table: presets, landmarks, body, skin, eyes, makeup, grooms with their settings, costume pieces, quality, idle start and rate.
   - Add a switch to choose between the two looks.
   - **Same commit:** `people.py` `_cast_problems` (2723-2757) must accept the new rows. It asserts at import (2759-2760), and a failing import drops people.py, the figures included, from the Blender build (Tools/build_physis_conclave.py:33, 62-69).
3. **New `Tools/conclave/people_audit.py`.** Checks:
   - Every groom and preset file exists.
   - Face variants are unique and within 0-152.
   - U/V values and heights are in range.
   - Iris values are on the allowed list.
   - Costume colours pass `palette.allowed`.
4. **`sim_scenario.py`:**
   - Add Look to the BP_NPC template (149-153).
   - Add a ChildActorComponent stub with `set_child_actor_class` (446-448).
   - Update `check_people` (782-793) and `check_cast` (994-1015).
5. **Editor code** (written now, run later):
   - New `Content/Python/physis_conclave_people.py` with operations `people_new`, `people_preview`, `people_guides`, `people_rig`, `people_textures`, `people_assemble`, `people_import`, `people_post`, `people_verify` and `npc_look`. The tools module reloads and delegates to it, as it already does for the ground module (README:300-302).
   - `npc_blueprint` gains Look (physis_conclave_tools.py:2183-2206).
   - M_CNSurface's `master()` call (:894) gets `used_with_skeletal_mesh=True`, so costumes can use the Conclave materials.
   - Scenario: `look()` (649-681) and `wear()` (691-731) set the Look class and empty Body, Lower, Upper, Head and Shape for humans. Figures clear Look. Mannequin rows keep the old path.
   - `fitting()` (734-766) checks the Look class, that Body uses `/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel`, the idle, and that the costume follows Body.
   - BP_NPC BeginPlay: add `:bIncludeFromChildActors true` to `GetActorBounds` (conclave_logic.py:420) [S7].
6. **Costumes:**
   - New `Tools/conclave_meshes/costumes.py`: people.py's garment builders, driven by body measurements taken from each person's exported guides instead of the Mannequin tables (people.py:46-69). New builders for sleeves, trousers, footwear and socks. Hats sized on the groom's outer hair-volume mesh (its LOD5 "helmet" shell) [I].
   - New `Tools/build_conclave_people.py`, headless Blender, modelled on `Tools/build_physis_outfit.py`: transfer weights from the body (:153-170), weight rigid parts 100% to one bone, limit 4 influences (:442-443), export FBX, and bake the skin mask (:236-246).
   - `check.py` must pass on the costumes. **This is the largest work item.**

#### Phase 1: spike on the Listener (one character)
1. **Prepare the editor.** The author closes apps that hold VRAM.
   - Start a fresh GPU editor on `/Engine/Maps/Entry` with `-noraytracing -ExecCmds="r.Nanite 0,sg.ShadowQuality 1,sg.GlobalIlluminationQuality 1,sg.ReflectionQuality 1,r.MipMapLODBias 1,r.Streaming.PoolSize 700"`. This matches the 2026-10-30 session (ConnectionLaunch.log:548). Put the pool size last; `sg.TextureQuality 3` would reset it (BaseScalability.ini:774-782).
   - Keep `r.HairStrands.Enable` on (Tools/rebuild_physis.py:13-14).
   - Not `-nullrhi`: assembly fails there, and the editing steps are untested there.
2. **Build the identity:** `conclave:people_new:Listener` creates `/Game/Characters/Conclave/MHC_Listener` [S2, S3, S4, S13]. Save `Art/Characters/Conclave/Listener/face.json`.
3. **Preview:** `people_preview` renders studio portraits. **Author approves the look**, and sets HeadScale in the UI if wanted.
4. **Guides:** `people_guides` exports the body and face meshes. Same pattern as `export_body_guide` (physis_character_tools.py:155-181) and `export_face_guide` (physis_outfit_tools.py:799-809). Then quit the editor; Blender and Unreal never run together (README:553-554).
5. **Costume:** run the Blender costume build for the Listener, headless.
6. **Cloud.** Start a fresh editor with the same flags.
   - **The author signs in to Epic**: the first auto-rig call starts the sign-in flow (Epic Python page). A 403 means the MetaHuman EULA is not accepted.
   - Run `people_rig` (JOINTS_ONLY, blocking), then `people_textures` (2K) [S1].
7. **Assembly.** Start `Tools/watch_unreal_vram.sh` on the host.
   - Run `people_assemble`: OPTIMIZED/HIGH, build path `/Game/Conclave/People`, shared folder `/Game/MetaHumans/Common`. It follows the low-memory steps at physis_outfit_tools.py:1082-1101 [S5].
   - Then check the shared folder and Physis [S11].
8. **Import:** run `conclave:surface_skeletal` (sets used_with_skeletal_mesh on M_CNSurface alone; never `conclave:materials` while the unverified art-round ground module is in the tree), then `people_import` [S8].
9. **Post-pass:** `people_post` [S6].
   - Body plays `/Game/Characters/Physis/Animations/Physis_MM_Idle` in single-node mode, with its own start time and rate.
   - Body and Face tick their pose only when rendered.
   - Body, Face, grooms and costume tick while the game is paused.
   - The costume sits under Body and follows it.
   - Apply the groom and texture settings from 3.2.
   - Parent the body material to the masked version with this person's ClothMask.
10. **Wire up BP_NPC:**
    - Run `conclave:npc_look` (`conclave:blueprints` never remakes BP_NPC, :2215-2216).
    - Run `conclave_logic.py npc` and read the graphs back.
    - Run `conclave:scenario` in the GPU editor; its people report must be empty [S7].
11. **Check in a ray-traced editor**, with apps closed: captures at (-566, 104) and in the studio, the palette audit, the VRAM measurement, and a talk test in Play [S7, S9, S10].

**Gate A:** the author approves the look and the cost.

#### Phase 2: Teodor
Settles the remaining risks: a helmet over a hair groom, sleeves and boots against the idle's arm positions, black hair against the palette [S12], and two rows sharing one Blueprint.

#### Phase 3: the other 10
1. **One CPU session:** identity and preview for everyone. The author reviews a contact sheet, and decides Tamsin's approach and the iris policy.
2. **Guides and Blender costumes**, with the editor closed.
3. **One cloud session:** all rigs and textures, one sign-in.
4. **Assemblies:** 3-4 per fresh editor, because of the Linux RAM issue in Epic's 5.8 known issues page. Watchdog on every build.
5. **Finish:** import and post-pass, `conclave:scenario`, Fab placement, save the level (README:511-515). Then captures and audits, and update the README sections People, BP_NPC, run order and palette rule 2.

#### Phase 4: after sign-off
Retire the Mannequin path: SKINS (:803-807), `skins()` (:1141-1150), its entry in `check_palette` (:1600), and the SM_CP_G_* garment meshes.

### 3.4 Spike tests

| Test | What it checks | Status before the spike |
|---|---|---|
| S1 | Rig and textures finish from here; time each | [V] it worked about 2026-10-30; forum reports 300 s timeouts outside the US |
| S2 | Face variant 112 sticks after save and reload. The property's metadata says ClampMax 1 (MetaHumanCharacterSkin.h:36-37), but presets store values up to 141 | [U] |
| S3 | Blending two presets plus the 1.15× push commits without artefacts. Epic documents interpolating two characters | [I] |
| S4 | How much of a landmark request the face model applies, on a non-Physis face | [I] |
| S5 | Assembly time, peak VRAM, Vulkan allocation failures (a good Physis build logged about 3,200: watch_unreal_vram.sh:9-11), RAM | [U] |
| S6 | Python can set the post-pass properties on the Blueprint; the idle plays on a 203 cm body without arm clipping | [U] |
| S7 | Look yaw, hide/show by token, facing, talk-icon height and reach, head follows the body during a paused talk | [I] |
| S8 | Costume keeps vertex colours; M_CNSurface works on a skinned mesh; no visible texture swim; the mask hides the skin (and the body material shares Physis's master) | [I]/[U] |
| S9 | Render audit with `palette.family` on irises, lashes, robe and the baked gold liner | [U] |
| S10 | VRAM added by one person and by three copies of the same person | [U] |
| S11 | `/Game/MetaHumans/Common` unchanged against the backup; BP_Physis still compiles and renders | [U] |
| S12 | (Teodor) black hair passes the palette; helmet over the groom | [U] |
| S13 | Body constraint minimums and maximums, especially Height for Tamsin. Height is 135-220 cm in body_model.dna and shape_body clamps to it; the solver does not clamp a lower target but extrapolates it, so below 135 is untested and Tamsin is built at 135 | [V] range, [U] below 135 |

### 3.5 How to verify
- **Offline:** `check.py` on the costumes, `people_audit.py`, `sim_scenario.py`.
- **Editor reports:** `people_verify` checks the skeleton, idle, tick settings, card hair, ray-tracing flags, texture sizes, costume following Body, and the mask parent. The scenario's people list must be empty.
- **Screenshots:** studio portraits (front, three-quarter, profile) at the preview and after assembly; in-level ray-traced shots at each person's spot.
- **Palette audit:** pixel checks on captures that show only one component at a time, with skin masked out.
- **VRAM:** `rhi.DumpResourceMemory`, `stat RHI`, `r.SkinCache.PrintMemorySummary`. Target: 0.5 GB or less for all people.
- **Play:** talk to the Listener and to one Kairos row.

### 3.6 Rollback
- **Looks:** flip the cast switch back to `CAST_MANNEQUIN` and re-run `conclave:scenario`. The Mannequin assets and code path stay until Phase 4.
- **Code:** git revert.
- **Content:** delete `/Game/Conclave/People` and `/Game/Characters/Conclave`. An empty Look behaves like today's BP_NPC.
- **Assets:** restore the Phase 0 backup with the editor closed.

## 4. Risks and costs

**VRAM**
- With ray tracing on, the Conclave alone filled 4.58-4.76 GB before running out. With `-noraytracing` it ran out at 2.97 GB when other apps held more (researcher 4's crash logs; nvidia-smi showed 2,744 MiB used with no editor).
- Estimate for the people [I]: about 0.4-0.7 GB lean, 1.1 GB at worst. Default HIGH output without caps would be about 320 MiB of textures per person.
- Assembly runs at the out-of-memory edge (watch_unreal_vram.sh:9-11).
- Hidden duplicate rows keep their hair buffers. A lever if needed: clear Look while a row is hidden.
- Ray-tracing editor sessions will crash more often. Use them only for shots, with apps closed (MEM/conclave-aaa-push.md:14, 24).

**RAM:** Epic says assembly can exceed 32 GB, and this machine has 31.5 GB. Repeated assemblies on Linux can exhaust RAM, so keep swap on (15.4 GB configured) and restart every 3-4 builds. An out-of-memory kill can leave the NVIDIA driver unusable until a reboot (MEM/unreal-mcp-access.md:19).

**Time** [I]:
- About 20 minutes of machine time per person: identity 5, cloud 4-6 (150-200 s per rig per the forum), assembly under 2 (watch_unreal_vram.sh:11), Blender about 5, import and post 3. Roughly 4 hours over about 6 editor launches.
- Writing the costume port is the long pole: 1-2 working sessions.
- Keep runs short and in sequence (MEM/physis-art-integration.md:17).

**Disk:**
- MH_Physis.uasset is 142 MB. Its assembled folder is 164 MB, of which Hair_M_Layered is 63 MB. Common is 171 MB (du).
- Twelve people: about 3.5-5 GB in Content [I], plus backups. 452 GB free.
- Packaged size growth is unknown, for both Linux and Windows.

**Cloud and author involvement**
- Sign-in through Epic's EOS system and the MetaHuman EULA are needed.
- Regional timeouts are possible. A US VPN or Cloudflare WARP is the author's call.
- The plugin is Beta (MetaHumanCharacter.uplugin:14), so 5.9 may break the scripts.

**Risks to the other levels**
- The shared `/Game/MetaHumans/Common` is used by Physis in every level. Back it up before the first build [S11].
- The M_CNSurface recompile and its extra shader permutations affect the Conclave only.
- Avoid global hair, ray-tracing and virtual-texture-pool settings; they would change Physis and the other levels.
- `Physis_MM_Idle` becomes a dependency. Never re-retarget over it (MEM/physis-author-direction.md:15).
- Other sessions that open L_Conclave will pay the extra VRAM and load time.
- Cook time and package size grow on both platforms.

**Look risks**
- Tamsin may read as a small adult, or turn uncanny.
- Hats over hair grooms may clip.
- The Mannequin idle's arms may clip on heavy bodies and bulky clothes.
- Hair and irises may fail the palette.
- Faces stay still: no blinks and no lip sync. A rig with blendshapes and face animation is a later step.

**Questions for the author**
1. Close VRAM-holding apps before each GPU session.
2. Epic sign-in at Phase 1 step 6.
3. Approve the Listener at Phase 1 step 3.
4. Tamsin: answered 2026-11-09, scale an adult down: built at 135 cm, Look at 0.9 (about 122 cm). Open: 0.9 or 0.95 after the in-level shots.
5. Irises: keep them in the palette as designed, or allow natural brown.
6. Orsolya's fair plait (CAST had black).
7. The Listener's light-blue hood lining.
8. If the spike's VRAM figure is over budget: accept it, or use MEDIUM for minor people.