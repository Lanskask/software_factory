# Review-skill benchmark (2026-11-14)

Question: which available review skill finds the most real defects with the least noise, when run by a clean reviewer
that sees only the diff? Answer: `ponytail:ponytail-review` (blind letter B) ranked first; a plain no-skill prompt (A)
was second; `pr-agent-review` (E) had perfect precision but missed 1 of 6 defects. See `judge-opus.md`.

- Inputs: `diffs/` (1 seeded diff with 4 planted defects, 2 real Factory PRs with 1 confirmed defect each),
  `ground-truth.md` (hidden from reviewers).
- Runs: 6 methods x 3 diffs = 18 fresh Sonnet subagents, one run each; outputs in `reports/`.
- Judge: one Opus agent, blind (letters from `blind-mapping.json`), analysis in `judge-opus.md`.
- Decision: use `ponytail:ponytail-review` for Factory PR reviews; patch it with the judge's steps 4, 5, 8 (a failing
  test per bug, shown arithmetic, self-verification). A combined skill is not built: B already has 6/6 recall, and the
  sample (3 diffs, 6 defects, one run each) cannot show a combined prompt is better.
- Limits: Sonnet only, Python only, diff-only context, `pr-agent` spends hidden `claude -p` tokens not counted.
