# Hand-drawn keyframes (`scripts/frames2ascii.py`)

## File format
```
# fps: 8
# colour: #e8e0d0
# bg: #121018
--- frame
   /\_/\
  ( -.- )
   > ^ <
--- frame x3
   /\_/\
  ( o.o )
   > ^ <
```
- Header lines (optional) come before the first `--- frame`.
- `--- frame xN` holds that frame for N ticks. Use it for pauses instead of copy-pasting frames.
- Rows are right-padded to the widest row, but **every frame must have the same number of rows**. Pad with blank lines, or the figure jumps vertically. The script names the offending frame.
- The frame after the last is frame 0, so don't repeat frame 0 at the end.

## Drawing a motion that reads
1. **Fix a ground line and an anchor** (feet, base, centre of mass) and keep it on the same row and column in every frame. Most "jitter" is the anchor drifting by one cell.
2. **Key poses first**: draw the extremes (squat, peak, landing). Add in-betweens only where the change between keys exceeds about two cells; ASCII can't show sub-cell motion, and extra frames just shimmer.
3. **Change only what moves.** Diff consecutive frames mentally: a static body part should be byte-identical across frames.
4. **Timing over frame count**: hold extremes (`x2`–`x3`), move fast through the middle. 8–12 fps suits hand-drawn work.
5. **Silhouette first**: at 20–40 columns, a strong outline beats interior detail. Use dense glyphs (`#@%`) for mass and light ones (`.:'`) for edges and motion trails.
6. Keep it small: 20–60 columns × 8–25 rows. Bigger hand-drawn frames take long to draw and rarely look better.

## Review
Render with `--sheet` and look at the contact sheet before showing anyone. Check that the anchor stays put, the row count is constant, and the last frame flows into the first. `--check` validates without rendering.
