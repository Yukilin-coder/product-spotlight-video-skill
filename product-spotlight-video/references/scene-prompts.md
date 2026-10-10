# Scene preparation prompts

Use the uploaded image as an edit/reference input, not merely a text description. Inspect the generated result before configuring masks.

## Photo-only default

```text
Create one clean photographic all-on scene for a product spotlight advertisement.
The supplied product photo is the identity reference. Preserve the recognizable
product shape, material, color, toppings, package proportions and visible label.
If the input shows multiple products, use those actual products. If it shows one
product, show three identical instances, without inventing different variants.

Arrange three products side by side around x=32%, 49%, 66% of the canvas.
Use a low frontal camera, a dark muted teal background, and a subtle warm tabletop.
Place product bases on the same surface near y=80%. Leave negative space above
each product for captions. Maintain natural differences in product height.
Output approximately 1.45:1 landscape, matching 1480×1020.

Illuminate all products clearly with localized soft light. Keep the room dramatic
and dim, with realistic material reflections and contact shadows. This is the
all-on source frame; animation will be composed later from this exact image.
No captions, extra products, invented logos, watermark, UI, presenter or split panels.
```

## Reference-driven variant

Attach a crop of the creative scene as a second reference. State:

```text
Image 1 defines product identity. Image 2 defines framing, viewpoint, spacing,
surface angle, lighting mood and the negative space for typography. Replace
the products in image 2 with the actual products in image 1. Do not copy the
reference's product identity, presenter, app UI or typography into the photograph.
Return one clean all-on scene with no text; typography will be added separately.
```

Explicitly name identity-critical details for each product. If a label needs exact
reproduction and generation changes it, preserve the original photo layout or use
a host-supported compositing workflow. Do not promise pixel-perfect preservation
of a newly generated viewpoint. Reuse the final scene for every light state.
