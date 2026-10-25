# The renderer (`scripts/ascii_render.py`)

The look copies ezascii.com's video-to-ascii mode, which the user preferred over hand-rolled styles. Each frame is box-averaged into square character cells. Each cell then gets:

1. **Pixel pass** (`enhance`): brightness 0, contrast 45, saturation 1.65, gamma 1.2, applied in that order.
2. **Glyph**: `lum = Rec.601 luma / 255`, then `ramp[floor(lum ** exponent * (len - 1))]`. Cells darker than `bg_cut` (0.02) stay empty; any other cell gets at least the first visible glyph, so dim areas still carry colour.
3. **Ink**: the cell's own colour, scaled up (hue kept) until its brightest channel reaches ~170. A glyph only covers part of its cell, so unscaled colours look muddy.

## Knobs
| Knob | Default | Effect |
|---|---|---|
| `--cols` | 120 (video), 173 (rig) | Detail vs size. 80–120 for READMEs, 160+ for hero banners. |
| `--ramp` | `detailed` ` dbkhao*#MW&8%B@$` | Dense, letter-heavy texture; best in colour. `default` ` .:-=+*#%@` is airier and suits monochrome. Any custom string works, ordered light → dense. |
| `--exponent` | 1.4 | Higher pushes mid-tones toward light glyphs, giving more contrast and a cleaner background. |
| `--mono '#hex'` | off | One ink colour for every glyph. Smaller GIFs, and it suits terminals and minimal sites. |
| cell size / font | 5 px cells, 8 px font | Set in `draw`; a font search falls back to Pillow's built-in font. |

## Aspect
The cells are square (5 × 5 px) and glyphs are centred in them, so images keep their proportions in GIF/WebP/MP4. Text exports (`.txt`, `.html`, `.json`) display in a real monospace font, whose cells are about twice as tall as wide. For those targets, `video2ascii.py` halves the row count so figures aren't stretched tall.

## Size budget
GIF is the biggest format. In order of effectiveness:
1. `--step N` keeps every Nth frame and lengthens each one, so playback speed is unchanged.
2. `--mono`: fewer colours compress much better.
3. Fewer `--cols`.
4. A shorter clip.

`--max-mb` automates step 1. The GIF palette is one 256-colour median-cut palette sampled from four frames, with no dithering, because dither noise flickers in ASCII.

## Flicker
Video frames shimmer when a cell's luminance sits on a ramp boundary. The fixes, cheapest first: raise `--exponent`, drop `--fps` to 10–12, crop away busy backgrounds, then (only with the user's OK) `--segment`.
