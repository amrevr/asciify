# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""Hand-drawn ASCII frames in a text file -> looping animation. Headers: `# fps: 8`, `# colour: #hex`, `# bg: #hex`;
frames split by `--- frame` (`--- frame x3` holds it 3 ticks)."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import ascii_render as ar

hexrgb = lambda s: tuple(int(s.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

def parse(text):
    """Returns (headers, [(rows, hold)])."""
    hdr, frames = {}, []
    for line in text.splitlines():
        m = re.match(r"^--- frame( x(\d+))?\s*$", line)
        if m: frames.append(([], int(m.group(2) or 1)))
        elif not frames and (h := re.match(r"^#\s*(\w+):\s*(.+?)\s*$", line)): hdr[h.group(1)] = h.group(2)
        elif frames: frames[-1][0].append(line.rstrip())
    for rows, _ in frames:
        while rows and not rows[-1]: rows.pop()  # tolerate trailing blank lines
    return hdr, frames

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input"); ap.add_argument("-o", "--out"); ap.add_argument("--sheet")
    ap.add_argument("--check", action="store_true", help="validate only"); ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--cell", type=int, default=10)
    a = ap.parse_args(argv)
    hdr, frames = parse(open(a.input).read())
    if not frames: sys.exit("no frames: separate them with '--- frame' lines")
    n = len(frames[0][0])
    for i, (rows, _) in enumerate(frames):
        if len(rows) != n: print(f"frame {i + 1} has {len(rows)} rows, frame 1 has {n}", file=sys.stderr); sys.exit(1)
    if frames[-1][0] == frames[0][0] and len(frames) > 1: print("warning: last frame equals first; the duplicate stutters at the loop seam", file=sys.stderr)
    if a.check: return print(f"ok: {len(frames)} frames, {n} rows")
    w = max(len(r) for rows, _ in frames for r in rows)
    col = hexrgb(hdr.get("colour", "#e8e0d0"))
    grids = []
    for rows, hold in frames:
        ch = np.array([list(r.ljust(w)) for r in rows])
        grids += [(ch, np.broadcast_to(np.array(col), (*ch.shape, 3)).copy())] * hold
    kw = dict(cell=a.cell, font_size=a.cell, **({"bg": hexrgb(hdr["bg"])} if "bg" in hdr else {}))
    if a.out: ar.export(grids, a.out, frame_ms=round(1000 / float(hdr.get("fps", 8))), step=a.step, **kw)
    if a.sheet: ar.contact_sheet(grids, a.sheet, **kw)
    print(f"{len(grids)} ticks from {len(frames)} frames, {w}x{n}, seam {ar.seam(grids):.3f}")

if __name__ == "__main__": main()
