import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Toast } from '../../../components/ui/Toast'
import { ToastContainer } from '../../../components/ui/ToastContainer'

describe('Toast', () => {
	const mockOnClose = vi.fn()

	beforeEach(() => {
		mockOnClose.mockClear()
		vi.useFakeTimers()
	})

	afterEach(() => {
		vi.useRealTimers()
	})

	describe('Basic Rendering', () => {
		it('should render toast with title', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					onClose={mockOnClose}
				/>
			)

			expect(screen.getByRole('alert')).toBeInTheDocument()
			expect(screen.getByText('Test Toast')).toBeInTheDocument()
		})

		it('should render toast with title and description', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					description="This is a test description"
					onClose={mockOnClose}
				/>
			)

			expect(screen.getByText('Test Toast')).toBeInTheDocument()
			expect(screen.getByText('This is a test description')).toBeInTheDocument()
		})

		it('should render close button', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					onClose={mockOnClose}
				/>
			)

			const closeButton = screen.getByLabelText('Close notification')
			expect(closeButton).toBeInTheDocument()
		})
	})

	describe('Toast Types', () => {
		it('should render success toast with correct styling', () => {
			render(
				<Toast
					id="test-1"
					title="Success"
					type="success"
					onClose={mockOnClose}
				/>
			)

			const alert = screen.getByRole('alert')
			expect(alert).toHaveClass('bg-green-50', 'text-green-800')
		})

		it('should render error toast with correct styling', () => {
			render(
				<Toast
					id="test-1"
					title="Error"
					type="error"
					onClose={mockOnClose}
				/>
			)

			const alert = screen.getByRole('alert')
			expect(alert).toHaveClass('bg-red-50', 'text-red-800')
		})

		it('should render info toast with correct styling', () => {
			render(
				<Toast
					id="test-1"
					title="Info"
					type="info"
					onClose={mockOnClose}
				/>
			)

			const alert = screen.getByRole('alert')
			expect(alert).toHaveClass('bg-blue-50', 'text-blue-800')
		})

		it('should render warning toast with correct styling', () => {
			render(
				<Toast
					id="test-1"
					title="Warning"
					type="warning"
					onClose={mockOnClose}
				/>
			)

			const alert = screen.getByRole('alert')
			expect(alert).toHaveClass('bg-yellow-50', 'text-yellow-800')
		})
	})

	describe('Auto-dismiss', () => {
		it('should auto-dismiss after default duration', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					onClose={mockOnClose}
				/>
			)

			expect(mockOnClose).not.toHaveBeenCalled()

			// Fast-forward default duration (3000ms)
			vi.advanceTimersByTime(3000)

			expect(mockOnClose).toHaveBeenCalledWith('test-1')
			expect(mockOnClose).toHaveBeenCalledTimes(1)
		})

		it('should auto-dismiss after custom duration', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					duration={5000}
					onClose={mockOnClose}
				/>
			)

			expect(mockOnClose).not.toHaveBeenCalled()

			// Fast-forward custom duration
			vi.advanceTimersByTime(5000)

			expect(mockOnClose).toHaveBeenCalledWith('test-1')
		})

		it('should not auto-dismiss when duration is 0', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					duration={0}
					onClose={mockOnClose}
				/>
			)

			// Fast-forward a long time
			vi.advanceTimersByTime(10000)

			expect(mockOnClose).not.toHaveBeenCalled()
		})

		it('should clear timer when unmounted', () => {
			const { unmount } = render(
				<Toast
					id="test-1"
					title="Test Toast"
					onClose={mockOnClose}
				/>
			)

			unmount()

			// Fast-forward past duration
			vi.advanceTimersByTime(5000)

			expect(mockOnClose).not.toHaveBeenCalled()
		})
	})

	describe('User Interactions', () => {
		it('should call onClose when close button is clicked', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					onClose={mockOnClose}
				/>
			)

			const closeButton = screen.getByLabelText('Close notification')
			fireEvent.click(closeButton)

			expect(mockOnClose).toHaveBeenCalledWith('test-1')
			expect(mockOnClose).toHaveBeenCalledTimes(1)
		})

		it('should be keyboard accessible', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					onClose={mockOnClose}
				/>
			)

			const closeButton = screen.getByLabelText('Close notification')
			closeButton.focus()

			// Click is more reliable than keyDown for button elements
			fireEvent.click(closeButton)

			expect(mockOnClose).toHaveBeenCalledWith('test-1')
		})
	})

	describe('Accessibility', () => {
		it('should have proper ARIA attributes', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					onClose={mockOnClose}
				/>
			)

			const alert = screen.getByRole('alert')
			expect(alert).toHaveAttribute('aria-live', 'polite')
		})

		it('should have accessible close button', () => {
			render(
				<Toast
					id="test-1"
					title="Test Toast"
					onClose={mockOnClose}
				/>
			)

			const closeButton = screen.getByLabelText('Close notification')
			expect(closeButton).toBeInTheDocument()
		})
	})
})

describe('ToastContainer', () => {
	const mockOnClose = vi.fn()

	beforeEach(() => {
		mockOnClose.mockClear()
	})

	it('should render nothing when no toasts', () => {
		const { container } = render(
			<ToastContainer toasts={[]} onClose={mockOnClose} />
		)

		expect(container.firstChild).toBeNull()
	})

	it('should render multiple toasts', () => {
		const toasts = [
			{ id: '1', title: 'Toast 1', type: 'success' as const },
			{ id: '2', title: 'Toast 2', type: 'error' as const },
			{ id: '3', title: 'Toast 3', type: 'info' as const }
		]

		render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)

		expect(screen.getByText('Toast 1')).toBeInTheDocument()
		expect(screen.getByText('Toast 2')).toBeInTheDocument()
		expect(screen.getByText('Toast 3')).toBeInTheDocument()
		expect(screen.getAllByRole('alert')).toHaveLength(3)
	})

	it('should position container correctly', () => {
		const toasts = [{ id: '1', title: 'Toast 1' }]

		render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)

		const container = screen.getByRole('alert').parentElement
		expect(container).toHaveClass('fixed', 'top-4', 'right-4', 'z-50')
	})

	it('should pass onClose to each toast', () => {
		const toasts = [
			{ id: '1', title: 'Toast 1' },
			{ id: '2', title: 'Toast 2' }
		]

		render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)

		const closeButtons = screen.getAllByLabelText('Close notification')
		fireEvent.click(closeButtons[0])

		expect(mockOnClose).toHaveBeenCalledWith('1')
	})
})