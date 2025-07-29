import React from 'react'
import { CopyButton } from './CopyButton'
import { useToast } from '../../hooks/useToast'
import { ToastContainer } from '../ui/ToastContainer'

// Sample order ticket data
const sampleOrderTicket = `VERTICAL SPREAD ORDER
Symbol: SPY
Date: 0DTE (Dec 29, 2024)
Type: Bull Call Spread
Quantity: 2 contracts

BUY TO OPEN:
Strike: $595 CALL
Exp: Dec 29, 2024

SELL TO OPEN:
Strike: $600 CALL
Exp: Dec 29, 2024

Net Debit: $2.35
Max Risk: $470
Max Profit: $530
Risk/Reward: 1:1.13`

export const CopyButtonDemo: React.FC = () => {
	const { toasts, toast, removeToast } = useToast()

	const handleCopy = (success: boolean) => {
		if (success) {
			toast.success('Order copied!', 'Paste into your broker platform')
		} else {
			toast.error('Copy failed', 'Please try selecting and copying manually')
		}
	}

	return (
		<div className="p-8 max-w-4xl mx-auto">
			<h1 className="text-2xl font-bold mb-6">Copy Button Demo</h1>
			
			<div className="space-y-8">
				{/* Basic Examples */}
				<section>
					<h2 className="text-lg font-semibold mb-4">Basic Examples</h2>
					<div className="flex flex-wrap gap-4">
						<CopyButton
							text="Simple text to copy"
							onCopy={handleCopy}
						/>
						
						<CopyButton
							text="Custom button text"
							buttonText="Copy Order"
							onCopy={handleCopy}
						/>
						
						<CopyButton
							text="With custom messages"
							buttonText="Copy Trade"
							successText="Trade Copied!"
							errorText="Copy Failed!"
							onCopy={handleCopy}
						/>
					</div>
				</section>

				{/* Size Variants */}
				<section>
					<h2 className="text-lg font-semibold mb-4">Size Variants</h2>
					<div className="flex items-center gap-4">
						<CopyButton
							text="Small button"
							size="sm"
							onCopy={handleCopy}
						/>
						
						<CopyButton
							text="Medium button (default)"
							size="md"
							onCopy={handleCopy}
						/>
						
						<CopyButton
							text="Large button"
							size="lg"
							onCopy={handleCopy}
						/>
					</div>
				</section>

				{/* Style Variants */}
				<section>
					<h2 className="text-lg font-semibold mb-4">Style Variants</h2>
					<div className="flex gap-4">
						<CopyButton
							text="Default variant"
							variant="default"
							onCopy={handleCopy}
						/>
						
						<CopyButton
							text="Outline variant"
							variant="outline"
							onCopy={handleCopy}
						/>
						
						<CopyButton
							text="Ghost variant"
							variant="ghost"
							onCopy={handleCopy}
						/>
					</div>
				</section>

				{/* Order Ticket Example */}
				<section>
					<h2 className="text-lg font-semibold mb-4">Order Ticket Example</h2>
					<div className="bg-gray-50 p-6 rounded-lg">
						<pre className="text-sm mb-4 whitespace-pre-wrap">{sampleOrderTicket}</pre>
						<CopyButton
							text={sampleOrderTicket}
							buttonText="Copy Order Ticket"
							successText="Order Ticket Copied!"
							size="lg"
							onCopy={handleCopy}
							className="w-full"
						/>
					</div>
				</section>

				{/* Disabled State */}
				<section>
					<h2 className="text-lg font-semibold mb-4">Disabled State</h2>
					<CopyButton
						text="This button is disabled"
						disabled
						onCopy={handleCopy}
					/>
				</section>

				{/* Browser Compatibility Test */}
				<section>
					<h2 className="text-lg font-semibold mb-4">Browser Information</h2>
					<div className="bg-blue-50 p-4 rounded-lg text-sm">
						<p><strong>User Agent:</strong> {navigator.userAgent}</p>
						<p><strong>Clipboard API Available:</strong> {navigator.clipboard ? 'Yes' : 'No'}</p>
						<p><strong>execCommand Available:</strong> {document.execCommand ? 'Yes' : 'No'}</p>
					</div>
				</section>
			</div>

			{/* Toast Container */}
			<ToastContainer toasts={toasts} onClose={removeToast} />
		</div>
	)
}