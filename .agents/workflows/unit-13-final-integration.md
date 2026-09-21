---
name: unit-13-final-integration
description: Final full-dataset run, deploy, dashboard merge, and submission prep
---

## Goal
Bring everything together into a submittable, deployed, demo-ready state.

## Prerequisite
`unit-12-failure-simulator.md` complete (or skipped if time-boxed).

## Steps
1. Run the full pipeline against `local-server/data-advanced/`. Final
   `score_cli.py` check — record the score.
2. Deploy to Cloud Run.
3. If the dashboard (Unit 6) was held for teammates and their work has now
   arrived, run the **Integration Evaluation Protocol** from
   `unit-06-dashboard.md` before merging it in. If it was already built and
   merged earlier, confirm it renders real pipeline output correctly.
4. Record the 5-minute pitch video: demonstrate a mismatch being caught, an
   escalation firing, and the dashboard reacting live. Stay under 5 minutes
   — going over costs 1 point per 30 seconds late.
5. Write the README.md and the written responses (problem-solution
   alignment, AI/cloud integration, testing, challenges, success metrics,
   scalability).
6. Submit via the Google Form before the deadline: 22 Sept 2026, 12:00pm.

## Exit Criteria
- Deployed system is reachable and functional (not just localhost).
- All required submission components (GitHub repo + README, pitch video,
  written responses) are ready.
- Submission form completed before the deadline.

## This Is the Last Unit
No further unit follows. If time remains after this, use it for polish, not
new scope — see `docs/BUILD-ORDER.md`'s "Additional Suggestions for Success"
for what's worth spending remaining time on (accuracy trend logging,
KNOWN-ISSUES.md, etc.).
