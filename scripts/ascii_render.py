# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""Shared ASCII-art core, lifted from make_walk.py (the tuned look): enhance, cell averaging, glyph pick, ink scaling, draw, export.
A grid is (chars, colours): chars (rows, cols) 1-char str with " " = empty, colours int (rows, cols, 3)."""
import io, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAMPS = {"default": " .:-=+*#%@", "detailed": " dbkhao*#MW&8%B@$"}  # ezascii's two ramps
FONTS = ["/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
         "/usr/share/fonts/truetype/freefont/FreeMono.ttf", "LiberationMono-Regular.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"]

def find_font(size):
    for p in FONTS:
        try: return ImageFont.truetype(p, size)
        except OSError: pass
    return ImageFont.load_default(size)

def enhance(rgb, brightness=0, contrast=45, saturation=1.65, gamma=1.2):
    """ezascii's pixel pass: brightness, contrast, saturation, gamma."""
    rgb = rgb + brightness
    rgb = (259 * (contrast + 255) / (255 * (259 - contrast))) * (rgb - 128) + 128
    grey = (rgb * (.299, .587, .114)).sum(-1, keepdims=True)
    rgb = np.clip(grey + (rgb - grey) * saturation, 0, 255)
    return 255 * (rgb / 255) ** (1 / gamma)

def box(rgb, cols, rows):
    """Area-average float RGB to (rows, cols, 3); PIL's float BOX filter does it per channel."""
    return np.stack([np.asarray(Image.fromarray(rgb[..., i].astype(np.float32), "F").resize((cols, rows), Image.BOX)) for i in range(3)], -1)

def cells_from_rgb(rgb, cols, rows=None, ramp="detailed", exponent=1.4, mono=None, bg_cut=0.02, char_aspect=1.0,
                   ink_min=170, ink_gain=1.6, enhance_kw=None):
    """Float RGB (H,W,3, 0..255) -> grid. rows follow the aspect ratio unless given; char_aspect = cell height / width."""
    rgb = np.asarray(rgb, float)
    h, w = rgb.shape[:2]
    rows = rows or max(1, round(cols * h / w / char_aspect))
    ramp = RAMPS.get(ramp, ramp)
    col = enhance(box(rgb, cols, rows), **(enhance_kw or {}))
    lum = np.clip((col * (.299, .587, .114)).sum(-1) / 255, 0, 1)
    idx = np.maximum(np.floor(lum ** exponent * (len(ramp) - 1)).astype(int), 1)  # lit cells keep the first visible glyph
    chars = np.where(lum > bg_cut, np.array(list(ramp))[idx], " ")
    ink = col * np.clip(ink_min / np.maximum(col.max(-1, keepdims=True), 1), 1, ink_gain)  # glyphs cover part of a cell, so scale ink, hue kept
    ink = np.clip(ink, 0, 255).astype(int)
    if mono is not None: ink = np.broadcast_to(np.array(mono, int), ink.shape).copy()
    return chars, ink

def draw(grid, cell=5, bg=(18, 14, 24), font_size=8, caption=None):
    chars, col = grid
    rows, cols = chars.shape
    img = Image.new("RGB", (cols * cell, rows * cell + (22 if caption else 0)), tuple(bg))
    d, font = ImageDraw.Draw(img), find_font(font_size)
    for r, c in zip(*np.nonzero(chars != " ")):  # centred in its cell, like ezascii's textAlign/textBaseline middle
        d.text(((c + .5) * cell, (r + .5) * cell), chars[r, c], font=font, fill=tuple(int(v) for v in col[r, c]), anchor="mm")
    if caption: d.text((cols * cell / 2, rows * cell + 11), caption, font=find_font(13), fill=(185, 163, 196), anchor="mm")
    return img

def seam(grids):
    """Fraction of cells whose char differs between the last frame and the first (0 = seamless wrap)."""
    return float((grids[-1][0] != grids[0][0]).mean())

def gif_bytes(imgs, ms, pal_idx):
    sheet = Image.new("RGB", (imgs[0].width * 2, imgs[0].height * 2))
    for i, k in enumerate(pal_idx): sheet.paste(imgs[k], (i % 2 * imgs[0].width, i // 2 * imgs[0].height))
    pal = sheet.quantize(colors=256, method=Image.Quantize.MEDIAN_CUT if hasattr(Image.Quantize, "MEDIAN_CUT") else Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]
    b = io.BytesIO()
    q[0].save(b, "GIF", save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True)
    return b.getvalue()

PLAYER = """<!doctype html><meta charset=utf-8><title>ascii</title><body style="margin:0;background:%(bg)s"><pre id=p style="margin:0;padding:8px;color:%(fg)s;font:12px/1 ui-monospace,Menlo,Consolas,monospace;white-space:pre"></pre>
<script>const F=%(frames)s,p=document.getElementById('p');let i=0;p.textContent=F[0];
if(!matchMedia('(prefers-reduced-motion: reduce)').matches)setInterval(()=>{i=(i+1)%%F.length;p.textContent=F[i]},%(ms)d)</script>"""

def export(grids, out_path, frame_ms=80, step=1, max_mb=None, palette_frames=None, **draw_kw):
    """Write grids as .gif/.webp/.mp4/.txt/.json/.html by suffix. step keeps every Nth frame (duration x N); max_mb raises step until the gif fits."""
    out = Path(out_path)
    ext = out.suffix.lower()
    if ext in (".gif", ".webp", ".mp4"):
        imgs = [draw(g, **draw_kw) for g in grids]
    if ext == ".gif":
        pal = palette_frames or [int(len(imgs) * x) for x in (0, .2, .4, .65)]
        while True:
            kept = imgs[::step]
            data = gif_bytes(kept, frame_ms * step, [min(k // step, len(kept) - 1) for k in pal])  # palette indices follow the kept frames
            if not max_mb or len(data) <= max_mb * 1e6 or len(kept) <= 2: break
            step += 1
        if max_mb: print(f"gif step {step}: {len(data) / 1e6:.2f} MB", file=sys.stderr)
        out.write_bytes(data)
    elif ext == ".webp":
        k = imgs[::step]
        k[0].save(out, save_all=True, append_images=k[1:], duration=frame_ms * step, loop=0, quality=80)
    elif ext == ".mp4":
        import imageio_ffmpeg
        k, (w, h) = imgs[::step], imgs[0].size
        w2, h2 = w + w % 2, h + h % 2  # yuv420p needs even dimensions
        wr = imageio_ffmpeg.write_frames(str(out), (w2, h2), fps=1000 / (frame_ms * step), codec="libx264", macro_block_size=1)
        wr.send(None)
        for im in k:
            pad = Image.new("RGB", (w2, h2), tuple(draw_kw.get("bg", (18, 14, 24))))
            pad.paste(im)
            wr.send(pad.tobytes())
        wr.close()
    else:
        text = ["\n".join("".join(r) for r in g[0]) for g in grids[::step]]
        ms = frame_ms * step
        if ext == ".txt": out.write_text("\n\x0c\n".join(text))
        elif ext == ".json":
            lit = np.concatenate([g[1][g[0] != " "] for g in grids])
            mono = not len(lit) or (lit == lit[0]).all()
            cols = None if mono else [[["#%02x%02x%02x" % tuple(c) for c in r] for r in g[1]] for g in grids[::step]]
            out.write_text(json.dumps({"frame_ms": ms, "cols": grids[0][0].shape[1], "rows": grids[0][0].shape[0], "frames": text, "colours": cols}))
        elif ext == ".html":
            lit = grids[0][0] != " "
            fg = "#%02x%02x%02x" % tuple(grids[0][1][lit][0]) if lit.any() else "#e8e0d0"
            bg = "#%02x%02x%02x" % tuple(draw_kw.get("bg", (18, 14, 24)))
            out.write_text(PLAYER % dict(bg=bg, fg=fg, frames=json.dumps(text).replace("</", "<\\/"), ms=ms))
        else: raise ValueError(f"unknown output type {ext}")
    return out

def contact_sheet(grids, out_png, n=8, **draw_kw):
    """n evenly spaced frames in a grid PNG for quick review."""
    ks = np.linspace(0, len(grids), min(n, len(grids)), endpoint=False).astype(int)
    ims = [draw(grids[k], **draw_kw) for k in ks]
    nc = min(4, len(ims))
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * nc, h * -(-len(ims) // nc)), tuple(draw_kw.get("bg", (18, 14, 24))))
    for i, im in enumerate(ims): sheet.paste(im, (i % nc * w, i // nc * h))
    sheet.save(out_png)
    return out_png
