import { test, expect } from '@playwright/test';

test('dashboard loads without errors', async ({ page }) => {
  // Navigate to the dashboard
  await page.goto('/');
  
  // Wait for any loading to complete
  await page.waitForLoadState('networkidle');
  
  // Check that we're not showing an error page
  const bodyText = await page.textContent('body');
  expect(bodyText).not.toContain('Error');
  expect(bodyText).not.toContain('Failed to fetch');
  
  // Dashboard should contain SPY-FLY branding or title
  const title = await page.title();
  expect(title.toLowerCase()).toContain('spy');
  
  // Take a screenshot for visual verification
  await page.screenshot({ path: 'dashboard-screenshot.png', fullPage: true });
  
  console.log('✅ Dashboard loaded successfully!');
});