# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""Render a procedural-figure timeline module (examples/*.py) to an ASCII animation.
uv run scripts/pose2ascii.py examples/twirl.py -o out.gif [--no-scene] [--step N] [--max-mb 10] [--sheet s.png] [--check-only]
The module must expose `tl` (a rig.Timeline) and optionally `mw` (the rig module it used, e.g. waveskip's patched copy); or check() + grids()
(examples/cycle.py). The loop is checked first; --check-only stops there and exits 0 (loop ok) or 1."""
import argparse, importlib.util, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig, ascii_render as ar

def load(path):
    spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))  # examples import their siblings (cycle -> twirl)
    spec.loader.exec_module(m)
    return m

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("module"); ap.add_argument("-o", "--out", default="out.gif")
    ap.add_argument("--no-scene", action="store_true", help="figure on black, no night road")
    ap.add_argument("--step", type=int, default=1); ap.add_argument("--max-mb", type=float)
    ap.add_argument("--sheet"); ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args(argv)
    m = load(a.module)
    rm = getattr(m, "mw", rig)
    if a.no_scene: rm.SCENE = rig.SCENE = False
    try:
        if hasattr(m, "check"): m.check()
        else: rm.check_loop(m.tl)
    except AssertionError as e:
        print("loop check FAILED:", e, file=sys.stderr); return 1
    if a.check_only: print("loop ok"); return 0
    g = m.grids() if hasattr(m, "grids") else [rm.frame(m.tl, f) for f in range(m.tl.nf)]
    if a.sheet: ar.contact_sheet(g, a.sheet, cell=rig.CELL)
    out = ar.export(g, a.out, frame_ms=rig.FRAME_MS, step=a.step, max_mb=a.max_mb)
    print(f"{out} {os.path.getsize(out) / 1e6:.2f} MB, {len(g)} frames, seam {ar.seam(g):.3f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
