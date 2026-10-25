# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""Writes the eval input clips (synthetic, so the repo carries no third-party footage): dance.mp4, skater.mp4 (busy background), intro.mp4.
Run: uv run evals/make_fixtures.py      (writes into each case's files/ folder)"""
import os
import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 320, 240, 24

def figure(d, cx, cy, t, kind):
    """A thick-limbed person; t in seconds drives the pose."""
    s = 2 * np.pi * t
    if kind == "dance": arm, leg, bob = 1.2 * np.sin(s), 0.5 * np.sin(s + 1), 6 * abs(np.sin(s))
    elif kind == "skate": arm, leg, bob = 0.5 + 0.2 * np.sin(s / 2), 0.25, 2 * np.sin(s)
    else: arm, leg, bob = 0.0, 0.1, 0  # intro: right arm waves
    cy -= bob
    skin, shirt, pants = (235, 200, 180), (230, 90, 80), (60, 70, 140)
    line = lambda a, b, c, w: d.line([a, b], fill=c, width=w)
    hip, neck = (cx, cy + 10), (cx, cy - 30)
    d.ellipse([cx - 12, cy - 58, cx + 12, cy - 32], fill=skin)
    line(neck, hip, shirt, 18)
    for sgn, ph in ((1, leg), (-1, -leg)):
        knee = (cx + sgn * 8 + 22 * np.sin(ph), cy + 38)
        line(hip, knee, pants, 10); line(knee, (knee[0] + 4 * sgn, cy + 68), pants, 9)
    for sgn in (1, -1):
        a = arm * sgn if kind != "intro" else (0 if sgn < 0 else 2.2 + 0.5 * np.sin(3 * s))
        el = (cx + sgn * (16 + 14 * np.cos(a)), neck[1] + 6 + 22 * np.sin(-a) * (1 if kind != "intro" else 1))
        line((cx + sgn * 8, neck[1] + 4), el, shirt, 8); line(el, (el[0] + sgn * 14 * np.cos(a), el[1] - 18 * np.sin(a)), skin, 6)

def busy(t, rng_img):
    """Scrolling high-contrast clutter: the background the skater case wants isolated."""
    return np.roll(rng_img, int(t * 90), axis=1).copy()

def write(path, secs, kind, background=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w = imageio_ffmpeg.write_frames(path, (W, H), fps=FPS, codec="libx264", pix_fmt_out="yuv420p", output_params=["-crf", "30"])
    w.send(None)
    for i in range(int(secs * FPS)):
        t = i / FPS
        img = Image.fromarray(background(t)) if background else Image.new("RGB", (W, H), (25, 25, 32))
        figure(ImageDraw.Draw(img), W / 2 + (60 * np.sin(t) if kind == "skate" else 0), 130, t, kind)
        w.send(np.asarray(img).tobytes())
    w.close()
    print(path, os.path.getsize(path), "bytes")

if __name__ == "__main__":
    rng = np.random.default_rng(7)
    clutter = Image.new("RGB", (W, H), (120, 120, 110)); d = ImageDraw.Draw(clutter)
    for _ in range(140):
        x, y = rng.integers(0, W), rng.integers(0, H)
        d.rectangle([x, y, x + rng.integers(6, 50), y + rng.integers(6, 50)], fill=tuple(int(c) for c in rng.integers(0, 255, 3)))
    clutter = np.asarray(clutter)
    write(f"{HERE}/video-clip-to-loop/files/dance.mp4", 6, "dance")
    write(f"{HERE}/busy-background-asks-first/files/skater.mp4", 4, "skate", lambda t: busy(t, clutter))
    write(f"{HERE}/web-player-reduced-motion/files/intro.mp4", 3, "intro")
