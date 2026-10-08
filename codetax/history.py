"""Read commit history with `git log --numstat`. No dependencies beyond git itself."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Trailers and markers that AI coding tools leave in commit messages.
AI_MARKERS = re.compile(
    r"co-authored-by:.*\b(claude|copilot|cursor|codeium|windsurf|aider|devin|codex|gemini|chatgpt)\b"
    r"|generated (with|by) .*(claude|copilot|cursor|chatgpt|codex)"
    r"|^\s*ai-assisted:\s*(yes|true)",
    re.IGNORECASE | re.MULTILINE,
)

SEP = "\x1e"          # record separator between commits


@dataclass
class Change:
    path: str
    added: int
    deleted: int


@dataclass
class Commit:
    sha: str
    when: datetime
    author: str
    message: str
    changes: list[Change] = field(default_factory=list)

    @property
    def ai_assisted(self) -> bool:
        return bool(AI_MARKERS.search(self.message))

    @property
    def churn(self) -> int:
        return sum(c.added + c.deleted for c in self.changes)


def read(repo: str, since: str | None = None) -> list[Commit]:
    """Oldest first. Merge commits are skipped: their diffs repeat work already counted."""
    cmd = ["git", "-C", repo, "log", "--no-merges", "--reverse", "--numstat", "--no-renames",
           f"--format={SEP}%H%x1f%aI%x1f%an%x1f%B%x1f"]
    if since:
        cmd.append(f"--since={since}")
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    commits = []
    for block in out.split(SEP)[1:]:
        sha, when, author, message, rest = block.split("\x1f", 4)
        c = Commit(sha, datetime.fromisoformat(when).astimezone(timezone.utc), author, message.strip())
        for line in rest.strip().splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[0] != "-":          # "-" marks binary files
                c.changes.append(Change(parts[2], int(parts[0]), int(parts[1])))
        commits.append(c)
    return commits


def tracked_files(repo: str) -> list[str]:
    out = subprocess.run(["git", "-C", repo, "ls-files"], capture_output=True, text=True, check=True).stdout
    return out.splitlines()
