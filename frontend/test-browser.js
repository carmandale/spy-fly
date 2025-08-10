const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Capture console messages
  page.on('console', msg => {
    console.log(`[${msg.type()}]`, msg.text());
  });
  
  // Capture page errors
  page.on('pageerror', error => {
    console.error('Page error:', error.message);
  });
  
  // Navigate to the app
  await page.goto('http://localhost:3003');
  
  // Wait a bit to see any errors
  await page.waitForTimeout(5000);
  
  // Try to get any error messages from the page
  const bodyText = await page.textContent('body');
  console.log('Page body text:', bodyText);
  
  // Check if root div has content
  const rootContent = await page.evaluate(() => {
    const root = document.getElementById('root');
    return root ? root.innerHTML : 'Root not found';
  });
  console.log('Root div content:', rootContent);
  
  // Keep browser open for inspection
  console.log('Browser will stay open. Press Ctrl+C to exit.');
})();