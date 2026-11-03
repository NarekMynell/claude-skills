# Character sources

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require. Licenses, versions and downloads change often: check each on its source's page before relying on it, and record what you found. Facts below were checked in November 2026.

## Licenses

- **CC0**: use, change and ship freely, no credit needed.
- **CC-BY**: allowed with credit to the author, in `docs/third-party-assets.md` and the game's credits.
- **Avoid** in a commercial game: NC (non-commercial), ND (no derivatives), share-alike or GPL for the assets themselves, an unclear "free" label, and anything ripped from a game.
- **Record every asset** in `docs/third-party-assets.md`: name, source URL, author, license and its version, date obtained, what was changed.
- Downloads that need an account, a payment or a browser login are the user's to do: Claude never logs in, accepts terms or pays for the user. Downloads and installs change the user's machine: ask first.

## MPFB: realistic humans

MPFB, MakeHuman for Blender, makes human bodies from sliders (gender, age, weight, muscle, proportions), with eyes, eyebrows, hair, clothes, proxies and rigs.

- **Version:** 2.0.18 (2026-10-10) is the latest, an approved extension on extensions.blender.org for Blender 4.2 and newer; 2.0.14 fixed Blender 5.1 problems and 2.0.18 the hair editor on 5.2. Open on 5.2: normal-map baking fails (issue #453).
- **Install** (ask the user first): Blender's Get Extensions panel, or `blender --command extension install -s -e mpfb` (`-s` syncs the repository list, `-e` enables it). Blender may need online access allowed in its preferences.
- **Assets:** MPFB needs the system assets pack: [makehuman_system_assets_cc0.zip](https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip), 267 MB, CC0. Load packs with `bpy.ops.mpfb.load_pack(filepath=...)`. Most other packs on the [asset packs page](https://static.makehumancommunity.org/assets/assetpacks/index.html) are CC0 and some are CC-BY: check each.
- **License:** the code is GPL, the assets CC0, and characters made with them can go into closed-source games ([FAQ](https://static.makehumancommunity.org/mpfb/faq/use_in_closed_source.html)).
- **Rig: `game_engine`.** 53 bones with Unreal-mannequin names (`pelvis`, `spine_01`, `thigh_l`) and three-bone fingers; MPFB documents it as fully compatible with Unity's Mecanim. It has no eye or jaw bones. `mixamo_unity` (64 bones) adds face and breast bones.
- **Topology:** the full body is about 13,400 quads (about 27,000 triangles). Proxies give lower-poly topologies of the same body: `proxy741` about 1,500 triangles, `male1591` and `female1605` about 3,200. Choose the one that fits the budget instead of decimating.
- **Clothes** hide the body under them with delete groups, a vertex group and a Mask modifier; the faces go only when the masks are baked: `ExportService.bake_modifiers_remove_helpers(basemesh, bake_masks=True, remove_helpers=True, also_proxy=True)`.
- **Scripting,** run with Blender 5.2.1 and MPFB 2.0.17 (2026-11-03). Each service is documented in the [MPFB docs](https://github.com/makehumancommunity/mpfb2/blob/master/docs/index.md), with examples in `script_samples/`. The module is `bl_ext.<repository>.mpfb`: `blender_org` from the official repository, `user_default` when installed from a file; find it by the `.mpfb` suffix in `sys.modules`. The order matters:
  1. `HumanService.create_human(macro_detail_dict=...)`: a 1.675 m human by default, feet on the ground, facing −Y, in an A-pose with the arms about 48° below horizontal and the palms facing back.
  2. `HumanService.add_builtin_rig(basemesh, "game_engine")`, before any proxy or clothes, or they get no rig.
  3. `HumanService.add_mhclo_asset(path, basemesh, asset_type="Proxymeshes", subdiv_levels=0, material_type="GAMEENGINE")` with a `.proxy` file, for a lower-poly body.
  4. The same call with `asset_type="Clothes"` or `"Hair"` and an `.mhclo` file per garment, shoes and hair.
  5. `ExportService.bake_modifiers_remove_helpers(basemesh, bake_masks=True, remove_helpers=True, also_proxy=True)`: deletes the faces the clothes cover.
  6. Export the proxy, clothes and hair; leave out the basemesh, which stays as MPFB's own reference.

  Asset paths sit under `LocationService.get_user_data()`: `proxymeshes/male1591/male1591.proxy`, `clothes/<name>/<name>.mhclo`, `hair/<name>/<name>.mhclo`. `bpy.ops.mpfb.load_pack(filepath=...)` installs a pack zip.
- **What the checks found on that result**, MPFB's defaults unchanged, and what to do about each:
  - the proxy body pokes through the clothes and the hair (about 100 face pairs each), because the clothes fit the high-poly basemesh: delete the proxy faces the clothes cover, with a ring under the edges, or move the clothes out, then check again;
  - shoes sit inside the trouser legs and the hair cards within 2 mm of the scalp: delete what's covered, and list hair cards in `SEE_THROUGH`;
  - clothes weights had more than 4 influences: limit to 4 and normalize;
  - the clothes stretch in the extreme test poses: look at the pose sheet and fix the weights where it shows. Transfer weights only from a complete body: from a body whose covered faces were already deleted, the transfer made the stretching three times worse;
  - one garment can outweigh the body: the casual suit is 8,336 faces against the proxy's 1,030, so choose clothes by the triangle budget too.
- **Known export issues** from MPFB's documentation: only the GameEngine material survives FBX export; textures can go missing in FBX, so copy them next to the file or set them up in Unity; shape keys disappear when modifiers are applied on export.
- MakeHuman's forum went offline on 2026-10-21; the static site, the asset packs and GitHub remain.

## Quaternius: stylized humans and animation

- **Universal Base Characters** (2025): the free Standard version has 2 base bodies and 5 hairstyles, in OBJ, FBX and glTF; about 14,000–15,000 triangles; 65 joints with Unreal-style names (`pelvis`, `spine_01`, `upperarm_l`). The paid Source version adds more bodies and hairstyles, rigged `.blend` files and engine projects.
- **Universal Animation Library 1 and 2:** 45 and 42 free animations, more in the paid tiers. Version 2.0 renamed the bones to match the base characters; since 2026-06-16 there are root-motion and in-place versions.
- **Modular Character Outfits – Fantasy:** outfits made to fit the base characters' head, with no body under the clothes.
- **License:** the pack pages say CC0, but [quaternius.com/license.html](https://quaternius.com/license.html) has had QAL v1.0 since 2026-08-28: commercial use without credit, but the assets themselves can't be redistributed, which includes a public repository holding them. The license in force when an asset was obtained applies.
- **Download:** itch.io's pay-what-you-want page needs a browser, so the user downloads.
- Unity Humanoid compatibility isn't documented: check the mapping in Configure Avatar.

## Kenney

CC0, stated in the `License.txt` of each pack.

- **Animated Characters 1–3:** Mixamo-style bone names (`Hips`, `LeftUpLeg`) plus control bones; check the Humanoid mapping.
- **Mini Characters:** a 7-joint skeleton, so Generic only: Humanoid needs at least 15 bones.
- **Blocky Characters:** no skinning; the parts are animated directly.

## Mixamo: auto-rigging

- Free with an Adobe ID, royalty-free in games, but the files can't be redistributed on their own. There's no public API: it runs in the user's browser, logged in. Logins have broken for days at a time.
- The auto-rigger takes a character in T-pose with limbs and fingers apart. The user places markers on the chin, wrists, elbows, knees and groin, and picks a skeleton with three-joint fingers when the character holds things. Bones are named `mixamorig:...`, which Unity maps automatically. Bipeds only.
- Its animations: [animation guide](../../animation/SKILL.md#2-sources).

## Other tools

- **AccuRIG 2.0** (Reallusion): a free auto-rigger with a Unity export preset, but Windows only, and exporting needs a free ActorCore account.
- **Auto-Rig Pro:** a paid Blender add-on that supports Blender up to 5.2, with Humanoid game-engine export. Use it when the user owns it; this guide can't assume it.
- **Rigify:** bundled with Blender, but its deform bones hang under non-deforming `ORG` bones, so the FBX exporter writes those too. Don't export a Rigify rig to Unity without re-parenting the deform bones.
- **Ready Player Me** shut down on 2026-01-31.
- **Poly Pizza, OpenGameArt, Sketchfab, Fab:** the license is per model, under the terms at download time: check each one, credit CC-BY, and record it.

## AI 3D generators

| Tool | Topology | Rigging | License |
|---|---|---|---|
| Meshy | Remesh to quads or triangles, 100–300k faces | Standard bipeds only | Free plan CC BY 4.0; paid plans own their assets; API on paid plans |
| Tripo | Quads up to 25k faces (vendor's claim) | | Free-plan terms contradict each other |
| Rodin Gen-2 | Quad presets of 4k–50k faces; T/A-pose option | | Free-plan rights unstated |
| Hunyuan3D 2.1 | Open weights | | Excludes the EU, the UK and South Korea, outputs included |
| TRELLIS.2 | | | MIT; Linux with an NVIDIA GPU of 24 GB or more |

Typical defects: irregular triangle soup, melted accessories, blurry details, scattered UVs, lighting baked into the color texture, holes and floating parts, poor deformation at the shoulders and mouth. Use a generated character only when the user chooses it: retopologize it, re-unwrap it, remove the lighting from its textures, rig it, and run every check on it like any other base.
