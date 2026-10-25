# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg", "scipy"]
# ///
"""Offline checks for the ascii-animation scripts: uv run scripts/selftest.py"""
import contextlib, io, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import imageio_ffmpeg
import ascii_render as ar, video2ascii, frames2ascii, ab_compare, check_output, record_eval

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
    # new channels: a jumping-jack timeline built in code (no example file): raise / spread / bob cycle 0 -> 1 -> 0, two hops per loop
    import dataclasses
    nf = 16
    base = rig.make_pose_fn(nf, rig.Keys({0: (180, 0, 0, 0, 0)}), np.zeros((nf + 1, 4)), [np.zeros(nf + 1)] * 3)
    def jj(f):
        u = 0.5 - 0.5 * np.cos(2 * np.pi * f / nf)
        return dataclasses.replace(base(f), raise_=u, spread=u, bob=0.05 * np.sin(np.pi * (f % (nf // 2)) / (nf // 2)))
    tl = rig.Timeline(nf, jj)
    rig.check_loop(tl)
    grids = [rig.frame(tl, f) for f in range(nf)]
    ar.contact_sheet(grids, os.path.join(tmp, "jj_sheet.png"), cell=rig.CELL)
    assert os.path.getsize(os.path.join(tmp, "jj_sheet.png")) > 0
    assert (grids[0][0] != grids[nf // 2][0]).any(), "raise/spread=1 must differ from 0"
    rest = rig.frame(rig.Timeline(1, lambda f: rig.Pose(loop=1)), 0)[0]
    for k in ("raise_", "spread"):
        g = rig.frame(rig.Timeline(1, lambda f: dataclasses.replace(rig.Pose(loop=1), **{k: 1.0})), 0)[0]
        assert (g != rest).any(), k

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
        code, o = run(video2ascii, P("clip.mp4"), "-o", P("pp.json"), "--fps", "12", "--cols", "40", "--pingpong")
        assert code == 0 and o.startswith("46 frames") and "seam n/a (pingpong" in o and len(json.load(open(P("pp.json")))["frames"]) == 46; ok("--pingpong 2n-2")
        # moving disc over static random noise: median background should strip the noise, keep the disc
        rng = np.random.default_rng(0); noise = rng.integers(0, 256, (120, 160, 3)).astype(float)
        yy, xx = np.mgrid[:120, :160]; fr = []
        for i in range(24):
            f = noise.copy(); f[(xx - (20 + i * 5)) ** 2 + (yy - 60) ** 2 < 15 ** 2] = (255, 0, 0); fr.append(f)
        ms = video2ascii.key_mask(fr, 40)
        assert np.mean([m.mean() for m in ms]) < .25 and ms[12][60, 20 + 12 * 5] and all(m[60, 20 + i * 5] for i, m in enumerate(ms)); ok(f"--key: coverage {np.mean([m.mean() for m in ms]):.1%}, disc kept")
        g = [ar.cells_from_rgb(np.random.default_rng(i).random((30, 40, 3)) * 255, 20) for i in range(5)]
        assert ar.seam([g[0], g[1], g[0]]) == 0 and ar.seam(g) > 0; ok("seam")
        ar.export(g, P("a.html")); ar.export(g, P("a.json"), step=1)
        assert "prefers-reduced-motion" in open(P("a.html")).read(); ok("html reduced-motion")
        h = open(P("a.html")).read()
        assert "<!-- ascii-animation: paste from here -->" in h and "<!-- to here -->" in h and 'role="img"' in h and "addEventListener('change'" in h and "IntersectionObserver" in h
        ok("html paste block, live reduced-motion, offscreen pause")
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
        # usage-born evals: record a case, re-record appends, check_output grades by code
        store = P("evals-store")
        base = ["--name", "dance-too-small", "--source", "critique", "--prompt", "make my clip ascii", "--store", store]
        code, o = run(record_eval, *base, "--input", P("clip.mp4"), "--expect", "the dancer fills the frame", "--check", "*.gif: --max-mb 10", "--good", P("a.gif"), "--note", "too tiny")
        c = o.strip(); assert code == 0 and c == os.path.join(store, "dance-too-small"), (code, o)
        pm = open(c + "/prompt.md").read().split("\n")
        assert pm[0] == "---" and pm[5] == "---" and all(any(l.startswith(k + ":") for l in pm[1:5]) for k in ("tags", "max_turns", "timeout_seconds", "allowed_tools")) and pm[-2] == "Input files: clip.mp4", pm
        y = open(c + "/case.yaml").read(); assert 'schema_version: "1.1"' in y and "name: dance-too-small" in y and "scaffold_script: place-files.sh" in y
        gs = sorted(os.listdir(c + "/graders")); assert len(gs) == 2 and gs[0].startswith("01-") and open(c + "/graders/" + gs[0]).read().startswith("---\ntype: llm\nfocus: trace\nweight: 1\n---\n"), gs
        assert "reports passed: true" in open(c + "/graders/" + gs[1]).read()
        assert os.access(c + "/place-files.sh", os.X_OK) and os.path.exists(c + "/files/clip.mp4") and os.path.exists(c + "/refs/good.gif") and os.path.exists(c + "/refs/good.png")
        run(record_eval, *base, "--expect", "second critique")
        assert len(os.listdir(c + "/graders")) == 3 and "01-" in "".join(os.listdir(c + "/graders")) and len(open(store + "/index.jsonl").read().splitlines()) == 2
        assert run(record_eval, "--name", "results", "--source", "failure", "--prompt", "x", "--store", store)[0] != 0
        assert "dance-too-small" in run(record_eval, "--list", "--store", store)[1]; ok("record_eval: layout, append on re-record, --list")
        err = io.StringIO()  # the same file as good and bad ref: the check can't tell them apart, so it must warn
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            record_eval.main(["--name", "same-refs", "--source", "critique", "--prompt", "p", "--store", store, "--check", "*.gif: --max-mb 10", "--good", P("a.gif"), "--bad", P("a.gif")])
        assert "passes on the bad ref" in err.getvalue(), err.getvalue(); ok("record_eval warns on a non-discriminating check")
        code, o = run(check_output, P("a.gif"), "--frames", "24", "--min-coverage", "0.001")
        assert code == 0 and json.loads(o)["passed"], o
        assert run(check_output, P("a.gif"), "--max-mb", "0.000001")[0] == 1
        open(P("rag.json"), "w").write(json.dumps({"frames": ["ab\nc", "ab\nc"]}))
        assert run(check_output, P("rag.json"), "--rows-equal")[0] == 1 and run(check_output, P("a.json"), "--rows-equal", "--frames", "5")[0] == 0
        assert run(check_output, P("a.html"), "--reduced-motion")[0] == 0 and run(check_output, P("a.gif"), "--reduced-motion")[0] == 1
        ok("check_output: pass, size fail, ragged fail, html reduced-motion")
        if os.path.exists(os.path.join(HERE, "rig.py")): rig_checks(tmp); ok("rig checks")

if __name__ == "__main__": main()
