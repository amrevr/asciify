# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Blind A/B page: two renders side by side in random order; the mapping goes to stdout only."""
import argparse, base64, json, mimetypes, os, random

def src(p, out_dir):
    if os.path.getsize(p) < 15e6:
        return f"data:{mimetypes.guess_type(p)[0] or 'application/octet-stream'};base64," + base64.b64encode(open(p, "rb").read()).decode()
    return os.path.relpath(p, out_dir)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--labels"); ap.add_argument("--seed", type=int)
    a = ap.parse_args(argv)
    items = list(zip(a.labels.split(",") if a.labels else [a.a, a.b], [a.a, a.b]))
    random.Random(a.seed).shuffle(items)
    out_dir = os.path.dirname(os.path.abspath(a.out))
    cells = ""
    for name, (label, p) in zip("AB", items):
        s, ext = src(p, out_dir), os.path.splitext(p)[1].lower()
        tag = {".mp4": f'<video src="{s}" autoplay loop muted playsinline></video>', ".html": f'<iframe src="{s}"></iframe>'}.get(ext, f'<img src="{s}">')
        cells += f"<figure><figcaption>{name}</figcaption>{tag}</figure>"
    open(a.out, "w").write(f"""<!doctype html><meta charset=utf-8><title>A/B</title><style>body{{margin:0;background:#120e18;color:#b9a3c4;font:16px monospace;display:flex;gap:16px;padding:16px;flex-wrap:wrap;justify-content:center}}
figure{{margin:0;text-align:center}}img,video,iframe{{width:min(46vw,640px);height:min(46vw,640px);object-fit:contain;border:0;background:#120e18}}</style>{cells}""")
    print(json.dumps({n: l for n, (l, _) in zip("AB", items)}))

if __name__ == "__main__": main()
