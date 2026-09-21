const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });

  const page = await context.newPage();
  console.log('Navigating to live URL: https://manifest-ai-509207.web.app');
  await page.goto('https://manifest-ai-509207.web.app', { waitUntil: 'networkidle' });

  // Switch to dashboard view
  console.log('Switching to dashboard view...');
  await page.locator('#tabNavDashboard').click();
  await page.waitForTimeout(1500);

  // Click btnAnalyticsAccuracy in the left sidebar
  console.log('Clicking #btnAnalyticsAccuracy...');
  const btnAnalytics = page.locator('#btnAnalyticsAccuracy');
  await btnAnalytics.waitFor({ state: 'visible' });
  await btnAnalytics.click();

  // Wait for modalAnalytics to be visible
  const modal = page.locator('#modalAnalytics');
  await modal.waitFor({ state: 'visible' });
  await page.waitForTimeout(1000);

  // Screenshot modal window
  const modalWindow = page.locator('#modalAnalytics .modal-window');
  const modalWindowPath = path.resolve(
    'C:/Users/Admin/.gemini/antigravity-ide/brain/6b431429-6bb9-417b-a483-5541de997865/accuracy_progression_modal_window.png'
  );
  await modalWindow.screenshot({ path: modalWindowPath });
  console.log('Saved modal window screenshot to:', modalWindowPath);

  // Screenshot full view
  const fullPath = path.resolve(
    'C:/Users/Admin/.gemini/antigravity-ide/brain/6b431429-6bb9-417b-a483-5541de997865/accuracy_progression_full.png'
  );
  await page.screenshot({ path: fullPath });
  console.log('Saved full screenshot to:', fullPath);

  // Inspect on-screen elements
  const values = await page.evaluate(() => {
    return {
      stage1F1: document.getElementById('benchStage1F1')?.textContent,
      stage1Sub: document.getElementById('benchStage1Sub')?.textContent,
      stage3F1: document.getElementById('benchStage3F1')?.textContent,
      stage3Sub: document.getElementById('benchStage3Sub')?.textContent,
      endToEndScore: document.getElementById('benchEndToEndScore')?.textContent,
      endToEndSub: document.getElementById('benchEndToEndSub')?.textContent,
      formulaScore: document.getElementById('benchFormulaScore')?.textContent,
      prodLabelDashboard: document.getElementById('kpiSparklineProdLabel')?.textContent,
      benchmarkSubtextDashboard: document.getElementById('kpiBenchmarkSubtext')?.textContent
    };
  });
  console.log('\n--- EXTRACTED MODAL & DASHBOARD VALUES ---');
  console.log(JSON.stringify(values, null, 2));
  console.log('------------------------------------------\n');

  await browser.close();
  console.log('Verification finished successfully!');
})();
