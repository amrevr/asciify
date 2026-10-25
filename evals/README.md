# Evals

Two sets of test cases, in the same folder format (`prompt.md`, `case.yaml`, `graders/`, optional `files/`). That's the layout `claude plugin eval` and the skill-creator workflow read.

## Baseline (shipped here)

Rules that hold for anyone using the skill, kept small on purpose:

| Case | Rule it checks |
|---|---|
| `video-clip-to-readme-gif` | Export meets its target's limits (GIF ≤ 10 MB, right duration), the subject reads clearly, and the loop seam is fixed or reported |
| `web-player-reduced-motion` | Web output is real text, follows reduced motion and has the correct character aspect |
| `douyin-link-needs-file` | No output invented from footage that couldn't be fetched; the stated cause matches what actually happened |
| `busy-background-asks-first` | Cheap isolation runs before the 170 MB model download, which needs a yes first |
| `description-human-action` | A described motion produces two blind A/B candidates, both looping |
| `description-nonhuman` | When the rig doesn't fit the subject, still two candidates (two hand-drawn styles) |

The input clips are synthetic, so the repo carries no third-party footage. Rebuild them with `uv run evals/make_fixtures.py`. None of the cases needs the network. `trigger-queries.json` is a separate set of should/shouldn't-trigger prompts for tuning the skill's description.

## Usage cases (grown per user)

Everything specific to how one person uses the skill comes from real sessions. When a user critiques, approves or picks an output, or the skill hits a failure, the agent runs `scripts/record_eval.py` (see SKILL.md §6). The case lands in `~/.claude/skill-evals/ascii-animation/<name>/` (or `$ASCII_ANIMATION_EVALS`), along with the inputs, the rejected and approved outputs as references, and an `index.jsonl` log. `record_eval.py --list` shows them.

Over time, that store holds the user's actual standards: "arms close to the body during a walk", "no face features", "fits in a README". A new version of the skill has to keep passing them.

## Graders

- **Measurable things are checked by code.** A grader that reads "Running check_output.py on … reports passed: true" means: run `uv run scripts/check_output.py <file> <args>` and use its JSON verdict. It covers size, frame count, seam, equal rows, single colour, coverage and the reduced-motion handler.
- **Everything else is a yes/no statement** an LLM judge answers from the transcript, the files and the contact sheet. There are no 1–10 scores: a pass/fail per criterion is easier to calibrate and to act on.
- **A grader must be able to fail.** When adding one, check that it fails on an empty output folder and on a run that ignores the rule. Iteration 1 found several graders that passed a run which did nothing.

## Running

- **skill-creator** ("run the ascii-animation evals"): spawns runs with and without the skill, grades them and opens the review viewer. Point it at `evals/` for the baseline, at the usage store for usage cases, or at both.
- **CLI** (Claude Code ≥ 2.1.269), from the skill directory: `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`. For usage cases, run it against a skill copy whose `evals/` also holds the usage store's cases. These are real, billed model runs.
- Run each case about 3 times per configuration. With one run, the spread is too wide to tell a real improvement from noise.
