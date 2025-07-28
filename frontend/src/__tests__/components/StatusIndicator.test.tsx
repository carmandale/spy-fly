import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusIndicator } from '../../components/StatusIndicator'

describe('StatusIndicator', () => {
  it('shows loading state', () => {
    render(<StatusIndicator status="loading" />)

    expect(screen.getByText(/Loading.../i)).toBeInTheDocument()
  })

  it('shows connected state', () => {
    render(<StatusIndicator status="connected" />)

    const statusText = screen.getByText(/Connected/i)
    expect(statusText).toBeInTheDocument()
    expect(statusText).toHaveClass('text-green-600')
  })

  it('shows error state', () => {
    render(<StatusIndicator status="error" error="Connection failed" />)

    const statusText = screen.getByText(/Error/i)
    expect(statusText).toBeInTheDocument()
    expect(statusText).toHaveClass('text-red-600')
    expect(screen.getByText(/Connection failed/i)).toBeInTheDocument()
  })

  it('shows disconnected state', () => {
    render(<StatusIndicator status="disconnected" />)

    const statusText = screen.getByText(/Disconnected/i)
    expect(statusText).toBeInTheDocument()
    expect(statusText).toHaveClass('text-yellow-600')
  })
})
