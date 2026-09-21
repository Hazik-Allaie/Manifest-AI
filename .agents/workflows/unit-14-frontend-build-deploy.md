---
name: unit-14-frontend-build-deploy
description: Complete/fix the frontend against DESIGN.md, then deploy backend + frontend to production
---

## Prerequisite
Units 0–13 complete (except Unit 6 built separately). `docs/DASHBOARD-INTEGRATION-REPORT.md`
exists from the prior evaluation pass — read it first, it tells you exactly
what's missing or broken before you start.

---

## Part A — Complete the Frontend

1. Read `docs/DASHBOARD-INTEGRATION-REPORT.md` (Phase 1 findings) — this is
   your checklist of what's missing, incomplete, or mismatched.
2. Read `docs/DESIGN.md` in full as the authoritative spec.
3. For every feature marked ❌ (missing) or ⚠️ (incomplete/deviates) in the
   integration report, build or fix it so it matches `docs/DESIGN.md`
   exactly — covering §2.1 through §2.8 (Kanban, Side-by-Side Comparison,
   Shipment Timeline, Search/Filter, Analytics Panel, Draft Correction
   Email button, Review/Correction Interface, Daily Digest).
4. Do **not** remove or alter any scope-creep features flagged in the
   report without asking first — just don't build anything new outside
   `docs/DESIGN.md`'s scope yourself.
5. Fix any schema mismatches identified in the report so the frontend
   correctly consumes `shared/schemas/` shapes (`SubmissionEntry`,
   `ComparisonResult`, etc.) — not a renamed or invented shape.
6. Re-run a smoke test against `mock_dashboard_data.json` — confirm no
   console errors, no broken renders, every view loads.

## Part B — Wire the Frontend to the Real Backend

1. Replace the frontend's mock-data loading with real API calls to the
   backend endpoints (`dashboard/backend/`) — the ones the orchestration
   pipeline and Firestore already populate.
2. Add an environment-variable-based API base URL (e.g.
   `VITE_API_BASE_URL` or equivalent for the framework in use) — never
   hardcode `localhost` into the built frontend, since it needs to point
   at the deployed backend URL after Part C.

## Part C — Deploy the Backend

Deploy to **Cloud Run** (already the planned target per `docs/TECHSTACK.md`):

1. Build a Dockerfile for the backend API (`dashboard/backend/` + the
   orchestration pipeline endpoints it needs to expose).
2. `gcloud run deploy` targeting the project/region already configured in
   `.env` (`MANIFEST_GCP_PROJECT_ID`, `MANIFEST_GCP_REGION`).
3. Enable CORS on the backend, allowing requests from the frontend's
   deployed domain (added in Part D) — without this, the deployed frontend
   will fail to reach the backend even if both are individually live.
4. Confirm the deployed backend's `/health` (or equivalent) endpoint
   responds correctly before moving on.

## Part D — Deploy the Frontend

**Default recommendation: deploy to Vercel**, as requested — it's simple,
free for this scale, and works well for a React/Vite frontend.

**Alternative worth considering: Firebase Hosting.** Since the backend is
already on Google Cloud (Cloud Run + Firestore + Vertex AI), hosting the
frontend on Firebase Hosting keeps the entire stack inside one GCP project —
simpler CORS setup (can even route through Firebase's rewrite rules to hit
Cloud Run without exposing a separate CORS-enabled public endpoint), one
billing dashboard, and one place to manage everything for the pitch demo.
It's a similarly simple `firebase deploy` command.

**Decide as follows:** if deploying quickly with zero extra GCP
configuration matters most, use Vercel. If keeping the whole stack in one
ecosystem and simplifying CORS matters more, use Firebase Hosting. Default
to **Vercel** unless told otherwise, since it was the explicit request —
but flag this tradeoff back to the user before finalizing, in case they'd
rather switch.

Steps (Vercel):
1. Connect the `dashboard/frontend/` folder as a Vercel project (via CLI
   `vercel` or the Vercel dashboard pointed at the GitHub repo, scoped to
   that subfolder).
2. Set the `VITE_API_BASE_URL` (or equivalent) environment variable on
   Vercel to the deployed Cloud Run backend URL from Part C.
3. Deploy and confirm the live URL loads.

## Part E — Final Wiring Check

1. Open the deployed frontend URL in a real browser.
2. Confirm it successfully fetches from the deployed backend (not mock
   data, not localhost).
3. Confirm no CORS errors, no failed network requests, no broken views.

## Exit Criteria
- Backend is live on Cloud Run and reachable.
- Frontend is live (Vercel or Firebase Hosting) and reachable.
- Frontend successfully loads real data from the live backend, not mock
  data.
- Every feature from `docs/DESIGN.md` §2 that was fixed in Part A renders
  correctly against real data.

## Output
Write a short `docs/DEPLOYMENT-LOG.md` recording: backend URL, frontend
URL, hosting choice made (Vercel vs Firebase Hosting) and why, and any
issues hit during deployment.

## Next
Once this unit passes, move to `unit-15-e2e-functional-test.md`.
