# Labeling Guidelines (Northstrike)

## Classes (IDs)
0: drone  
1: person  
2: vehicle  
3: obstacle  
4: landing_pad

- Use tight boxes around visible object extent.
- Include truncated/occluded objects if >40% visible.
- Exclude pure reflections/shadows.
- For tiny objects (< 12x12 px) in high-res frames: skip unless mission-critical.
- One class per box (no multi-class boxes).
- If an image is inherently unlabeled (e.g., blank sky), leave label file empty.

## Quality Tiers
- Tier A: ≤2% class or box errors per 100 images.
- Tier B: ≤5% errors.

## File Conventions
- YOLO txt per image: `<cls> <cx> <cy> <w> <h>` normalized [0..1].
- Centers inside [0..1]; width/height in (0,1].
- IDs must be contiguous 0..N-1 (see `configs/labeling/labelmap.yaml`).

## Review Cadence
- Random 20 images per 500 labeled, dual review; disagreements escalated.
