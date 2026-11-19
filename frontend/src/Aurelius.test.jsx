import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import App from './aurelius'

describe('Aurelius public demo', () => {
  afterEach(cleanup)

  it('renders a public portfolio overview without authentication', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Your wealth, in perspective.' })).toBeInTheDocument()
    expect(screen.getByText(/DEMO ENVIRONMENT/)).toBeInTheDocument()
    expect(screen.getAllByText('$128,450.20')).toHaveLength(2)
    expect(screen.getByText('No accounts connected')).toBeInTheDocument()
  })

  it('switches between the portfolio sections', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Portfolio' }))
    expect(screen.getByRole('heading', { name: 'Portfolio' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'All holdings' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Activity' }))
    expect(screen.getByRole('heading', { name: 'Activity log' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^Research/ }))
    expect(screen.getByRole('heading', { name: 'Consistency over prediction.' })).toBeInTheDocument()
  })

  it('changes the portfolio performance range', () => {
    render(<App />)
    const oneMonth = screen.getByRole('button', { name: '1M' })
    fireEvent.click(oneMonth)
    expect(oneMonth).toHaveClass('selected')
    expect(screen.getByRole('button', { name: '1Y' })).not.toHaveClass('selected')
  })

  it('filters holdings on the portfolio page', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Portfolio' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Search holdings' }), { target: { value: 'VXUS' } })
    expect(screen.getByText('Vanguard Total International')).toBeInTheDocument()
    expect(screen.queryByText('Vanguard Total Stock Market')).not.toBeInTheDocument()
  })
})
