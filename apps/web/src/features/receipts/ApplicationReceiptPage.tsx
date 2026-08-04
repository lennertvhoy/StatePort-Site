/**
 * ApplicationReceiptPage — capability-independent exact receipt deep link.
 *
 * Some application-native packages produce receipts without declaring the
 * optional development Workbench. This route keeps the audit evidence
 * application-scoped without granting those packages development tools.
 */
import { Receipt } from 'lucide-react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { EmptyState } from '@/components'

import { ReceiptDetail } from './ReceiptDetail'

export default function ApplicationReceiptPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { instanceId = '', receiptId = '' } = useParams<{
    instanceId: string
    receiptId: string
  }>()
  const expectedDigest = searchParams.get('digest')

  if (
    !instanceId ||
    !receiptId ||
    (expectedDigest !== null &&
      !/^(?:sha256:)?[0-9a-f]{64}$/.test(expectedDigest))
  ) {
    return (
      <div className="flex h-full items-center justify-center bg-app p-6">
        <EmptyState
          icon={Receipt}
          title="Receipt identity is invalid"
          description="Open the receipt again from the operation that created it so its exact identity can be verified."
        />
      </div>
    )
  }

  return (
    <div
      className="flex h-full items-center justify-center bg-app p-6"
      data-testid="application-receipt-page"
    >
      <EmptyState
        icon={Receipt}
        title="Application receipt"
        description="The exact operational record is open in the receipt drawer."
      />
      <ReceiptDetail
        instanceId={instanceId}
        receiptId={receiptId}
        expectedPayloadDigest={expectedDigest ?? undefined}
        onClose={() => navigate(`/app/${instanceId}`)}
      />
    </div>
  )
}
