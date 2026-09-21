# POST-UNIT-13 ADD-ON — PDF Report Export (Frontend Changes)

> Status: **Not yet started.** This is a stretch feature, only build if
> Unit 13 is fully complete and the backend endpoint
> (`REPORT-EXPORT-BACKEND.md`) is ready.

## What This Adds

A "Download Report" button on each shipment card in the dashboard, so a
reviewer can get a standalone PDF of that shipment's comparison result.

## Frontend Changes Required

### 1. New Button on Shipment Detail View

Add to the same view described in `DESIGN.md` §2.2 (Side-by-Side Comparison
View) — place it near the existing "Generate Reply" button (§2.6) so both
shipment-level actions live together.

```jsx
<button onClick={() => downloadReport(email_id)}>
  Download Report (PDF)
</button>
```

### 2. Download Handler

```javascript
async function downloadReport(emailId) {
  const response = await fetch(`/api/shipments/${emailId}/report.pdf`);
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `shipment_${emailId}_report.pdf`;
  a.click();
  window.URL.revokeObjectURL(url);
}
```

### 3. Loading / Error State

- Show a small spinner on the button while the PDF is generating (backend
  render can take a second or two).
- If the fetch fails, show a simple inline error — don't let it silently
  fail with no feedback.

### 4. No Changes Needed To

- The Kanban board (§2.1)
- The Analytics Panel (§2.5)
- The mock data shape — this button calls a live backend endpoint, it does
  not need new fields added to `mock_dashboard_data.json`

## Testing

- Click the button on one `OK`, one `MISMATCH`, and one `NEEDS_REVIEW`
  shipment — confirm each downloads a correctly named, correctly formatted
  PDF.
- Confirm the button doesn't appear broken/unresponsive while the PDF is
  generating (loading state works).

## Effort Estimate

Small — roughly 1–2 hours, assuming the backend endpoint from
`REPORT-EXPORT-BACKEND.md` is already working.

## Dependency Note

This frontend change **cannot be built or tested until the backend endpoint
exists**. If your team wants to build the button UI early (just the visual,
not the working download), that's fine — just stub the `downloadReport`
function with a placeholder until the real endpoint is live.
