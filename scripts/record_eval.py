# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""Record a usage-born eval case (critique / approval / A-B pick / failure) in the skill-creator layout.
uv run scripts/record_eval.py --name kebab-name --source critique|approval|ab-pick|failure --prompt "request" [--input PATH ...]
  [--expect "assertion" ...] [--check "OUTFILE_GLOB: --max-mb 10 --rows-equal" ...] [--good PATH] [--bad PATH] [--note "verbatim"] [--store DIR]
uv run scripts/record_eval.py --list
Store: $ASCII_ANIMATION_EVALS or ~/.claude/skill-evals/ascii-animation. Re-recording a name appends graders/refs; nothing is deleted."""
import argparse, datetime, json, os, re, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageSequence

BAD = {"results", "mocks", "node_modules", "files", "true", "false", "null"}
BIG = 25e6
SETTINGS = "---\ntags: [ascii-animation, usage, %s]\nmax_turns: 40\ntimeout_seconds: 1200\nallowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, AskUserQuestion]\n---\n\n"

def store_dir(s): return Path(s or os.environ.get("ASCII_ANIMATION_EVALS") or "~/.claude/skill-evals/ascii-animation").expanduser()

def sheet(gif, out, n=8):
    fr = [f.convert("RGB") for f in ImageSequence.Iterator(Image.open(gif))]
    ks = np.linspace(0, len(fr), min(n, len(fr)), endpoint=False).astype(int)
    nc, (w, h) = min(4, len(ks)), fr[0].size
    s = Image.new("RGB", (w * nc, h * -(-len(ks) // nc)))
    for i, k in enumerate(ks): s.paste(fr[k], (i % nc * w, i // nc * h))
    s.save(out)

def slug(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40]

def grader(d, text):
    gd = d / "graders"; gd.mkdir(exist_ok=True)
    k = len(list(gd.glob("[0-9][0-9]-*.md"))) + 1
    (gd / f"{k:02d}-{slug(text) or 'check'}.md").write_text(f"---\ntype: llm\nfocus: trace\nweight: 1\n---\n\n{text}\n")

def ref(d, path, kind):
    r = d / "refs"; r.mkdir(exist_ok=True)
    p = Path(path)
    dst = r / f"{kind}{p.suffix}"
    k = 1
    while dst.exists(): k += 1; dst = r / f"{kind}-{k}{p.suffix}"
    shutil.copy(p, dst)
    if p.suffix.lower() == ".gif": sheet(p, dst.with_suffix(".png"))

def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--name"); a.add_argument("--source", choices=["critique", "approval", "ab-pick", "failure"]); a.add_argument("--prompt")
    a.add_argument("--input", action="append", default=[]); a.add_argument("--expect", action="append", default=[]); a.add_argument("--check", action="append", default=[])
    a.add_argument("--good"); a.add_argument("--bad"); a.add_argument("--note", default=""); a.add_argument("--store"); a.add_argument("--list", action="store_true")
    a = a.parse_args(argv)
    st = store_dir(a.store)
    if a.list:
        for l in (st / "index.jsonl").read_text().splitlines() if (st / "index.jsonl").exists() else []:
            e = json.loads(l); print(f"{e['name']:32} {e['source']:9} {e['created']}  {(e['note'] or e['prompt'])[:60]}")
        return
    if not (a.name and a.source and a.prompt): sys.exit("--name, --source and --prompt are required")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", a.name) or a.name in BAD: sys.exit(f"bad --name {a.name!r}: lowercase-hyphen, not one of {sorted(BAD)}")
    d = st / a.name
    new = not d.exists()
    d.mkdir(parents=True, exist_ok=True)
    if new:
        names = [Path(i).name for i in a.input]
        (d / "prompt.md").write_text(SETTINGS % a.source + a.prompt + (f"\nInput files: {', '.join(names)}\n" if names else "\n"))
        out = "\n".join(f"- {e}" for e in a.expect) or "The response completes the task the prompt asks for."
        if a.note: out += "\n\nUser feedback (verbatim): " + a.note
        y = f'schema_version: "1.1"\nname: {a.name}\nexpected_outcome: |\n' + "".join(f"  {l}\n" for l in out.split("\n"))
        if a.input: y += "context:\n  scaffold_script: place-files.sh\n"
        (d / "case.yaml").write_text(y)
        if a.input:
            (d / "files").mkdir()
            sh = '#!/usr/bin/env bash\nset -eu\ncp -R "$(dirname "$0")/files/." .\n'
            for i in a.input:
                p = Path(i).resolve()
                if p.stat().st_size > BIG:
                    print(f"warning: {p} > 25 MB, not copied; place-files.sh links it", file=sys.stderr)
                    sh += f'cp {json.dumps(str(p))} .\n'
                else: shutil.copy(p, d / "files" / p.name)
            (d / "place-files.sh").write_text(sh); (d / "place-files.sh").chmod(0o755)
    for e in a.expect: grader(d, e)
    for c in a.check:
        g, _, args = c.partition(":")
        grader(d, f"Running check_output.py on the output file matching {g.strip()} with {args.strip() or 'no extra flags'} reports passed: true")
    if not list((d / "graders").glob("*.md") if (d / "graders").exists() else []): grader(d, "The result matches this description: " + (a.note or a.prompt))
    if a.good: ref(d, a.good, "good")
    if a.bad: ref(d, a.bad, "bad")
    # a check that can't tell the approved output from the rejected one measures nothing: say so now, not after a wasted eval run
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import check_output, contextlib, io
    for c in a.check:
        args = c.partition(":")[2].split()
        for path, want in ((a.good, True), (a.bad, False)):
            if not path: continue
            with contextlib.redirect_stdout(io.StringIO()): got = check_output.check([path, *args])
            if got != want: print(f"warning: check '{c}' {'fails' if want else 'passes'} on the {'good' if want else 'bad'} ref; it may not measure this critique, consider --expect", file=sys.stderr)
    with open(st / "index.jsonl", "a") as f:
        f.write(json.dumps({"name": a.name, "source": a.source, "created": datetime.date.today().isoformat(), "note": a.note, "prompt": a.prompt}) + "\n")
    print(d)

if __name__ == "__main__": main()
