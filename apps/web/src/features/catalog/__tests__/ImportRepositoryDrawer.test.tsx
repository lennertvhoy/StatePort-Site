/**
 * ImportRepositoryDrawer — the governed local-repository import flow:
 * discovery → read-only inspection → exact-identity review → explicit
 * approval → registration → open the new application.
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { resetClientForTests } from '@/client'

import { ImportRepositoryDrawer } from '../ImportRepositoryDrawer'

function InstanceProbe() {
  const { instanceId } = useParams()
  return <div data-testid="instance-overview">{instanceId}</div>
}

function renderDrawer() {
  return render(
    <MemoryRouter initialEntries={['/catalog']}>
      <Routes>
        <Route path="/catalog" element={<ImportRepositoryDrawer open onOpenChange={() => undefined} />} />
        <Route path="/app/:instanceId" element={<InstanceProbe />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  resetClientForTests()
})

afterEach(() => {
  cleanup()
  resetClientForTests()
})

describe('ImportRepositoryDrawer', () => {
  it('walks discovery, inspection, approval, and registration', async () => {
    const user = userEvent.setup()
    renderDrawer()

    // Discovery lists the allowlisted candidates.
    const candidates = await screen.findByTestId('import-candidates')
    expect(candidates.textContent).toContain('photography-portfolio')

    // Inspection is read-only and shows the exact identity.
    await user.click(screen.getByTestId('import-candidate-photography-portfolio'))
    const review = await screen.findByTestId('import-review')
    expect(review.textContent).toContain('main')
    expect(review.textContent).toContain('Clean')

    // Registration stays disabled until the exact-identity approval is given.
    const registerButton = screen.getByTestId('import-register') as HTMLButtonElement
    expect(registerButton.disabled).toBe(true)
    await user.click(screen.getByRole('checkbox', { name: /approve registration/i }))
    expect((screen.getByTestId('import-register') as HTMLButtonElement).disabled).toBe(false)

    await user.click(screen.getByTestId('import-register'))
    const done = await screen.findByTestId('import-done')
    expect(done.textContent).toContain('is registered')

    // Opening the registered application navigates to its route.
    await user.click(screen.getByTestId('import-open-application'))
    const overview = await screen.findByTestId('instance-overview')
    expect(overview.textContent).toMatch(/^ins-/)
  })
})
