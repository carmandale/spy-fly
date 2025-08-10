import { chromium } from 'playwright';

async function testApp() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const errors = [];
  const consoleLogs = [];
  
  // Capture console messages
  page.on('console', msg => {
    const logEntry = `[${msg.type()}] ${msg.text()}`;
    consoleLogs.push(logEntry);
    if (msg.type() === 'error') {
      console.log('❌ Console Error:', msg.text());
    }
  });
  
  // Capture page errors
  page.on('pageerror', error => {
    errors.push(error.message);
    console.log('❌ Page Error:', error.message);
  });
  
  console.log('📱 Testing SimpleApp first...');
  await page.goto('http://localhost:3003');
  await page.waitForTimeout(1000);
  
  const simpleAppText = await page.textContent('body');
  console.log('✅ SimpleApp renders:', simpleAppText.trim());
  
  // Now let's test the real App
  console.log('\n📱 Now testing the real Dashboard...');
  
  // First, let's modify main.tsx back to use App
  await page.evaluate(() => {
    console.log('Attempting to import Dashboard dynamically...');
    return import('/src/components/Dashboard.tsx')
      .then(module => {
        console.log('Dashboard module loaded:', Object.keys(module));
        return 'Dashboard loaded successfully';
      })
      .catch(err => {
        console.error('Failed to load Dashboard:', err);
        throw err;
      });
  }).then(result => {
    console.log('✅', result);
  }).catch(err => {
    console.log('❌ Import failed:', err.message);
  });
  
  // Check what's in the page
  const rootContent = await page.evaluate(() => {
    const root = document.getElementById('root');
    return root ? root.innerHTML.substring(0, 200) : 'No root element';
  });
  console.log('\n📄 Root element content:', rootContent);
  
  // Print all console logs
  if (consoleLogs.length > 0) {
    console.log('\n📋 All console logs:');
    consoleLogs.forEach(log => console.log('  ', log));
  }
  
  if (errors.length > 0) {
    console.log('\n❌ Errors found:', errors);
  }
  
  await browser.close();
}

testApp().catch(console.error);