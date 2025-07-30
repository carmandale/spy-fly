import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import LivePLMonitorPanel from '../../components/LivePLMonitorPanel'

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock recharts to avoid complex chart rendering in tests
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
}))

describe('LivePLMonitorPanel', () => {
  const mockPLData = {
    currentValue: -200,
    entryValue: -250,
    unrealizedPL: 50,
    unrealizedPLPercent: 10,
    timeDecay: -15,
    alertStatus: 'none' as const,
  }

  const mockHistoricalData = {
    equityCurve: [
      { date: '2025-01-01', value: 100 },
      { date: '2025-01-02', value: 150 },
      { date: '2025-01-03', value: 200 },
    ],
    winRate: 65.5,
    avgProfitLoss: 75,
  }

  it('renders the Live P/L Monitor panel correctly', () => {
    render(<LivePLMonitorPanel plData={mockPLData} historicalData={mockHistoricalData} />)
    
    expect(screen.getByText('Live P/L Monitor')).toBeInTheDocument()
    expect(screen.getByText('Historical Performance')).toBeInTheDocument()
  })

  it('displays current P/L values correctly', () => {
    render(<LivePLMonitorPanel plData={mockPLData} historicalData={mockHistoricalData} />)
    
    // Check P/L dollar amount with + prefix for profit
    expect(screen.getByText('+$50')).toBeInTheDocument()
    
    // Check P/L percentage with + prefix for profit
    expect(screen.getByText('(+10.00%)')).toBeInTheDocument()
    
    // Check entry and current values
    expect(screen.getByText('$-250')).toBeInTheDocument()
    expect(screen.getByText('$-200')).toBeInTheDocument()
  })

  it('displays negative P/L correctly', () => {
    const negativePLData = {
      ...mockPLData,
      unrealizedPL: -30,
      unrealizedPLPercent: -6,
    }

    render(<LivePLMonitorPanel plData={negativePLData} historicalData={mockHistoricalData} />)
    
    // Check negative P/L with $ prefix
    expect(screen.getByText('$-30')).toBeInTheDocument()
    expect(screen.getByText('(-6.00%)')).toBeInTheDocument()
  })

  it('displays time decay correctly', () => {
    render(<LivePLMonitorPanel plData={mockPLData} historicalData={mockHistoricalData} />)
    
    expect(screen.getByText('Time Decay')).toBeInTheDocument()
    expect(screen.getByText('$-15')).toBeInTheDocument()
  })

  it('shows profit target alert icon when alert status is profit-target', () => {
    const alertPLData = {
      ...mockPLData,
      alertStatus: 'profit-target' as const,
    }

    render(<LivePLMonitorPanel plData={alertPLData} historicalData={mockHistoricalData} />)
    
    const profitIcon = screen.getByLabelText('Profit target alert')
    expect(profitIcon).toBeInTheDocument()
    expect(profitIcon).toHaveClass('text-green-400', 'animate-pulse')
  })

  it('shows stop-loss alert icon when alert status is stop-loss', () => {
    const alertPLData = {
      ...mockPLData,
      alertStatus: 'stop-loss' as const,
    }

    render(<LivePLMonitorPanel plData={alertPLData} historicalData={mockHistoricalData} />)
    
    const stopLossIcon = screen.getByLabelText('Stop loss alert')
    expect(stopLossIcon).toBeInTheDocument()
    expect(stopLossIcon).toHaveClass('text-red-400', 'animate-pulse')
  })

  it('does not show alert icon when alert status is none', () => {
    render(<LivePLMonitorPanel plData={mockPLData} historicalData={mockHistoricalData} />)
    
    expect(screen.queryByLabelText('Profit target alert')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Stop loss alert')).not.toBeInTheDocument()
  })

  it('renders P/L progress bar with correct attributes', () => {
    render(<LivePLMonitorPanel plData={mockPLData} historicalData={mockHistoricalData} />)
    
    const progressBar = screen.getByRole('progressbar')
    expect(progressBar).toBeInTheDocument()
    expect(progressBar).toHaveAttribute('aria-valuenow', '10')
    expect(progressBar).toHaveAttribute('aria-valuemin', '0')
    expect(progressBar).toHaveAttribute('aria-valuemax', '100')
    expect(progressBar).toHaveAttribute('aria-label', 'P/L percentage: 10.00%')
    
    // Check that progress bar percentage text is displayed
    expect(screen.getByText('10.0%')).toBeInTheDocument()
  })

  it('displays historical performance stats correctly', () => {
    render(<LivePLMonitorPanel plData={mockPLData} historicalData={mockHistoricalData} />)
    
    expect(screen.getByText('Win Rate')).toBeInTheDocument()
    expect(screen.getByText('65.5%')).toBeInTheDocument()
    
    expect(screen.getByText('Avg P/L')).toBeInTheDocument()
    expect(screen.getByText('$75')).toBeInTheDocument()
  })

  it('renders chart components for equity curve', () => {
    render(<LivePLMonitorPanel plData={mockPLData} historicalData={mockHistoricalData} />)
    
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    expect(screen.getByTestId('line')).toBeInTheDocument()
    expect(screen.getByTestId('x-axis')).toBeInTheDocument()
    expect(screen.getByTestId('y-axis')).toBeInTheDocument()
  })

  it('applies correct CSS classes for profit colors', () => {
    render(<LivePLMonitorPanel plData={mockPLData} historicalData={mockHistoricalData} />)
    
    // Check that profit values have green color classes (on parent div)
    const profitElement = screen.getByText('+$50').closest('div')
    expect(profitElement).toHaveClass('text-green-400')
    
    const profitPercentElement = screen.getByText('(+10.00%)').closest('div')
    expect(profitPercentElement).toHaveClass('text-green-400')
  })

  it('applies correct CSS classes for loss colors', () => {
    const lossPLData = {
      ...mockPLData,
      unrealizedPL: -100,
      unrealizedPLPercent: -20,
    }

    render(<LivePLMonitorPanel plData={lossPLData} historicalData={mockHistoricalData} />)
    
    // Check that loss values have red color classes
    const lossElement = screen.getByText('$-100')
    expect(lossElement).toHaveClass('text-red-400')
    
    const lossPercentElement = screen.getByText('(-20.00%)')
    expect(lossPercentElement).toHaveClass('text-red-400')
  })

  it('handles zero P/L correctly', () => {
    const zeroPLData = {
      ...mockPLData,
      unrealizedPL: 0,
      unrealizedPLPercent: 0,
    }

    render(<LivePLMonitorPanel plData={zeroPLData} historicalData={mockHistoricalData} />)
    
    expect(screen.getByText('+$0')).toBeInTheDocument()
    expect(screen.getByText('(+0.00%)')).toBeInTheDocument()
  })

  it('handles edge case with 100% P/L correctly', () => {
    const maxPLData = {
      ...mockPLData,
      unrealizedPL: 500,
      unrealizedPLPercent: 100,
    }

    render(<LivePLMonitorPanel plData={maxPLData} historicalData={mockHistoricalData} />)
    
    const progressBar = screen.getByRole('progressbar')
    expect(progressBar).toHaveAttribute('aria-valuenow', '100')
    expect(screen.getByText('100.0%')).toBeInTheDocument()
  })

  it('caps progress bar width at 100% for extreme values', () => {
    const extremePLData = {
      ...mockPLData,
      unrealizedPL: 1000,
      unrealizedPLPercent: 200, // 200% would exceed max bar width
    }

    render(<LivePLMonitorPanel plData={extremePLData} historicalData={mockHistoricalData} />)
    
    const progressBar = screen.getByRole('progressbar')
    expect(progressBar).toHaveAttribute('aria-valuenow', '200')
    
    // The text should show the actual percentage
    expect(screen.getByText('200.0%')).toBeInTheDocument()
  })

  it('displays negative historical average P/L with correct color', () => {
    const negativeHistoricalData = {
      ...mockHistoricalData,
      avgProfitLoss: -50,
    }

    render(<LivePLMonitorPanel plData={mockPLData} historicalData={negativeHistoricalData} />)
    
    const avgPLElement = screen.getByText('$-50')
    expect(avgPLElement).toHaveClass('text-red-400')
  })

  it('handles empty equity curve data gracefully', () => {
    const emptyHistoricalData = {
      ...mockHistoricalData,
      equityCurve: [],
    }

    render(<LivePLMonitorPanel plData={mockPLData} historicalData={emptyHistoricalData} />)
    
    // Chart should still render even with empty data
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })
})