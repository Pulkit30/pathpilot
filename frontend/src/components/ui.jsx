// Small shared building blocks.
import { STAGE_STYLE } from '../constants.js'

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      {label}
    </div>
  )
}

export function ErrorMessage({ error, children }) {
  if (!error) return null
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700" role="alert">
      {error.message || String(error)}
      {children}
    </div>
  )
}

export function Badge({ children, className = 'bg-slate-100 text-slate-700 ring-slate-200' }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${className}`}>
      {children}
    </span>
  )
}

export function StageBadge({ stage }) {
  const s = STAGE_STYLE[stage]
  return <Badge className={s.chip}>{s.label}</Badge>
}

export function Page({ children, className = '' }) {
  return <main className={`mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 ${className}`}>{children}</main>
}
