import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
  })

  it('displays API status', async () => {
    render(<App />)
    
    // Should show loading or status
    const statusElement = await screen.findByText(/API Status:/i)
    expect(statusElement).toBeInTheDocument()
  })
})