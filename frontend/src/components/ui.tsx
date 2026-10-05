// The small vocabulary every page is built from. One surface, one hairline,
// one accent; hierarchy comes from type and spacing, not boxes.
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export function Card({
  className = '',
  interactive = false,
  children,
}: {
  className?: string
  interactive?: boolean
  children: ReactNode
}) {
  return (
    <div
      className={`rounded-2xl border border-line bg-surface shadow-[0_1px_2px_rgba(28,25,23,0.04)] ${
        interactive
          ? 'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-12px_rgba(28,25,23,0.18)] motion-reduce:transition-none motion-reduce:hover:translate-y-0'
          : ''
      } ${className}`}
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
      className={`text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-faint ${className}`}
    >
      {children}
    </span>
  )
}

export function PageTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
      <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
      {children}
    </div>
  )
}

type Variant = 'primary' | 'secondary' | 'accept' | 'reject' | 'modify' | 'ghost'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-ink text-paper hover:bg-stone-700 shadow-sm',
  secondary: 'border border-line-strong bg-surface text-ink hover:bg-stone-100',
  accept: 'bg-[#e3f1e5] text-[#1b5e2f] hover:bg-[#c8e5cd]',
  reject: 'bg-[#fbe7e5] text-[#9a2c21] hover:bg-[#f4cfcb]',
  modify: 'bg-accent-soft text-accent hover:bg-[#ddd8f7]',
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
      className={`rounded-full font-medium transition-all duration-150 active:scale-[0.97] disabled:cursor-default disabled:opacity-40 disabled:active:scale-100 motion-reduce:transition-none motion-reduce:active:scale-100 ${padding} ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  )
}

export const inputClass =
  'rounded-xl border border-line-strong bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none'

// Segmented control (iOS-style) shared by tabs, modes, and time windows.
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: {
  options: { id: T; label: string }[]
  value: T
  onChange: (next: T) => void
  ariaLabel?: string
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="inline-flex max-w-full gap-0.5 overflow-x-auto rounded-full border border-line bg-stone-200/50 p-1"
    >
      {options.map((option) => (
        <button
          key={option.id}
          role="tab"
          aria-selected={value === option.id}
          className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium transition-all duration-150 ${
            value === option.id
              ? 'bg-surface text-ink shadow-[0_1px_4px_rgba(28,25,23,0.12)]'
              : 'text-ink-soft hover:text-ink'
          }`}
          onClick={() => onChange(option.id)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

// Soft iridescent backdrop blobs (the "Taiga glow", in daylight).
export function GlowBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute -top-32 left-1/2 h-96 w-[42rem] -translate-x-[70%] rounded-full bg-[#c9c2f2] opacity-50 blur-3xl" />
      <div className="absolute -top-24 left-1/2 h-80 w-[36rem] -translate-x-[15%] rounded-full bg-[#f7d8bb] opacity-50 blur-3xl" />
      <div className="absolute top-40 left-1/2 h-64 w-[30rem] -translate-x-1/2 rounded-full bg-[#f3c9d8] opacity-30 blur-3xl" />
    </div>
  )
}

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
      className="fixed inset-0 z-50 flex items-start justify-center bg-ink/25 p-4 pt-[12vh] backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-label={label}
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div
        className={`anim-pop w-full ${
          wide ? 'max-w-2xl' : 'max-w-md'
        } rounded-2xl border border-line bg-surface p-5 shadow-[0_24px_60px_-12px_rgba(28,25,23,0.25)]`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}
