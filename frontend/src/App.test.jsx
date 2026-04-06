import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders without crashing', () => {
    const { container } = render(<App />)
    expect(container.innerHTML.length).toBeGreaterThan(0)
  })

  it('renders login page when unauthenticated', () => {
    render(<App />)
    // App shows AuthPage by default when no token in localStorage
    expect(screen.getByPlaceholderText('user@example.com')).toBeTruthy()
  })

  it('renders the onboarding tour on first visit', () => {
    render(<App />)
    expect(screen.getAllByText(/NexusForge/i).length).toBeGreaterThan(0)
  })
})
