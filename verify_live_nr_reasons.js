const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TARGET_URL = process.env.TEST_URL || 'https://manifest-ai-509207.web.app';

(async () => {
  console.log('==========================================================');
  console.log('VERIFYING 4 CANONICAL REVIEW REASONS IN LIVE UI');
  console.log('Target URL:', TARGET_URL);
  console.log('Timestamp:', new Date().toISOString());
  console.log('==========================================================\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleLogs = [];
  page.on('console', msg => consoleLogs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => consoleLogs.push(`[PAGE ERROR] ${err.message}`));

  try {
    console.log('1. Navigating to live site...');
    await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 30000 });

    console.log('2. Switching to Triage Command Center tab...');
    const tabBtn = await page.waitForSelector('#tabNavDashboard, button:has-text("Triage Command Center")', { timeout: 10000 });
    await tabBtn.click();
    await page.waitForTimeout(2000);

    console.log('3. Waiting for Kanban column #kanbanColNeedsReview to render...');
    await page.waitForSelector('#kanbanColNeedsReview', { timeout: 10000 });

    // Extract all Subgroup Headers in Needs Review
    const subgroupHeaders = await page.$$eval('#kanbanColNeedsReview .subgroup-header', els => els.map(e => ({
      text: e.innerText.trim(),
      dataSubgroup: e.getAttribute('data-subgroup')
    })));
    console.log('\n--- SUBGROUP HEADERS IN NEEDS REVIEW COLUMN ---');
    console.log(JSON.stringify(subgroupHeaders, null, 2));

    // Extract all Cards in Needs Review
    const nrCards = await page.$$eval('#kanbanColNeedsReview .kanban-card', els => els.map(e => {
      const refId = e.querySelector('.card-ref-id')?.innerText.trim() || '';
      const po = e.querySelector('.card-po-pill')?.innerText.trim() || '';
      const badge = e.querySelector('.badge-tag-mismatch')?.innerText.trim() || '';
      const badgeStyle = e.querySelector('.badge-tag-mismatch')?.getAttribute('style') || '';
      const company = e.querySelector('.card-company-name')?.innerText.trim() || '';
      const subject = e.querySelector('.card-subject')?.innerText.trim() || '';
      const missingDetails = Array.from(e.querySelectorAll('.missing-row')).map(r => r.innerText.trim());
      const actionBtn = e.querySelector('.card-action-bar button:first-of-type')?.innerText.trim() || '';
      const dataReason = e.getAttribute('data-review-reason');
      const dataStatus = e.getAttribute('data-status');
      return {
        refId,
        po,
        badge,
        badgeStyle,
        company,
        subject,
        missingDetails,
        actionBtn,
        dataReason,
        dataStatus
      };
    }));

    console.log(`\nTotal Needs Review Cards Rendered in DOM: ${nrCards.length}`);

    // Group cards by review_reason
    const grouped = {};
    nrCards.forEach(c => {
      const r = c.dataReason || 'unknown';
      if (!grouped[r]) grouped[r] = [];
      grouped[r].push(c);
    });

    console.log('\n--- CARDS GROUPED BY CANONICAL REVIEW REASON ---');
    for (const [reason, cards] of Object.entries(grouped)) {
      console.log(`\n▶ [${reason.toUpperCase()}] Count: ${cards.length}`);
      cards.slice(0, 2).forEach(c => {
        console.log(`  - Ref: ${c.refId} (${c.po}) | Badge: "${c.badge}" | Action: "${c.actionBtn}"`);
        console.log(`    Missing Items: ${c.missingDetails.join(' ; ')}`);
      });
      if (cards.length > 2) {
        console.log(`    ... and ${cards.length - 2} more (Total: ${cards.length} cards: ${cards.map(x => x.refId).join(', ')})`);
      }
    }

    // Verify all 4 canonical values
    const requiredReasons = ['wrong_doc_type', 'missing_attachment', 'unreadable', 'missing_value'];
    const results = {};
    let allPresent = true;

    for (const req of requiredReasons) {
      const matched = grouped[req] || [];
      const hasCards = matched.length > 0;
      const header = subgroupHeaders.find(h => h.dataSubgroup === req || h.text.toLowerCase().includes(req));
      results[req] = {
        present: hasCards,
        count: matched.length,
        headerFound: !!header,
        headerText: header ? header.text : null,
        sampleCard: matched[0] || null,
        allCardIds: matched.map(c => c.refId)
      };
      if (!hasCards) allPresent = false;
    }

    // Test clicking a card from each category to verify Inspector representation
    console.log('\n--- VERIFYING INSPECTOR FOR EACH OF THE 4 REASONS ---');
    for (const req of requiredReasons) {
      const cardSelector = `#kanbanColNeedsReview .kanban-card[data-review-reason="${req}"]`;
      const card = await page.$(cardSelector);
      if (card) {
        await card.click();
        await page.waitForTimeout(400);
        const refPill = await page.$eval('#inspRefPill', el => el.innerText.trim()).catch(() => '');
        const carrierPill = await page.$eval('#inspCarrierPill', el => el.innerText.trim()).catch(() => '');
        console.log(`Click [${req}] -> Inspector Ref: "${refPill}" | Carrier/Exception Pill: "${carrierPill}"`);
        results[req].inspectorVerification = { refPill, carrierPill };
      }
    }

    // Take screenshot of Needs Review column
    const screenshotPath = path.join(__dirname, 'evidence_needs_review_reasons.png');
    const nrCol = await page.$('#kanbanColNeedsReview');
    if (nrCol) {
      await nrCol.screenshot({ path: screenshotPath });
      console.log(`\nScreenshot saved: ${screenshotPath}`);
    }

    // Save JSON evidence
    const outputEvidence = {
      verifiedAt: new Date().toISOString(),
      url: TARGET_URL,
      allPresent,
      totalNeedsReviewCount: nrCards.length,
      subgroupHeaders,
      breakdown: results,
      consoleErrors: consoleLogs.filter(l => l.includes('ERROR'))
    };

    fs.writeFileSync(path.join(__dirname, 'nr_reasons_evidence.json'), JSON.stringify(outputEvidence, null, 2), 'utf-8');
    console.log('Saved detailed evidence to nr_reasons_evidence.json');

    console.log('\n==========================================================');
    console.log(`FINAL RESULT: ${allPresent ? '✅ ALL 4 CANONICAL REASONS VERIFIED' : '❌ FAILED'}`);
    console.log('==========================================================');

    process.exit(allPresent ? 0 : 1);

  } catch (err) {
    console.error('Execution Error:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
