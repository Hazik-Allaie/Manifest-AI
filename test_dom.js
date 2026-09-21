const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://manifest-ai-509207.web.app', { waitUntil: 'networkidle' });
  
  // Find all buttons, inputs, cards
  const buttons = await page.$$eval('button', els => els.map(e => ({ text: e.innerText.trim(), id: e.id, class: e.className })));
  const inputs = await page.$$eval('input, textarea', els => els.map(e => ({ tag: e.tagName, type: e.type, id: e.id, class: e.className, placeholder: e.placeholder })));
  
  console.log('=== BUTTONS COUNT ===', buttons.length);
  console.log('Sample buttons:', JSON.stringify(buttons.slice(0, 15), null, 2));
  console.log('=== INPUTS COUNT ===', inputs.length);
  console.log('Inputs:', JSON.stringify(inputs, null, 2));
  
  const modalCorr = await page.$eval('#modalCorrection', el => ({ class: el.className, text: el.innerText })).catch(e => e.message);
  console.log('modalCorrection element:', modalCorr);
  
  await browser.close();
})();
