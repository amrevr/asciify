# The pose rig (`scripts/rig.py`)

A procedural figure (a faceless girl: bob haircut with a bow, blouse, pleated skirt, socks and loafers) on an optional night road. Each frame is drawn as luminance and part maps at 3× supersampling, shaded, then turned into cells by the shared renderer. It is the figure from the README banner that this skill grew out of, so treat it as one well-tuned character, not a general 3D skeleton.

## Writing a timeline

A timeline module exposes `tl = rig.Timeline(nf, pose_fn)`. `pose_fn(f) -> rig.Pose` must work for every integer `f` in `0..nf` **inclusive**, because frame `nf` is "the frame after the last" and must equal frame 0. Frames are 80 ms.

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))  # or the skill's scripts dir
import numpy as np
import rig

NF = 32
T = {0: (180, 0, 0, 0, 0), 6: (180, .6, 0, 0, 0), 10: (180, 0, 0, 1, 1), 22: (180, 0, 0, 1, 1), 28: (180, .3, 0, 0, 0), 32: (180, 0, 0, 0, 0)}
keys = rig.Keys(T)                                  # {frame: (yaw°, squat, tuck, near, far)}, Catmull-Rom between keys
spr = rig.springs(NF, rig.head_drive(keys, None))   # hair/ribbon/hem follow-through
gt = [np.zeros(NF + 1)] * 3                        # (fl, amp, travel): standing still; to walk use rig.gait(...), see below
tl = rig.Timeline(NF, rig.make_pose_fn(NF, keys, spr, gt, jig_from=None, idle_n=4))
```
Then `uv run ${CLAUDE_SKILL_DIR}/scripts/pose2ascii.py my_motion.py -o a.gif --sheet a.png`, adding `--check-only` while iterating. If you need a channel that `make_pose_fn` doesn't set, wrap it: `base = make_pose_fn(...)`, then `pose_fn = lambda f: dataclasses.replace(base(f), bob=…, wave=…)`. The examples do exactly this.

## Channels (fields of `rig.Pose`)
| Field | Range | What it does |
|---|---|---|
| `yaw_hip`, `yaw_sh`, `yaw_head` | radians, π = facing us, 0 = back | Turning and spinning. Shoulders and head lead the hips. Keys take degrees. |
| `squat` | 0..1 | Knee bend; the body drops 0.03 H at 1. Use for anticipation and landings. |
| `tuck` | 0..1 | Hands pulled in to the chest. |
| `near`, `far` | 0..1 | Arms swung out (front view: both out wide). |
| `wave`, `wph` | 0..1, phase | Right hand raised and waving. |
| `sway`, `shim`, `htilt` | small | Hip shift, shoulder roll, head tilt (the jig uses these). |
| `bob` | fraction of H | Vertical offset of the whole body (breathing, or small hops). |
| `fl`, `amp`, `travel` | from `gait` | Walk phase, walk amplitude, metres walked. |
| `fan`, `whip`, `flare`, `hem_x`, `tail_x`, `bounce` | from `springs` | Hair and skirt dynamics. Usually leave these to `springs`. |
| `peek` | bool | Back view with the head turned toward us (look-back). |

Helpers: `rig.jig_at` (a ready-made dance phrase), `rig.gait(nf, walk_from, wind_from, stop_at, strides)` (ease-in walk; **use an even number of strides** so the road wraps), `rig.walk_amp`, `rig.classic_timeline(blocks)` (lengthen by whole walk blocks), `rig.SPIN_AWAY` / `rig.SPIN_BACK` (tuned spin key tables).

## What it can't do (yet)
- Arms above the head, legs spread apart, jumps with both feet off the ground, sitting, lying down, a second person, or non-human subjects.
- Facial features. That's deliberate: eyes looked uncanny at this size, and the user asked for them to be removed.

When a request needs one of these, tell the user plainly. Then choose one of two routes:
1. Extend the rig in a copy: add a `Pose` field and use it in `girl()` where the limb capsules are built (arm and leg endpoints are computed there).
2. Lean on hand-drawn (B) for that request, and present the rig version as the closest approximation in the A/B.

Don't quietly substitute a different motion. "Jumping jacks" rendered as arm waves, without saying so, is the failure to avoid.

## Loop rules (`check_loop`, enforced by `pose2ascii.py`)
`pose_fn(nf)` must match `pose_fn(0)` in:
- every rest-pose field;
- yaw modulo 360°, so spins must total whole turns;
- gait phase modulo 2π;
- jig phase;
- `t` modulo nf;
- `travel` modulo 2.8 m (two strides, the lamp spacing);
- the rendered characters.

`Pose.loop` must equal `nf`; `make_pose_fn` sets it. With `--no-scene` there is no road, but keep the travel rule anyway so the same timeline works with the scene on.

## Look and size
173 × 120 cells, 5 px each, so 865 × 600 px. A 90-frame scene-on GIF is about 8 MB. For READMEs, use `--step 2`, `--no-scene` or `--max-mb 10`. `examples/cycle.py` chains several timelines into one seamless banner; its joins are asserted to be character-identical.
