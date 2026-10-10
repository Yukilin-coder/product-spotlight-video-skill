---
name: product-spotlight-video
description: Create a product spotlight short video from uploaded product photos, with products lighting up individually, synchronized captions and switch sounds, then a final all-on reveal. Use for static product light-switch ads, with an optional creative-video reference.
---

# Product Spotlight Video

Turn product photos into a finished MP4: dark scene → individual spotlight reveals → dark pauses → all products illuminated. A photo is the only required user input. Prepare the scene and configuration yourself; do not ask the user to draw masks, install fonts manually, or write JSON.

## Choose the scene

Inspect every supplied product image before generating or editing anything. Identify the actual products and preserve distinctive vessel shapes, toppings, packaging and visible brand marks.

Real packaging usually includes printed labels. Preserve legible source text, label placement and print curvature when recomposing; do not turn labeled products into blank mockups. Inspect for garbled text after generation. If exact packaging cannot be retained, use the original photo layout. Add fictional packaging names only for an explicitly fictional demonstration, never as a substitute for a user's real brand.

For a group photo, use its products. For a single product, create three instances of that same product by default, without inventing new variants. Default to three products on a dark teal backdrop, a low frontal view, a subtle warm tabletop, room above each product for small labels, and a landscape 1480×1020 canvas. Preserve a requested composition or aspect ratio instead of imposing the default. For one, two or more than three products, customize the event schedule.

Use the host's image-generation/editing tool to create ONE all-on scene from the supplied photo. Read [references/scene-prompts.md](references/scene-prompts.md) for the prompt and identity constraints. Save the generated scene in the working directory. If an AI image tool is unavailable, use the original group photo and adapt masks to its existing layout; disclose that this preserves the photo composition. A single-product photo can produce a single-product reveal with custom events. Do not claim a new AI composition was generated if it was not.

Do not independently generate dark and light versions: separate generations can move labels, change glass shapes or alter the product. The renderer derives the dark frame from the same all-on scene and switches masked areas, locking the geometry throughout the video. Generative re-composition can still change product details; inspect and disclose material changes.

## Optional reference

If a tutorial or screen recording is provided, inspect a contact sheet and isolate the embedded creative clip. Exclude the presenter, tutorial titles, app UI and screen-recording borders from the output. Match the creative clip's cadence, composition and typography as closely as the source permits. Inspect frames around each switch to recover frame-level times. Do not assume the whole recording is the creative clip.

Use the supplied reference's audio only when requested. Set `audio` to that video and `audio_start` to the creative segment start. Otherwise the renderer synthesizes original switch sounds, so the photo-only workflow needs no music file. Do not publish a third party's reference audio with this skill.

## Prepare masks and captions

Inspect the final all-on scene. Define normalized product polygons, including glass stems, handles and garnishes; use boxes only when they do not include adjacent products. Keep feathering small to avoid halos and light leaking into nearby objects. Position labels in the negative space above their products.

Use known product names or neutral captions such as `01 / ORIGINAL`, `02 / ORIGINAL`, `03 / ORIGINAL`. Omit ingredient lines unless the user supplied them. Visible packaging does not justify guessing ingredients or performance claims. Match reference text verbatim only when requested, and identify labels that are decorative rather than verified product facts.

Use a condensed bold font for yellow-green headings and a smaller regular font for secondary lines. Use an available font path; do not redistribute proprietary fonts. Confirm long captions fit and do not collide with products. When matching a reference, report any uncertain font identification.

Write a JSON configuration beside the all-on image. Read [references/configuration.md](references/configuration.md) for the schema and timing. Paths are relative to that JSON, not the current shell directory.

## Render and verify

Install the Python dependencies from `requirements.txt` if needed. Run:

```bash
python scripts/render.py --config /path/to/scene.json --output /path/to/new-output-folder
```

Resolve `scripts/render.py` relative to this skill. It uses system FFmpeg if available, otherwise the `imageio-ffmpeg` binary. Supply `--ffmpeg` when the host bundles a binary. Adapt the Python executable to the host instead of assuming `python` is on PATH.

The renderer saves `product-spotlight.mp4`, `bright.png`, `dark.png`, `audio.wav`, state previews and `manifest.json`. It refuses a nonempty output directory unless `--overwrite` is explicit. It uses RGB-plane masks: YUV chroma masks can brighten unselected products, a subtle but consequential failure.

Inspect every state preview and extract video frames near transitions. Check product identity, independent illumination, readable labels, blank dark pauses, final all-on scene, and audio timing. The renderer also verifies full video decoding. If a mask lights another product or misses part of a vessel, adjust it and rerender. Check H.264/yuv420p and AAC compatibility and the intended duration. Keep the photo-only default near 8.53 seconds at 30 fps; only change it to honor the user's request or a reference.

Deliver the playable MP4, bright/dark images and a short explanation of any AI reconstruction or approximate font match. Keep user media in the output workspace; upload or publish it only when that specific action is authorized.
