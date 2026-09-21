---
name: unit-11-realtime-architecture
description: Wire Pub/Sub event-driven processing and scheduler fallback/digest (#7)
---

## Goal
Make the pipeline react to new emails automatically instead of running as a
one-shot batch script.

## Prerequisite
`unit-10-escalation-feedback.md` complete. Consider this unit optional if
the team is behind schedule — see `docs/BUILD-ORDER.md` closing notes on
time-boxing Units 9–12.

## Steps
1. In `infra/pubsub_setup.py`, create a Pub/Sub topic (`new-email-events`)
   and a subscriber that triggers the `unit-07` orchestrator pipeline on
   each new message.
2. Add async processing so multiple emails can be mid-pipeline
   simultaneously.
3. Add a retry queue so failed processing attempts get requeued instead of
   silently dropped.
4. Add a Cloud Scheduler job as a polling fallback and/or to trigger the
   daily digest summary (small add-on to the dashboard's analytics panel —
   see `docs/DESIGN.md` §2.8).

## Test
Publish 3 test messages to the Pub/Sub topic. Confirm the pipeline reacts
without any manual triggering.

## Exit Criteria
- Pipeline reacts to a published event within seconds, not minutes.

## Next
Move to `unit-12-failure-simulator.md`.
