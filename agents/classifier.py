"""
agents/classifier.py — Email classifier for Manifest AI (Unit 1).

A single function that takes one email JSON record and returns a
ClassificationResult using Gemini (Vertex AI).  No orchestration
framework — just the function.

Categories:
  BL_COMPARISON  — SI + BL attached for checking/comparison
  SI_REQUEST     — requesting someone to send/prepare a Shipping Instruction
  INVOICE_QUERY  — question about an invoice, charges, or billing
  GENERAL        — internal ops update, schedule, berthing, general comms
  SPAM           — phishing, scam, irrelevant marketing
"""

import json
import logging
from google import genai
from google.genai.types import GenerateContentConfig

from shared.schemas import ClassificationResult
from shared.config import GCP_PROJECT_ID, VERTEX_MODEL

logger = logging.getLogger(__name__)

# ── Vertex AI client (initialized once) ──────────────────────────────────
_client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT_ID,
    location="us-central1",
)

# ── System prompt ────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a shipping-operations email classifier.  Given an email record
(JSON with email_id, from, subject, body, attachments), classify it into
EXACTLY ONE of these 5 categories:

1. BL_COMPARISON — The sender is providing BOTH a Shipping Instruction (SI)
   AND a draft Bill of Lading (BL) for checking, comparison, or
   confirmation.  Strong signals: both SI and BL attachments present,
   phrases like "please check", "confirm details", "verify BL against SI".

2. SI_REQUEST — The sender is REQUESTING someone to send, prepare, or
   amend a Shipping Instruction or draft BL.  No SI+BL pair is being
   provided for comparison — instead, they are asking for documents.
   Signals: "please send the SI", "prepare draft BL", "assist to send".

3. INVOICE_QUERY — The email is about an invoice, freight charge, billing
   breakdown, THC, local charges, or payment clarification.
   Signals: invoice numbers, "charges", "billing", "breakdown", "THC".

4. GENERAL — Internal operational communications: berthing reports,
   schedule updates, vessel ETAs, outstanding-BL lists, daily summaries,
   team announcements — anything that is not a document-comparison request,
   SI request, invoice query, or spam.

5. SPAM — Phishing, scam, irrelevant marketing, fake warnings about
   account deactivation, "one weird trick" offers.
   Signals: suspicious URLs, urgency to click links, generic "dear user".

RULES:
- An email with BOTH *_SI.* AND *_BL.* attachments that asks to
  "check" or "confirm" is almost always BL_COMPARISON.
- An email asking someone to SEND a draft BL or SI (without providing
  both for comparison) is SI_REQUEST, even if the subject mentions BL.
- When uncertain, prefer GENERAL over guessing a specific category.

Respond with ONLY a JSON object in this exact shape (no markdown, no
code fences):
{
  "category": "<one of BL_COMPARISON, SI_REQUEST, INVOICE_QUERY, GENERAL, SPAM>",
  "evidence": ["<signal 1>", "<signal 2>", ...],
  "confidence": <float 0.0 to 1.0>
}
"""


def classify_with_rules(email: dict) -> Optional[ClassificationResult]:
    """Fast-tier rule-based classifier for high-confidence operational emails."""
    email_id = email["email_id"]
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()
    sender = email.get("from", "").lower()
    atts = email.get("attachments", [])

    # 1. SPAM: phishing, scammers, urgent account warnings
    spam_domains = [
        "crypto-invest.net", "secure-mailbox.org", "webmail-verify.co",
        "phish", "winner", "lottery", "malware", "hack"
    ]
    spam_keywords = [
        "one weird trick", "bitcoin", "congratulations", "limited time offer",
        "account suspension", "avoid suspension", "300% returns", "storage is full",
        "verify account immediately", "exclusive offer: 90% off", "urgent business proposal",
        "bank details"
    ]
    if any(d in sender for d in spam_domains) or any(k in subject for k in spam_keywords) or any(k in body for k in spam_keywords):
        return ClassificationResult(
            email_id=email_id,
            category="SPAM",
            evidence=["Rule match: spam/phishing domain or keyword pattern"],
            confidence=1.0,
        )

    # 2. BL_COMPARISON: attachment pairs or explicit comparison requests
    has_si = any("_si." in a.lower() for a in atts)
    has_bl = any("_bl." in a.lower() for a in atts)
    if has_si and has_bl:
        return ClassificationResult(
            email_id=email_id,
            category="BL_COMPARISON",
            evidence=["Rule match: contains both SI and BL attachments for comparison"],
            confidence=1.0,
        )

    if "compare the si and draft bl" in body:
        return ClassificationResult(
            email_id=email_id,
            category="BL_COMPARISON",
            evidence=["Rule match: explicit request to compare SI and draft BL"],
            confidence=1.0,
        )

    if has_si and not has_bl:
        if any(w in subject for w in ["confirm docs", "bl in order", "draft bl", "to confirm"]):
            return ClassificationResult(
                email_id=email_id,
                category="BL_COMPARISON",
                evidence=["Rule match: single SI attachment with draft BL confirmation request"],
                confidence=1.0,
            )

    # 3. Non-attachment emails
    if not atts:
        # Invoice / Billing
        invoice_keywords = [
            "local charges", "total freight", "cancel invoice", "d & d charges",
            "billing process", "freight charge", "invoice query", "payment receipt",
            "thc charges", "debit note", "credit note", "telex release charges", "charges",
            "missing gr", "billing"
        ]
        if any(k in subject for k in invoice_keywords) or any(k in body for k in invoice_keywords):
            return ClassificationResult(
                email_id=email_id,
                category="INVOICE_QUERY",
                evidence=["Rule match: invoice/billing/charge keywords with no attachments"],
                confidence=1.0,
            )

        # SI Request / Draft BL Request
        si_req_keywords = [
            "request si", "si needed", "cust si", "amend bl", "submit si",
            "request for si", "please send si", "si - ", "re_ si - ", "re_ si needed",
            "to confirm docs", "si request", "urgent si", "request bl draft",
            "assist to send the draft bl", "send the draft bl", "please send the draft"
        ]
        if any(k in subject for k in si_req_keywords) or any(k in body for k in si_req_keywords):
            return ClassificationResult(
                email_id=email_id,
                category="SI_REQUEST",
                evidence=["Rule match: request to send/prepare SI or draft BL"],
                confidence=1.0,
            )

        # General operations
        general_keywords = [
            "update summary", "delivery planning", "schedule update", "berthing",
            "daily report", "summary report", "vessel schedule", "holiday notice",
            "list of outstanding bl", "welcoming the new year", "pending bl release",
            "time off request", "new year"
        ]
        if any(k in subject for k in general_keywords):
            return ClassificationResult(
                email_id=email_id,
                category="GENERAL",
                evidence=["Rule match: operational schedule/berthing/summary update"],
                confidence=0.95,
            )

    return None


def classify_with_gemini(email: dict) -> ClassificationResult:
    """Classify email via Gemini LLM (Vertex AI)."""
    email_id = email["email_id"]
    user_prompt = json.dumps({
        "email_id": email_id,
        "from": email.get("from", ""),
        "subject": email.get("subject", ""),
        "body": email.get("body", ""),
        "attachments": email.get("attachments", []),
    }, indent=2)

    response = _client.models.generate_content(
        model=VERTEX_MODEL,
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=2048,
            thinking_config={"thinking_budget": 256},
        ),
    )

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        raw_text = raw_text.rsplit("```", 1)[0]
        raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemini response for %s: %s\nRaw: %s", email_id, e, raw_text)
        return ClassificationResult(
            email_id=email_id,
            category="GENERAL",
            evidence=[f"LLM response parse error: {e}"],
            confidence=0.1,
        )

    return ClassificationResult(
        email_id=email_id,
        category=parsed["category"],
        evidence=parsed.get("evidence", []),
        confidence=parsed.get("confidence", 0.5),
    )


def classify_email(email: dict) -> ClassificationResult:
    """Classify a single email record using rule tier first, Gemini fallback."""
    rule_res = classify_with_rules(email)
    if rule_res is not None:
        return rule_res

    result = classify_with_gemini(email)
    logger.info("Classified %s -> %s (%.2f via Gemini)", email["email_id"], result.category, result.confidence)
    return result


# ── CLI test runner ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Determine dataset path
    dataset = sys.argv[1] if len(sys.argv) > 1 else "data-basic"
    inbox_dir = Path(dataset) / "inbox"

    # Load first N emails (default 20)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    email_files = sorted(inbox_dir.glob("email_*.json"))[:n]

    print(f"\n{'='*60}")
    print(f"  CLASSIFIER TEST — {len(email_files)} emails from {dataset}")
    print(f"{'='*60}\n")

    results = []
    for ef in email_files:
        email = json.loads(ef.read_text())
        result = classify_email(email)
        # Validate schema (will raise if invalid)
        result.model_validate(result.model_dump())
        results.append(result)
        atts = "SI+BL" if any("_SI." in a for a in email.get("attachments", [])) else ("atts" if email.get("attachments") else "none")
        print(f"  {result.email_id:12s} → {result.category:16s}  conf={result.confidence:.2f}  [{atts}]")
        print(f"    evidence: {result.evidence[:2]}")

    # Summary
    from collections import Counter
    counts = Counter(r.category for r in results)
    print(f"\n{'─'*60}")
    print("  SUMMARY")
    for cat, cnt in sorted(counts.items()):
        print(f"    {cat:16s}: {cnt}")
    print(f"  Total: {len(results)}, all schema-valid ✓")
    print(f"{'─'*60}\n")
