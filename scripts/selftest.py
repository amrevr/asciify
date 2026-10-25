# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""Offline checks for the ascii-animation scripts: uv run scripts/selftest.py"""
import contextlib, io, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import imageio_ffmpeg
import ascii_render as ar, video2ascii, frames2ascii, ab_compare

def run(mod, *args):
    """Runs mod.main(args); returns (exit code, stdout)."""
    out, code = io.StringIO(), 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try: mod.main(list(args))
        except SystemExit as e: code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue()

def ok(msg): print("PASS", msg)

def make_clip(path):
    w = imageio_ffmpeg.write_frames(path, (160, 120), fps=24, macro_block_size=1)
    w.send(None)
    yy, xx = np.mgrid[:120, :160]
    for i in range(48):
        f = np.full((120, 160, 3), 40, np.uint8)
        f[(xx - (20 + i * 2.5)) ** 2 + (yy - 60) ** 2 < 15 ** 2] = 255
        w.send(f.tobytes())
    w.close()

def rig_checks(tmp):
    """pose2ascii --check-only passes for every example; a timeline with nf off by one must fail check_loop."""
    import pose2ascii, rig
    ex = os.path.join(HERE, "..", "examples")
    for n in ("walk_classic", "twirl", "lookback", "waveskip", "cycle"):
        code, _ = run(pose2ascii, os.path.join(ex, n + ".py"), "--check-only")
        assert code == 0, f"{n}: check_loop failed"
    try: rig.check_loop(rig.Timeline(rig.CLASSIC.nf - 1, rig.CLASSIC.pose_fn))
    except AssertionError: pass
    else: raise AssertionError("off-by-one timeline passed check_loop")

def main():
    with tempfile.TemporaryDirectory() as tmp:
        P = lambda n: os.path.join(tmp, n)
        make_clip(P("clip.mp4"))
        code, o = run(video2ascii, P("clip.mp4"), "-o", P("a.gif"), "--fps", "12", "--cols", "40")
        assert code == 0 and o.startswith("24 frames, grid 40x30"), (code, o)
        ok("video2ascii: " + o.strip())
        run(video2ascii, P("clip.mp4"), "-o", P("a.json"), "--fps", "12", "--cols", "40")
        assert json.load(open(P("a.json")))["rows"] == 15; ok("json rows are half the gif rows (char_aspect 2)")
        grids = [ar.cells_from_rgb(np.full((30, 40, 3), v, float), 40) for v in (0, 90, 255)]
        assert set(np.unique(np.concatenate([g[0].ravel() for g in grids]))) <= set(ar.RAMPS["detailed"]); ok("glyphs in ramp")
        run(video2ascii, P("clip.mp4"), "-o", P("big.gif"), "--fps", "12", "--cols", "120")
        big, small = os.path.getsize(P("big.gif")), None
        code, o = run(video2ascii, P("clip.mp4"), "-o", P("small.gif"), "--fps", "12", "--cols", "120", "--max-mb", str(big / 2e6))
        small = os.path.getsize(P("small.gif"))
        assert small <= big / 2 or small < big, (big, small)
        ok(f"--max-mb: {big} -> {small} bytes")
        g = [ar.cells_from_rgb(np.random.default_rng(i).random((30, 40, 3)) * 255, 20) for i in range(5)]
        assert ar.seam([g[0], g[1], g[0]]) == 0 and ar.seam(g) > 0; ok("seam")
        ar.export(g, P("a.html")); ar.export(g, P("a.json"), step=1)
        assert "prefers-reduced-motion" in open(P("a.html")).read(); ok("html reduced-motion")
        d = json.load(open(P("a.json")))
        assert len(d["frames"]) == 5 and d["cols"] == 20 and d["colours"] is not None; ok("json round-trip")
        for ext in ("txt", "webp", "mp4"): ar.export(g, P("a." + ext)); assert os.path.getsize(P("a." + ext)) > 0
        ok("txt/webp/mp4 export")
        txt = lambda body: open(P("f.txt"), "w").write(body) and None
        txt("# fps: 8\n# colour: #ff0000\n--- frame\n o\n/|\\\n\n--- frame x3\n o\n-|-\n\n--- frame\n o \n\\|/\n")
        code, o = run(frames2ascii, P("f.txt"), "-o", P("f.gif"))
        assert code == 0 and o.startswith("5 ticks"), (code, o); ok("frames2ascii good file + x3 hold")
        txt("--- frame\n o\n/|\\\n--- frame\n o\n")
        assert run(frames2ascii, P("f.txt"), "--check")[0] == 1; ok("frames2ascii ragged -> exit 1")
        code, o = run(ab_compare, P("a.gif"), P("small.gif"), "-o", P("ab.html"), "--labels", "LBLONE,LBLTWO", "--seed", "3")
        m = json.loads(o)
        assert sorted(m.values()) == ["LBLONE", "LBLTWO"] and "LBL" not in open(P("ab.html")).read(); ok(f"ab_compare {m}")
        if os.path.exists(os.path.join(HERE, "rig.py")): rig_checks(tmp); ok("rig checks")

if __name__ == "__main__": main()
