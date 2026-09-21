/**
 * retest_interactions.js
 * Dedicated re-test script verifying the three flagged selector issues:
 * 1. Test 3a: Comparison view click opens on the first attempt
 * 2. Test 8: Correction submission via real input element -> fresh Firestore doc_id
 * 3. Test 12: PDF button click triggers real file download to downloads directory
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.TEST_URL || 'https://manifest-ai-509207.web.app';
const DOWNLOADS_DIR = path.join(__dirname, 'downloads_test');

if (!fs.existsSync(DOWNLOADS_DIR)) {
  fs.mkdirSync(DOWNLOADS_DIR, { recursive: true });
}

(async () => {
  console.log('==========================================================');
  console.log('RETESTING 3 FLAGGED INTERACTIONS WITH REAL AUTOMATION');
  console.log('Target URL:', BASE_URL);
  console.log('Timestamp:', new Date().toISOString());
  console.log('==========================================================\n');

  const browser = await chromium.launch({
    headless: true,
    downloadsPath: DOWNLOADS_DIR
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    acceptDownloads: true
  });

  const page = await context.newPage();

  const consoleLogs = [];
  page.on('console', msg => consoleLogs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => consoleLogs.push(`[PAGE ERROR] ${err.message}`));

  let test3aResult = { pass: false, evidence: {} };
  let test8Result  = { pass: false, evidence: {} };
  let test12Result = { pass: false, evidence: {} };

  try {
    // ── Navigate to live site ─────────────────────────────────────────
    console.log('Navigating to', BASE_URL, '...');
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // Switch to Triage Command Center tab
    console.log('Switching to Triage Command Center tab (#tabNavDashboard)...');
    const tabBtn = await page.waitForSelector('#tabNavDashboard, button:has-text("Triage Command Center")', { timeout: 10000 });
    await tabBtn.click();
    await page.waitForTimeout(1500);

    // Wait for Kanban board to populate with cards
    console.log('Waiting for Kanban columns to populate...');
    await page.waitForSelector('#kanbanColDiscrepancy .kanban-card, .kanban-card', { timeout: 15000 });

    // ──────────────────────────────────────────────────────────────────
    // RETEST 3a: Comparison View Click Opens on First Attempt
    // ──────────────────────────────────────────────────────────────────
    console.log('\n----------------------------------------------------------');
    console.log('RUNNING RETEST 3a: Comparison view click (first attempt)');
    console.log('----------------------------------------------------------');

    // Locate the first MISMATCH card in kanbanColDiscrepancy
    const mismatchCards = await page.$$('#kanbanColDiscrepancy .kanban-card');
    console.log(`Found ${mismatchCards.length} MISMATCH cards in #kanbanColDiscrepancy`);

    if (mismatchCards.length === 0) {
      throw new Error('No cards found in Discrepancy column');
    }

    const firstMismatchCard = mismatchCards[0];
    const cardText = await firstMismatchCard.innerText();
    const cardRefMatch = cardText.match(/#(email_\d+)/);
    const emailId = cardRefMatch ? cardRefMatch[1] : 'email_004';
    console.log(`Targeting MISMATCH Card: #${emailId}`);

    // Locate the "Inspect Side-by-Side" button inside this card
    const inspectBtn = await firstMismatchCard.$('button.btn-card-primary');
    if (!inspectBtn) {
      throw new Error('Could not find button.btn-card-primary inside target MISMATCH card');
    }

    const btnText = (await inspectBtn.innerText()).trim();
    console.log(`Clicking button selector: "button.btn-card-primary" (text: "${btnText}") on first attempt...`);

    // Click directly on the first attempt
    await inspectBtn.click();

    // Verify comparison inspector opens and renders fields
    const inspectorPanel = await page.waitForSelector('#comparisonInspectorPanel', { timeout: 6000 });
    await page.waitForSelector('#schemaTableBody tr', { timeout: 6000 });

    const refPill = await page.$eval('#inspRefPill', el => el.innerText.trim()).catch(() => '');
    const tableRows = await page.$$eval('#schemaTableBody tr', rows => rows.map(r => ({
      field: r.querySelector('.field-name-mono')?.innerText.trim() || '',
      si: r.querySelectorAll('.field-val-box')[0]?.innerText.trim() || '',
      bl: r.querySelectorAll('.field-val-box')[1]?.innerText.trim() || '',
      status: r.querySelector('.badge-tag-verified, .badge-tag-mismatch')?.innerText.trim() || '',
      isMismatchRow: r.classList.contains('row-mismatch')
    })));

    const mismatchRowCount = tableRows.filter(r => r.isMismatchRow || r.status.includes('MISMATCH')).length;

    console.log(`Inspector opened successfully on first attempt!`);
    console.log(`Inspector Reference Pill: "${refPill}"`);
    console.log(`Total Schema Table Fields Rendered: ${tableRows.length}`);
    console.log(`Mismatched Fields Highlighted: ${mismatchRowCount}`);
    console.log('Sample rows:', tableRows.slice(0, 3));

    if (tableRows.length === 7 && refPill.includes(emailId)) {
      test3aResult = {
        pass: true,
        evidence: {
          emailId,
          selectorUsed: '#kanbanColDiscrepancy .kanban-card:first-of-type button.btn-card-primary',
          buttonLabel: btnText,
          openedOnFirstAttempt: true,
          refPill,
          totalFields: tableRows.length,
          mismatchedFields: mismatchRowCount,
          fieldsVerified: tableRows.map(r => r.field)
        }
      };
      console.log('>>> RETEST 3a: PASS (Opened on first attempt with all 7 fields)\n');
    } else {
      test3aResult = {
        pass: false,
        evidence: {
          emailId,
          refPill,
          totalFields: tableRows.length
        }
      };
      console.log('>>> RETEST 3a: FAIL (Fields count != 7 or ref mismatch)\n');
    }

    // ──────────────────────────────────────────────────────────────────
    // RETEST 8: Correction Form Submission -> Fresh Firestore doc_id
    // ──────────────────────────────────────────────────────────────────
    console.log('----------------------------------------------------------');
    console.log('RUNNING RETEST 8: Correction submission via real input element');
    console.log('----------------------------------------------------------');

    // Locate the correction input element in the opened inspector
    const corrInput = await page.waitForSelector('#inspCorrectionInput, .correction-field-input', { timeout: 5000 });
    const fieldSelect = await page.waitForSelector('#inspCorrectionFieldSelect', { timeout: 5000 });
    const notesInput = await page.waitForSelector('#inspCorrectionNotes', { timeout: 5000 });
    const submitBtn = await page.waitForSelector('#btnSubmitInspectorCorrection', { timeout: 5000 });

    const selectedField = await fieldSelect.inputValue();
    const timestampNonce = Date.now().toString().slice(-6);
    const uniqueCorrectedValue = `3 x 40HC (Verified by E2E-${timestampNonce})`;
    const uniqueNotes = `E2E automated interaction test run at ${new Date().toISOString()}`;

    console.log(`Found real correction input element: id="${await corrInput.getAttribute('id')}"`);
    console.log(`Correcting field: "${selectedField}"`);
    console.log(`Filling input with unique test value: "${uniqueCorrectedValue}"`);
    await corrInput.fill(uniqueCorrectedValue);

    console.log(`Filling notes input: "${uniqueNotes}"`);
    await notesInput.fill(uniqueNotes);

    // Set up network interception for POST /api/correct
    console.log('Setting up network response listener for POST /api/correct...');
    const apiCorrectPromise = page.waitForResponse(res => {
      return res.url().includes('/api/correct') && res.request().method() === 'POST';
    }, { timeout: 15000 });

    console.log('Clicking Submit Correction button (#btnSubmitInspectorCorrection)...');
    await submitBtn.click();

    console.log('Awaiting network response from live backend...');
    const apiResponse = await apiCorrectPromise;
    const responseStatus = apiResponse.status();
    const responseJson = await apiResponse.json();

    console.log(`API HTTP Status: ${responseStatus}`);
    console.log('API Response Body:', JSON.stringify(responseJson, null, 2));

    const freshDocId = responseJson.doc_id;
    console.log(`Fresh Firestore doc_id received: "${freshDocId}"`);

    // Wait for DOM confirmation element
    const feedbackEl = await page.waitForSelector('#inspCorrectionFeedback, [data-doc-id]', { state: 'attached', timeout: 6000 }).catch(() => null);
    const feedbackText = feedbackEl ? await feedbackEl.innerText() : '';
    console.log(`DOM Confirmation Message: "${feedbackText}"`);

    if (responseStatus === 200 && freshDocId && freshDocId.length > 5) {
      test8Result = {
        pass: true,
        evidence: {
          emailId,
          fieldCorrected: selectedField,
          submittedValue: uniqueCorrectedValue,
          notes: uniqueNotes,
          httpStatus: responseStatus,
          freshFirestoreDocId: freshDocId,
          domConfirmationText: feedbackText,
          timestamp: new Date().toISOString()
        }
      };
      console.log(`>>> RETEST 8: PASS (Fresh Firestore write verified with doc_id: ${freshDocId})\n`);
    } else {
      test8Result = {
        pass: false,
        evidence: { responseStatus, responseJson }
      };
      console.log('>>> RETEST 8: FAIL (No valid doc_id returned)\n');
    }

    // ──────────────────────────────────────────────────────────────────
    // RETEST 12: PDF Download Button -> File Lands on Disk with %PDF
    // ──────────────────────────────────────────────────────────────────
    console.log('----------------------------------------------------------');
    console.log('RUNNING RETEST 12: PDF Download via UI button');
    console.log('----------------------------------------------------------');

    // Locate the "Download Report (PDF)" button in the inspector header
    const pdfBtn = await page.waitForSelector('#btnDownloadReport, button:has-text("Download Report (PDF)")', { timeout: 5000 });
    const pdfBtnText = (await pdfBtn.innerText()).trim();
    console.log(`Located PDF button: id="${await pdfBtn.getAttribute('id')}" text="${pdfBtnText}"`);

    // Set up download event listener BEFORE clicking to avoid race conditions
    console.log('Attaching Playwright waitForEvent("download") listener BEFORE click...');
    const downloadPromise = page.waitForEvent('download', { timeout: 20000 });

    console.log('Clicking "Download Report (PDF)" button...');
    await pdfBtn.click();

    console.log('Awaiting browser download event...');
    const download = await downloadPromise;

    const suggestedFilename = download.suggestedFilename();
    console.log(`Browser download event fired! Suggested filename: "${suggestedFilename}"`);

    const targetFilePath = path.join(DOWNLOADS_DIR, suggestedFilename);
    await download.saveAs(targetFilePath);
    console.log(`Saved downloaded file to disk: "${targetFilePath}"`);

    const fileExists = fs.existsSync(targetFilePath);
    const fileSize = fileExists ? fs.statSync(targetFilePath).size : 0;
    const fileHeader = fileExists ? fs.readFileSync(targetFilePath).slice(0, 10).toString('utf-8') : '';

    console.log(`File exists on disk: ${fileExists}`);
    console.log(`File size on disk: ${fileSize} bytes`);
    console.log(`File header signature: "${fileHeader.trim()}"`);

    const isPdf = fileHeader.startsWith('%PDF');

    if (fileExists && fileSize > 1000 && isPdf) {
      test12Result = {
        pass: true,
        evidence: {
          selectorUsed: '#btnDownloadReport',
          buttonText: pdfBtnText,
          suggestedFilename,
          targetFilePath,
          fileSizeBytes: fileSize,
          fileHeader: fileHeader.trim(),
          isRealPdf: isPdf,
          downloadEventConfirmed: true
        }
      };
      console.log(`>>> RETEST 12: PASS (Real PDF downloaded: ${suggestedFilename}, ${fileSize} bytes, header: ${fileHeader.trim()})\n`);
    } else {
      test12Result = {
        pass: false,
        evidence: { fileExists, fileSize, fileHeader }
      };
      console.log('>>> RETEST 12: FAIL (File not saved or invalid PDF header)\n');
    }

  } catch (err) {
    console.error('Test Execution Error:', err);
  } finally {
    await browser.close();
  }

  // ── Summary Report ────────────────────────────────────────────────
  console.log('==========================================================');
  console.log('RETEST EXECUTION SUMMARY');
  console.log('==========================================================');
  console.log(`Test 3a (Comparison View Click):  ${test3aResult.pass ? '✅ PASS' : '❌ FAIL'}`);
  console.log(`Test 8  (Correction Submission):  ${test8Result.pass  ? '✅ PASS' : '❌ FAIL'}`);
  console.log(`Test 12 (PDF Download):           ${test12Result.pass ? '✅ PASS' : '❌ FAIL'}`);
  console.log('==========================================================\n');

  // Save JSON evidence
  const evidenceOut = {
    testedAt: new Date().toISOString(),
    url: BASE_URL,
    test3a: test3aResult,
    test8: test8Result,
    test12: test12Result
  };

  fs.writeFileSync(path.join(__dirname, 'retest_evidence.json'), JSON.stringify(evidenceOut, null, 2), 'utf-8');
  console.log('Evidence saved to retest_evidence.json');

  const allPassed = test3aResult.pass && test8Result.pass && test12Result.pass;
  process.exit(allPassed ? 0 : 1);
})();
