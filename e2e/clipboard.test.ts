import { test, expect, type BrowserContext } from '@playwright/test'

// Helper to grant clipboard permissions
async function grantClipboardPermissions(context: BrowserContext) {
	await context.grantPermissions(['clipboard-read', 'clipboard-write'])
}

test.describe('Clipboard Functionality', () => {
	test.beforeEach(async ({ page, context }) => {
		// Grant clipboard permissions for Chromium-based browsers
		await grantClipboardPermissions(context)
		
		// Navigate to the demo page
		// Note: Update this URL when the demo is integrated into the app
		await page.goto('/execution/demo')
	})

	test.describe('Cross-Browser Clipboard Tests', () => {
		test('should copy text using Clipboard API in modern browsers', async ({ page, browserName }) => {
			// Find and click the basic copy button
			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			await copyButton.click()

			// Check for success state
			await expect(copyButton).toContainText('Copied!')
			
			// Verify toast notification appears
			await expect(page.getByText('Order copied!')).toBeVisible()

			// For Chromium-based browsers, we can verify clipboard content
			if (browserName === 'chromium' || browserName === 'webkit') {
				const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
				expect(clipboardText).toBe('Simple text to copy')
			}
		})

		test('should handle permission denied gracefully', async ({ page, context }) => {
			// Revoke clipboard permissions
			await context.clearPermissions()

			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			
			// Try to copy without permissions
			await copyButton.click()

			// Should show permission denied state
			await expect(copyButton).toContainText('Permission denied')
			
			// Should show error toast
			await expect(page.getByText('Copy failed')).toBeVisible()
		})

		test('should work with different button sizes', async ({ page }) => {
			// Test small button
			const smallButton = page.getByRole('button', { name: /Copy/ }).filter({ hasText: 'Copy' }).nth(3)
			await smallButton.click()
			await expect(smallButton).toContainText('Copied!')

			// Test large button
			const largeButton = page.getByRole('button', { name: /Copy/ }).filter({ hasText: 'Copy' }).nth(5)
			await largeButton.click()
			await expect(largeButton).toContainText('Copied!')
		})

		test('should copy complex order ticket data', async ({ page, browserName }) => {
			// Find the order ticket copy button
			const orderButton = page.getByRole('button', { name: 'Copy Order Ticket' })
			await orderButton.click()

			// Check for success
			await expect(orderButton).toContainText('Order Ticket Copied!')
			
			// Verify toast
			await expect(page.getByText('Order copied!')).toBeVisible()

			// Verify clipboard content for supported browsers
			if (browserName === 'chromium' || browserName === 'webkit') {
				const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
				expect(clipboardText).toContain('VERTICAL SPREAD ORDER')
				expect(clipboardText).toContain('Symbol: SPY')
				expect(clipboardText).toContain('Max Risk: $470')
			}
		})

		test('should reset to initial state after timeout', async ({ page }) => {
			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			
			// Click to copy
			await copyButton.click()
			await expect(copyButton).toContainText('Copied!')

			// Wait for reset (2 seconds + buffer)
			await page.waitForTimeout(2500)
			
			// Should be back to initial state
			await expect(copyButton).toContainText('Copy')
		})

		test('should handle multiple rapid clicks', async ({ page }) => {
			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			
			// Click multiple times rapidly
			await copyButton.click()
			await copyButton.click()
			await copyButton.click()

			// Should still show success state
			await expect(copyButton).toContainText('Copied!')
			
			// Should only show one toast (latest)
			const toasts = page.locator('[role="alert"]')
			await expect(toasts).toHaveCount(1)
		})

		test('should not copy when button is disabled', async ({ page }) => {
			// Find the disabled button
			const disabledButton = page.getByRole('button', { name: /Copy/, disabled: true })
			
			// Verify it's disabled
			await expect(disabledButton).toBeDisabled()
			
			// Try to click (should have no effect)
			await disabledButton.click({ force: true })
			
			// Should not change state
			await expect(disabledButton).toContainText('Copy')
			
			// No toast should appear
			await expect(page.getByRole('alert')).not.toBeVisible()
		})

		test('should be keyboard accessible', async ({ page }) => {
			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			
			// Focus the button
			await copyButton.focus()
			
			// Press Enter to activate
			await page.keyboard.press('Enter')
			
			// Should show success state
			await expect(copyButton).toContainText('Copied!')
		})

		test('should work with custom styling variants', async ({ page }) => {
			// Test outline variant
			const outlineButton = page.getByRole('button', { name: /Copy/ }).filter({ hasText: 'Copy' }).nth(7)
			await outlineButton.click()
			await expect(outlineButton).toContainText('Copied!')

			// Reset
			await page.waitForTimeout(2500)

			// Test ghost variant
			const ghostButton = page.getByRole('button', { name: /Copy/ }).filter({ hasText: 'Copy' }).nth(8)
			await ghostButton.click()
			await expect(ghostButton).toContainText('Copied!')
		})

		test('should close toast notifications', async ({ page }) => {
			// Trigger a copy to show toast
			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			await copyButton.click()

			// Wait for toast to appear
			const toast = page.getByRole('alert')
			await expect(toast).toBeVisible()

			// Click close button on toast
			const closeButton = page.getByLabel('Close notification')
			await closeButton.click()

			// Toast should disappear
			await expect(toast).not.toBeVisible()
		})
	})

	test.describe('Browser-Specific Tests', () => {
		test('should display browser compatibility info', async ({ page }) => {
			// Check that browser info section exists
			const browserInfo = page.locator('text=Browser Information').locator('..')
			await expect(browserInfo).toBeVisible()

			// Verify it shows clipboard API availability
			const clipboardInfo = browserInfo.locator('text=Clipboard API Available')
			await expect(clipboardInfo).toBeVisible()
		})

		test.skip(({ browserName }) => browserName !== 'chromium', 'Chromium-specific clipboard test')
		test('should handle clipboard API in Chromium', async ({ page }) => {
			// This test specifically checks Chromium's clipboard implementation
			const hasClipboardAPI = await page.evaluate(() => !!navigator.clipboard)
			expect(hasClipboardAPI).toBe(true)

			// Test writing and reading
			await page.evaluate(() => navigator.clipboard.writeText('Test from Chromium'))
			const text = await page.evaluate(() => navigator.clipboard.readText())
			expect(text).toBe('Test from Chromium')
		})

		test.skip(({ browserName }) => browserName !== 'firefox', 'Firefox-specific clipboard test')
		test('should handle clipboard in Firefox', async ({ page }) => {
			// Firefox may have different clipboard behavior
			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			await copyButton.click()

			// Firefox might use fallback mechanism
			await expect(copyButton).toContainText('Copied!')
		})

		test.skip(({ browserName }) => browserName !== 'webkit', 'Safari-specific clipboard test')
		test('should handle clipboard in Safari/WebKit', async ({ page }) => {
			// Safari/WebKit specific test
			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			await copyButton.click()

			// Check Safari handles it correctly
			await expect(copyButton).toContainText('Copied!')
		})
	})

	test.describe('Mobile Browser Simulation', () => {
		test('should work on mobile viewport', async ({ page }) => {
			// Set mobile viewport
			await page.setViewportSize({ width: 375, height: 667 })

			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			await copyButton.click()

			await expect(copyButton).toContainText('Copied!')
			
			// Toast should be visible on mobile
			await expect(page.getByRole('alert')).toBeVisible()
		})

		test('should handle touch events', async ({ page }) => {
			// Simulate touch device
			await page.setViewportSize({ width: 375, height: 667 })

			const copyButton = page.getByRole('button', { name: /^Copy$/ }).first()
			
			// Tap instead of click
			await copyButton.tap()

			await expect(copyButton).toContainText('Copied!')
		})
	})
})