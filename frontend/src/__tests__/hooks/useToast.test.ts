import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useToast } from '../../hooks/useToast'

describe('useToast', () => {
	beforeEach(() => {
		vi.clearAllMocks()
	})

	afterEach(() => {
		vi.clearAllMocks()
	})

	it('should initialize with empty toasts array', () => {
		const { result } = renderHook(() => useToast())

		expect(result.current.toasts).toEqual([])
	})

	describe('Toast Creation', () => {
		it('should add success toast', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.success('Success!', 'Operation completed')
			})

			expect(result.current.toasts).toHaveLength(1)
			expect(result.current.toasts[0]).toMatchObject({
				title: 'Success!',
				description: 'Operation completed',
				type: 'success'
			})
			expect(result.current.toasts[0].id).toBeDefined()
		})

		it('should add error toast', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.error('Error!', 'Something went wrong')
			})

			expect(result.current.toasts).toHaveLength(1)
			expect(result.current.toasts[0]).toMatchObject({
				title: 'Error!',
				description: 'Something went wrong',
				type: 'error'
			})
		})

		it('should add info toast', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.info('Info', 'Just so you know')
			})

			expect(result.current.toasts).toHaveLength(1)
			expect(result.current.toasts[0]).toMatchObject({
				title: 'Info',
				description: 'Just so you know',
				type: 'info'
			})
		})

		it('should add warning toast', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.warning('Warning', 'Be careful')
			})

			expect(result.current.toasts).toHaveLength(1)
			expect(result.current.toasts[0]).toMatchObject({
				title: 'Warning',
				description: 'Be careful',
				type: 'warning'
			})
		})

		it('should add custom toast', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.custom({
					title: 'Custom',
					description: 'Custom toast',
					type: 'info',
					duration: 5000
				})
			})

			expect(result.current.toasts).toHaveLength(1)
			expect(result.current.toasts[0]).toMatchObject({
				title: 'Custom',
				description: 'Custom toast',
				type: 'info',
				duration: 5000
			})
		})

		it('should add toast without description', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.success('Success!')
			})

			expect(result.current.toasts).toHaveLength(1)
			expect(result.current.toasts[0]).toMatchObject({
				title: 'Success!',
				type: 'success'
			})
			expect(result.current.toasts[0].description).toBeUndefined()
		})
	})

	describe('Multiple Toasts', () => {
		it('should handle multiple toasts', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.success('Toast 1')
				result.current.toast.error('Toast 2')
				result.current.toast.info('Toast 3')
			})

			expect(result.current.toasts).toHaveLength(3)
			expect(result.current.toasts[0].title).toBe('Toast 1')
			expect(result.current.toasts[1].title).toBe('Toast 2')
			expect(result.current.toasts[2].title).toBe('Toast 3')
		})

		it('should generate unique IDs for each toast', async () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.success('Toast 1')
			})

			// Add a small delay to ensure different timestamps
			await new Promise(resolve => setTimeout(resolve, 10))

			act(() => {
				result.current.toast.success('Toast 2')
			})

			expect(result.current.toasts).toHaveLength(2)
			const ids = result.current.toasts.map(t => t.id)
			expect(new Set(ids).size).toBe(2)
		})
	})

	describe('Toast Removal', () => {
		it('should remove toast by ID', () => {
			const { result } = renderHook(() => useToast())

			// Add toasts
			act(() => {
				result.current.toast.success('Toast 1')
				result.current.toast.error('Toast 2')
			})

			// Verify toasts were added
			expect(result.current.toasts).toHaveLength(2)
			
			// Get the ID before removing
			const firstToastId = result.current.toasts[0].id
			const secondToastTitle = result.current.toasts[1].title

			// Remove the first toast
			act(() => {
				result.current.removeToast(firstToastId)
			})

			// Verify removal
			expect(result.current.toasts).toHaveLength(1)
			expect(result.current.toasts[0].title).toBe(secondToastTitle)
		})

		it('should handle removing non-existent toast', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.success('Toast 1')
			})

			act(() => {
				result.current.removeToast('non-existent-id')
			})

			expect(result.current.toasts).toHaveLength(1)
		})

		it('should remove all toasts individually', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				result.current.toast.success('Toast 1')
				result.current.toast.error('Toast 2')
				result.current.toast.info('Toast 3')
			})

			const ids = [...result.current.toasts.map(t => t.id)]

			act(() => {
				ids.forEach(id => result.current.removeToast(id))
			})

			expect(result.current.toasts).toHaveLength(0)
		})
	})

	describe('Edge Cases', () => {
		it('should handle rapid toast creation', () => {
			const { result } = renderHook(() => useToast())

			act(() => {
				for (let i = 0; i < 10; i++) {
					result.current.toast.success(`Toast ${i}`)
				}
			})

			expect(result.current.toasts).toHaveLength(10)
		})

		it('should maintain order when removing middle toast', () => {
			const { result } = renderHook(() => useToast())

			// Add toasts
			act(() => {
				result.current.toast.success('Toast 1')
				result.current.toast.error('Toast 2')
				result.current.toast.info('Toast 3')
			})

			// Verify all toasts were added
			expect(result.current.toasts).toHaveLength(3)
			
			// Store references before removal
			const firstTitle = result.current.toasts[0].title
			const middleToastId = result.current.toasts[1].id
			const lastTitle = result.current.toasts[2].title

			// Remove middle toast
			act(() => {
				result.current.removeToast(middleToastId)
			})

			// Verify order is maintained
			expect(result.current.toasts).toHaveLength(2)
			expect(result.current.toasts[0].title).toBe(firstTitle)
			expect(result.current.toasts[1].title).toBe(lastTitle)
		})
	})
})