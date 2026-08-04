/**
 * Honesty tests for the platform surface pages: when the connected adapter
 * reports no durable host state (the mock adapter for these operator
 * surfaces), the pages must render their honest unavailable state and never
 * fabricate operator data or fake a working control.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { resetClientForTests } from '@/client'

import PlatformDeploymentsPage from '../PlatformDeploymentsPage'
import AuthorityPage from '../../authority/AuthorityPage'
import UpdaterPage from '../../updater/UpdaterPage'
import PreviewRoutesPage from '../../preview-routes/PreviewRoutesPage'

function renderAt(path: string, element: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={path} element={element} />
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

describe('PlatformDeploymentsPage (honest unavailable state)', () => {
  it('renders the page root and the honest unavailable notice (no fake data)', async () => {
    renderAt('/deployments', <PlatformDeploymentsPage />)
    expect(await screen.findByTestId('platform-deployments-page')).toBeTruthy()
    // The mock adapter reports no durable state; the surface must say so
    // honestly rather than rendering a fabricated deployment table.
    expect(await screen.findByText(/No durable deployment state on this host/i)).toBeTruthy()
    expect(screen.queryByTestId('platform-deployments-table')).toBeNull()
  })
})

describe('AuthorityPage (honest unavailable state)', () => {
  it('renders the page root and the honest unavailable notice', async () => {
    renderAt('/authority', <AuthorityPage />)
    expect(await screen.findByTestId('authority-page')).toBeTruthy()
    expect(await screen.findByText(/Authority store unavailable on this host/i)).toBeTruthy()
    expect(screen.queryByTestId('authority-grants-table')).toBeNull()
  })
})

describe('UpdaterPage (honest unavailable state)', () => {
  it('renders the page root and the honest unavailable notice', async () => {
    renderAt('/updater', <UpdaterPage />)
    expect(await screen.findByTestId('updater-page')).toBeTruthy()
    expect(await screen.findByText(/No installed updater state on this host/i)).toBeTruthy()
    expect(screen.queryByTestId('updater-policy-editor')).toBeNull()
  })
})

describe('PreviewRoutesPage (honest error state)', () => {
  it('renders the page root and surfaces the refused read honestly', async () => {
    renderAt('/preview-routes', <PreviewRoutesPage />)
    expect(await screen.findByTestId('preview-routes-page')).toBeTruthy()
    // The mock refuses; the surface must not fabricate a route table.
    expect(screen.queryByTestId('preview-routes-table')).toBeNull()
  })
})
