# Manifest AI — Project Identity

This is the Manifest AI hackathon project (Averis x Monash 2026): an AI
system that reads a shipping operations inbox, classifies each email, and
for document-comparison requests, checks a draft Bill of Lading (BL) against
its Shipping Instruction (SI) across 7 required fields — escalating to a
human whenever it cannot decide confidently.

## Read These First, In Order

1. `docs/ANTIGRAVITY.md` — your operating rules (READ FIRST, always)
2. `docs/PRD.md`            — what we're building, why, and the exact
   required output schema
3. `docs/ARCHITECTURE.md`   — the data contract (frozen after Unit 0 — do
   not deviate from it)
4. `docs/BUILD-ORDER.md`    — human-readable reference for the full
   unit-by-unit build sequence
5. `docs/TECHSTACK.md`      — approved libraries/cloud services
6. `docs/SETUP.md`          — environment setup
7. `docs/FOLDER-MAP.md`     — what goes where in this repo

## How to Build

For unit-by-unit build steps, follow `.agents/workflows/unit-*.md` in
order — these are your primary script, and each one states its own goal,
prerequisite, steps, test, and exit criteria before you move to the next.
`docs/BUILD-ORDER.md` is the human-readable reference version of the same
content — consult it for the bigger picture, but follow the workflow files
as the actual script to execute.

Do not skip ahead to a later unit "because it's easy," and do not build two
units in parallel inside a single working session unless explicitly told to.

## The Unit 6 Gate

`.agents/workflows/unit-06-dashboard.md` is gated. When you reach it, you
must stop and ask the user whether to build the dashboard now or hold it for
teammates — follow that file's instructions exactly. Do not proceed past the
gate without an explicit answer, even if building it seems like the natural
next step.

## Hard Rules (see docs/ANTIGRAVITY.md for full detail)

- Never read, import, or reference
  `local-server/data-advanced/ground_truth.json` from any pipeline code.
  The only legitimate access path is `local-server/server/score_cli.py`.
- Never change `shared/schemas/` silently after Unit 0 — flag it to the user
  first.
- A failure on one email must never crash the whole batch — route to
  `NEEDS_REVIEW` instead of raising unhandled exceptions.
- When teammate-built code arrives for a unit marked
  `PENDING — externally built`, run the Integration Evaluation Protocol
  (in `.agents/workflows/unit-06-dashboard.md`) before merging it in.

## When In Doubt

If a request conflicts with the Unit 6 gate or the data-contract freeze, say
so and ask before proceeding. If unsure which unit a task belongs to, check
`.agents/workflows/` before starting — don't invent a new unit ad hoc.