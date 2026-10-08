"""Build a small git repository with a scripted 10-week history to analyse.

Human commits add code that mostly stays. AI-assisted commits (with a Co-Authored-By
trailer) land faster and bigger, paste the same helper into several files, and get
partly rewritten within a couple of weeks: the pattern the article describes.
"""
from __future__ import annotations

import os
import random
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HELPER = '''
def parse_lap_time(value):
    if value is None or value == "":
        return None
    if ":" in value:
        minutes, seconds = value.split(":")
        return int(minutes) * 60 + float(seconds)
    return float(value)
'''


def body(name: str, n: int, rng: random.Random, branches: int = 1) -> str:
    lines = [f"def {name}_{i}(data):" + "".join(
        f"\n    if data.get('k{j}') and data['k{j}'] > {rng.randint(1, 9)}:\n        data['k{j}'] -= 1"
        for j in range(branches)) + f"\n    return data.get('v{i}', {rng.randint(0, 99)})\n" for i in range(n)]
    return "\n\n".join(lines)


def git(repo: Path, *args: str, when: datetime | None = None) -> None:
    env = dict(os.environ, GIT_AUTHOR_NAME="Dev", GIT_AUTHOR_EMAIL="dev@example.com",
               GIT_COMMITTER_NAME="Dev", GIT_COMMITTER_EMAIL="dev@example.com")
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when.isoformat()
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def build(target: str | None = None, seed: int = 3) -> str:
    rng = random.Random(seed)
    repo = Path(target or tempfile.mkdtemp(prefix="codetax-sample-"))
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    t = datetime(2026, 6, 1, 9, tzinfo=timezone.utc)
    files = {"timing/ingest.py": "", "timing/scoring.py": "", "api/routes.py": "", "api/export.py": "",
             "reports/standings.py": ""}

    def commit(msg: str, ai: bool, when: datetime):
        for f, text in files.items():
            p = repo / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        git(repo, "add", "-A")
        trailer = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>" if ai else ""
        git(repo, "commit", "-q", "-m", msg + trailer, when=when)

    for week in range(10):
        day = t + timedelta(weeks=week)
        # human work: modest, stable additions
        f = rng.choice(list(files))
        files[f] += "\n\n" + body(f"w{week}h", 2, rng, branches=1)
        commit(f"Add week {week} rules to {f}", False, day)
        # AI-assisted work: bigger drops, plus the same helper pasted into whichever file needs it
        f = rng.choice(list(files))
        before = files[f]
        generated = body(f"w{week}a", 5, rng, branches=3)
        helper = HELPER if week % 2 == 0 and "def parse_lap_time" not in before else ""
        files[f] = before + "\n\n" + generated + helper
        commit(f"Generate week {week} handlers for {f}", True, day + timedelta(days=1))
        # rework a week later: three of the five generated handlers are replaced
        kept = "\n\n".join(generated.split("\n\n")[:2])
        files[f] = before + "\n\n" + kept + "\n\n" + body(f"w{week}fix", 1, rng, branches=2) + helper
        commit(f"Fix edge cases in {f}", False, day + timedelta(days=8))
    return str(repo)


if __name__ == "__main__":
    print(build())
