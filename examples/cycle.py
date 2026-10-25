# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""One seamless loop through all four walks (classic -> wave & skip -> twirl -> look-back -> classic ...), for banners.

Run: uv run examples/cycle.py [--short] [--step N] [-o walk_cycle.gif] [--max-mb 10]      (~2-3 min)
--short drops the look-back (smaller file; the classic keeps its full walk because the road only wraps every 5.6 m).
Each segment is rendered without its last frame (that frame is frame 0 of the next segment); check_joins asserts every join renders identical
characters (and colours to within 1/255 of float noise). Segments: twirl/waveskip/lookback.py supply timelines (lookback_timeline(from_front=True)
is the bridged version) and their own `mw` rig module (waveskip patches an in-memory copy of rig.py).
Unlike the other examples this has no single `tl`: it exposes check() and grids() instead, which pose2ascii.py uses when present.
"""
import argparse, os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import numpy as np
import rig, ascii_render as ar
import waveskip, twirl, lookback

FULL = [("classic", rig.CLASSIC, rig), ("waveskip", waveskip.tl, waveskip.mw), ("twirl", twirl.tl, twirl.mw),
        ("lookback", lookback.lookback_timeline(from_front=True), rig)]
SEGMENTS = FULL

def check(segments=None):
    segs = segments or SEGMENTS
    for i, (n, tl, m) in enumerate(segs):
        m.check_loop(tl)
        n2, tl2, m2 = segs[(i + 1) % len(segs)]
        (ca, ka), (cb, kb) = m.frame(tl, tl.nf), m2.frame(tl2, 0)
        assert (ca == cb).all() and np.abs(ka - kb).max() <= 1, f"join {n} -> {n2} differs"
        print("join ok:", n, "->", n2)

def grids(segments=None):
    return [m.frame(tl, f) for _, tl, m in (segments or SEGMENTS) for f in range(tl.nf)]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--short", action="store_true")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("-o", "--out", default="walk_cycle.gif")
    ap.add_argument("--max-mb", type=float)
    args = ap.parse_args()
    segs = FULL[:3] if args.short else FULL
    check(segs)
    g = grids(segs)
    out = ar.export(g, args.out, frame_ms=rig.FRAME_MS, step=args.step, max_mb=args.max_mb)
    print(out, os.path.getsize(out), len(g), "frames")
