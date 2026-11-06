# Character review

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

The critique after `inspect_character.py` passes, following the [review method](../../game-assets/references/review.md#method). Go region by region through the `CHARACTER` sheet and then the wireframe, matcap and pose sheets. Look for each defect below by name: they are the ones generated characters show most. Write each finding as tile, defect, cause, fix.

## Whole figure

Tiles: front, back, left, right, both 3/4 views.

- **Proportions on the grid** (`GRID` = the style's head count): the head fills one division. For realistic adults, measured averages put the crotch at about 0.48 of the height (0.46–0.51), the shoulders at 0.82, shoulder width at about 0.29 of the height for men and 0.28 for women, hand length at 0.11 and foot length at 0.15; the arm span about equals the height. Stylized characters change these on purpose and consistently, not at random.
- **Torso:** narrower at the waist than at the chest and, for women, the hips. Front-view waist-to-hip width is about 0.94 for men and 0.85 for women. No bloated waist or belly, no sunken chest, unless the design asks for them.
- **Silhouette:** reads from the front and from the side; arms and legs clearly apart from the body; no lumps the design doesn't name.
- **Symmetry:** both sides mirror, except the parts the design makes asymmetric.
- **Stance:** upright, weight centered, both feet flat on the floor line, nothing floating above it or sunk into it.

## Head and face

Tiles: face, face_left.

- Eyes level, the same size, centered in the sockets, neither sunk nor bulging; the lids meet the eyeball.
- Nose, mouth and chin on the center line; ears between the brow and the base of the nose; a clean jaw line.
- Neck joins the head and shoulders without a step or a pinch.
- **Hair** sits on the scalp: no gap above it, never cutting into the forehead, ears or neck. A natural hairline. No scalp showing through unless designed, and no hair inside the face or neck.

## From above, and from the game

Tiles: top, head_top, game, game_on_screen. The player sees these, and most of them rarely appear in a modeling tool's default views.

- **Hats and hair:** nothing of the head or hair comes through the crown. No gap under the brim that shows the scalp.
- **Shoulders, top of the head, bags:** they fill most of a high camera's view: are they designed, or just left over?
- **At on-screen size:** can you tell who it is, and which way they face? Which details vanished? Remove them; enlarge what must read.
- **Each variant,** not only the first one.

## Arms and hands

Tiles: front, left_hand_top, right_hand_top, left_hand_bottom.

- **The right hand on each arm:** in the rest pose, with palms down, both thumbs point forward. A thumb pointing back means the hand is mirrored: a right hand on the left arm. Its bones are mirrored too, and animations bend it the wrong way.
- **Fingers:** the design's count, in order from the thumb: index, middle, ring, little. Each one separate, straight or gently curved; the middle finger longest; knuckles lined up across the hand. No crooked, crossed, fused or bent-back fingers, no webbing.
- Palm flat, nails on the back of the hand, wrist straight and not twisted.
- Arms: elbows point backward; upper and lower arm in proportion; the hands reach about mid-thigh when the arms hang.

## Legs and feet

Tiles: front, left, right, feet_front.

- A visible gap between the legs from the feet up to the crotch; thighs that don't merge.
- Knees and toes point forward, or slightly out.
- Feet flat on the floor line: heels down, toes not under the floor, ankles not twisted. Shoes have soles of believable thickness.

## Bodies built from parts

Sheet with `COLOR="OBJECT"`.

- Parts meet where a joint is, with the seam where the design wants it. No step or gap the design doesn't name.
- A part's end shows nowhere it shouldn't: an arm's root doesn't come out of the back, a thigh's top doesn't stand out of the hip.
- In the pose sheet, every joint stays closed: no opening at the shoulder with the arms up, no hip gap in the squat.

## Clothes and layers

Every sheet, posed ones included.

- No skin showing through clothes anywhere.
- No gap between clothes and body at collars, cuffs and hems; on a smooth body, clothes 2–5 mm off it, never floating. On a body of parts, a cuff or a hem may bite into the limb that comes out of it.
- Folds where fabric bends, not painted noise. Belts, straps and pouches sit on the surface.
- One layer: no body left under clothes unless outfits swap.

## Surface

Sheet with `LIGHT="MATCAP"` and `COLOR="SINGLE"`.

- No dents, bumps, creases, spikes or random noise; smooth shading across the body; no faceting on curved areas.
- No dark streaks from flipped or broken normals.

## Topology

Sheet with `WIREFRAME=True`.

- Even quads that follow the forms.
- At least three edge loops at elbows, knees, shoulders, hips and finger joints; loops around the eyes and mouth if the face animates.
- Density on the silhouette, the face and the hands, not on flat areas; no long thin triangles; no needless faces under the budget's cap.

## Deformation

Sheet of the test poses, through `FRAMES`.

- Elbows and knees keep their volume: no collapse, no candy-wrapper twist.
- Shoulders don't tear or cave with the arms up, and the armpits stay clean.
- The hips and crotch hold their shape in the squat and the stride.
- Fingers curl into a clean fist without cutting into each other.
- Clothes and hair follow the body in every pose.

## Textures and materials

- No seams on the face or the front of the body; no stretching.
- No lighting, shadows or noise in the skin and cloth colors.
- Materials as the brief allows: as few as possible.
