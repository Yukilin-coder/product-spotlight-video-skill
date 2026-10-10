# Renderer configuration

The agent prepares this configuration after inspecting the final scene. The user only needs to provide a photo.

```json
{
  "scene": "scene.png",
  "size": [1480, 1020],
  "fps": 30,
  "duration": 8.533333333,
  "dark_level": 0.25,
  "title_color": "#DAE045",
  "detail_color": "#9A9D57",
  "products": [
    {"label": "01 / ORIGINAL", "box": [0.23, 0.35, 0.40, 0.83], "label_position": [0.20, 0.25]},
    {"label": "02 / ORIGINAL", "box": [0.41, 0.30, 0.58, 0.83], "label_position": [0.42, 0.20]},
    {"label": "03 / ORIGINAL", "box": [0.59, 0.38, 0.76, 0.83], "label_position": [0.62, 0.28]}
  ]
}
```

**Example coordinates are illustrative, not universal product masks.** Inspect the scene and adapt every mask. Coordinates are normalized to `[0,1]` in the final image. A `box` is `[left,top,right,bottom]`. For precise masks replace `box` with `polygon: [[x,y], ...]`; polygons have at least three points. Include the whole product, including its stem, leaf, handle or pump.

Product options: `details` (array of verified text lines), `feather` (fraction of shortest image edge; default `0.006`), `font_size` (fraction of image height; default `0.026`), `detail_size` (default `0.019`). `label_position` is the text's top-left position. Supply `font` and `detail_font` as installed TrueType/OpenType file paths when exact fonts are available. Without them the renderer selects an installed condensed font or a Pillow fallback. It does not bundle fonts.

Default schedule for three products:

| Time (seconds) | Visible lighting and captions |
| --- | --- |
| 0–0.1 | All dark |
| 0.1–0.9333 | Product 0 on |
| 0.9333–2.1 | All dark |
| 2.1–2.9333 | Product 1 on |
| 2.9333–4.0667 | All dark |
| 4.0667–4.9 | Product 2 on |
| 4.9–5.9 | All dark |
| 5.9–8.5333 | All on |

Custom events replace the entire default schedule:

```json
"events": [
  {"start": 0.1, "end": 0.9, "products": [0]},
  {"start": 2.1, "end": 2.9, "products": [1]},
  {"start": 4.1, "end": 4.9, "products": [2]},
  {"start": 5.9, "end": 8.533333333, "products": [0, 1, 2]}
]
```

Events must not overlap. Products are zero-indexed. Intervals are half-open: start included, end excluded. Unspecified frames stay dark. Times round to the nearest frame. One to six products are supported, but a non-three-product scene needs custom events.

Optional `audio` is a local audio or video path, with `audio_start` in seconds (default `0`). Audio is trimmed or padded to the video's duration, including a short file. Without `audio`, original switch sounds are synthesized at all lighting changes, including lights turning off. `crf` defaults to `18`.

Dimensions must be even integers between 64 and 3840. Source and output aspect ratios should match; the renderer rejects significant mismatches rather than stretching a portrait photo into a landscape advertisement.
