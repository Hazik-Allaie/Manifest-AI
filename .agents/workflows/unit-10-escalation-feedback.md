---
name: unit-10-escalation-feedback
description: Wire real escalation notifications (#4) and the self-improving feedback loop (#5)
---

## Goal
Make `NEEDS_REVIEW` cases actually notify a human with evidence, and make
human corrections feed back into future pipeline runs.

## Prerequisite
`unit-09-ensemble-embeddings.md` complete.

## Steps
1. In `escalation/notifier.py`, wire a Discord (or Slack/email) webhook that
   fires on every `NEEDS_REVIEW` case. The message must include the
   escalation evidence packet (see `docs/ARCHITECTURE.md` §5): email_id,
   review_reason, field, source_snippet, system_guess.
2. In `infra/firestore_schema.py`, define a `corrections` collection:
   what the system originally said, what the human corrected it to, and why
   (if given).
3. Build few-shot injection: when running extraction/comparison, pull the
   most relevant recent corrections from Firestore and include them as
   examples in the prompt.
4. (Optional, time-permitting) Set up a periodic Vertex AI fine-tuning job
   using accumulated corrections.

## Test
1. Manually trigger 3 escalations end-to-end, confirm the Discord
   notification fires with correct evidence attached.
2. Submit 3 fake corrections to Firestore, confirm they appear in the
   `corrections` collection and measurably influence a subsequent pipeline
   run's prompt.

## Exit Criteria
- Notification delivery confirmed for all 3 test escalations.
- Correction logging confirmed in Firestore.
- Observable behavior change in a prompt after few-shot injection.

## Next
Move to `unit-11-realtime-architecture.md`.
