/** StatePort's public-safe source mark; no external image asset is required. */
import type { CSSProperties } from 'react'

import { cn } from '@/lib/utils'

export type BrandMarkSize = 16 | 20 | 24 | 32

export function BrandMark({
  size = 20,
  className,
  style,
  title,
}: {
  size?: BrandMarkSize
  className?: string
  style?: CSSProperties
  /** Accessible name; omit when decorative beside a visible wordmark. */
  title?: string
}) {
  return (
    <span
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      className={cn('inline-flex shrink-0 items-center justify-center', className)}
      style={{ width: size, height: size, ...style }}
      data-testid="brand-mark"
    >
      <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" className="block size-full fill-none">
        <path d="M7 4.5h10v5H9.5v5H17v5H7z" className="stroke-[#2F7DFF]" strokeWidth="2.25" strokeLinejoin="round" />
        <path d="m13.5 7 3 2.5-3 2.5" className="stroke-[#2F7DFF]" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  )
}

/** Expanded source-code lockup for the application shell. */
export function BrandLockup({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2 text-foreground', className)} data-testid="brand-lockup">
      <BrandMark size={32} />
      <span className="text-[15px] font-semibold leading-none tracking-[-0.01em]">StatePort</span>
    </span>
  )
}
