"""python -m codetax [repo] [--since 6.months] [--window 21] [--json]"""
from __future__ import annotations

import argparse
import json

from . import history, metrics


def analyse(repo: str, since: str | None = None, window: int = 21) -> dict:
    commits = history.read(repo, since)
    files = history.tracked_files(repo)
    groups = metrics.rework(commits, window)
    dup, dup_pairs = metrics.duplication(repo, files)
    return {
        "commits": len(commits),
        "ai_assisted_share": groups["ai-assisted"].commits / len(commits) if commits else 0.0,
        "rework": {k: {"commits": g.commits, "lines_added": g.lines_added, "rework_rate": round(g.rework_rate, 3)}
                   for k, g in groups.items()},
        "duplication": round(dup, 3),
        "duplicate_pairs": dup_pairs,
        "hotspots": metrics.hotspots(repo, commits, files),
    }


def report(r: dict, window: int) -> str:
    out = [f"{r['commits']} commits, {r['ai_assisted_share']:.0%} marked AI-assisted", "",
           f"Rework within {window} days of landing (lines later deleted / lines added)"]
    for k, g in r["rework"].items():
        out.append(f"  {k:<12} {g['rework_rate']:>6.1%}   ({g['commits']} commits, {g['lines_added']:,} lines added)")
    ai, other = r["rework"]["ai-assisted"]["rework_rate"], r["rework"]["other"]["rework_rate"]
    if ai and other:
        out.append(f"  -> AI-assisted code is reworked {ai / other:.1f}x as often")
    out += ["", f"Duplicated code: {r['duplication']:.1%} of lines sit in blocks repeated elsewhere"]
    out += [f"  {a}  <->  {b}   ({n} shared blocks)" for a, b, n in r["duplicate_pairs"]]
    out += ["", "Hotspots (churn x complexity): pay down debt here first"]
    out += [f"  {f:<34} churn {ch:>5,}  complexity {cx:>3}  score {s:>7,}" for f, ch, cx, s in r["hotspots"]]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(prog="codetax", description=__doc__)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--since", help="git date, e.g. 6.months or 2026-01-01")
    ap.add_argument("--window", type=int, default=21, help="rework window in days (default 21)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = analyse(a.repo, a.since, a.window)
    print(json.dumps(r, indent=2) if a.json else report(r, a.window))


if __name__ == "__main__":
    main()
