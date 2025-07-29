import { useState, useCallback } from 'react'
import { ToastData } from '../components/ui/ToastContainer'

export const useToast = () => {
	const [toasts, setToasts] = useState<ToastData[]>([])

	const showToast = useCallback((toast: Omit<ToastData, 'id'>) => {
		const id = Date.now().toString()
		setToasts((prev) => [...prev, { ...toast, id }])
	}, [])

	const removeToast = useCallback((id: string) => {
		setToasts((prev) => prev.filter((toast) => toast.id !== id))
	}, [])

	const toast = {
		success: (title: string, description?: string) =>
			showToast({ title, description, type: 'success' }),
		error: (title: string, description?: string) =>
			showToast({ title, description, type: 'error' }),
		info: (title: string, description?: string) =>
			showToast({ title, description, type: 'info' }),
		warning: (title: string, description?: string) =>
			showToast({ title, description, type: 'warning' }),
		custom: (options: Omit<ToastData, 'id'>) => showToast(options)
	}

	return {
		toasts,
		toast,
		removeToast
	}
}