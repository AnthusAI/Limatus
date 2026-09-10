# Agent copy-edit: scan, judge, and compare

Kanbus initiative: `LIM-df9d58`.

Successor to the shipped diagnose → steer → options → weighted verify loop (`LIM-9d14e6`).

## Commands (target)

- `limatus scan` — draft + style profile → findings (always-lane ∪ optional OpenAI judge). `diagnose` may remain an alias.
- `limatus compare` — rank 2+ candidates or original vs working copy. Replaces weighted `verify` as the agent-facing better/worse tool.
- `limatus options` — unchanged role: 2–3 patches for findings marked rewrite.

## Lanes

| Lane | Needs network | Role |
|------|----------------|------|
| Always | No | Profile heuristics; reproducible |
| Judge | OpenAI + key | Terra default; adds findings + rubric; never drops always-lane |
| Compare | Optional judge | Rank all candidates; hard-fail unsupported-claim increases |

Prioritize (skip/rewrite/…) is the **agent or human**, recorded explicitly.

## Epics

See children of `LIM-df9d58` on the board.
