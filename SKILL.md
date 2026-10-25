---
name: ascii-animation
description: Make looping ASCII-art animations from a video (file, YouTube/TikTok/Douyin link, a clip of it) or from a plain description of a motion ("a girl twirling", "someone doing jumping jacks", "a cat stretching"), in a dense ezascii-style shaded look. Exports GIF, WebP/MP4, text frames, or a self-contained web player. Use this whenever someone wants an animated ASCII/text-art version of a clip, a moving ASCII banner or mascot, a "video to ascii" conversion, or an ASCII animation invented from words, even if they only say "make it ascii and loop it". Not for one-off static ASCII of an image or FIGlet text banners.
---

# ASCII animation

Two inputs, one look. Every path ends in the same renderer (`scripts/ascii_render.py`), so a converted clip and an invented one share the same glyphs, colour pass and exporters:

- **Video** → `scripts/video2ascii.py` (frames are box-averaged into character cells, then shaded).
- **Description** → two generators, which you A/B with the user:
  - **A: pose rig** (`scripts/rig.py` + `scripts/pose2ascii.py`): a parametric human figure driven by a keyed timeline. Smooth in-betweens, real shading, people only.
  - **B: hand-drawn keyframes** (`scripts/frames2ascii.py`): you draw the frames as text. Any subject (animals, objects, logos), stylised, cheaper.

Run every script with `uv run ${CLAUDE_SKILL_DIR}/scripts/<name>.py …`. Each declares its own dependencies (numpy, pillow, imageio-ffmpeg), so system ffmpeg and a global Pillow aren't needed. `uv run ${CLAUDE_SKILL_DIR}/scripts/selftest.py` checks the toolchain in about a minute; run it once if anything looks off.

## 1. Route the request

- A file path or URL to a video, or "this clip" → **video path**.
- Words describing a motion with no footage → **description path**.
- Both (footage plus "but make her twirl at the end") → video for the footage part, a description generator for the rest, then join them (see "Joining segments").
- Unclear which they mean, or no target given? Ask once: what it is for (website, terminal, chat, a file to share) and roughly how long. The target decides the export format and size budget, so it's worth one question.

## 2. Video path

Read `references/sources.md` when the input is a URL or the user hasn't said which part to use.

1. **Get the footage.** Use a local file directly. For a URL, `video2ascii.py` calls `uv tool run yt-dlp` and downloads only the section you ask for (it falls back to a full download plus a local trim if sectioning fails). When a download fails, tell the user the cause the tool output actually shows. A firewall or proxy 403 ("Approval required for …") means the user has to approve the domain. A site error means the site wants their cookies; Douyin, TikTok and Instagram usually do. Either way, offer the simplest unblock (approve the domain, or send the file), don't keep retrying, and never invent output from a clip you couldn't fetch.
2. **Pick the clip.** Use the range the user gave ("first 9 seconds"). Otherwise choose 2–6 s around the main action and say which range you used, since short clips loop better and keep GIFs small.
3. **Convert:**
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/video2ascii.py clip.mp4 -o out.gif --start 0 --dur 9 --fps 12 --cols 120 --sheet sheet.png
   ```
   `--mono '#e8e0d0'` for single-colour text, `--mirror` to flip the facing direction, `--crop x,y,w,h` to frame the subject, `--ramp default` for a lighter, sparser look.
4. **Background bleeding into the subject?** Work up a ladder of fixes, cheapest first, and stop as soon as the contact sheet looks clean:
   1. **Run** `--crop` around the subject's path, then `--key auto`. The key keeps pixels that differ from the clip's median background, then the largest connected blob. No download is needed, and it handles busy backgrounds behind a moving subject.
   2. Raise `--exponent` to push leftover texture toward empty cells.
   3. Only if that still isn't clean: background removal (`--segment`). It uses rembg, which downloads a ~170 MB model, so **ask the user first**, every time. Show them the sheet from the cheap attempt, say what the download costs, and pass `--i-asked-the-user` only after a yes.

   Actually run steps 1–2 before asking. The user would rather get a decent result now than answer a question you could have avoided.
5. **Clip doesn't cycle** (a straight cut, high seam score)? `--pingpong` plays it forward then backward without repeating the turn frames, so the seam disappears. Otherwise, pick cut points where the pose matches.

## 3. Description path (A/B)

Unless the user has already stated a preference (check your memory too), build **both** candidates and let them choose. The two generators fail in different ways: the rig looks more human and moves better, while hand-drawn is more stylised and handles non-human subjects. People can't predict which they'll like from a description. Showing both costs one extra render; picking wrong costs a whole iteration.

**A: pose rig** (people). Read `references/pose-rig.md`. Write a new timeline module that exposes `tl` (a `rig.Timeline`), modelled on `examples/` (`walk_classic.py`, `twirl.py`, `lookback.py`, `waveskip.py`). Those are references for the API and the motion vocabulary, not templates to copy. Start from the requested motion: key the yaw/squat/arm channels per frame, add springs for hair/hem follow-through, and use `gait` only if the figure walks. Then:
```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pose2ascii.py my_motion.py -o a.gif --sheet a.png    # runs check_loop first
```
`--no-scene` drops the night-road background for a figure on black.

**B: hand-drawn** (anything). Read `references/hand-drawn.md`. Write keyframes into a `.txt` file, then:
```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/frames2ascii.py my_motion.txt -o b.gif --sheet b.png
```

**Always deliver two candidates.** The comparison is the point of this path. When the rig can't do the motion (a non-human subject, or a pose outside its channels; see "What it can't do" in `pose-rig.md`), say so in one line. Then make two hand-drawn candidates in clearly different styles, such as a filled silhouette and a line drawing, and compare those instead. Don't drop to a single candidate, and don't quietly substitute a different motion.

**Compare blind:**
```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ab_compare.py a.gif b.gif -o ab.html --labels rig,hand
```
It prints which side is which. Keep that to yourself, show the user `ab.html` (or the two contact sheets), and ask with AskUserQuestion which they prefer: A, B, or "neither, change X". Refine the winner. Save the preference to memory (e.g. "prefers rig for people, hand-drawn for objects") so next time you can lead with it and only offer the other on request.

## 4. Make it loop

A visible seam is the most common complaint. Every exporter prints a seam score (the fraction of cells that change between the last frame and the first); aim for ~0 on rig output and as low as possible on video.
- Rig: `check_loop` must pass, and `pose2ascii.py` refuses to render otherwise. The pose at frame `nf` must equal frame 0: yaw modulo 360°, gait phase on the beat, walked distance a whole number of lamp spacings (strides in pairs).
- Hand-drawn: the frame after the last is frame 0. Don't repeat frame 0 at the end; the duplicate shows up as a stutter.
- Video: pick start/end points where the pose matches (look at the contact sheet), or play forward then reversed if the motion allows.

## 5. Preview, then export for the target

Always render a contact sheet (`--sheet`) and look at it yourself before showing the user. It catches squashed figures, empty frames and noisy backgrounds cheaply. Give the user file paths. If they want it served on a port, ask which port first.

| Target | Format | Notes |
|---|---|---|
| Website | `.html` player, or `.json` frames for an existing component | Text stays sharp and tiny. The page has a marked paste block (`<pre>` plus a scoped script) that follows `prefers-reduced-motion` live and pauses offscreen. Tell the user the text colour assumes a dark background. |
| Terminal / plain text | `.txt` | Frames separated by form-feed lines. |
| Chat / social | `.webp` or `.mp4` | Smaller than GIF at the same quality. |

## Joining segments

To chain animations (e.g. a walk into a twirl into a look-back), each segment's last frame must flow into the next segment's first. `examples/cycle.py` shows the pattern: render each segment without its last frame, assert every join is character-identical, and use one shared palette so colours don't jump at the joins.

## Lessons that carry over

From the session that produced this skill, kept here because they generalise:
- **Faces:** leave out eyes and mouths on small figures. At this resolution they read as uncanny, while blush or shading reads as a face.
- **Arms during a walk** should swing close to the body. Big swings read as flailing.
- **Lengthen a loop** by repeating whole cycles (e.g. walk strides in pairs) rather than slowing the frame rate. 80 ms frames (12.5 fps) look smooth in ASCII; fewer frames make it choppy.
- **Ramps:** the detailed ramp (` dbkhao*#MW&8%B@$`) gives the dense ezascii look; the default (` .:-=+*#%@`) is lighter and better for monochrome.
- **Iterate on contact sheets, not full renders**, and change one thing at a time when the user critiques a specific body part or motion.

## 6. Grow the evals from usage

This skill's tests come from how it's actually used, not from guesses. Whenever one of these moments happens, record an eval case so future versions of the skill are checked against it:

| Moment | Example | What to record |
|---|---|---|
| **Critique** | "her arms flail too much", "the loop jumps", "the file's too big" | A regression case: the original request, its inputs, the rejected output as `--bad`, and the critique turned into a check |
| **Approval** | "perfect", "ship it" | The approved output as `--good`, so later versions can be compared blind against it |
| **A/B pick** | the user chose B | The choice and the reason they gave, so the preference is tested, not just remembered |
| **Failure** | a download failed, a script crashed, you needed a workaround | What happened and the correct behaviour (e.g. "reports the firewall block and asks for approval") |

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/record_eval.py --name walk-arms-close --source critique \
  --prompt "<the user's original request>" --input clip.mp4 --bad out_v1.gif --note "<what they said, verbatim>" \
  --expect "During the walk, the figure's arms swing close to the body; no frame shows an arm raised above shoulder height" \
  --check "*.gif: --max-mb 10 --seam-max 0.1"
```

How to write the checks:
- **Generalise one step.** Describe the class of problem, not the single frame. "Arms flail at frame 23" won't catch the same mistake in a different motion; "during a walk the arms swing close to the body" will.
- **Use code for anything measurable.** File size, frame count, seam, equal rows and reduced motion go in `--check`, which `scripts/check_output.py` grades with no judgement call. Put only what needs eyes in `--expect`, phrased so a grader can say yes or no from the contact sheet.
- **A check has to tell good from bad.** Pass the approved and rejected outputs as `--good`/`--bad`; `record_eval.py` runs every `--check` against both and warns when it can't tell them apart. That means the critique is about taste: move it to `--expect`.
- **Phrase each check as the user's standard, not your fix.** Write "the loop has no visible jump", not "used --pingpong".

Recording runs locally into `~/.claude/skill-evals/ascii-animation/` (override with `$ASCII_ANIMATION_EVALS`) and copies the input files there. Tell the user in one line that you recorded a case and what it checks. If they say not to, stop recording for the rest of the session. `record_eval.py --list` shows what has been collected.

The skill also ships a small **baseline** in `evals/`: rules that hold for every user (export limits, no invented output, cheap fixes before the large download, two candidates for a description, loop seams). Usage cases add the rules specific to how this user works. `evals/README.md` explains how to run either set.
