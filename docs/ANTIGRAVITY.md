# ANTIGRAVITY — Operating Instructions for This Repo

Read this first, before touching any code. This file governs *how* you work
in this repo, not *what* the product is (see PRD.md for that).

## 1. Build Workflow — Non-Negotiable

Follow `BUILD-ORDER.md` strictly, unit by unit:

1. Build **one unit**.
2. **Test that unit in isolation** against the sample data specified for it.
3. Only after it passes its stated exit criteria, move to the next unit.
4. Never build two units in parallel inside a single working session unless
   explicitly told to.

Do not skip ahead "because it's easy" or merge multiple units into one
commit — this defeats the entire point of the incremental workflow, which
exists specifically to keep this project error-free under time pressure.

## 2. The Data Contract Is Law

Everything reads and writes `shared/schemas/` (see `ARCHITECTURE.md` §2). If
you think a schema needs to change after Unit 0 is complete:
- Stop.
- Flag it explicitly to the user before changing it.
- Never silently invent a new field shape "just for this module."

## 3. The Unit 6 Gate (Dashboard)

When `BUILD-ORDER.md` reaches **Unit 6**, you must stop and ask the user:

> "Unit 6 (Dashboard) is next. Should I build this now, or is this the part
> going to your teammates? If you say no, I'll mark it PENDING and move to
> Unit 7, picking it back up only when you hand me their finished work."

- If the user says **build it** → follow `DESIGN.md` against the mock JSON
  it specifies.
- If the user says **no / hold it** → mark Unit 6 as `PENDING — externally
  built` in your working notes, skip to Unit 7, and do not write any
  dashboard code.
- **Do not proceed with Unit 6 without asking, even if it seems like the
  natural next step.**

## 4. Handling Teammate-Delivered Work

When the user later provides code/files for a `PENDING — externally built`
unit (most likely Unit 6):

1. Run the full **Integration Evaluation Protocol** from `BUILD-ORDER.md`
   ("Integration Evaluation Protocol" section) before merging anything.
2. Report back clearly: what passes, what fails, what doesn't match the
   schema, what's missing from the `DESIGN.md` feature checklist.
3. Only merge after issues are fixed or the user explicitly accepts the gaps.
4. Never silently patch around a schema mismatch by changing `shared/schemas/`
   to fit the teammate's code — flag it instead; the contract is law (see §2).

## 5. Never Touch `ground_truth.json`

No pipeline code — extraction, matching, comparison, escalation, or
otherwise — may read, import, or reference
`local-server/data-advanced/ground_truth.json`. The only legitimate access
path is running `local-server/server/score_cli.py` as an external scoring
step. If you ever find yourself about to write code that opens this file
directly, stop and flag it instead.

## 6. Error Handling Philosophy

A failure on one email must never crash the whole batch. Every unit from
Unit 5 onward should catch its own failures and route to `NEEDS_REVIEW`
rather than raising an unhandled exception. If you hit a genuinely
unrecoverable error while building, report it plainly rather than papering
over it with a broad `except: pass`.

## 7. When In Doubt

- If a request conflicts with the Unit 6 gate or the data-contract freeze,
  say so and ask before proceeding — don't guess.
- If you're unsure which unit a task belongs to, check `BUILD-ORDER.md`
  before starting; don't invent a new unit ad hoc.
- Log the score after every unit from Unit 5 onward (`score_cli.py` output)
  so the team has a running accuracy trail.
