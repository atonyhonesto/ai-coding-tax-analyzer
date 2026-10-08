"""Build the scripted sample repository and analyse it."""
from codetax.__main__ import analyse, report
from sample_repo import build

repo = build()
print(f"Sample repository: 10 weeks of scripted history\n")
print(report(analyse(repo), 21))
