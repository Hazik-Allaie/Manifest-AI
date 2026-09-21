const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const downloadDir = path.resolve(__dirname, 'downloads_test');
  if (!fs.existsSync(downloadDir)) {
    fs.mkdirSync(downloadDir, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    permissions: ['clipboard-read', 'clipboard-write'],
    viewport: { width: 1440, height: 900 },
    acceptDownloads: true
  });

  const page = await context.newPage();
  console.log('Navigating to live URL: https://manifest-ai-509207.web.app');
  await page.goto('https://manifest-ai-509207.web.app', { waitUntil: 'networkidle' });

  // Switch to dashboard view
  console.log('Switching to dashboard view...');
  await page.locator('#tabNavDashboard').click();
  await page.waitForTimeout(1500);

  // Click btnDailyDigest
  console.log('Clicking #btnDailyDigest...');
  const digestBtn = page.locator('#btnDailyDigest');
  await digestBtn.waitFor({ state: 'visible' });
  await digestBtn.click();

  // Wait for modalDailyDigest to be active
  const modal = page.locator('#modalDailyDigest');
  await modal.waitFor({ state: 'visible' });
  await page.waitForTimeout(1000);

  // Take screenshot of the modal
  const screenshotPath = path.resolve(
    'C:/Users/Admin/.gemini/antigravity-ide/brain/6b431429-6bb9-417b-a483-5541de997865/daily_digest_modal_verified.png'
  );
  await page.screenshot({ path: screenshotPath });
  console.log('Saved screenshot to:', screenshotPath);

  // Also take a zoomed screenshot of the modal window specifically
  const modalWindow = page.locator('#modalDailyDigest .modal-window');
  const modalWindowPath = path.resolve(
    'C:/Users/Admin/.gemini/antigravity-ide/brain/6b431429-6bb9-417b-a483-5541de997865/daily_digest_modal_window.png'
  );
  await modalWindow.screenshot({ path: modalWindowPath });
  console.log('Saved modal window screenshot to:', modalWindowPath);

  // 1. Test Copy Summary
  console.log('Clicking Copy Summary button...');
  const copyBtn = page.locator('#btnDigestCopySummary');
  await copyBtn.click();
  await page.waitForTimeout(500);

  // Read clipboard text
  const clipboardText = await page.evaluate(async () => {
    try {
      return await navigator.clipboard.readText();
    } catch (e) {
      return 'CLIPBOARD_ERROR: ' + e.message;
    }
  });
  console.log('\n--- CLIPBOARD TEXT ---');
  console.log(clipboardText);
  console.log('----------------------\n');

  // Also test pasting into an input element to verify genuine paste
  const pasteTest = await page.evaluate(async () => {
    const input = document.createElement('textarea');
    document.body.appendChild(input);
    input.focus();
    const clip = await navigator.clipboard.readText();
    input.value = clip;
    const val = input.value;
    document.body.removeChild(input);
    return { length: val.length, preview: val.substring(0, 100) };
  });
  console.log('Paste verification:', pasteTest);

  // 2. Test Download JSON
  console.log('Testing Download JSON...');
  const [jsonDownload] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('#btnDigestExportJSON').click()
  ]);
  const jsonSavePath = path.join(downloadDir, 'daily_manifest_digest.json');
  await jsonDownload.saveAs(jsonSavePath);
  console.log('Saved JSON to:', jsonSavePath);
  const jsonContent = fs.readFileSync(jsonSavePath, 'utf-8');
  console.log('\n--- JSON CONTENT (FIRST 500 CHARS) ---');
  console.log(jsonContent.substring(0, 500));
  console.log('-------------------------------------\n');

  // Also copy JSON to artifacts directory so user can link/inspect
  const artifactJsonPath = path.resolve(
    'C:/Users/Admin/.gemini/antigravity-ide/brain/6b431429-6bb9-417b-a483-5541de997865/daily_manifest_digest.json'
  );
  fs.writeFileSync(artifactJsonPath, jsonContent);

  // 3. Test Download CSV
  console.log('Testing Download CSV...');
  const [csvDownload] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('#btnDigestExportCSV').click()
  ]);
  const csvSavePath = path.join(downloadDir, 'daily_manifest_digest.csv');
  await csvDownload.saveAs(csvSavePath);
  console.log('Saved CSV to:', csvSavePath);
  const csvContent = fs.readFileSync(csvSavePath, 'utf-8');
  console.log('\n--- CSV CONTENT ---');
  console.log(csvContent);
  console.log('-------------------\n');

  // Also copy CSV to artifacts directory
  const artifactCsvPath = path.resolve(
    'C:/Users/Admin/.gemini/antigravity-ide/brain/6b431429-6bb9-417b-a483-5541de997865/daily_manifest_digest.csv'
  );
  fs.writeFileSync(artifactCsvPath, csvContent);

  // Extract modal on-screen values
  const onScreenValues = await page.evaluate(() => {
    return {
      totalIngested: document.getElementById('digestTotalIngested')?.textContent,
      clearanceRate: document.getElementById('digestClearanceRate')?.textContent,
      mismatchesCount: document.getElementById('digestMismatchesCount')?.textContent,
      bodyText: document.getElementById('dailyDigestContent')?.innerText
    };
  });
  console.log('On-screen modal values:', onScreenValues);

  await browser.close();
  console.log('Verification completed successfully!');
})();
