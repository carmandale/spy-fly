import React, { useState, useCallback } from 'react'
import { Check, Copy, X, Loader2 } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface CopyButtonProps {
	text: string
	buttonText?: string
	successText?: string
	errorText?: string
	permissionDeniedText?: string
	className?: string
	size?: 'sm' | 'md' | 'lg'
	variant?: 'default' | 'outline' | 'ghost'
	disabled?: boolean
	tooltip?: string
	onCopy?: (success: boolean) => void
}

type CopyState = 'idle' | 'loading' | 'success' | 'error' | 'permission-denied'

export const CopyButton: React.FC<CopyButtonProps> = ({
	text,
	buttonText = 'Copy',
	successText = 'Copied!',
	errorText = 'Failed to copy',
	permissionDeniedText = 'Permission denied',
	className,
	size = 'md',
	variant = 'default',
	disabled = false,
	tooltip,
	onCopy
}) => {
	const [copyState, setCopyState] = useState<CopyState>('idle')

	const copyToClipboard = useCallback(async () => {
		if (disabled) return

		setCopyState('loading')

		try {
			// Modern clipboard API
			if (navigator.clipboard && navigator.clipboard.writeText) {
				await navigator.clipboard.writeText(text)
				setCopyState('success')
				onCopy?.(true)
			} else {
				// Fallback for older browsers
				const textArea = document.createElement('textarea')
				textArea.value = text
				textArea.style.position = 'fixed'
				textArea.style.left = '-999999px'
				textArea.style.top = '-999999px'
				document.body.appendChild(textArea)
				textArea.focus()
				textArea.select()

				try {
					const successful = document.execCommand('copy')
					if (successful) {
						setCopyState('success')
						onCopy?.(true)
					} else {
						setCopyState('error')
						onCopy?.(false)
					}
				} catch {
					setCopyState('error')
					onCopy?.(false)
				} finally {
					document.body.removeChild(textArea)
				}
			}
		} catch (error) {
			// Check if it's a permission error
			if (error instanceof DOMException && error.name === 'NotAllowedError') {
				setCopyState('permission-denied')
			} else {
				setCopyState('error')
			}
			onCopy?.(false)
		}

		// Reset state after 2 seconds
		setTimeout(() => {
			setCopyState('idle')
		}, 2000)
	}, [text, disabled, onCopy])

	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault()
			copyToClipboard()
		}
	}

	// Size classes
	const sizeClasses = {
		sm: 'h-8 px-3 text-sm',
		md: 'h-9 px-4 text-sm',
		lg: 'h-10 px-6'
	}

	// Variant classes
	const variantClasses = {
		default: 'bg-primary text-primary-foreground hover:bg-primary/90',
		outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
		ghost: 'hover:bg-accent hover:text-accent-foreground'
	}

	// State-based content
	const getButtonContent = () => {
		switch (copyState) {
			case 'loading':
				return (
					<>
						<Loader2 className="mr-2 h-4 w-4 animate-spin" data-testid="copy-loading-icon" />
						<span>Copying...</span>
					</>
				)
			case 'success':
				return (
					<>
						<Check className="mr-2 h-4 w-4" data-testid="copy-success-icon" />
						<span>{successText}</span>
					</>
				)
			case 'error':
				return (
					<>
						<X className="mr-2 h-4 w-4" data-testid="copy-error-icon" />
						<span>{errorText}</span>
					</>
				)
			case 'permission-denied':
				return (
					<>
						<X className="mr-2 h-4 w-4" data-testid="copy-error-icon" />
						<span>{permissionDeniedText}</span>
					</>
				)
			default:
				return (
					<>
						<Copy className="mr-2 h-4 w-4" />
						<span>{buttonText}</span>
					</>
				)
		}
	}

	// ARIA label based on state
	const getAriaLabel = () => {
		switch (copyState) {
			case 'loading':
				return 'Copying to clipboard'
			case 'success':
				return 'Copied to clipboard'
			case 'error':
			case 'permission-denied':
				return 'Failed to copy to clipboard'
			default:
				return tooltip || 'Copy to clipboard'
		}
	}

	return (
		<button
			onClick={copyToClipboard}
			onKeyDown={handleKeyDown}
			disabled={disabled || copyState === 'loading'}
			className={cn(
				'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
				sizeClasses[size],
				variantClasses[variant],
				className
			)}
			aria-label={getAriaLabel()}
		>
			{getButtonContent()}
		</button>
	)
}