# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg", "scipy"]
# ///
"""Video (file or URL) -> looping ASCII animation (.gif/.webp/.mp4/.txt/.json/.html)."""
import argparse, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imageio_ffmpeg
import ascii_render as ar

def fetch(url, start, dur, tmp):
    """Returns (path, sectioned). Sectioned download needs ffmpeg (imageio's); if it fails, fetch whole and let read() trim."""
    cmd = ["uv", "tool", "run", "yt-dlp", "--ffmpeg-location", imageio_ffmpeg.get_ffmpeg_exe(),  # not uvx: some uv installs ship without that shim
           "-o", os.path.join(tmp, "in.%(ext)s")]
    sect = start is not None or dur
    if sect and not subprocess.run(cmd + ["-f", "mp4/best", "--download-sections", f"*{start or 0}-{(start or 0) + dur if dur else 'inf'}", url]).returncode:
        return os.path.join(tmp, next(f for f in os.listdir(tmp) if f.startswith("in."))), True
    if sect: print("sectioned download failed, fetching the whole video and trimming locally", file=sys.stderr)
    if subprocess.run(cmd + ["-f", "mp4/best", "-S", "+size", url]).returncode:
        sys.exit("download failed: Douyin/TikTok/Instagram usually need cookies, or give me your own video file instead")
    return os.path.join(tmp, next(f for f in os.listdir(tmp) if f.startswith("in."))), False

def key_mask(frames, thresh):
    """Subject = pixels far from the temporal-median background; keep the biggest blob plus blobs touching it (limbs, hair)."""
    from scipy import ndimage as nd
    g = [f.mean(-1) for f in frames]
    F0 = np.fft.fft2(g[0])
    sh = []  # per-frame global shift vs frame 0 by phase correlation: a panning camera moves the background, which dominates the frame
    for x in g:
        c = np.fft.ifft2(F0 * np.conj(np.fft.fft2(x)) / (abs(F0 * np.conj(np.fft.fft2(x))) + 1e-9)).real
        dy, dx = np.unravel_index(c.argmax(), c.shape)
        sh.append((dy - c.shape[0] if dy > c.shape[0] // 2 else dy, dx - c.shape[1] if dx > c.shape[1] // 2 else dx))
    med = np.median(np.stack([np.roll(f, s, (0, 1)) for f, s in zip(frames, sh)]), 0)  # backgrounds aligned, subject smeared out
    masks = []
    for f, s in zip(frames, sh):
        m = nd.binary_opening(np.sqrt(((f - np.roll(med, (-s[0], -s[1]), (0, 1))) ** 2).sum(-1)) > thresh)  # opening drops speckle
        lab, n = nd.label(m, np.ones((3, 3)))
        if n:
            big = 1 + np.argmax(nd.sum(m, lab, range(1, n + 1)))
            near = nd.binary_dilation(lab == big, iterations=max(3, f.shape[1] // 40))
            m = np.isin(lab, np.unique(lab[near & m]))
        masks.append(nd.binary_closing(m, iterations=2))  # fills holes where subject matches the background
    return masks

def read(path, start, dur, fps):
    """Yields (H,W,3) uint8 frames at fps via ffmpeg's fps filter."""
    meta = next(g := imageio_ffmpeg.read_frames(path, input_params=(["-ss", str(start)] if start else []) + (["-t", str(dur)] if dur else []),
                                                output_params=["-vf", f"fps={fps}"]))
    w, h = meta["size"]
    for b in g: yield np.frombuffer(b, np.uint8).reshape(h, w, 3)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input"); ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--start", type=float, default=0); ap.add_argument("--dur", type=float)
    ap.add_argument("--fps", type=float, default=12); ap.add_argument("--cols", type=int, default=120)
    ap.add_argument("--ramp", default="detailed"); ap.add_argument("--exponent", type=float, default=1.4)
    ap.add_argument("--mono", help="#hex: paint every glyph this colour"); ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--crop", help="x,y,w,h in source pixels"); ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--pingpong", action="store_true", help="play forward then back, no repeated frame at the turns")
    ap.add_argument("--key", choices=["auto"], help="auto: isolate the subject against a temporal-median background (try before rembg)")
    ap.add_argument("--key-thresh", type=float, default=40, help="RGB distance from the background that counts as subject")
    ap.add_argument("--max-mb", type=float); ap.add_argument("--sheet")
    ap.add_argument("--segment", action="store_true", help="cut out the subject with rembg (asks a 170 MB model download)")
    ap.add_argument("--i-asked-the-user", action="store_true")
    a = ap.parse_args(argv)
    if a.segment:
        if not a.i_asked_the_user: sys.exit("--segment downloads a ~170 MB model: ask the user, then add --i-asked-the-user")
        try: from rembg import remove
        except ImportError: sys.exit('rembg missing. Re-run with: uv run --with "rembg[cpu]" scripts/video2ascii.py ' + " ".join(sys.argv[1:]))
    mono = tuple(int(a.mono.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) if a.mono else None
    aspect = 2.0 if os.path.splitext(a.out)[1].lower() in (".txt", ".html", ".json") else 1.0  # text shows in tall monospace cells
    with tempfile.TemporaryDirectory() as tmp:
        src, sect = fetch(a.input, a.start, a.dur, tmp) if a.input.startswith(("http://", "https://")) else (a.input, False)
        t0, d0 = (0, None) if src != a.input and sect else (a.start, a.dur)  # a downloaded section already starts at 0
        frames = []
        for fr in read(src, t0, d0, a.fps):
            if a.crop: x, y, w, h = map(int, a.crop.split(",")); fr = fr[y:y + h, x:x + w]
            if a.mirror: fr = fr[:, ::-1]
            frames.append(fr)
        cover = ""
        if a.key and frames:
            ms = key_mask(frames, a.key_thresh)
            frames = [f * m[..., None] for f, m in zip(frames, ms)]
            cover = f", key coverage {np.mean([m.mean() for m in ms]):.1%}"
        grids = []
        for fr in frames:
            if a.segment: fr = np.asarray(remove(fr, bgcolor=(0, 0, 0, 255)).convert("RGB"))  # black background reads as empty cells
            grids.append(ar.cells_from_rgb(fr.astype(float), a.cols, ramp=a.ramp, exponent=a.exponent, mono=mono, char_aspect=aspect))
    if not grids: sys.exit("no frames decoded")
    if a.pingpong: grids += grids[-2:0:-1]  # endpoints not repeated, so the turns don't stall
    ar.export(grids, a.out, frame_ms=round(1000 / a.fps), step=a.step, max_mb=a.max_mb)
    if a.sheet: ar.contact_sheet(grids, a.sheet)
    print(f"{len(grids)} frames, grid {grids[0][0].shape[1]}x{grids[0][0].shape[0]}, seam {'n/a (pingpong wraps like any other step)' if a.pingpong else f'{ar.seam(grids):.3f}'}, {a.out} {os.path.getsize(a.out) / 1e6:.2f} MB{cover}")

if __name__ == "__main__": main()
