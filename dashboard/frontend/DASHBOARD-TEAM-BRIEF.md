# Dashboard Team Brief — Manifest AI

Welcome — you own the **Dashboard**: the screen that shows the results of
every email our AI system processes. This is the most *visible* part of the
whole project — it's what the judges will actually look at during our pitch.

## What You're Building

Read **`DESIGN.md`** — that's your full spec: every screen, every feature,
exactly what to build. Don't worry about the AI/backend side of the project;
that's being handled separately.

## You Do NOT Need

- Google Cloud access — you're not touching it, and that's intentional
- Any AI/Vertex AI/model knowledge
- To understand how emails get classified or compared — just how to *display*
  the results

## Build Against Fake Data First

You have **`mock_dashboard_data.json`** — a realistic sample of what the
real backend will eventually send you: emails with different outcomes (clean
match, mismatch, needs-review for different reasons), plus a sample analytics
snapshot at the bottom (`_analytics_snapshot`).

**Build your entire UI against this file.** Load it, render it, make every
view in `DESIGN.md` work with this data. When the real backend is ready,
someone will just swap this file for a live data source — your UI code
shouldn't need to change.

## Your 3 Sub-Parts (split however works for your team)

1. **Kanban board** (Auto-Cleared / Discrepancy Found / Exception-Needs
   Review) + search/filter — see `DESIGN.md` §2.1, §2.4
2. **Side-by-side comparison view** + shipment timeline — see `DESIGN.md`
   §2.2, §2.3
3. **Analytics panel** + accuracy chart + "Generate Reply" button (the
   button just needs a UI — it'll call a real function later, for now you
   can mock its response too) — see `DESIGN.md` §2.5, §2.6

## Deadline

Preliminary submission: **22 Sept 2026, 12:00pm**. Aim to have a working UI
against the mock data by end of Day 2 (Sept 20) so there's buffer time to
plug in real data on Day 3.

## When You're Done

Hand your code back and it'll go through a review to make sure it lines up
correctly with the rest of the system before it's merged in — so don't
worry about getting every detail perfect on the first try, we'll catch and
fix anything that needs adjusting together.

## Questions?

Ask in the team channel — don't guess on anything in `DESIGN.md` that's
unclear.
