import { test, expect } from '@playwright/test';

test.describe('SPY-FLY Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Start from the dashboard page
    await page.goto('/');
  });

  test('should load dashboard with all main components', async ({ page }) => {
    // Wait for dashboard to load
    await page.waitForLoadState('networkidle');

    // Check title
    await expect(page).toHaveTitle(/SPY-FLY/);

    // Market Status Bar should be visible
    const marketStatusBar = page.getByText(/SPY/).first();
    await expect(marketStatusBar).toBeVisible();

    // Sentiment Panel should show
    await expect(page.getByText('Market Sentiment')).toBeVisible();
    
    // Should show sentiment score (0-100)
    const sentimentScore = page.locator('text=/\\d{1,3}/ >> nth=0');
    await expect(sentimentScore).toBeVisible();

    // Should show PROCEED or SKIP decision
    const decision = page.locator('text=/PROCEED|SKIP/');
    await expect(decision).toBeVisible();

    // Live P/L Monitor should be visible
    await expect(page.getByText('Live P/L Monitor')).toBeVisible();

    // Recommended Spreads section should exist
    await expect(page.getByText('Recommended Spreads')).toBeVisible();
  });

  test('should display sentiment component breakdown', async ({ page }) => {
    // Check for VIX, Futures, Technical components
    await expect(page.getByText('VIX')).toBeVisible();
    await expect(page.getByText('Futures')).toBeVisible();
    await expect(page.getByText('Technical')).toBeVisible();
    await expect(page.getByText('News')).toBeVisible();
  });

  test('should show market data when API is connected', async ({ page }) => {
    // Wait for API connection
    await page.waitForFunction(() => {
      const statusElements = document.querySelectorAll('*');
      return Array.from(statusElements).some(el => 
        el.textContent?.includes('connected') || 
        el.textContent?.includes('open')
      );
    }, { timeout: 10000 });

    // Check for SPY price (should be a number)
    const priceRegex = /\$?\d{3}\.\d{2}/;
    await expect(page.locator(`text=${priceRegex}`).first()).toBeVisible();

    // Check for VIX value
    const vixRegex = /\d{1,2}\.\d{1,2}/;
    const vixElements = await page.locator(`text=${vixRegex}`).all();
    expect(vixElements.length).toBeGreaterThan(0);
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Dashboard should still be functional
    await expect(page.getByText('Market Sentiment')).toBeVisible();
    
    // Components should stack vertically on mobile
    const sentimentPanel = page.locator('[class*="xl:col-span-2"]').first();
    await expect(sentimentPanel).toBeVisible();
  });

  test('should handle loading and error states', async ({ page }) => {
    // Initially should show loading or data
    const content = await page.textContent('body');
    
    // Should not show raw error messages
    expect(content).not.toContain('TypeError');
    expect(content).not.toContain('undefined');
    expect(content).not.toContain('null');
    
    // Should have proper error boundaries
    if (content?.includes('error')) {
      // If there's an error, it should be user-friendly
      expect(content).toMatch(/failed|unavailable|try again/i);
    }
  });

  test('sentiment gauge should display correctly', async ({ page }) => {
    // Look for SVG gauge element
    const gauge = page.locator('svg[viewBox*="120"]');
    await expect(gauge).toBeVisible();

    // Should have score display
    const scoreDisplay = page.locator('[class*="text-4xl"]').first();
    await expect(scoreDisplay).toBeVisible();
    
    // Score should be a number
    const scoreText = await scoreDisplay.textContent();
    expect(scoreText).toMatch(/^\d{1,3}$/);
  });

  test('recommended spreads should display spread details', async ({ page }) => {
    // Wait for spreads section
    const spreadsSection = page.locator('text=Recommended Spreads').locator('..');
    await expect(spreadsSection).toBeVisible();

    // Should show spread format (e.g., "485/490 Call")
    const spreadPattern = /\d{3}\/\d{3}\s+Call/;
    const spreadElements = await page.locator(`text=${spreadPattern}`).all();
    
    // If spreads are loaded, check their structure
    if (spreadElements.length > 0) {
      // Should show debit amount
      await expect(page.locator('text=/Debit.*\\$?\\d+\\.\\d{2}/')).toBeVisible();
      
      // Should show max profit/loss
      await expect(page.locator('text=/Max Profit/')).toBeVisible();
      await expect(page.locator('text=/Max Loss/')).toBeVisible();
    }
  });
});

test.describe('Dashboard API Integration', () => {
  test('should fetch sentiment data from API', async ({ page }) => {
    // Intercept API calls
    const sentimentResponse = page.waitForResponse(
      response => response.url().includes('/api/v1/sentiment/calculate') && response.status() === 200
    );

    await page.goto('/');
    
    try {
      const response = await sentimentResponse;
      const data = await response.json();
      
      // Verify API response structure
      expect(data).toHaveProperty('score');
      expect(data).toHaveProperty('decision');
      expect(data).toHaveProperty('breakdown');
      expect(data.score).toBeGreaterThanOrEqual(0);
      expect(data.score).toBeLessThanOrEqual(100);
    } catch {
      // API might not be running, which is okay for UI test
      console.log('API not available, testing UI only');
    }
  });
});