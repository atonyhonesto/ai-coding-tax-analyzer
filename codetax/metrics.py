"""The four signals the article argues for: churn, rework, duplication and hotspots."""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .history import Commit

CODE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".cs", ".java", ".go", ".rb", ".php", ".kt", ".swift", ".rs", ".sql"}
BRANCH = re.compile(r"\b(if|elif|else if|for|foreach|while|case|catch|except|and|or|&&|\|\|)\b|\?")


@dataclass
class GroupStats:
    commits: int = 0
    lines_added: int = 0
    reworked_lines: int = 0          # lines deleted from a file within the window after this group added to it

    @property
    def rework_rate(self) -> float:
        return self.reworked_lines / self.lines_added if self.lines_added else 0.0


def rework(commits: list[Commit], window_days: int = 21) -> dict[str, GroupStats]:
    """Code that has to be rewritten soon after it lands is the clearest cost of moving fast.

    For each commit that adds lines to a file, count the lines deleted from that file by
    *later* commits inside the window, capped at what was added, and charge them to the
    adding commit's group (AI-assisted or not).
    """
    window = timedelta(days=window_days)
    groups = {"ai-assisted": GroupStats(), "other": GroupStats()}
    by_file: dict[str, list[tuple[Commit, int, int]]] = defaultdict(list)
    for c in commits:
        g = groups["ai-assisted" if c.ai_assisted else "other"]
        g.commits += 1
        for ch in c.changes:
            by_file[ch.path].append((c, ch.added, ch.deleted))
            g.lines_added += ch.added
    for events in by_file.values():
        for i, (c, added, _) in enumerate(events):
            if not added:
                continue
            later = sum(d for c2, _, d in events[i + 1:] if c2.when - c.when <= window)
            groups["ai-assisted" if c.ai_assisted else "other"].reworked_lines += min(added, later)
    return groups


def churn_by_file(commits: list[Commit]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for c in commits:
        for ch in c.changes:
            out[ch.path] += ch.added + ch.deleted
    return dict(out)


def complexity(text: str) -> int:
    """Rough cyclomatic complexity: 1 + branch keywords. Good enough to rank files."""
    return 1 + sum(len(BRANCH.findall(line)) for line in text.splitlines()
                   if not line.strip().startswith(("#", "//", "*")))


def hotspots(repo: str, commits: list[Commit], files: list[str], top: int = 5) -> list[tuple[str, int, int, int]]:
    """Files that change a lot AND are complex: where debt costs the most (churn x complexity)."""
    churn = churn_by_file(commits)
    rows = []
    for f in files:
        p = Path(repo) / f
        if p.suffix in CODE_SUFFIXES and p.exists() and f in churn:
            cx = complexity(p.read_text(errors="replace"))
            rows.append((f, churn[f], cx, churn[f] * cx))
    return sorted(rows, key=lambda r: r[3], reverse=True)[:top]


def normalise(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def duplication(repo: str, files: list[str], window: int = 6) -> tuple[float, list[tuple[str, str, int]]]:
    """Share of code lines that sit inside a block of `window` lines repeated elsewhere.

    Assistants happily paste a near-identical helper into each file that needs it;
    this finds those blocks by hashing every run of `window` normalised, non-blank lines.
    """
    seen: dict[str, list[tuple[str, int]]] = defaultdict(list)
    lines_per_file: dict[str, list[str]] = {}
    for f in files:
        p = Path(repo) / f
        if p.suffix not in CODE_SUFFIXES or not p.exists():
            continue
        lines = [normalise(l) for l in p.read_text(errors="replace").splitlines()]
        lines = [l for l in lines if l and l not in ("}", "{", ")", "]", "pass")]
        lines_per_file[f] = lines
        for i in range(len(lines) - window + 1):
            h = hashlib.sha1("\n".join(lines[i:i + window]).encode()).hexdigest()
            seen[h].append((f, i))
    dup_lines: set[tuple[str, int]] = set()
    pairs: dict[tuple[str, str], int] = defaultdict(int)
    for locs in seen.values():
        if len(locs) > 1:
            for f, i in locs:
                dup_lines.update((f, i + k) for k in range(window))
            files_here = sorted({f for f, _ in locs})
            for a in range(len(files_here)):
                for b in range(a + 1, len(files_here)):
                    pairs[(files_here[a], files_here[b])] += 1
    total = sum(len(v) for v in lines_per_file.values())
    top = sorted(((a, b, n) for (a, b), n in pairs.items()), key=lambda r: r[2], reverse=True)[:5]
    return (len(dup_lines) / total if total else 0.0), top
