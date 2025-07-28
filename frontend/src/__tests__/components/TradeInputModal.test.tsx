import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TradeInputModal from '../../components/TradeInputModal'
import { apiClient, Trade } from '../../api/client'

// Mock the API client
vi.mock('../../api/client', () => ({
  apiClient: {
    createTrade: vi.fn()
  },
  Trade: {},
  TradeCreate: {},
  TradeSpread: {}
}))

describe('TradeInputModal', () => {
  const mockOnClose = vi.fn()
  const mockOnTradeCreated = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders when open', () => {
    render(
      <TradeInputModal
        isOpen={true}
        onClose={mockOnClose}
        onTradeCreated={mockOnTradeCreated}
      />
    )

    expect(screen.getByText('Record Trade')).toBeInTheDocument()
    expect(screen.getByText('Trade Date')).toBeInTheDocument()
    expect(screen.getByText('Long Strike')).toBeInTheDocument()
    expect(screen.getByText('Short Strike')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(
      <TradeInputModal
        isOpen={false}
        onClose={mockOnClose}
        onTradeCreated={mockOnTradeCreated}
      />
    )

    expect(screen.queryByText('Record Trade')).not.toBeInTheDocument()
  })

  it('calls onClose when cancel button is clicked', () => {
    render(
      <TradeInputModal
        isOpen={true}
        onClose={mockOnClose}
        onTradeCreated={mockOnTradeCreated}
      />
    )

    fireEvent.click(screen.getByText('Cancel'))
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('calculates spread metrics when premium values change', async () => {
    const user = userEvent.setup()
    
    render(
      <TradeInputModal
        isOpen={true}
        onClose={mockOnClose}
        onTradeCreated={mockOnTradeCreated}
      />
    )

    // Set strike prices - find inputs by their type and step attributes
    const numberInputs = screen.getAllByRole('spinbutton')
    const longStrikeInput = numberInputs.find(input => input.getAttribute('step') === '0.50')!
    const shortStrikeInput = numberInputs.find((input, index) => input.getAttribute('step') === '0.50' && numberInputs.indexOf(input) > numberInputs.indexOf(longStrikeInput))!
    const longPremiumInput = numberInputs.find(input => input.getAttribute('step') === '0.01')!
    const shortPremiumInput = numberInputs.find((input, index) => input.getAttribute('step') === '0.01' && numberInputs.indexOf(input) > numberInputs.indexOf(longPremiumInput))!
    
    await user.clear(longStrikeInput)
    await user.type(longStrikeInput, '570')
    
    await user.clear(shortStrikeInput)
    await user.type(shortStrikeInput, '575')
    
    // Set premiums
    await user.clear(longPremiumInput)
    await user.type(longPremiumInput, '2.50')
    
    await user.clear(shortPremiumInput)
    await user.type(shortPremiumInput, '1.50')
    
    // Trigger calculation by blurring
    fireEvent.blur(shortPremiumInput)
    
    // Check if metrics are displayed
    await waitFor(() => {
      expect(screen.getByText('$1.00')).toBeInTheDocument() // Net Debit
    })
  })

  it('submits trade successfully', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.createTrade).mockResolvedValueOnce({
      id: 1,
      trade_date: '2025-01-28',
      trade_type: 'paper',
      status: 'entered'
    })

    render(
      <TradeInputModal
        isOpen={true}
        onClose={mockOnClose}
        onTradeCreated={mockOnTradeCreated}
      />
    )

    // Fill in required fields - find inputs by their type and step attributes
    const numberInputs = screen.getAllByRole('spinbutton')
    const longStrikeInput = numberInputs.find(input => input.getAttribute('step') === '0.50')!
    const shortStrikeInput = numberInputs.find((input, index) => input.getAttribute('step') === '0.50' && numberInputs.indexOf(input) > numberInputs.indexOf(longStrikeInput))!
    const longPremiumInput = numberInputs.find(input => input.getAttribute('step') === '0.01')!
    const shortPremiumInput = numberInputs.find((input, index) => input.getAttribute('step') === '0.01' && numberInputs.indexOf(input) > numberInputs.indexOf(longPremiumInput))!
    
    await user.clear(longStrikeInput)
    await user.type(longStrikeInput, '570')
    
    await user.clear(shortStrikeInput)
    await user.type(shortStrikeInput, '575')
    
    await user.clear(longPremiumInput)
    await user.type(longPremiumInput, '2.50')
    
    await user.clear(shortPremiumInput)
    await user.type(shortPremiumInput, '1.50')

    // Submit form
    fireEvent.click(screen.getByText('Create Trade'))

    await waitFor(() => {
      expect(apiClient.createTrade).toHaveBeenCalled()
      expect(mockOnTradeCreated).toHaveBeenCalled()
      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  it('displays error message on submission failure', async () => {
    vi.mocked(apiClient.createTrade).mockRejectedValueOnce(
      new Error('Failed to create trade')
    )

    render(
      <TradeInputModal
        isOpen={true}
        onClose={mockOnClose}
        onTradeCreated={mockOnTradeCreated}
      />
    )

    // Submit form
    fireEvent.click(screen.getByText('Create Trade'))

    await waitFor(() => {
      expect(screen.getByText('Failed to create trade')).toBeInTheDocument()
    })
  })
})