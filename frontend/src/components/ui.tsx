// The small vocabulary every page is built from. One surface, one hairline,
// one accent; hierarchy comes from type and spacing, not boxes.
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={`rounded-2xl border border-line bg-surface shadow-[0_1px_2px_rgba(28,25,23,0.04)] ${className}`}
    >
      {children}
    </div>
  )
}

// The tracked, uppercase micro-label used for table headers and field names.
export function MicroLabel({
  className = '',
  children,
}: {
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={`text-[11px] font-medium uppercase tracking-[0.08em] text-ink-faint ${className}`}
    >
      {children}
    </span>
  )
}

export function PageTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <h1 className="font-display text-[1.9rem] font-semibold tracking-tight">{title}</h1>
      {children}
    </div>
  )
}

type Variant = 'primary' | 'secondary' | 'accept' | 'reject' | 'modify' | 'ghost'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-ink text-paper hover:bg-stone-700 shadow-sm',
  secondary: 'border border-line-strong bg-surface text-ink hover:bg-stone-100',
  accept: 'bg-[#e3f1e5] text-[#1b5e2f] hover:bg-[#d2e9d6]',
  reject: 'bg-[#fbe7e5] text-[#9a2c21] hover:bg-[#f6d7d4]',
  modify: 'bg-accent-soft text-accent hover:bg-[#e0dcf8]',
  ghost: 'text-ink-soft hover:text-ink hover:bg-stone-100',
}

export function Button({
  variant = 'secondary',
  size = 'md',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'sm' | 'md' }) {
  const padding = size === 'sm' ? 'px-3 py-1 text-[13px]' : 'px-4 py-1.5 text-sm'
  return (
    <button
      className={`rounded-full font-medium transition-colors disabled:cursor-default disabled:opacity-40 ${padding} ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  )
}

export const inputClass =
  'rounded-xl border border-line-strong bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none'

export function Dialog({
  label,
  onClose,
  children,
  wide = false,
}: {
  label: string
  onClose: () => void
  children: ReactNode
  wide?: boolean
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-ink/25 p-6 pt-[12vh] backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-label={label}
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div
        className={`w-full ${
          wide ? 'max-w-2xl' : 'max-w-md'
        } rounded-2xl border border-line bg-surface p-5 shadow-[0_24px_60px_-12px_rgba(28,25,23,0.25)]`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}
