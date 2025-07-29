import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CopyButton } from '../../../components/execution/CopyButton'

describe('CopyButton', () => {
	// Mock clipboard API
	const mockWriteText = vi.fn()
	const originalClipboard = navigator.clipboard

	beforeEach(() => {
		// Reset mocks
		mockWriteText.mockReset()
		
		// Mock navigator.clipboard
		Object.defineProperty(navigator, 'clipboard', {
			value: {
				writeText: mockWriteText
			},
			writable: true,
			configurable: true
		})
	})

	afterEach(() => {
		// Restore original clipboard
		Object.defineProperty(navigator, 'clipboard', {
			value: originalClipboard,
			writable: true,
			configurable: true
		})
	})

	describe('Success States', () => {
		it('should render with initial state', () => {
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			expect(button).toBeInTheDocument()
			expect(button).toHaveTextContent(/copy/i)
			expect(button).not.toBeDisabled()
		})

		it('should copy text to clipboard on click', async () => {
			mockWriteText.mockResolvedValueOnce(undefined)
			
			render(<CopyButton text="Test text to copy" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			expect(mockWriteText).toHaveBeenCalledWith('Test text to copy')
			expect(mockWriteText).toHaveBeenCalledTimes(1)
		})

		it('should show success state after successful copy', async () => {
			mockWriteText.mockResolvedValueOnce(undefined)
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			// Should show success state
			await waitFor(() => {
				expect(button).toHaveTextContent(/copied/i)
			})
			
			// Button should show checkmark icon
			expect(screen.getByTestId('copy-success-icon')).toBeInTheDocument()
		})

		it('should reset to initial state after success timeout', async () => {
			mockWriteText.mockResolvedValueOnce(undefined)
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			// Wait for success state
			await waitFor(() => {
				expect(button).toHaveTextContent(/copied/i)
			})
			
			// Wait for reset (default 2 seconds)
			await waitFor(() => {
				expect(button).toHaveTextContent(/copy/i)
			}, { timeout: 3000 })
		})

		it('should accept custom button text', () => {
			render(<CopyButton text="Test text" buttonText="Copy Order" />)
			
			expect(screen.getByRole('button')).toHaveTextContent('Copy Order')
		})

		it('should accept custom success text', async () => {
			mockWriteText.mockResolvedValueOnce(undefined)
			
			render(<CopyButton text="Test text" successText="Order Copied!" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(button).toHaveTextContent('Order Copied!')
			})
		})

		it('should handle custom onCopy callback', async () => {
			mockWriteText.mockResolvedValueOnce(undefined)
			const onCopy = vi.fn()
			
			render(<CopyButton text="Test text" onCopy={onCopy} />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(onCopy).toHaveBeenCalledWith(true)
			})
		})
	})

	describe('Error States', () => {
		it('should show error state when clipboard write fails', async () => {
			mockWriteText.mockRejectedValueOnce(new Error('Clipboard error'))
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(button).toHaveTextContent(/failed/i)
			})
			
			// Should show error icon
			expect(screen.getByTestId('copy-error-icon')).toBeInTheDocument()
		})

		it('should handle permission denied error', async () => {
			const error = new DOMException('The request is not allowed', 'NotAllowedError')
			mockWriteText.mockRejectedValueOnce(error)
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(button).toHaveTextContent(/permission denied/i)
			})
		})

		it('should call onCopy with false on error', async () => {
			mockWriteText.mockRejectedValueOnce(new Error('Clipboard error'))
			const onCopy = vi.fn()
			
			render(<CopyButton text="Test text" onCopy={onCopy} />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(onCopy).toHaveBeenCalledWith(false)
			})
		})

		it('should reset to initial state after error timeout', async () => {
			mockWriteText.mockRejectedValueOnce(new Error('Clipboard error'))
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			// Wait for error state
			await waitFor(() => {
				expect(button).toHaveTextContent(/failed/i)
			})
			
			// Wait for reset
			await waitFor(() => {
				expect(button).toHaveTextContent(/copy/i)
			}, { timeout: 3000 })
		})

		it('should accept custom error text', async () => {
			mockWriteText.mockRejectedValueOnce(new Error('Clipboard error'))
			
			render(<CopyButton text="Test text" errorText="Copy Error!" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(button).toHaveTextContent('Copy Error!')
			})
		})
	})

	describe('Loading State', () => {
		it('should show loading state during copy operation', async () => {
			let resolvePromise: () => void
			const promise = new Promise<void>((resolve) => {
				resolvePromise = resolve
			})
			mockWriteText.mockReturnValueOnce(promise)
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			// Should be disabled during operation
			expect(button).toBeDisabled()
			
			// Should show loading spinner
			expect(screen.getByTestId('copy-loading-icon')).toBeInTheDocument()
			
			// Resolve the promise
			resolvePromise!()
			
			// Should re-enable after operation
			await waitFor(() => {
				expect(button).not.toBeDisabled()
			})
		})
	})

	describe('Props and Customization', () => {
		it('should apply custom className', () => {
			render(<CopyButton text="Test text" className="custom-class" />)
			
			const button = screen.getByRole('button')
			expect(button).toHaveClass('custom-class')
		})

		it('should apply custom size', () => {
			render(<CopyButton text="Test text" size="sm" />)
			
			const button = screen.getByRole('button')
			expect(button).toHaveClass('h-8')
		})

		it('should apply custom variant', () => {
			render(<CopyButton text="Test text" variant="outline" />)
			
			const button = screen.getByRole('button')
			expect(button).toHaveClass('border')
		})

		it('should respect disabled prop', () => {
			render(<CopyButton text="Test text" disabled />)
			
			const button = screen.getByRole('button')
			expect(button).toBeDisabled()
			
			// Should not call clipboard API when disabled
			fireEvent.click(button)
			expect(mockWriteText).not.toHaveBeenCalled()
		})

		it('should show tooltip when provided', () => {
			render(<CopyButton text="Test text" tooltip="Click to copy order details" />)
			
			// Note: Tooltip testing would depend on the specific tooltip implementation
			// This is a placeholder for tooltip testing
			expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Click to copy order details')
		})
	})

	describe('Fallback Mechanisms', () => {
		it('should use execCommand fallback when clipboard API is not available', async () => {
			// Remove clipboard API
			Object.defineProperty(navigator, 'clipboard', {
				value: undefined,
				writable: true,
				configurable: true
			})
			
			// Mock document.execCommand
			const mockExecCommand = vi.fn().mockReturnValue(true)
			document.execCommand = mockExecCommand
			
			// Mock document selection
			const mockRemoveAllRanges = vi.fn()
			const mockAddRange = vi.fn()
			
			Object.defineProperty(window, 'getSelection', {
				value: () => ({
					removeAllRanges: mockRemoveAllRanges,
					addRange: mockAddRange
				}),
				writable: true,
				configurable: true
			})
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(mockExecCommand).toHaveBeenCalledWith('copy')
			})
		})

		it('should handle execCommand fallback failure', async () => {
			// Remove clipboard API
			Object.defineProperty(navigator, 'clipboard', {
				value: undefined,
				writable: true,
				configurable: true
			})
			
			// Mock document.execCommand to fail
			document.execCommand = vi.fn().mockReturnValue(false)
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(button).toHaveTextContent(/failed/i)
			})
		})
	})

	describe('Accessibility', () => {
		it('should have proper ARIA attributes', () => {
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			expect(button).toHaveAttribute('aria-label', 'Copy to clipboard')
		})

		it('should update ARIA label based on state', async () => {
			mockWriteText.mockResolvedValueOnce(undefined)
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			fireEvent.click(button)
			
			await waitFor(() => {
				expect(button).toHaveAttribute('aria-label', 'Copied to clipboard')
			})
		})

		it('should be keyboard accessible', async () => {
			mockWriteText.mockResolvedValueOnce(undefined)
			
			render(<CopyButton text="Test text" />)
			
			const button = screen.getByRole('button')
			button.focus()
			
			// Simulate Enter key press
			fireEvent.keyDown(button, { key: 'Enter', code: 'Enter' })
			
			expect(mockWriteText).toHaveBeenCalled()
		})
	})
})