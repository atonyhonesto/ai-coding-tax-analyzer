<div align="center">

# 🧾 ai-coding-tax-analyzer

**AI tools make code arrive faster. This measures what it costs afterwards, straight from git history.**

[![ci](https://github.com/atonyhonesto/ai-coding-tax-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/atonyhonesto/ai-coding-tax-analyzer/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-git_only-2ea44f)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Companion code for my LinkedIn article<br>
**[The AI Coding Tax: Stop AI Tools From Quietly Accumulating Technical Debt →](https://www.linkedin.com/pulse/ai-coding-tax-stop-tools-from-quietly-accumulating-debt-tony-honesto-ikagc/)**

</div>

---

## The idea in one paragraph

Velocity is easy to see; its cost isn't. Code that lands quickly and is rewritten two weeks later, helpers pasted into five files instead of shared, and complex files that change every sprint are all debt, and none of it shows up in a story-point chart. `codetax` reads `git log` and reports four signals: **rework** (lines deleted soon after they were added), split by whether the commit was **AI-assisted**; **duplication** (repeated blocks across files); and **hotspots** (churn × complexity), the files where debt costs the most.

## Run it on your own repository

```bash
pip install git+https://github.com/atonyhonesto/ai-coding-tax-analyzer
codetax /path/to/repo                   # full history
codetax /path/to/repo --since 6.months  # recent work only
codetax . --window 14 --json            # stricter rework window, machine-readable
```

No dependencies beyond Python 3.10+ and `git`. Nothing leaves your machine.

## Or see it on a sample history

`python demo.py` builds a small repository with ten weeks of scripted commits (some with a `Co-Authored-By` AI trailer, some reworked a week later, one helper pasted into several files) and analyses it. Real output:

```text
Sample repository: 10 weeks of scripted history

30 commits, 33% marked AI-assisted

Rework within 21 days of landing (lines later deleted / lines added)
  ai-assisted   54.9%   (10 commits, 532 lines added)
  other         14.8%   (20 commits, 155 lines added)
  -> AI-assisted code is reworked 3.7x as often

Duplicated code: 8.5% of lines sit in blocks repeated elsewhere
  api/export.py  <->  api/routes.py   (2 shared blocks)
  api/export.py  <->  reports/standings.py   (2 shared blocks)
  api/export.py  <->  timing/scoring.py   (2 shared blocks)
  api/routes.py  <->  reports/standings.py   (2 shared blocks)
  api/routes.py  <->  timing/scoring.py   (2 shared blocks)

Hotspots (churn x complexity): pay down debt here first
  api/export.py                      churn   352  complexity  76  score  26,752
  timing/scoring.py                  churn   204  complexity  48  score   9,792
  timing/ingest.py                   churn   172  complexity  37  score   6,364
  reports/standings.py               churn   123  complexity  32  score   3,936
  api/routes.py                      churn   101  complexity  24  score   2,424
```

## How each number is computed

| Signal | How | Why it matters |
|---|---|---|
| **AI-assisted** | Commit message has a `Co-Authored-By:` trailer for Claude, Copilot, Cursor, Codex, Gemini and similar, `Generated with …`, or `AI-assisted: yes` | Splits the rest of the metrics so the two kinds of work can be compared |
| **Rework rate** | For every commit that adds lines to a file, lines deleted from that file by later commits within the window (default 21 days), capped at what was added | Code rewritten soon after landing was paid for twice |
| **Duplication** | Share of code lines inside any 6-line block (whitespace-normalised) that also appears elsewhere | Assistants paste rather than refactor; each copy is a future bug fix done N times |
| **Hotspots** | Total churn × a keyword-based cyclomatic complexity of the current file | Debt in a file nobody touches is cheap; debt in a complex file that changes weekly is not |

## Reading the results honestly

- **It's a signal, not a verdict.** A high rework rate can mean fast iteration that converged, not waste. Look at the files behind the number.
- **Tagging matters.** Only commits that say they're AI-assisted are counted as such. Teams that want this data should keep the trailers that tools add (Claude Code adds one by default) or use an `AI-assisted: yes` trailer.
- **Thresholds are yours.** Watch the trend per sprint rather than one absolute number.

## Project layout

```text
codetax/
  history.py     git log --numstat parsing, AI trailer detection
  metrics.py     rework, duplication, complexity and hotspots
  __main__.py    CLI and report
sample_repo.py   builds the scripted sample repository
demo.py          builds it and prints the report
tests/           unit and end-to-end tests
```

---

<sub>Built by **Tony Honesto**, cloud & integration engineer. More articles and companion code: [github.com/atonyhonesto](https://github.com/atonyhonesto) · [article-labs](https://github.com/atonyhonesto/article-labs) · [LinkedIn](https://www.linkedin.com/in/tony-honesto-4195023)</sub>
