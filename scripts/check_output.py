# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""Deterministic checks on an ascii-animation output, so measurable claims are graded by code, not an LLM.
uv run scripts/check_output.py OUT [--max-mb F] [--seam-max F] [--frames N] [--rows-equal] [--reduced-motion] [--mono] [--min-coverage F]
Prints one JSON object {file, checks:[{name,passed,value}], passed}; exit 0 if all pass, else 1.
Images (.gif/.webp): seam = fraction of pixels whose max channel differs by > 24 between first and last frame (pixel-based, not glyph-based).
Text (.json/.txt/.html): frames as ascii_render.export writes them; seam = fraction of cells whose char differs, like ar.seam."""
import argparse, json, re, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageSequence

TOL = 24

def text_frames(p):
    s = p.read_text()
    if p.suffix == ".json": return json.loads(s)["frames"], json.loads(s).get("colours")
    if p.suffix == ".html":
        m = re.search(r"\bF=(?=\[)", s)  # the player's frame array
        return (json.JSONDecoder().raw_decode(s, m.end())[0] if m else []), None
    return s.split("\n\x0c\n"), None

def char_grid(f, w, h):
    g = np.full((h, w), " ")
    for r, line in enumerate(f.split("\n")): g[r, :len(line)] = list(line)
    return g

def image_frames(p):
    im = Image.open(p)
    fr = [np.asarray(f.convert("RGB")).astype(int) for f in ImageSequence.Iterator(im)]
    ms = sum(f.info.get("duration", 0) for f in ImageSequence.Iterator(im))
    return fr, ms / 1000

def bg_of(f):
    v, n = np.unique(f.reshape(-1, 3), axis=0, return_counts=True)
    return v[n.argmax()]

def check(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("out"); a.add_argument("--max-mb", type=float); a.add_argument("--seam-max", type=float); a.add_argument("--frames", type=int)
    a.add_argument("--rows-equal", action="store_true"); a.add_argument("--reduced-motion", action="store_true")
    a.add_argument("--mono", action="store_true"); a.add_argument("--min-coverage", type=float)
    a = a.parse_args(argv)
    p, ext, cs = Path(a.out), Path(a.out).suffix.lower(), []
    add = lambda n, ok, v: cs.append({"name": n, "passed": bool(ok), "value": v})
    if not p.is_file():  # a missing output is a failed check, not a crash
        print(json.dumps({"file": str(p), "checks": [{"name": "exists", "passed": False, "value": None}], "passed": False})); return False
    mb = p.stat().st_size / 1e6
    add("size_mb", a.max_mb is None or mb <= a.max_mb, round(mb, 4))
    if ext in (".gif", ".webp"):
        fr, dur = image_frames(p)
        n = len(fr); add("duration_s", True, round(dur, 3))
        sm = float((np.abs(fr[-1] - fr[0]).max(-1) > TOL).mean()) if n > 1 else 0.0
        bg = bg_of(fr[0])
        ink = [(f[(np.abs(f - bg).max(-1) > TOL)]) for f in fr]
        cover = float(np.mean([len(i) / (f.shape[0] * f.shape[1]) for i, f in zip(ink, fr)]))
        def hues():  # ink colours seen as hue directions from the bg; antialiasing only moves along that line
            pts = np.concatenate([i[::max(1, len(i) // 2000)] for i in ink[::max(1, n // 8)]]) - bg
            pts = pts[np.abs(pts).max(-1) > 80]  # strong ink only: blends with the bg are dimmer
            d = pts / np.maximum(np.linalg.norm(pts, axis=-1, keepdims=True), 1)
            return len({tuple(x) for x in np.round(d * 3).astype(int)})
        mono = lambda: hues() <= 2
    elif ext in (".json", ".txt", ".html"):
        fs, colours = text_frames(p)
        n = len(fs)
        lines = [l for f in fs for l in f.split("\n")]
        w, h = max(map(len, lines), default=0), max((f.count("\n") + 1 for f in fs), default=0)
        sm = float((char_grid(fs[-1], w, h) != char_grid(fs[0], w, h)).mean()) if n > 1 else 0.0
        cover = float(np.mean([(char_grid(f, w, h) != " ").mean() for f in fs])) if n and w else 0.0
        mono = lambda: ext != ".json" or colours is None
    else: sys.exit(f"unsupported output type {ext}")
    add("frames", a.frames is None or n == a.frames, n)
    if a.seam_max is not None: add("seam", sm <= a.seam_max, round(sm, 4))
    if a.rows_equal:
        if ext in (".gif", ".webp"): add("rows_equal", True, "n/a (image)")
        else: add("rows_equal", len({len(l) for l in lines}) <= 1 and len({f.count("\n") for f in fs}) <= 1, sorted({len(l) for l in lines})[:5])
    if a.reduced_motion:
        s = p.read_text() if ext == ".html" else ""
        # behaviour, not our markup: any player that reads the media query and reacts when it changes passes
        live = re.search(r"addEventListener\(\s*['\"]change['\"]|\.addListener\(|\.onchange\s*=", s)
        add("reduced_motion", bool(re.search(r"matchMedia\(\s*['\"]\(?prefers-reduced-motion", s) and live), "html only" if ext != ".html" else bool(live))
    if a.mono: add("mono", mono(), None)
    if a.min_coverage is not None: add("coverage", cover >= a.min_coverage, round(cover, 4))
    ok = all(c["passed"] for c in cs)
    print(json.dumps({"file": str(p), "checks": cs, "passed": ok}))
    return ok

def main(argv=None):
    sys.exit(0 if check(argv) else 1)

if __name__ == "__main__": main()
