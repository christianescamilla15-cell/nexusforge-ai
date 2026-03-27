import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders without crashing', () => {
    const { container } = render(<App />)
    expect(container.innerHTML.length).toBeGreaterThan(0)
  })

  it('renders sidebar with navigation', () => {
    render(<App />)
    expect(screen.getByLabelText('Dashboard')).toBeTruthy()
    expect(screen.getByLabelText('Workflows')).toBeTruthy()
    expect(screen.getByLabelText('Agents')).toBeTruthy()
  })

  it('renders the onboarding tour on first visit', () => {
    render(<App />)
    expect(screen.getAllByText(/NexusForge/i).length).toBeGreaterThan(0)
  })
})
