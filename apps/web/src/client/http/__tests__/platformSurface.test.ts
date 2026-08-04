/**
 * Platform surface HTTP client contract tests: deployments, standing
 * authority, installed updater, and preview routes.
 *
 * These pin the honesty rules:
 * - Reads validate the structural envelope and pass rich payloads through.
 * - Digest-bound mutations resolve the local actor from /v1/status and send
 *   `approval: {decision, actorId, proposalDigest}`.
 * - A `409 *_state_unavailable` surfaces as an honest ClientError (the UI must
 *   not fake a working control).
 * - Updater rollback plan carries `applyBoundary: 'installed-authority-cli'`.
 */
import { describe, expect, it } from 'vitest'

import { ClientError } from '../../types'
import { HttpTransport } from '../transport'
import {
  DigestApproval,
  HttpAuthorityClient,
  HttpPlatformDeploymentsClient,
  HttpPreviewRoutesClient,
  HttpUpdaterClient,
} from '../domainsPlatformSurface'
import { jsonResponse, makeFakeFetch, type RecordedCall } from './helpers'

const STATUS_OK = { ok: true, result: { state: 'connected', actor: { role: 'platform_operator', actorId: 'op-1' } } }

const SHA = `sha256:${'a'.repeat(64)}`

/** Narrow a recorded call body to a record for field access in assertions. */
function bodyOf(call: RecordedCall): Record<string, unknown> {
  return (call.body ?? {}) as Record<string, unknown>
}

function deploymentIndex() {
  return {
    formatVersion: 'stateport.deployment-index/v1',
    deployments: [
      {
        deploymentId: 'dep_web',
        lifecycleState: 'healthy',
        driftStatus: 'aligned',
        desiredRevision: SHA,
        approvedPlanDigest: SHA,
        acceptedRevision: SHA,
        observedRevision: SHA,
        rollback: null,
        retainedDataState: { present: true },
        currentOperation: null,
        serviceHealth: { state: 'healthy' },
      },
    ],
  }
}

describe('HttpPlatformDeploymentsClient', () => {
  it('lists deployments and validates the index envelope', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/deployments', jsonResponse({ ok: true, result: deploymentIndex() })],
    ])
    const client = new HttpPlatformDeploymentsClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const index = await client.list()
    expect(index.formatVersion).toBe('stateport.deployment-index/v1')
    expect(index.deployments).toHaveLength(1)
    expect(index.deployments[0].deploymentId).toBe('dep_web')
    expect(index.deployments[0].retainedDataState).toEqual({ present: true })
  })

  it('returns an empty index when no durable state exists', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/deployments', jsonResponse({ ok: true, result: { formatVersion: 'stateport.deployment-index/v1', deployments: [] } })],
    ])
    const client = new HttpPlatformDeploymentsClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const index = await client.list()
    expect(index.deployments).toHaveLength(0)
  })

  it('reads deployment detail as a passthrough state projection', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/deployments/dep_web', jsonResponse({ ok: true, result: { state: { deploymentId: 'dep_web', lifecycleState: 'degraded', extra: { ports: [8080] } } } })],
    ])
    const client = new HttpPlatformDeploymentsClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const detail = await client.get('dep_web')
    expect(detail.state.deploymentId).toBe('dep_web')
    expect(detail.state.extra).toEqual({ ports: [8080] })
  })

  it('plans a deployment with the exact body shape', async () => {
    const fake = makeFakeFetch([
      ['POST', '/v1/deployments/plan', (call) => jsonResponse({ ok: true, result: { planDigest: SHA, operation: 'apply', grantId: bodyOf(call).grantId } })],
    ])
    const client = new HttpPlatformDeploymentsClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const result = await client.plan({ project: '/workspace/stateport', deploymentId: 'dep_web', grantId: 'grant_daily', sliceId: 'slc_1' })
    expect((result as Record<string, unknown>).planDigest).toBe(SHA)
    const call = fake.callsTo('/v1/deployments/plan')[0]
    expect(call.body).toEqual({
      project: '/workspace/stateport',
      deploymentId: 'dep_web',
      grantId: 'grant_daily',
      sliceId: 'slc_1',
    })
    expect(call.headers['x-stateport-csrf']).toBe('test-csrf')
  })

  it('applies an accepted plan with digest-bound approval from /v1/status', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/status', jsonResponse(STATUS_OK)],
      ['POST', '/v1/deployments/dep_web/apply', (call) => jsonResponse({ ok: true, result: { applied: true, acceptPlanDigest: bodyOf(call).acceptPlanDigest } })],
    ])
    const transport = new HttpTransport({ fetchFn: fake.fetchFn })
    const client = new HttpPlatformDeploymentsClient(transport)
    const result = await client.apply('dep_web', { acceptPlanDigest: SHA, grantId: 'grant_daily' })
    expect((result as Record<string, unknown>).applied).toBe(true)
    const call = fake.callsTo('/v1/deployments/dep_web/apply')[0]
    expect(bodyOf(call).approval).toEqual({ decision: 'approve', actorId: 'op-1', proposalDigest: SHA })
    expect(bodyOf(call).grantId).toBe('grant_daily')
    expect(bodyOf(call).acceptPlanDigest).toBe(SHA)
  })

  it('observes status and collects logs through the grant body', async () => {
    const fake = makeFakeFetch([
      ['POST', '/v1/deployments/dep_web/status', (call) => jsonResponse({ ok: true, result: { observed: true, grantId: bodyOf(call).grantId } })],
      ['POST', '/v1/deployments/dep_web/logs', (call) => jsonResponse({ ok: true, result: { lines: ['hi'], tail: bodyOf(call).tail, serviceId: bodyOf(call).serviceId } })],
    ])
    const client = new HttpPlatformDeploymentsClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const status = await client.status('dep_web', { grantId: 'g' })
    expect((status as Record<string, unknown>).observed).toBe(true)
    const logs = await client.logs('dep_web', { grantId: 'g', serviceId: 'web', tail: 50 })
    expect((logs as Record<string, unknown>).lines).toEqual(['hi'])
    const logCall = fake.callsTo('/v1/deployments/dep_web/logs')[0]
    expect(logCall.body).toEqual({ grantId: 'g', serviceId: 'web', tail: 50 })
  })

  it('restart and remove carry the digest-bound approval member', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/status', jsonResponse(STATUS_OK)],
      ['POST', '/v1/deployments/dep_web/restart', (call) => jsonResponse({ ok: true, result: { restarted: true, approvalActor: bodyOf(call).approval } })],
      ['POST', '/v1/deployments/dep_web/remove', (call) => jsonResponse({ ok: true, result: { removed: true, approvalDecision: bodyOf(call).approval } })],
    ])
    const client = new HttpPlatformDeploymentsClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const restarted = await client.restart('dep_web', { grantId: 'g' })
    expect((restarted as Record<string, unknown>).restarted).toBe(true)
    const removed = await client.remove('dep_web', { grantId: 'g' })
    expect((removed as Record<string, unknown>).removed).toBe(true)
    expect(bodyOf(fake.callsTo('/v1/deployments/dep_web/restart')[0]).approval).toMatchObject({ actorId: 'op-1' })
  })

  it('plans retained-data purge', async () => {
    const fake = makeFakeFetch([
      ['POST', '/v1/deployments/dep_web/purge/plan', (call) => jsonResponse({ ok: true, result: { operation: 'purge_data', grantId: bodyOf(call).grantId } })],
    ])
    const client = new HttpPlatformDeploymentsClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const result = await client.planPurge('dep_web', { grantId: 'g' })
    expect((result as Record<string, unknown>).operation).toBe('purge_data')
  })

  it('surfaces a 409 deployment_state_unavailable as an honest ClientError', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/deployments', jsonResponse({ ok: false, error: { code: 'deployment_state_unavailable', message: 'no durable state' } }, 409)],
    ])
    const client = new HttpPlatformDeploymentsClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const error = await client.list().catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ClientError)
    expect((error as ClientError).code).toBe('deployment_state_unavailable')
  })
})

describe('HttpAuthorityClient', () => {
  it('lists profiles with the full envelope', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/authority/profiles', jsonResponse({ ok: true, result: {
        formatVersion: 'stateport.authority-profile-index/v1',
        schema: 'stateport.authority-policy/v1',
        defaultProfile: 'balanced',
        policyDigest: SHA,
        actionPolicies: { plan_deployment: { requireApproval: true } },
        profiles: { balanced: { name: 'balanced' } },
        hardDeny: ['deploy'],
        mergeRequirements: ['reviews'],
        subagentDefaultDeny: ['push'],
        escalationConditions: [{ when: 'destructive' }],
      } })],
    ])
    const client = new HttpAuthorityClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const profiles = await client.listProfiles()
    expect(profiles.defaultProfile).toBe('balanced')
    expect(profiles.hardDeny).toEqual(['deploy'])
    expect(profiles.actionPolicies.plan_deployment.requireApproval).toBe(true)
  })

  it('lists grants and resolves the pause control state', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/authority/grants', jsonResponse({ ok: true, result: {
        grants: [{ grantId: 'grant_daily', grantDigest: SHA, profile: 'balanced' }],
        paused: false,
        control: { controlDigest: SHA, paused: false },
      } })],
    ])
    const client = new HttpAuthorityClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const grants = await client.listGrants()
    expect(grants.grants[0].grantId).toBe('grant_daily')
    expect(grants.paused).toBe(false)
    expect((grants.control as Record<string, unknown>).controlDigest).toBe(SHA)
  })

  it('pauses without a digest (pause is not digest-bound)', async () => {
    const fake = makeFakeFetch([
      ['POST', '/v1/authority/pause', (call) => jsonResponse({ ok: true, result: { paused: true, sawApproval: 'approval' in bodyOf(call) } })],
    ])
    const client = new HttpAuthorityClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const result = await client.setPaused({ paused: true, ownerDirectiveId: 'dir_1', reason: 'maintenance' })
    expect((result.control as Record<string, unknown>).paused).toBe(true)
    const call = fake.callsTo('/v1/authority/pause')[0]
    expect(bodyOf(call).paused).toBe(true)
    expect(bodyOf(call).approval).toBeUndefined()
    expect(bodyOf(call).ownerDirectiveId).toBe('dir_1')
  })

  it('unpauses with the control digest resolved from the grants projection', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/status', jsonResponse(STATUS_OK)],
      ['GET', '/v1/authority/grants', jsonResponse({ ok: true, result: {
        grants: [],
        paused: true,
        control: { controlDigest: SHA, paused: true },
      } })],
      ['POST', '/v1/authority/pause', (call) => jsonResponse({ ok: true, result: { paused: false, approval: bodyOf(call).approval } })],
    ])
    const client = new HttpAuthorityClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const result = await client.setPaused({ paused: false, ownerDirectiveId: 'dir_2', reason: 'resume' })
    expect((result.control as Record<string, unknown>).paused).toBe(false)
    const call = fake.callsTo('/v1/authority/pause')[0]
    expect(bodyOf(call).approval).toEqual({ decision: 'approve', actorId: 'op-1', proposalDigest: SHA })
  })

  it('revokes a grant with the digest resolved from the grant detail', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/status', jsonResponse(STATUS_OK)],
      ['GET', '/v1/authority/grants/grant_daily', jsonResponse({ ok: true, result: {
        grant: { grantId: 'grant_daily', grantDigest: SHA },
        paused: false,
      } })],
      ['POST', '/v1/authority/grants/grant_daily/revoke', (call) => {
        const approval = bodyOf(call).approval as Record<string, unknown>
        return jsonResponse({ ok: true, result: { revocation: { revoked: true }, revokedGrantDigest: approval.proposalDigest } })
      }],
    ])
    const client = new HttpAuthorityClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const result = await client.revokeGrant('grant_daily', { ownerDirectiveId: 'dir_3', reason: 'expired' })
    expect(result.revokedGrantDigest).toBe(SHA)
    const call = fake.callsTo('/v1/authority/grants/grant_daily/revoke')[0]
    expect(bodyOf(call).approval).toEqual({ decision: 'approve', actorId: 'op-1', proposalDigest: SHA })
    expect(bodyOf(call).ownerDirectiveId).toBe('dir_3')
    expect(bodyOf(call).reason).toBe('expired')
  })

  it('surfaces a 404 grant_not_found honestly', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/authority/grants/missing', jsonResponse({ ok: false, error: { code: 'grant_not_found', message: 'no such grant' } }, 404)],
    ])
    const client = new HttpAuthorityClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const error = await client.getGrant('missing').catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ClientError)
    expect((error as ClientError).code).toBe('grant_not_found')
  })
})

describe('HttpUpdaterClient', () => {
  it('reads the installed updater status as a passthrough projection', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/updater/status', jsonResponse({ ok: true, result: { phase: 'idle', target: 'stateport-vm', current: { version: '1.0.0' } } })],
    ])
    const client = new HttpUpdaterClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const status = await client.getStatus()
    expect(status.phase).toBe('idle')
    expect(status.target).toBe('stateport-vm')
  })

  it('reads policy and rollback projections with their envelopes', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/updater/policy', jsonResponse({ ok: true, result: {
        formatVersion: 'stateport.updater-policy/v1',
        policy: { channel: 'stable' },
        statusDigest: SHA,
      } })],
      ['GET', '/v1/updater/rollback', jsonResponse({ ok: true, result: {
        formatVersion: 'stateport.updater-rollback/v1',
        phase: 'idle',
        pendingPhase: null,
        retainedPredecessor: { version: '0.9.0', digest: SHA },
        rollbackAvailable: true,
        statusDigest: SHA,
      } })],
    ])
    const client = new HttpUpdaterClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const policy = await client.getPolicy()
    expect(policy.statusDigest).toBe(SHA)
    expect(policy.policy.channel).toBe('stable')
    const rollback = await client.getRollback()
    expect(rollback.rollbackAvailable).toBe(true)
    expect(rollback.retainedPredecessor).not.toBeNull()
  })

  it('mutates the policy with digest-bound approval', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/status', jsonResponse(STATUS_OK)],
      ['POST', '/v1/updater/policy', (call) => {
        const policy = bodyOf(call).policy as Record<string, unknown>
        return jsonResponse({ ok: true, result: { ok: true, observedDigest: bodyOf(call).expectedStatusDigest, channel: policy.channel } })
      }],
    ])
    const client = new HttpUpdaterClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const result = await client.setPolicy({ policy: { channel: 'beta' }, expectedStatusDigest: SHA })
    expect((result as Record<string, unknown>).channel).toBe('beta')
    const call = fake.callsTo('/v1/updater/policy')[0]
    expect(bodyOf(call).approval).toEqual({ decision: 'approve', actorId: 'op-1', proposalDigest: SHA })
    expect(bodyOf(call).policy).toEqual({ channel: 'beta' })
  })

  it('plans rollback with the apply boundary marker (never applies over HTTP)', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/status', jsonResponse(STATUS_OK)],
      ['POST', '/v1/updater/rollback', (call) => jsonResponse({ ok: true, result: {
        plan: { operation: 'rollback', digest: SHA, observedDigest: bodyOf(call).expectedStatusDigest },
        applyBoundary: 'installed-authority-cli',
        note: 'apply remains reserved to the installed updater authority boundary',
      } })],
    ])
    const client = new HttpUpdaterClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const result = await client.planRollback({ expectedStatusDigest: SHA })
    expect(result.applyBoundary).toBe('installed-authority-cli')
    expect(result.note).toContain('reserved')
    const call = fake.callsTo('/v1/updater/rollback')[0]
    expect(bodyOf(call).approval).toEqual({ decision: 'approve', actorId: 'op-1', proposalDigest: SHA })
  })

  it('surfaces updater_state_unavailable honestly when no host state exists', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/updater/status', jsonResponse({ ok: false, error: { code: 'updater_state_unavailable', message: 'no updater' } }, 409)],
    ])
    const client = new HttpUpdaterClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const error = await client.getStatus().catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ClientError)
    expect((error as ClientError).code).toBe('updater_state_unavailable')
  })
})

describe('HttpPreviewRoutesClient', () => {
  const ROUTE = {
    schema: 'stateport.preview-route/v1',
    routeId: 'route_' + '0'.repeat(24),
    capsuleId: 'capsule_web',
    serviceId: 'web',
    revisionDigest: SHA,
    upstream: { host: '127.0.0.1', port: 8080 },
    createdAt: '2026-08-03T10:00:00Z',
    expiresAt: '2026-08-03T11:00:00Z',
    revokedAt: null,
    revocationReason: null,
    routeDigest: SHA,
    status: 'active' as const,
  }

  it('lists routes with derived status', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/preview-routes', jsonResponse({ ok: true, result: { routes: [ROUTE] } })],
    ])
    const client = new HttpPreviewRoutesClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const index = await client.list()
    expect(index.routes).toHaveLength(1)
    expect(index.routes[0].status).toBe('active')
    expect(index.routes[0].upstream.port).toBe(8080)
  })

  it('registers a route with the exact body shape', async () => {
    const fake = makeFakeFetch([
      ['POST', '/v1/preview-routes', (call) => {
        const body = bodyOf(call)
        return jsonResponse({ ok: true, result: { ...ROUTE, upstream: { host: '127.0.0.1', port: body.upstreamPort } } })
      }],
    ])
    const client = new HttpPreviewRoutesClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const route = await client.register({ capsuleId: 'capsule_web', serviceId: 'web', revisionDigest: SHA, upstreamPort: 3000, ttlSeconds: 3600 })
    expect(route.upstream.port).toBe(3000)
    const call = fake.callsTo('/v1/preview-routes')[0]
    expect(call.body).toEqual({ capsuleId: 'capsule_web', serviceId: 'web', revisionDigest: SHA, upstreamPort: 3000, ttlSeconds: 3600 })
  })

  it('revokes a route with a reason', async () => {
    const fake = makeFakeFetch([
      ['POST', '/v1/preview-routes/' + ROUTE.routeId + '/revoke', (call) => jsonResponse({ ok: true, result: { ...ROUTE, revokedAt: '2026-08-03T12:00:00Z', revocationReason: bodyOf(call).reason, status: 'revoked' } })],
    ])
    const client = new HttpPreviewRoutesClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const route = await client.revoke(ROUTE.routeId, { reason: 'rolled back' })
    expect(route.status).toBe('revoked')
    expect(route.revocationReason).toBe('rolled back')
    const call = fake.callsTo('/revoke')[0]
    expect(call.body).toEqual({ reason: 'rolled back' })
  })

  it('atomically rewrites a route to a new revision and port', async () => {
    const newDigest = `sha256:${'b'.repeat(64)}`
    const fake = makeFakeFetch([
      ['POST', '/v1/preview-routes/' + ROUTE.routeId + '/rewrite', (call) => {
        const body = bodyOf(call)
        return jsonResponse({ ok: true, result: { ...ROUTE, revisionDigest: body.revisionDigest, upstream: { host: '127.0.0.1', port: body.upstreamPort } } })
      }],
    ])
    const client = new HttpPreviewRoutesClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const route = await client.rewrite(ROUTE.routeId, { revisionDigest: newDigest, upstreamPort: 4000 })
    expect(route.revisionDigest).toBe(newDigest)
    expect(route.upstream.port).toBe(4000)
    const call = fake.callsTo('/rewrite')[0]
    expect(call.body).toEqual({ revisionDigest: newDigest, upstreamPort: 4000 })
  })

  it('validates the route document (rejects an unknown schema)', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/preview-routes', jsonResponse({ ok: true, result: { routes: [{ ...ROUTE, schema: 'something.else/v9' }] } })],
    ])
    const client = new HttpPreviewRoutesClient(new HttpTransport({ fetchFn: fake.fetchFn }))
    const error = await client.list().catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ClientError)
    expect((error as ClientError).kind).toBe('validation')
  })
})

describe('DigestApproval', () => {
  it('caches the actor identity across calls', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/status', jsonResponse(STATUS_OK)],
    ])
    const transport = new HttpTransport({ fetchFn: fake.fetchFn })
    const approval = new DigestApproval(transport)
    const a1 = await approval.build('d1')
    const a2 = await approval.build('d2')
    expect(a1.actorId).toBe('op-1')
    expect(a2.actorId).toBe('op-1')
    expect(a2.proposalDigest).toBe('d2')
    // /v1/status fetched exactly once (cached).
    expect(fake.callsTo('/v1/status')).toHaveLength(1)
  })

  it('fails closed when the status projection carries no actor identity', async () => {
    const fake = makeFakeFetch([
      ['GET', '/v1/status', jsonResponse({ ok: true, result: { state: 'connected' } })],
    ])
    const approval = new DigestApproval(new HttpTransport({ fetchFn: fake.fetchFn }))
    const error = await approval.build('d1').catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ClientError)
    expect((error as ClientError).kind).toBe('validation')
  })
})
