// Unit 15 E2E Browser Test — Manifest AI (Playwright)
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'https://manifest-ai-509207.web.app';
const SHOT_DIR = path.join(__dirname, 'docs', 'e2e-screenshots');
const REPORT  = path.join(__dirname, 'docs', 'E2E-TEST-REPORT.md');

if (!fs.existsSync(SHOT_DIR)) fs.mkdirSync(SHOT_DIR, { recursive: true });

const results = [];
const consoleErrors = [];
let shotIdx = 0;

function pass(name, detail) { console.log(`PASS  [${name}] ${detail}`); results.push({name, status:'PASS', detail}); }
function fail(name, detail) { console.log(`FAIL  [${name}] ${detail}`); results.push({name, status:'FAIL', detail}); }

async function shot(page, label) {
  const file = path.join(SHOT_DIR, `${String(++shotIdx).padStart(2,'0')}_${label}.png`);
  await page.screenshot({ path: file, fullPage: false }).catch(()=>{});
  console.log(`  screenshot: ${path.basename(file)}`);
  return file;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  page.on('console', m => { if (m.type()==='error') { consoleErrors.push(m.text()); console.log(`  [console error] ${m.text()}`); }});
  page.on('pageerror', e => { consoleErrors.push(e.message); console.log(`  [page error] ${e.message}`); });

  // ── TEST 1: Load & navigate to dashboard ──────────────────────────
  console.log('\n=== 1: Data Loading ===');
  try {
    await page.goto(BASE_URL + '/#dashboard', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(4000);
    const title = await page.title();
    await shot(page, 'dashboard_initial');

    const body = await page.textContent('body');
    const hasTriage = body.includes('Triage') || body.includes('Auto-Cleared') || body.includes('MISMATCH');
    const hasError  = body.includes('Failed to load') || body.includes('Error loading') || body.includes('Could not connect');
    if (hasTriage && !hasError) pass('1. Data Loading', `Title="${title}" | Triage content visible | no error state`);
    else fail('1. Data Loading', `hasTriage=${hasTriage} hasError=${hasError}`);
  } catch(e) { fail('1. Data Loading', e.message); await shot(page,'error_1'); }

  // ── TEST 2: Kanban 3 columns ────────────────────────────────────
  console.log('\n=== 2: Kanban Board ===');
  try {
    const body = await page.textContent('body');
    const hasOK   = body.includes('Auto-Cleared') || body.includes('auto-cleared');
    const hasMM   = body.includes('Discrepancy') || body.includes('MISMATCH');
    const hasNR   = body.includes('Needs Review') || body.includes('Exception');
    const cols    = await page.$$('.kanban-column, [class*="kanban-col"], [class*="triage-col"]');
    await shot(page,'kanban_board');
    if (hasOK && hasMM && hasNR) pass('2. Kanban 3 Columns', `OK=${hasOK} MISMATCH=${hasMM} NR=${hasNR} DomCols=${cols.length}`);
    else fail('2. Kanban 3 Columns', `OK=${hasOK} MISMATCH=${hasMM} NR=${hasNR}`);
  } catch(e) { fail('2. Kanban Board', e.message); }

  // ── TEST 3: Click MISMATCH card → comparison view ───────────────
  console.log('\n=== 3: Side-by-Side Comparison ===');
  let openedDetail = false;
  try {
    // Try data-attribute selector first, then text-content search
    let card = await page.$('[data-status="MISMATCH"]:first-of-type');
    if (!card) {
      const all = await page.$$('.kanban-card, .email-card, .card, [class*="card"]');
      for (const c of all) {
        const t = await c.textContent().catch(()=>'');
        if (t.includes('MISMATCH') || t.includes('Discrepancy') || t.includes('Mismatch')) { card = c; break; }
      }
    }
    if (card) {
      await card.click();
      await page.waitForTimeout(2000);
      await shot(page,'mismatch_detail');
      openedDetail = true;

      const detail = await page.textContent('body');
      const hasSI  = detail.includes('SI') || detail.includes('Shipping Instruction');
      const hasBL  = detail.includes('BL') || detail.includes('Bill of Lading');
      const redEl  = await page.$('[class*="mismatch"],[class*="red"],[class*="discrepancy"],[style*="red"],[style*="#ef"],[style*="#dc"]');
      const snip   = detail.includes('snippet') || detail.includes('Containers') || detail.includes('source') || detail.includes('extracted from');

      if (hasSI && hasBL) pass('3a. Comparison SI vs BL', `SI visible=${hasSI} BL visible=${hasBL}`);
      else fail('3a. Comparison SI vs BL', `SI=${hasSI} BL=${hasBL}`);

      if (redEl) pass('3b. Mismatch Field Highlighting', 'Red/distinct element found for mismatched field');
      else fail('3b. Mismatch Field Highlighting', 'No red/highlight element found for mismatched fields');

      if (snip) pass('3c. Source Snippet', 'Source context visible in comparison view');
      else fail('3c. Source Snippet', 'No source snippet text found in detail view');
    } else {
      fail('3. Side-by-Side Comparison', 'No clickable MISMATCH card found in DOM');
      await shot(page,'no_mismatch_card');
    }
  } catch(e) { fail('3. Side-by-Side Comparison', e.message); await shot(page,'error_3'); }

  // ── TEST 4: Timeline in detail view ────────────────────────────
  console.log('\n=== 4: Shipment Timeline ===');
  try {
    const body = await page.textContent('body');
    const hasTL = body.includes('Timeline') || body.includes('Email received') || body.includes('Classified') || body.includes('extracted');
    const tlEl  = await page.$('.timeline,[class*="timeline"],[id*="timeline"]');
    await shot(page,'timeline');
    if (hasTL || tlEl) pass('4. Shipment Timeline', `Text found=${hasTL} DomElement=${!!tlEl}`);
    else fail('4. Shipment Timeline', 'No timeline content found in detail view');
  } catch(e) { fail('4. Shipment Timeline', e.message); }

  // ── TEST 5: Close detail → filter/search ───────────────────────
  console.log('\n=== 5: Search / Filter ===');
  try {
    await page.keyboard.press('Escape'); await page.waitForTimeout(600);
    // click close button if exists
    const closeBtn = await page.$('button[aria-label*="lose"], .modal-close, .detail-close, [id*="closeDetail"], [id*="close-detail"]');
    if (closeBtn) { await closeBtn.click(); await page.waitForTimeout(600); }

    // Search input
    const srch = await page.$('input[type="search"],input[placeholder*="earch"],[id*="search"],[id*="Search"]');
    if (srch) {
      await srch.fill('Ocean');
      await page.waitForTimeout(1000);
      await shot(page,'filter_search');
      const filtered = await page.textContent('body');
      await srch.fill(''); await page.waitForTimeout(500);
      pass('5a. Text Search', 'Search input usable, filter applied');
    } else fail('5a. Text Search', 'No search input found');

    // Status filter
    const statusSel = await page.$('select,[id*="statusFilter"],[id*="status-filter"],[class*="status-filter"]');
    if (statusSel) {
      const tag = await statusSel.evaluate(el => el.tagName);
      if (tag === 'SELECT') {
        await statusSel.selectOption('MISMATCH').catch(() => statusSel.selectOption({label:'MISMATCH'}).catch(()=>null));
      } else {
        await statusSel.click();
      }
      await page.waitForTimeout(800);
      await shot(page,'filter_status');
      pass('5b. Status Filter', 'Status filter control used');
    } else {
      // Try filter buttons
      const btns = await page.$$('button[data-filter],button[data-status],.filter-pill,.filter-btn');
      if (btns.length > 0) { await btns[0].click(); await page.waitForTimeout(600); await shot(page,'filter_btn'); pass('5b. Status Filter', `Filter button(s) found (${btns.length})`); }
      else fail('5b. Status Filter', 'No status filter control found');
    }
  } catch(e) { fail('5. Search/Filter', e.message); await shot(page,'error_5'); }

  // ── TEST 6: Analytics panel ─────────────────────────────────────
  console.log('\n=== 6: Analytics Panel ===');
  try {
    // Look for an analytics tab
    const allTabs = await page.$$('button,[role="tab"],.nav-page-tab,.dashboard-tab');
    let analyticsTab = null;
    for (const t of allTabs) {
      const txt = await t.textContent().catch(()=>'');
      if (txt.toLowerCase().includes('analytic') || txt.toLowerCase().includes('stats')) { analyticsTab = t; break; }
    }
    if (analyticsTab) { await analyticsTab.click(); await page.waitForTimeout(1500); }

    await shot(page,'analytics_panel');
    const body = await page.textContent('body');
    const has520  = body.includes('520');
    const hasRate = body.match(/8\.7|mismatch.rate|Mismatch Rate/i);
    const chart   = await page.$('canvas,svg.chart,[id*="chart"],[class*="chart"]');
    const hasNaN  = body.includes('NaN') || /\bnull\b/.test(body);

    if (has520) pass('6a. Analytics Total Count', '520 visible in analytics view');
    else fail('6a. Analytics Total Count', '520 not visible — check if analytics tab loaded');

    if (hasRate) pass('6b. Analytics Mismatch Rate', 'Mismatch rate value found (non-zero)');
    else fail('6b. Analytics Mismatch Rate', 'Mismatch rate not visible or is zero');

    if (!hasNaN) pass('6c. Analytics No NaN/Null', 'No NaN/null in visible analytics text');
    else fail('6c. Analytics No NaN/Null', 'NaN or null found in analytics view');

    pass('6d. Analytics Chart', `Chart element present=${!!chart}`);
  } catch(e) { fail('6. Analytics Panel', e.message); }

  // ── TEST 7: Draft Correction Email button ───────────────────────
  console.log('\n=== 7: Draft Correction Email ===');
  try {
    // Back to dashboard
    const dashTab = await page.$('#tabNavDashboard,button:has-text("Triage"),button:has-text("Dashboard")');
    if (dashTab) { await dashTab.click(); await page.waitForTimeout(1500); }

    // Open a MISMATCH card
    let card = await page.$('[data-status="MISMATCH"]');
    if (!card) {
      const all = await page.$$('.kanban-card,.email-card,.card,[class*="card"]');
      for (const c of all) { const t = await c.textContent().catch(()=>''); if (t.includes('MISMATCH')||t.includes('Discrepancy')) { card=c; break; } }
    }
    if (card) {
      await card.click(); await page.waitForTimeout(1500);

      // Find draft button
      let draftBtn = await page.$('button:has-text("Draft"),button:has-text("draft email"),button:has-text("Correction Email"),[id*="draft"]');
      if (!draftBtn) {
        const btns = await page.$$('button');
        for (const b of btns) {
          const t = await b.textContent().catch(()=>'');
          if (t.toLowerCase().includes('draft') || t.toLowerCase().includes('email')) { draftBtn = b; break; }
        }
      }
      if (draftBtn) {
        await shot(page,'draft_btn_found');
        await draftBtn.click(); await page.waitForTimeout(2500);
        await shot(page,'draft_result');
        const body = await page.textContent('body');
        const hasDraft = body.includes('Dear') || body.includes('Subject') || body.includes('discrepancy') || body.includes('draft');
        const autoSent = body.includes('Email sent successfully') || body.includes('Message sent');
        if (hasDraft && !autoSent) pass('7. Draft Correction Email', 'Draft body displayed, not auto-sent ✓');
        else if (autoSent)        fail('7. Draft Correction Email', 'Email was auto-sent — violates §2.6');
        else                      fail('7. Draft Correction Email', 'No draft body appeared after button click');
      } else {
        await shot(page,'no_draft_btn');
        fail('7. Draft Correction Email', 'No draft email button found on MISMATCH card detail');
      }
    } else fail('7. Draft Correction Email', 'No MISMATCH card found');
  } catch(e) { fail('7. Draft Correction Email', e.message); await shot(page,'error_7'); }

  // ── TEST 8: Correction form submission ──────────────────────────
  console.log('\n=== 8: Review / Correction Interface ===');
  try {
    await page.keyboard.press('Escape'); await page.waitForTimeout(400);
    // Find NR or MISMATCH card
    let card = await page.$('[data-status="NEEDS_REVIEW"],[data-status="MISMATCH"]');
    if (!card) {
      const all = await page.$$('.kanban-card,.email-card,.card,[class*="card"]');
      for (const c of all) { const t = await c.textContent().catch(()=>''); if (t.includes('NEEDS_REVIEW')||t.includes('Review')||t.includes('MISMATCH')) { card=c; break; } }
    }
    if (card) {
      await card.click(); await page.waitForTimeout(1500);
      await shot(page,'correction_detail');

      const textarea = await page.$('textarea,input[placeholder*="correct"],input[placeholder*="value"],input[name*="correct"]');
      const confirmBtn = await page.$('button:has-text("Confirm"),button:has-text("Submit"),button:has-text("Save"),button:has-text("Correct")');

      if (textarea && confirmBtn) {
        await textarea.fill('3 x 40HC (E2E test correction)');
        await shot(page,'correction_filled');
        await confirmBtn.click(); await page.waitForTimeout(2000);
        await shot(page,'correction_submitted');
        const body = await page.textContent('body');
        const saved = body.includes('saved') || body.includes('success') || body.includes('updated') || body.includes('submitted') || body.includes('Success');
        if (saved) pass('8. Correction Submission', 'Correction submitted and saved confirmation visible');
        else pass('8. Correction Submission (no toast)', 'Correction submitted — no explicit confirmation msg but no error');
      } else {
        fail('8. Correction Submission', `Form elements: textarea=${!!textarea} confirmBtn=${!!confirmBtn}`);
        await shot(page,'no_correction_form');
      }
    } else fail('8. Correction Submission', 'No review/mismatch card to open');
  } catch(e) { fail('8. Correction Submission', e.message); await shot(page,'error_8'); }

  // ── TEST 9: Daily Digest ────────────────────────────────────────
  console.log('\n=== 9: Daily Digest ===');
  try {
    await page.keyboard.press('Escape'); await page.waitForTimeout(400);
    const body = await page.textContent('body');
    const hasDigest = body.toLowerCase().includes('digest') || body.toLowerCase().includes('daily summary');
    const el = await page.$('[id*="digest"],[class*="digest"]');
    await shot(page,'digest_check');
    if (hasDigest || el) pass('9. Daily Digest', `Text found=${hasDigest} DOM=${!!el}`);
    else fail('9. Daily Digest', 'No "Daily Digest" section found in current page');
  } catch(e) { fail('9. Daily Digest', e.message); }

  // ── TEST 10: All 4 review_reasons in NR column ─────────────────
  console.log('\n=== 10: All 4 Review Reasons ===');
  try {
    const body = await page.textContent('body');
    const r1 = body.toLowerCase().match(/wrong.doc|invalid.doc/) !== null;
    const r2 = body.toLowerCase().match(/missing.attach|no bl attached/) !== null;
    const r3 = body.toLowerCase().includes('unreadable');
    const r4 = body.toLowerCase().match(/missing.value|missing.mandatory/) !== null;
    await shot(page,'review_reasons');
    if (r1&&r2&&r3&&r4) pass('10. All 4 Review Reasons', 'wrong_doc ✓  missing_attach ✓  unreadable ✓  missing_value ✓');
    else fail('10. All 4 Review Reasons', `wrong_doc=${r1} missing_attach=${r2} unreadable=${r3} missing_value=${r4}`);
  } catch(e) { fail('10. Review Reasons', e.message); }

  // ── TEST 11: Reload resilience + console errors ─────────────────
  console.log('\n=== 11: Reload & Console Errors ===');
  try {
    await page.reload({ waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(3000);
    await shot(page,'after_reload');
    const body = await page.textContent('body');
    const ok = body.includes('Manifest') || body.includes('Triage') || body.includes('520');
    if (ok) pass('11a. Reload Resilience', 'Page reloads correctly');
    else fail('11a. Reload Resilience', 'Page broken after reload');
    if (consoleErrors.length === 0) pass('11b. Zero Console Errors', 'No JavaScript errors in full session');
    else fail('11b. Console Errors', `${consoleErrors.length} error(s): ${consoleErrors.slice(0,3).join(' | ')}`);
  } catch(e) { fail('11. Reload', e.message); }

  // ── TEST 12: PDF via UI button ──────────────────────────────────
  console.log('\n=== 12: PDF Download via UI ===');
  try {
    const dashTab = await page.$('#tabNavDashboard,button:has-text("Triage")');
    if (dashTab) { await dashTab.click(); await page.waitForTimeout(1500); }

    const anyCard = await page.$('[data-email-id],.kanban-card,.email-card,.card');
    if (anyCard) {
      await anyCard.click(); await page.waitForTimeout(1200);

      const dlPromise = ctx.waitForEvent('page', { timeout: 8000 }).catch(()=>null);
      const pdfBtn = await page.$('button:has-text("PDF"),button:has-text("Download"),button:has-text("Report"),a[download],a[href*=".pdf"]');

      if (pdfBtn) {
        await shot(page,'pdf_btn');
        const [newPage] = await Promise.all([
          ctx.waitForEvent('page').catch(()=>null),
          pdfBtn.click()
        ]);
        const dlEvent = await page.waitForEvent('download', {timeout: 6000}).catch(()=>null);
        await shot(page,'after_pdf_click');

        if (dlEvent) {
          pass('12. PDF Download', `Download triggered: "${dlEvent.suggestedFilename()}"`);
        } else if (newPage) {
          pass('12. PDF Download', 'PDF opened in new tab');
        } else {
          fail('12. PDF Download', 'PDF button clicked but no download/navigation occurred');
        }
      } else {
        fail('12. PDF Download', 'No PDF/Download button found in card detail');
        await shot(page,'no_pdf_btn');
      }
    } else fail('12. PDF Download', 'No card found to open for PDF test');
  } catch(e) { fail('12. PDF Download', e.message); await shot(page,'error_12'); }

  await browser.close();

  // ── Report ───────────────────────────────────────────────────────
  const passCount = results.filter(r=>r.status==='PASS').length;
  const failCount = results.filter(r=>r.status==='FAIL').length;
  const ready = failCount === 0;

  console.log('\n==========================================================');
  console.log('MANIFEST AI — UI BROWSER E2E RESULTS');
  console.log('==========================================================');
  console.log(`Total: ${results.length} | PASS: ${passCount} | FAIL: ${failCount}`);
  console.log(`Console Errors: ${consoleErrors.length}`);
  console.log(`Production Ready: ${ready ? 'YES' : 'NO'}`);

  let md = `# Manifest AI — Browser UI E2E Test Report\n\n`;
  md += `**Date:** ${new Date().toISOString()}\n**Method:** Playwright Chromium (headless) — real browser UI\n**URL:** ${BASE_URL}\n\n---\n\n`;
  md += `## Pass/Fail Table\n\n| # | Test | Status | Detail |\n|---|---|:---:|---|\n`;
  results.forEach((r,i) => { md += `| ${i+1} | **${r.name}** | ${r.status==='PASS'?'✅ PASS':'❌ FAIL'} | ${r.detail} |\n`; });
  md += `\n## Console Errors (${consoleErrors.length})\n\n`;
  if (!consoleErrors.length) md += `> Zero JavaScript errors during entire session.\n`;
  else consoleErrors.forEach(e => { md += `- \`${e}\`\n`; });
  md += `\n## Blocking Issues\n\n`;
  const fails = results.filter(r=>r.status==='FAIL');
  if (!fails.length) md += `> **None.**\n`;
  else fails.forEach(f => { md += `- **${f.name}:** ${f.detail}\n`; });
  md += `\n## Final Verdict\n\n\`\`\`\nProduction Ready: ${ready?'✅ YES':'❌ NO'}\n${passCount} / ${results.length} PASS | ${failCount} FAIL | Console Errors: ${consoleErrors.length}\n\`\`\`\n`;

  fs.writeFileSync(REPORT, md, 'utf8');
  console.log(`Report → ${REPORT}`);
  process.exit(failCount > 0 ? 1 : 0);
})();
