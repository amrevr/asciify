# ascii-animation

A Claude Code skill that turns a video, or a description of a motion, into a looping ASCII animation in the dense, colour-inked style of ezascii.com. It grew out of building an animated README banner (a girl doing the TikTok walk trend); the examples in `examples/` are that banner's animations.

## Install

Clone this repo as the skill folder:

```bash
git clone git@github.com:amrevr/asciify.git ~/.claude/skills/asciify
# or over HTTPS: git clone https://github.com/amrevr/asciify.git ~/.claude/skills/asciify
```

Requires [`uv`](https://docs.astral.sh/uv/). Each script declares its Python dependencies (numpy, pillow, imageio-ffmpeg), so you don't need system ffmpeg. URLs use `uv tool run yt-dlp`.

## What it does

| Input | Script | Notes |
|---|---|---|
| Video file or URL | `scripts/video2ascii.py` | Downloads only the requested section, then converts to ASCII cells |
| Description of a person moving | `scripts/rig.py` + `scripts/pose2ascii.py` | Parametric figure with keyed poses, springs and gait; enforces a seamless loop |
| Description of anything | `scripts/frames2ascii.py` | Frames drawn as text, then validated and exported |
| Two candidates | `scripts/ab_compare.py` | Blind A/B page, so the user can choose between generators |

Exports: `.gif` (with an optional size cap for READMEs), `.webp`, `.mp4`, `.txt`, `.json`, and a self-contained `.html` player that respects `prefers-reduced-motion`.

```bash
uv run scripts/video2ascii.py clip.mp4 -o banner.gif --start 0 --dur 6 --cols 120 --max-mb 10 --sheet sheet.png
uv run scripts/pose2ascii.py examples/twirl.py -o twirl.gif
uv run scripts/frames2ascii.py cat.txt -o cat.html
uv run scripts/selftest.py        # about 1 minute, no network
```

## Evals

`evals/` holds test cases in the format `claude plugin eval` reads (`prompt.md`, `case.yaml`, `graders/`). Their input clips are synthetic, rebuilt with `uv run evals/make_fixtures.py`. `evals/trigger-queries.json` holds should/shouldn't-trigger prompts for tuning the description.
