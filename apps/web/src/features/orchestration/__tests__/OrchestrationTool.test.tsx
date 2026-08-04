/**
 * OrchestrationTool — binding behaviors from design/orchestration.md:
 * stage-gated controls (only the current stage may act, approve stays hidden
 * before the slice is prepared and paged), the always-visible safety facts,
 * the ONE blocked state, the stop control, and a close that stops everything.
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { getClient, resetClientForTests, resetMockState, useScenarioStore } from '@/client'
import type { ScenarioId } from '@/client'
import { INSTANCE_IDS } from '@/client/mock/seed'

import OrchestrationTool from '../OrchestrationTool'

const NIXOS = INSTANCE_IDS.nixosInfra
const CTO = INSTANCE_IDS.ctoPilot

function renderTool(instanceId: string = NIXOS) {
  return render(
    <MemoryRouter initialEntries={[`/app/${instanceId}/workbench/orchestration`]}>
      <Routes>
        <Route path="/app/:instanceId/workbench/orchestration" element={<OrchestrationTool />} />
        <Route path="/app/:instanceId/workbench/receipts/:receiptId" element={<div data-testid="receipt-detail" />} />
      </Routes>
    </MemoryRouter>,
  )
}

function setScenario(id: ScenarioId | null) {
  useScenarioStore.getState().setActive(id)
}

beforeEach(() => {
  resetClientForTests()
  resetMockState()
  setScenario(null)
})

afterEach(() => {
  cleanup()
  setScenario(null)
  resetClientForTests()
})

describe('OrchestrationTool — stage-gated controls', () => {
  it('hides approve before a slice is prepared and paged to the gate', async () => {
    const user = userEvent.setup()
    renderTool()

    // No session: empty state + objective form; no approval/run controls.
    expect(await screen.findByText('No orchestration session')).toBeTruthy()
    expect(screen.queryByTestId('orchestration-approve')).toBeNull()
    expect(screen.queryByTestId('orchestration-run')).toBeNull()
    expect(screen.queryByTestId('orchestration-close')).toBeNull()
    // Stepper marks stage 1 as current (aria-current).
    const currentStep = screen.getByTestId('orchestration-stepper').querySelector('[aria-current="step"]')
    expect(currentStep?.getAttribute('data-stage')).toBe('enter_objective')

    // Prepare the slice (stages 1–3 in the client).
    await user.type(screen.getByTestId('orchestration-objective'), 'Review the setup docs')
    await user.click(screen.getByTestId('orchestration-prepare'))

    // Stage 4 (review base): safety facts visible, approve STILL hidden.
    expect(await screen.findByTestId('stage-review_base')).toBeTruthy()
    expect(screen.getByTestId('safety-bar')).toBeTruthy()
    expect(screen.queryByTestId('orchestration-approve')).toBeNull()
    expect(screen.queryByTestId('orchestration-run')).toBeNull()

    // Page the reviews: base → plan → permissions → budget — still no approve.
    await user.click(await screen.findByTestId('orchestration-mark-reviewed'))
    expect(await screen.findByTestId('stage-review_plan')).toBeTruthy()
    expect(screen.queryByTestId('orchestration-approve')).toBeNull()

    await user.click(await screen.findByTestId('orchestration-mark-reviewed'))
    expect(await screen.findByTestId('stage-review_permissions')).toBeTruthy()
    expect(screen.queryByTestId('orchestration-approve')).toBeNull()

    await user.click(await screen.findByTestId('orchestration-mark-reviewed'))
    expect(await screen.findByTestId('stage-review_budget')).toBeTruthy()
    expect(screen.queryByTestId('orchestration-approve')).toBeNull()

    // …→ approve stage: only NOW does the approve control render.
    await user.click(await screen.findByTestId('orchestration-mark-reviewed'))
    expect(await screen.findByTestId('stage-approve')).toBeTruthy()
    const approve = await screen.findByTestId('orchestration-approve')
    expect(approve).toBeTruthy()
    expect(screen.getByTestId('orchestration-stepper').querySelector('[aria-current="step"]')?.getAttribute('data-stage')).toBe('approve')

    // Approving moves to the run stage; approve disappears again.
    await user.click(approve)
    expect(await screen.findByTestId('stage-run')).toBeTruthy()
    expect(await screen.findByTestId('orchestration-run')).toBeTruthy()
    expect(screen.queryByTestId('orchestration-approve')).toBeNull()
  }, 15_000)

  it('runs the approved slice once, then walks review → close → receipt', async () => {
    const user = userEvent.setup()
    setScenario('orchestration_approved')
    renderTool()

    // Approved scenario: run stage with the run control, nothing else active.
    expect(await screen.findByTestId('stage-run')).toBeTruthy()
    const run = await screen.findByTestId('orchestration-run')
    expect(screen.queryByTestId('orchestration-approve')).toBeNull()
    expect(screen.queryByTestId('orchestration-close')).toBeNull()
    await user.click(run)

    // Runs once, then waits at review result (never auto-continues).
    expect(await screen.findByTestId('stage-review_result', {}, { timeout: 12_000 })).toBeTruthy()
    expect(screen.getByText(/Health endpoint added|ready for your review|ran within budget|completed/i)).toBeTruthy()
    await user.click(screen.getByTestId('orchestration-to-independent-review'))

    // Independent review: reviewer ≠ implementer is stated.
    expect(await screen.findByTestId('stage-independent_review')).toBeTruthy()
    expect(screen.getByText(/never the implementer/)).toBeTruthy()
    await user.click(screen.getByTestId('orchestration-accept'))

    // Close: honest copy, then the receipt with the stop-everything line.
    expect(await screen.findByTestId('stage-close')).toBeTruthy()
    await user.click(screen.getByTestId('orchestration-close'))
    expect(await screen.findByTestId('stage-receipt')).toBeTruthy()
    expect(screen.getByText(/nothing continues in the background/)).toBeTruthy()
    const receiptButton = screen.getByTestId('orchestration-close-receipt')
    await user.click(receiptButton)
    expect(await screen.findByTestId('receipt-detail')).toBeTruthy()
  }, 25_000)
})

describe('OrchestrationTool — unavailable state', () => {
  it('shows ONE blocked state with inactive execution controls', async () => {
    setScenario('orchestration_unavailable')
    renderTool()
    const blocked = await screen.findByTestId('orchestration-unavailable')
    expect(within(blocked).getByText('Orchestration state unavailable')).toBeTruthy()
    expect(within(blocked).getByText(/Execution controls are inactive/)).toBeTruthy()
    expect(within(blocked).getByTestId('orchestration-reload')).toBeTruthy()
    // No form, no stepper-gated controls, no safety bar behind the block.
    expect(screen.queryByTestId('orchestration-objective')).toBeNull()
    expect(screen.queryByTestId('orchestration-approve')).toBeNull()
    expect(screen.queryByTestId('safety-bar')).toBeNull()
  })
})

describe('OrchestrationTool — stop + degraded capability', () => {
  it('keeps the stop control available on a running slice and stops honestly', async () => {
    const user = userEvent.setup()
    setScenario('orchestration_running')
    renderTool()

    // Running session reloaded from the record: Stop is visible.
    const stop = await screen.findByTestId('orchestration-stop')
    await user.click(stop)
    const dialog = await screen.findByTestId('confirm-dialog')
    expect(within(dialog).getByText(/stops after the current step/)).toBeTruthy()
    await user.click(within(dialog).getByTestId('confirm-action'))

    // Stopped → cancelled at the close stage; close still writes the receipt.
    expect(await screen.findByTestId('stage-close')).toBeTruthy()
    expect(screen.getByText(/stopped before completion/)).toBeTruthy()
  }, 15_000)

  it('notes assisted-only mode on the degraded CTO pilot', async () => {
    renderTool(CTO)
    expect(await screen.findByTestId('orchestration-degraded')).toBeTruthy()
    // Non-assisted modes are not offered.
    expect((screen.getByTestId('mode-advisory') as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByTestId('mode-managed_approved_queue') as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByTestId('mode-assisted') as HTMLButtonElement).disabled).toBe(false)
  })

  it('hides mock-only stop controls when the adapter advertises no stop transition', async () => {
    Object.defineProperty(getClient().orchestration, 'canStop', { value: false })
    setScenario('orchestration_running')
    renderTool()

    expect(await screen.findByTestId('safety-bar')).toBeTruthy()
    expect(screen.queryByTestId('orchestration-stop')).toBeNull()
    expect(screen.queryByTestId('orchestration-stop-header')).toBeNull()
    expect(screen.queryByTestId('orchestration-stop-sticky')).toBeNull()
    expect(screen.getByText(/connected service has no stop transition/i)).toBeTruthy()
  })

  it('hides mock-only reviewer rejection while preserving exact acceptance', async () => {
    const user = userEvent.setup()
    Object.defineProperty(getClient().orchestration, 'canRejectReview', { value: false })
    setScenario('orchestration_awaiting_review')
    renderTool()

    await user.click(await screen.findByTestId('orchestration-to-independent-review'))
    expect(await screen.findByTestId('orchestration-accept')).toBeTruthy()
    expect(screen.queryByTestId('orchestration-flag')).toBeNull()
    expect(screen.queryByTestId('orchestration-submit-flag')).toBeNull()
    expect(screen.getByText(/no rejection or reviewer-notes transition/i)).toBeTruthy()
  })
})
