import { useEffect } from 'react'
import { Badge, StageBadge } from './ui.jsx'

const TYPE_ICON = { docs: '📄', course: '🎓', tutorial: '🛠️', book: '📘', practice: '🏋️', article: '📰', video: '🎬' }

/** Slide-over panel with everything about one roadmap step. */
export default function SkillDrawer({ step, skillNames, onClose, done, onToggleDone }) {
  useEffect(() => {
    if (!step) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [step, onClose])

  if (!step) return null

  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label={step.name}>
      <button className="absolute inset-0 bg-slate-900/30" onClick={onClose} aria-label="Close" />
      <aside className="relative flex h-full w-full max-w-md flex-col overflow-y-auto bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Step {step.step}</p>
            <h2 className="text-2xl font-bold text-slate-900">{step.name}</h2>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-xl leading-none text-slate-500 hover:bg-slate-100" aria-label="Close">
            ×
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <StageBadge stage={step.stage} />
          <Badge>~{step.est_hours} hours</Badge>
          <Badge>
            Difficulty {'●'.repeat(step.difficulty)}
            <span className="text-slate-300">{'●'.repeat(5 - step.difficulty)}</span>
          </Badge>
        </div>

        <p className="mt-5 text-slate-700">{step.description}</p>

        {onToggleDone && (
          <button
            onClick={() => onToggleDone(step.skill_id, !done)}
            className={`mt-5 w-full rounded-xl px-4 py-2.5 font-semibold transition ${
              done ? 'border border-green-300 bg-green-50 text-green-700 hover:bg-green-100' : 'bg-brand-600 text-white hover:bg-brand-700'
            }`}
          >
            {done ? '✓ Done (click to undo)' : 'Mark as done'}
          </button>
        )}

        {step.prereqs.length > 0 && (
          <div className="mt-5">
            <h3 className="mb-2 text-sm font-semibold text-slate-900">Learn first</h3>
            <div className="flex flex-wrap gap-1.5">
              {step.prereqs.map((p) => (
                <Badge key={p}>{skillNames[p]?.name || p}</Badge>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6">
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Free resources</h3>
          <ul className="space-y-2">
            {step.resources.map((r) => (
              <li key={r.url}>
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-3 rounded-xl border border-slate-200 p-3 transition hover:border-brand-300 hover:bg-brand-50"
                >
                  <span className="text-lg">{TYPE_ICON[r.type] || '🔗'}</span>
                  <span>
                    <span className="block text-sm font-medium text-slate-800">{r.title}</span>
                    <span className="text-xs capitalize text-slate-500">{r.type}</span>
                  </span>
                  <span className="ml-auto text-slate-400">↗</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  )
}
