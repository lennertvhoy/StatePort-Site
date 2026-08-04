import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { BrandLockup, BrandMark } from '../Brand'

afterEach(cleanup)

describe('StatePort source mark', () => {
  it('uses the public-safe inline mark for the compact rail', () => {
    render(<BrandMark size={20} title="StatePort" />)
    const mark = screen.getByRole('img', { name: 'StatePort' })
    expect(mark.querySelector('svg')).toBeTruthy()
    expect(mark.querySelector('img')).toBeNull()
    expect(mark.getAttribute('style')).toContain('width: 20px')
  })

  it('reuses the inline mark in the expanded lockup', () => {
    render(<BrandLockup />)
    const lockup = screen.getByTestId('brand-lockup')
    expect(lockup.textContent).toBe('StatePort')
    expect(lockup.querySelector('svg')).toBeTruthy()
    expect(lockup.querySelector('img')).toBeNull()
  })
})
