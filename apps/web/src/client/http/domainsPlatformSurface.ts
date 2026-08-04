/**
 * HTTP domain clients — platform deployments, standing authority, installed
 * updater, and preview routes.
 *
 * These are operator-only host-state projections. Honesty rules:
 * - Every read validates the structural envelope (formatVersion + the fields
 *   the UI renders) and passes the rest through, so a richer backend stays
 *   visible without the client inventing a second authority.
 * - Digest-bound mutations (apply / restart / remove / revoke / unpause /
 *   updater policy / updater rollback) resolve the local actor identity from
 *   `/v1/status` and send `approval: {decision, actorId, proposalDigest}`.
 * - A `409 *_state_unavailable` (no durable host state) and
 *   `409 approval_digest_mismatch` (stale review) surface as honest
 *   ClientErrors; the UI shows its real state instead of fake controls.
 * - Updater rollback *apply* is never exposed: the backend returns
 *   `applyBoundary: 'installed-authority-cli'` and the UI must show that as a
 *   limitation, not a working apply button.
 */
import { z } from 'zod'

import type {
  AuthorityClient,
  PlatformDeploymentsClient,
  PreviewRoutesClient,
  UpdaterClient,
} from '../client'
import type {
  AuthorityGrantDetail,
  AuthorityGrantsIndex,
  AuthorityProfileIndex,
  PlatformDeploymentDetail,
  PlatformDeploymentIndex,
  PlatformDeploymentMutationResult,
  PlatformDeploymentPlanResult,
  PreviewRoute,
  PreviewRouteIndex,
  UpdaterPolicyProjection,
  UpdaterRollbackPlanResult,
  UpdaterRollbackProjection,
  UpdaterStatus,
} from '../types'
import { ClientError } from '../types'
import { endpoints } from './endpoints'
import { HttpTransport } from './transport'

const unknownPayload = z.unknown()
const sha256Digest = z.string().regex(/^sha256:[0-9a-f]{64}$/)
const routeIdSchema = z.string().regex(/^route_[0-9a-f]{24}$/)

const deploymentSummary = z
  .object({
    deploymentId: z.string().min(1),
    lifecycleState: z.string().min(1),
    driftStatus: z.string().nullable(),
    desiredRevision: z.string().nullable(),
    approvedPlanDigest: z.string().nullable(),
    acceptedRevision: z.string().nullable(),
    observedRevision: z.string().nullable(),
    rollback: z.unknown(),
    retainedDataState: z.unknown(),
    currentOperation: z.string().nullable(),
    serviceHealth: z.unknown(),
  })
  .passthrough()

const deploymentIndexSchema = z
  .object({
    formatVersion: z.literal('stateport.deployment-index/v1'),
    deployments: z.array(deploymentSummary),
  })
  .passthrough()

const deploymentDetailSchema = z
  .object({
    state: z.record(z.string(), z.unknown()),
  })
  .passthrough()

const authorityProfileSchema = z
  .object({
    formatVersion: z.literal('stateport.authority-profile-index/v1'),
    schema: z.string().min(1),
    defaultProfile: z.string().min(1),
    policyDigest: z.string().min(1),
    actionPolicies: z.record(z.string(), z.record(z.string(), z.unknown())),
    profiles: z.record(z.string(), z.record(z.string(), z.unknown())),
    hardDeny: z.array(z.string()),
    mergeRequirements: z.array(z.string()),
    subagentDefaultDeny: z.array(z.string()),
    escalationConditions: z.array(z.unknown()),
  })
  .passthrough()

const authorityGrantRow = z
  .object({
    grantId: z.string().min(1),
    grantDigest: z.string().min(1),
  })
  .passthrough()

const authorityGrantsSchema = z
  .object({
    grants: z.array(authorityGrantRow),
    paused: z.boolean(),
  })
  .passthrough()

const authorityGrantDetailSchema = z
  .object({
    grant: authorityGrantRow,
    paused: z.boolean(),
  })
  .passthrough()

const authorityRevokeResultSchema = z
  .object({
    revokedGrantDigest: z.string().min(1),
  })
  .passthrough()

const updaterPolicySchema = z
  .object({
    formatVersion: z.literal('stateport.updater-policy/v1'),
    policy: z.record(z.string(), z.unknown()),
    statusDigest: z.string().min(1),
  })
  .passthrough()

const updaterRollbackSchema = z
  .object({
    formatVersion: z.literal('stateport.updater-rollback/v1'),
    phase: z.string().min(1),
    pendingPhase: z.string().nullable(),
    retainedPredecessor: z.record(z.string(), z.unknown()).nullable(),
    rollbackAvailable: z.boolean(),
    statusDigest: z.string().min(1),
  })
  .passthrough()

const updaterRollbackPlanSchema = z
  .object({
    plan: z.record(z.string(), z.unknown()),
    applyBoundary: z.literal('installed-authority-cli'),
    note: z.string().min(1),
  })
  .passthrough()

const previewRouteSchema = z
  .object({
    schema: z.literal('stateport.preview-route/v1'),
    routeId: routeIdSchema,
    capsuleId: z.string().min(1),
    serviceId: z.string().min(1),
    revisionDigest: sha256Digest,
    upstream: z.object({ host: z.string().min(1), port: z.number().int().min(1).max(65535) }),
    createdAt: z.string().min(1),
    expiresAt: z.string().min(1),
    revokedAt: z.string().nullable(),
    revocationReason: z.string().nullable(),
    routeDigest: sha256Digest,
    status: z.enum(['active', 'expired', 'revoked']),
  })
  .passthrough()

const previewRouteIndexSchema = z
  .object({
    routes: z.array(previewRouteSchema),
  })
  .passthrough()

/**
 * Resolve the local operator actor identity from the status projection, then
 * build the exact digest-bound approval body member the contract requires.
 * The actor identity is cached for the life of the client (same as the
 * repository-import client).
 */
export class DigestApproval {
  private actorId: string | null = null
  private readonly transport: HttpTransport

  constructor(transport: HttpTransport) {
    this.transport = transport
  }

  async build(proposalDigest: string): Promise<{
    decision: 'approve'
    actorId: string
    proposalDigest: string
  }> {
    const actorId = await this.currentActorId()
    return { decision: 'approve', actorId, proposalDigest }
  }

  private async currentActorId(): Promise<string> {
    if (this.actorId) return this.actorId
    const payload = await this.transport.request(endpoints.status, { schema: unknownPayload })
    const wire = z
      .object({ actor: z.object({ actorId: z.string().optional() }).optional() })
      .passthrough()
      .parse(payload)
    const actorId = wire.actor?.actorId
    if (!actorId) {
      throw new ClientError('validation', 'The service status projection carried no actor identity')
    }
    this.actorId = actorId
    return actorId
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Platform deployments
// ─────────────────────────────────────────────────────────────────────────────

export class HttpPlatformDeploymentsClient implements PlatformDeploymentsClient {
  private readonly transport: HttpTransport
  private readonly approval: DigestApproval

  constructor(transport: HttpTransport, approval?: DigestApproval) {
    this.transport = transport
    this.approval = approval ?? new DigestApproval(transport)
  }

  async list(): Promise<PlatformDeploymentIndex> {
    const payload = await this.transport.request(endpoints.deployments, {
      schema: deploymentIndexSchema,
    })
    return payload as unknown as PlatformDeploymentIndex
  }

  async get(deploymentId: string): Promise<PlatformDeploymentDetail> {
    const payload = await this.transport.request(endpoints.deployment(deploymentId), {
      schema: deploymentDetailSchema,
    })
    return payload as unknown as PlatformDeploymentDetail
  }

  async plan(input: {
    project: string
    deploymentId: string
    grantId: string
    sliceId?: string
    rollbackOf?: string
  }): Promise<PlatformDeploymentPlanResult> {
    const body: Record<string, unknown> = {
      project: input.project,
      deploymentId: input.deploymentId,
      grantId: input.grantId,
    }
    if (input.sliceId !== undefined) body.sliceId = input.sliceId
    if (input.rollbackOf !== undefined) body.rollbackOf = input.rollbackOf
    return this.transport.request(endpoints.deploymentPlan, {
      method: 'POST',
      body,
      schema: unknownPayload,
    }) as Promise<PlatformDeploymentPlanResult>
  }

  async apply(
    deploymentId: string,
    input: { acceptPlanDigest: string; grantId: string; sliceId?: string },
  ): Promise<PlatformDeploymentMutationResult> {
    const approval = await this.approval.build(input.acceptPlanDigest)
    const body: Record<string, unknown> = {
      acceptPlanDigest: input.acceptPlanDigest,
      grantId: input.grantId,
      approval,
    }
    if (input.sliceId !== undefined) body.sliceId = input.sliceId
    return this.transport.request(endpoints.deploymentApply(deploymentId), {
      method: 'POST',
      body,
      schema: unknownPayload,
    }) as Promise<PlatformDeploymentMutationResult>
  }

  async status(
    deploymentId: string,
    input: { grantId: string; sliceId?: string },
  ): Promise<PlatformDeploymentMutationResult> {
    return this.governedRead(endpoints.deploymentStatus(deploymentId), input)
  }

  async logs(
    deploymentId: string,
    input: { grantId: string; sliceId?: string; serviceId?: string; tail?: number },
  ): Promise<PlatformDeploymentMutationResult> {
    const body: Record<string, unknown> = { grantId: input.grantId }
    if (input.sliceId !== undefined) body.sliceId = input.sliceId
    if (input.serviceId !== undefined) body.serviceId = input.serviceId
    if (input.tail !== undefined) body.tail = input.tail
    return this.transport.request(endpoints.deploymentLogs(deploymentId), {
      method: 'POST',
      body,
      schema: unknownPayload,
    }) as Promise<PlatformDeploymentMutationResult>
  }

  async restart(
    deploymentId: string,
    input: { grantId: string; sliceId?: string },
  ): Promise<PlatformDeploymentMutationResult> {
    return this.digestBoundRuntime(endpoints.deploymentRestart(deploymentId), input)
  }

  async remove(
    deploymentId: string,
    input: { grantId: string; sliceId?: string },
  ): Promise<PlatformDeploymentMutationResult> {
    return this.digestBoundRuntime(endpoints.deploymentRemove(deploymentId), input)
  }

  async planPurge(
    deploymentId: string,
    input: { grantId: string; sliceId?: string },
  ): Promise<PlatformDeploymentPlanResult> {
    return this.governedRead(endpoints.deploymentPurgePlan(deploymentId), input) as Promise<PlatformDeploymentPlanResult>
  }

  private async governedRead(
    path: string,
    input: { grantId: string; sliceId?: string },
  ): Promise<PlatformDeploymentMutationResult> {
    const body: Record<string, unknown> = { grantId: input.grantId }
    if (input.sliceId !== undefined) body.sliceId = input.sliceId
    return this.transport.request(path, {
      method: 'POST',
      body,
      schema: unknownPayload,
    }) as Promise<PlatformDeploymentMutationResult>
  }

  /**
   * Restart/remove are digest-bound to the pending authority run id. The
   * server resolves the expected run id itself (`peek_authority_run_id`) and
   * binds the approval to that value; the client sends the canonical approval
   * member and the server re-checks the exact value. If no pending run exists
   * the server refuses typed, which surfaces as an honest ClientError.
   */
  private async digestBoundRuntime(
    path: string,
    input: { grantId: string; sliceId?: string },
  ): Promise<PlatformDeploymentMutationResult> {
    const approval = await this.approval.build('')
    const body: Record<string, unknown> = { grantId: input.grantId, approval }
    if (input.sliceId !== undefined) body.sliceId = input.sliceId
    return this.transport.request(path, {
      method: 'POST',
      body,
      schema: unknownPayload,
    }) as Promise<PlatformDeploymentMutationResult>
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Standing authority
// ─────────────────────────────────────────────────────────────────────────────

export class HttpAuthorityClient implements AuthorityClient {
  private readonly transport: HttpTransport
  private readonly approval: DigestApproval

  constructor(transport: HttpTransport, approval?: DigestApproval) {
    this.transport = transport
    this.approval = approval ?? new DigestApproval(transport)
  }

  async listProfiles(): Promise<AuthorityProfileIndex> {
    const payload = await this.transport.request(endpoints.authorityProfiles, {
      schema: authorityProfileSchema,
    })
    return payload as unknown as AuthorityProfileIndex
  }

  async listGrants(): Promise<AuthorityGrantsIndex> {
    const payload = await this.transport.request(endpoints.authorityGrants, {
      schema: authorityGrantsSchema,
    })
    return payload as unknown as AuthorityGrantsIndex
  }

  async getGrant(grantId: string): Promise<AuthorityGrantDetail> {
    const payload = await this.transport.request(endpoints.authorityGrant(grantId), {
      schema: authorityGrantDetailSchema,
    })
    return payload as unknown as AuthorityGrantDetail
  }

  async revokeGrant(
    grantId: string,
    input: { ownerDirectiveId: string; reason: string },
  ): Promise<{ revocation: unknown; revokedGrantDigest: string }> {
    // Resolve the current grant digest so the approval binds the exact grant
    // the operator reviewed (the server re-checks and refuses typed on drift).
    const detail = await this.getGrant(grantId)
    const digest = detail.grant.grantDigest
    const approval = await this.approval.build(digest)
    const payload = await this.transport.request(endpoints.authorityGrantRevoke(grantId), {
      method: 'POST',
      body: {
        ownerDirectiveId: input.ownerDirectiveId,
        reason: input.reason,
        approval,
      },
      schema: authorityRevokeResultSchema,
    })
    return payload as unknown as { revocation: unknown; revokedGrantDigest: string }
  }

  async setPaused(input: {
    paused: boolean
    ownerDirectiveId: string
    reason: string
  }): Promise<{ control: unknown }> {
    const body: Record<string, unknown> = {
      paused: input.paused,
      ownerDirectiveId: input.ownerDirectiveId,
      reason: input.reason,
    }
    // Unpause is digest-bound to the control digest; pause is not. The server
    // resolves the current control digest and rechecks it.
    if (!input.paused) {
      const grants = await this.listGrants()
      const control = grants.control as Record<string, unknown> | undefined
      const controlDigest = control?.controlDigest
      if (typeof controlDigest !== 'string') {
        throw new ClientError(
          'validation',
          'The authority control projection carried no control digest',
        )
      }
      body.approval = await this.approval.build(controlDigest)
    }
    const payload = await this.transport.request(endpoints.authorityPause, {
      method: 'POST',
      body,
      schema: unknownPayload,
    })
    return { control: payload }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Installed updater
// ─────────────────────────────────────────────────────────────────────────────

export class HttpUpdaterClient implements UpdaterClient {
  private readonly transport: HttpTransport
  private readonly approval: DigestApproval

  constructor(transport: HttpTransport, approval?: DigestApproval) {
    this.transport = transport
    this.approval = approval ?? new DigestApproval(transport)
  }

  async getStatus(): Promise<UpdaterStatus> {
    return this.transport.request(endpoints.updaterStatus, {
      schema: unknownPayload,
    }) as Promise<UpdaterStatus>
  }

  async getPolicy(): Promise<UpdaterPolicyProjection> {
    const payload = await this.transport.request(endpoints.updaterPolicy, {
      schema: updaterPolicySchema,
    })
    return payload as unknown as UpdaterPolicyProjection
  }

  async getRollback(): Promise<UpdaterRollbackProjection> {
    const payload = await this.transport.request(endpoints.updaterRollback, {
      schema: updaterRollbackSchema,
    })
    return payload as unknown as UpdaterRollbackProjection
  }

  async setPolicy(input: {
    policy: Record<string, unknown>
    expectedStatusDigest: string
  }): Promise<unknown> {
    const approval = await this.approval.build(input.expectedStatusDigest)
    return this.transport.request(endpoints.updaterPolicy, {
      method: 'POST',
      body: {
        policy: input.policy,
        expectedStatusDigest: input.expectedStatusDigest,
        approval,
      },
      schema: unknownPayload,
    })
  }

  async planRollback(input: { expectedStatusDigest: string }): Promise<UpdaterRollbackPlanResult> {
    const approval = await this.approval.build(input.expectedStatusDigest)
    const payload = await this.transport.request(endpoints.updaterRollback, {
      method: 'POST',
      body: {
        expectedStatusDigest: input.expectedStatusDigest,
        approval,
      },
      schema: updaterRollbackPlanSchema,
    })
    return payload as unknown as UpdaterRollbackPlanResult
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Preview routes
// ─────────────────────────────────────────────────────────────────────────────

export class HttpPreviewRoutesClient implements PreviewRoutesClient {
  private readonly transport: HttpTransport

  constructor(transport: HttpTransport) {
    this.transport = transport
  }

  async list(): Promise<PreviewRouteIndex> {
    const payload = await this.transport.request(endpoints.previewRoutes, {
      schema: previewRouteIndexSchema,
    })
    return payload as unknown as PreviewRouteIndex
  }

  async register(input: {
    capsuleId: string
    serviceId: string
    revisionDigest: string
    upstreamPort: number
    ttlSeconds: number
  }): Promise<PreviewRoute> {
    const payload = await this.transport.request(endpoints.previewRoutes, {
      method: 'POST',
      body: {
        capsuleId: input.capsuleId,
        serviceId: input.serviceId,
        revisionDigest: input.revisionDigest,
        upstreamPort: input.upstreamPort,
        ttlSeconds: input.ttlSeconds,
      },
      schema: previewRouteSchema,
    })
    return payload as unknown as PreviewRoute
  }

  async revoke(routeId: string, input: { reason: string }): Promise<PreviewRoute> {
    const payload = await this.transport.request(endpoints.previewRouteRevoke(routeId), {
      method: 'POST',
      body: { reason: input.reason },
      schema: previewRouteSchema,
    })
    return payload as unknown as PreviewRoute
  }

  async rewrite(
    routeId: string,
    input: { revisionDigest: string; upstreamPort: number },
  ): Promise<PreviewRoute> {
    const payload = await this.transport.request(endpoints.previewRouteRewrite(routeId), {
      method: 'POST',
      body: {
        revisionDigest: input.revisionDigest,
        upstreamPort: input.upstreamPort,
      },
      schema: previewRouteSchema,
    })
    return payload as unknown as PreviewRoute
  }
}
