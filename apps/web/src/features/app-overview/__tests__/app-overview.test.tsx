/**
 * App overview — the front door to an application:
 * - CTO Pilot surfaces backup-due as the ONE dominant attention state (badge +
 *   fact, not restated), and Back up now flows through the client,
 * - StudyState Alpha shows the learning goal + evidence progress and renders
 *   NO workbench actions (capability-gated),
 * - NixOS Infrastructure shows the stopped VM as neutral (a fact, not an
 *   alarm) and the pending approval as the dominant state,
 * - contextual palette commands register (pin, approvals, backup).
 */
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { getClient, resetClientForTests } from '@/client'
import { useCommandStore } from '@/shell/commands'
import { invalidateInstanceCache } from '@/shell/data'
import { AppContextShell } from '@/shell/AppContextShell'
import { useSessionStore, useWorkspaceStore } from '@/state'

import AppOverviewPage from '../AppOverviewPage'
import { resetDashboardSnapshotForTests } from '@/features/applications/lib/dashboardData'
import { useApplicationsPrefs } from '@/features/applications/lib/prefsStore'

const LONG = 15_000

beforeEach(() => {
  resetClientForTests()
  invalidateInstanceCache()
  resetDashboardSnapshotForTests()
  useApplicationsPrefs.setState({
    pinnedOrder: [],
    sort: 'recent',
    onboardingDismissed: false,
    checklistDoneOverrides: {},
    studyGoalOverrides: {},
  })
  useWorkspaceStore.setState({
    lastInstanceId: null,
    lastView: null,
    lastWorkbenchTool: null,
    density: 'compact',
    layouts: {},
    openFiles: {},
    activeFile: {},
  })
  useSessionStore.setState({ serviceStatus: { state: 'connected', endpoint: 'http://127.0.0.1:8734' } })
  useSessionStore.getState().setActiveScenario(null)
  useCommandStore.setState({ commands: {}, paletteOpen: false, shortcutsOpen: false })
})

afterEach(() => {
  cleanup()
})

function renderOverview(instanceId: string) {
  return render(
    <MemoryRouter initialEntries={[`/app/${instanceId}`]}>
      <Routes>
        <Route path="/app/:instanceId" element={<AppContextShell />}>
          <Route index element={<AppOverviewPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('App overview', () => {
  it(
    'CTO Pilot: backup due is the dominant attention state (badge + fact), not restated',
    async () => {
      renderOverview('ins_cto_pilot')
      const header = await screen.findByTestId('overview-header', undefined, { timeout: LONG })
      expect(header.textContent).toContain('StatePort CTO Pilot')
      expect(header.textContent).toContain('ProjectState')
      // One dominant badge, honest attention state.
      expect(header.textContent).toContain('Backup due')

      // Facts strip carries the same state once, mapped as attention.
      const fact = await screen.findByTestId('fact-backup', undefined, { timeout: LONG })
      expect(fact.textContent).toContain('Backup due')
      expect(fact.querySelector('[data-state]')?.getAttribute('data-state')).toBe('attention')

      // Needs attention section lists the backup item with an acknowledge affordance.
      const section = await screen.findByTestId('overview-attention-section', undefined, { timeout: LONG })
      expect(section.textContent).toContain('Backup is due')

      // Recovery section offers the governed action.
      expect(screen.getByRole('button', { name: /back up now/i })).toBeTruthy()
    },
    LONG,
  )

  it(
    'CTO Pilot: Back up now runs through the client and recovery becomes current',
    async () => {
      const user = userEvent.setup()
      renderOverview('ins_cto_pilot')
      const button = await screen.findByRole('button', { name: /back up now/i }, { timeout: LONG })
      await user.click(button)

      await waitFor(
        () => expect(useSessionStore.getState().toasts.some((t) => t.title === 'Backup completed')).toBe(true),
        { timeout: LONG },
      )

      // Fresh client read proves the domain change persisted (after debounce).
      await waitFor(
        async () => {
          resetClientForTests()
          const instance = await getClient().applications.get('ins_cto_pilot')
          expect(instance.recovery.state).toBe('current')
        },
        { timeout: LONG },
      )
    },
    LONG * 2,
  )

  it(
    'CTO Pilot: provenance is human-first and exact identity stays behind disclosure',
    async () => {
      const user = userEvent.setup()
      renderOverview('ins_cto_pilot')
      const section = await screen.findByTestId('provenance-ownership-section', undefined, {
        timeout: LONG,
      })

      expect(section.textContent).toContain('Canonical source')
      expect(section.textContent).toContain('Version 1.4.0')
      expect(within(section).getByTestId('ownership-count-template').textContent).toBe('3')
      expect(within(section).getByTestId('ownership-count-instance').textContent).toBe('2')
      expect(
        within(section).queryByText('https://github.com/example/project-state.git'),
      ).toBeNull()

      const disclosure = within(section).getByRole('button', {
        name: /exact identity and bounded paths/i,
      })
      expect(disclosure.getAttribute('aria-expanded')).toBe('false')
      await user.click(disclosure)
      expect(disclosure.getAttribute('aria-expanded')).toBe('true')

      const exact = within(section).getByTestId('provenance-exact-detail')
      expect(exact.textContent).toContain('https://github.com/example/project-state.git')
      expect(exact.textContent).toContain('Git commit')
      expect(exact.textContent).toContain('README.md')
      expect(exact.textContent).toContain('.statedd/lock.yaml')
    },
    LONG,
  )

  it(
    'StudyState Alpha: shows learning goal and evidence progress, and NO workbench actions',
    async () => {
      renderOverview('ins_study_alpha')
      const section = await screen.findByTestId('study-section', undefined, { timeout: LONG })
      expect(section.textContent).toContain('Pass the NixOS fundamentals assessment')
      expect(section.textContent).toContain('62% toward goal')
      expect(section.textContent).toContain('1 of 3 evidence items verified')
      expect(section.textContent).toContain('Read: modules and options')

      // Header: honest Ready badge; generic Conversation is secondary so the
      // state-derived learning action owns the page's primary hierarchy.
      const header = await screen.findByTestId('overview-header', undefined, { timeout: LONG })
      expect(header.textContent).toContain('Ready')
      expect(screen.queryByRole('button', { name: /open conversation — studystate alpha/i })).toBeNull()
      expect(screen.getByRole('button', { name: 'Conversation' }).getAttribute('data-variant')).toBe('outline')

      // The workbench capability is unavailable → no workbench action anywhere.
      expect(screen.queryByRole('button', { name: /workbench/i })).toBeNull()
      expect(screen.queryByRole('link', { name: /workbench/i })).toBeNull()
      expect(screen.queryByTestId('quick-links')).toBeNull()
      expect(document.querySelectorAll('a[href*="/workbench"]').length).toBe(0)

      // StudyState has no backup capability → no backup action/command either.
      expect(screen.queryByRole('button', { name: /back up now/i })).toBeNull()
      const ids = Object.keys(useCommandStore.getState().commands)
      expect(ids).toContain('app.toggle_pin')
      expect(ids).not.toContain('app.run_backup')
      expect(ids).not.toContain('app.open_approvals')
    },
    LONG,
  )

  it(
    'ChecklistState Sample: checklist renders with honest progress and item toggling persists',
    async () => {
      const user = userEvent.setup()
      renderOverview('ins_checklist_sample')
      const section = await screen.findByTestId('checklist-section', undefined, { timeout: LONG })
      expect(section.textContent).toContain('2 of 5 complete')
      expect(section.textContent).toContain('Next up:')
      expect(section.textContent).toContain('Open the receipt for the change')

      // Toggle the next unchecked item — optimistic, persisted in the feature store.
      const checkbox = await screen.findByRole('checkbox', { name: 'Open the receipt for the change' }, { timeout: LONG })
      await user.click(checkbox)
      await waitFor(() => {
        expect(useApplicationsPrefs.getState().checklistDoneOverrides['ins_checklist_sample:chk_3']).toBe(true)
      })
      expect((await screen.findByTestId('checklist-section')).textContent).toContain('3 of 5 complete')

      // The local override is explicitly labelled — never presented as
      // recorded application state — and can be reset.
      const draftNote = await screen.findByTestId('checklist-local-draft')
      expect(draftNote.textContent).toContain('stored in this browser only')
      await user.click(within(draftNote).getByRole('button', { name: /reset to application state/i }))
      await waitFor(() => {
        expect(useApplicationsPrefs.getState().checklistDoneOverrides['ins_checklist_sample:chk_3']).toBeUndefined()
      })
      expect(screen.queryByTestId('checklist-local-draft')).toBeNull()

      // Recovery honestly says not configured; no backup button.
      expect(screen.getByTestId('recovery-section').textContent).toContain('Not configured')
      expect(screen.queryByRole('button', { name: /back up now/i })).toBeNull()
    },
    LONG,
  )

  it(
    'NixOS Infrastructure: stopped VM is neutral, pending approval is dominant, commands register',
    async () => {
      renderOverview('ins_nixos_infra')
      // Wait for overview data (approvals drive the dominant badge).
      const vm = await screen.findByTestId('target-vm', undefined, { timeout: LONG })
      const header = await screen.findByTestId('overview-header', undefined, { timeout: LONG })
      await waitFor(() => expect(header.textContent).toContain('Awaiting approval'), { timeout: LONG })
      expect(header.textContent).toContain('NixOS Infrastructure')
      expect(vm.textContent).toContain('Stopped')
      expect(vm.querySelector('[data-state]')?.getAttribute('data-state')).toBe('neutral')
      const ssh = screen.getByTestId('target-ssh')
      expect(ssh.textContent).toContain('SSH unavailable — VM stopped')
      expect(ssh.querySelector('[data-state]')?.getAttribute('data-state')).toBe('neutral')

      // Repository line is present and clean.
      const project = screen.getByTestId('project-section')
      expect(project.textContent).toContain('nixos-homelab')
      expect(project.textContent).toContain('Clean')

      // The pending approval surfaces in Needs attention.
      const section = await screen.findByTestId('overview-attention-section', undefined, { timeout: LONG })
      expect(section.textContent).toContain('Start virtual machine')
      // De-duplicated: the raw "approval waiting" attention item is not doubled.
      expect(section.textContent).not.toContain('One approval is waiting')

      // Contextual commands: pin, approvals for this app, run backup.
      const ids = Object.keys(useCommandStore.getState().commands)
      expect(ids).toContain('app.toggle_pin')
      expect(ids).toContain('app.open_approvals')
      expect(ids).toContain('app.run_backup')
    },
    LONG,
  )

  it(
    'keeps the legacy app-overview-stub alias for the shell route-smoke test',
    async () => {
      renderOverview('ins_cto_pilot')
      expect(await screen.findByTestId('app-overview-stub', undefined, { timeout: LONG })).toBeTruthy()
      expect(screen.getByTestId('app-overview-page')).toBeTruthy()
    },
    LONG,
  )
})
