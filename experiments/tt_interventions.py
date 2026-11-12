"""Count owner interventions in the terminal-task-tracker transcripts (the counter now lives in factory.retro).

Question: where did the owner have to step in while building terminal-task-tracker? Answer (run 2026-11-12, see
docs/factory-analysis.md): 311 typed messages; biggest buckets git/PR plumbing (91), decisions (72), visual review
(65), echoing the agent's skipped list (48), pasted errors (43), relaying handoffs (41). Counts are +/-10 %.

Usage: python3 -I experiments/tt_interventions.py [TRANSCRIPT_DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from factory.retro import count, transcript_dir  # noqa: E402

default = transcript_dir(Path.home() / "Programming/My_Projects/terminal-task-tracker")
total, counts = count(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
print(f"typed messages: {total}")
for k, n in counts.most_common():
    print(f"{n:4d}  {k}")
