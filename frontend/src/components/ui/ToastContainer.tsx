import React from 'react'
import { Toast, type ToastProps } from './Toast'

export interface ToastData extends Omit<ToastProps, 'onClose'> {}

interface ToastContainerProps {
	toasts: ToastData[]
	onClose: (id: string) => void
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onClose }) => {
	if (toasts.length === 0) return null

	return (
		<div
			className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
			aria-live="polite"
			aria-atomic="true"
		>
			{toasts.map((toast) => (
				<Toast
					key={toast.id}
					{...toast}
					onClose={onClose}
				/>
			))}
		</div>
	)
}