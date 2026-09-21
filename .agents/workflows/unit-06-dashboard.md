---
name: unit-06-dashboard
description: Dashboard build (#6) — GATED, requires explicit user go-ahead before starting
---

## ⚠️ Stop Before Starting

Before writing any code for this unit, ask the user exactly this:

> "Unit 6 (Dashboard) is next. Should I build this now, or is this the part
> going to your teammates? If you say no, I'll mark it PENDING and move to
> Unit 7, and pick it back up only when you hand me their finished work for
> integration."

Do not proceed with this unit until the user responds.

## If the User Says "Build It Now"
Follow `docs/DESIGN.md` in full, building against the mock JSON it specifies
in §3 (or `mock_dashboard_data.json` if present in the repo).

## If the User Says "No / Hold It"
1. Mark this unit's status as `PENDING — externally built` in your working
   notes.
2. Skip directly to `unit-07-orchestration-assembly.md`.
3. Do not write any dashboard code.
4. When the user later hands over teammate-built code for this unit, run the
   **Integration Evaluation Protocol** (below) before merging, regardless of
   how much time has passed.

## Integration Evaluation Protocol (run when teammate code arrives)
1. **Schema check** — does every input/output match `shared/schemas/`?
   Reject/flag anything that invented its own shape.
2. **Smoke test** — does it run against the mock JSON and, if ready, real
   pipeline output?
3. **Breakage check** — run the full pipeline test suite (Units 1–11) after
   merging; confirm nothing that worked before now fails.
4. **Feature checklist** — cross-check against `docs/DESIGN.md` §2's view
   list; flag anything missing or partially built.
5. **Report back** — a short pass/fail summary per feature, with specific
   fixes needed if something doesn't align, before considering it merged.

## Next
Move to `unit-07-orchestration-assembly.md` (this happens regardless of the
gate decision above).
