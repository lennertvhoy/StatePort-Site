/**
 * Overview data hook — the domain reads the App overview needs beyond the
 * instance itself (which AppContextShell owns): activity, pending approvals,
 * operations, recent receipts, the infrastructure target (capability-gated),
 * and the package version. All through the typed client boundary, in
 * parallel; individual read failures degrade to empty rather than breaking
 * the page (the instance header still renders).
 */
import { useCallback, useEffect, useState } from 'react'

import type {
  ActivityItem,
  ApplicationInstance,
  Approval,
  InfrastructureTarget,
  OperationRecord,
  Receipt,
} from '@/client'
import { getClient } from '@/client'
import { useSessionStore } from '@/state'

export interface OverviewData {
  activity: ActivityItem[]
  pendingApprovals: Approval[]
  operations: OperationRecord[]
  receipts: Receipt[]
  infraTarget: InfrastructureTarget | null
  packageVersion: string | null
  loading: boolean
  refresh: () => void
}

const EMPTY = {
  activity: [] as ActivityItem[],
  pendingApprovals: [] as Approval[],
  operations: [] as OperationRecord[],
  receipts: [] as Receipt[],
  infraTarget: null as InfrastructureTarget | null,
  packageVersion: null as string | null,
}

export function useOverviewData(instance: ApplicationInstance | null): OverviewData {
  const activeScenario = useSessionStore((s) => s.activeScenario)
  // Keyed fetch result: data/loading derive from whether the in-flight key
  // has landed, so the effect never sets state synchronously.
  const [result, setResult] = useState<{ key: string; data: Omit<OverviewData, 'loading' | 'refresh'> } | null>(
    null,
  )
  const [nonce, setNonce] = useState(0)
  const requestKey = `${instance?.id ?? ''}#${activeScenario ?? ''}#${nonce}`

  useEffect(() => {
    if (!instance) return
    let cancelled = false
    const client = getClient()
    const hasInfrastructure = instance.capabilities.some(
      (c) => c.id === 'infrastructure' && (c.status === 'available' || c.status === 'degraded'),
    )
    const hasGoalExecution = instance.capabilities.some(
      (c) => c.id === 'cto_orchestration' && (c.status === 'available' || c.status === 'degraded'),
    )

    const safe = <T,>(p: Promise<T>, fallback: T): Promise<T> => p.catch(() => fallback)

    void Promise.all([
      safe(client.activity.listActivity({ instanceId: instance.id, limit: 20 }), [] as ActivityItem[]),
      safe(client.approvals.list({ instanceId: instance.id, status: 'pending' }), [] as Approval[]),
      safe(client.operations.list(), [] as OperationRecord[]),
      safe(client.receipts.list({ instanceId: instance.id, limit: 8, goalExecution: hasGoalExecution }), [] as Receipt[]),
      hasInfrastructure ? safe(client.infrastructure.getTarget(instance.id), null) : Promise.resolve(null),
      safe(client.catalog.get(instance.packageId).then((c) => c.pkg.version), null),
    ]).then(([activity, pendingApprovals, operations, receipts, infraTarget, packageVersion]) => {
      if (cancelled) return
      setResult({
        key: requestKey,
        data: {
          activity,
          pendingApprovals,
          operations: operations.filter((o) => o.instanceId === instance.id),
          receipts,
          infraTarget,
          packageVersion,
        },
      })
    })

    return () => {
      cancelled = true
    }
  }, [instance, activeScenario, nonce, requestKey])

  const refresh = useCallback(() => setNonce((n) => n + 1), [])
  const landed = result && result.key === requestKey ? result.data : null
  return { ...(landed ?? EMPTY), loading: !landed, refresh }
}
