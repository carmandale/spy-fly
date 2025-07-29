import React, { useEffect } from 'react'
import { X, CheckCircle, XCircle, Info, AlertTriangle } from 'lucide-react'
import { cn } from '../../lib/utils'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastProps {
	id: string
	title: string
	description?: string
	type?: ToastType
	duration?: number
	onClose: (id: string) => void
}

const icons = {
	success: CheckCircle,
	error: XCircle,
	info: Info,
	warning: AlertTriangle
}

const styles = {
	success: 'bg-green-50 text-green-800 border-green-200',
	error: 'bg-red-50 text-red-800 border-red-200',
	info: 'bg-blue-50 text-blue-800 border-blue-200',
	warning: 'bg-yellow-50 text-yellow-800 border-yellow-200'
}

export const Toast: React.FC<ToastProps> = ({
	id,
	title,
	description,
	type = 'info',
	duration = 3000,
	onClose
}) => {
	useEffect(() => {
		if (duration > 0) {
			const timer = setTimeout(() => {
				onClose(id)
			}, duration)

			return () => clearTimeout(timer)
		}
	}, [id, duration, onClose])

	const Icon = icons[type]

	return (
		<div
			className={cn(
				'flex items-start gap-3 rounded-lg border p-4 shadow-lg transition-all',
				styles[type]
			)}
			role="alert"
			aria-live="polite"
		>
			<Icon className="h-5 w-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
			<div className="flex-1">
				<h3 className="font-medium">{title}</h3>
				{description && (
					<p className="mt-1 text-sm opacity-90">{description}</p>
				)}
			</div>
			<button
				onClick={() => onClose(id)}
				className="ml-3 inline-flex rounded-md p-1 hover:bg-black/10 transition-colors"
				aria-label="Close notification"
			>
				<X className="h-4 w-4" />
			</button>
		</div>
	)
}