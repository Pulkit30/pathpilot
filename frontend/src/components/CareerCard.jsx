import { useState } from 'react'
import { Link } from 'react-router'
import { sendFeedback } from '../api.js'
import { DEMAND_STYLE, formatSalary } from '../constants.js'
import { Badge } from './ui.jsx'

export default function CareerCard({ rec, rank, knownSkills, query }) {
  const top = rank === 1
  const roadmapUrl = `/roadmap/${rec.career_id}?${new URLSearchParams({ known: knownSkills.join(',') })}`

  return (
    <article className={`rounded-2xl border bg-white p-5 shadow-sm sm:p-6 ${top ? 'border-brand-300 ring-2 ring-brand-100' : 'border-slate-200'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{top ? 'Best match' : `#${rank}`}</p>
          <h2 className="text-xl font-bold text-slate-900">{rec.name}</h2>
          <p className="mt-1 text-sm text-slate-600">{rec.description}</p>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-extrabold ${top ? 'text-brand-600' : 'text-slate-700'}`}>{Math.round(rec.match)}%</div>
          <div className="text-xs text-slate-500">match</div>
        </div>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${top ? 'bg-brand-600' : 'bg-slate-400'}`} style={{ width: `${Math.max(rec.match, 2)}%` }} />
      </div>

      <ul className="mt-4 space-y-1.5">
        {rec.reasons.map((r) => (
          <li key={r} className="flex gap-2 text-sm text-slate-700">
            <span className="text-brand-500">✓</span>
            {r}
          </li>
        ))}
      </ul>

      <Feedback query={query} careerId={rec.career_id} rank={rank} />

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Badge>
          You know {rec.skills_known} of {rec.skills_total} skills
        </Badge>
        <Badge className={DEMAND_STYLE[rec.demand]}>{rec.demand} demand</Badge>
        <Badge>{formatSalary(rec.salary_inr_lpa)}</Badge>
        <Link
          to={roadmapUrl}
          className={`ml-auto rounded-xl px-4 py-2 text-sm font-semibold transition ${
            top ? 'bg-brand-600 text-white hover:bg-brand-700' : 'border border-slate-300 text-slate-700 hover:bg-slate-50'
          }`}
        >
          View roadmap →
        </Link>
      </div>
    </article>
  )
}

/** "Is this a good match?" 👍/👎. The answers are used to retrain the model (ml/retrain.py). */
function Feedback({ query, careerId, rank }) {
  const [rating, setRating] = useState(null)
  const [failed, setFailed] = useState(false)

  const send = async (value) => {
    setRating(value)
    setFailed(false)
    try {
      await sendFeedback(query, careerId, value, rank)
    } catch {
      setRating(null)
      setFailed(true)
    }
  }

  if (rating) {
    return <p className="mt-4 text-sm text-slate-500">{rating === 1 ? '👍' : '👎'} Thanks! Your feedback helps PathPilot improve.</p>
  }
  return (
    <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
      <span>Good match for you?</span>
      {[
        [1, '👍', 'Yes, good match'],
        [-1, '👎', 'No, not a good match'],
      ].map(([value, icon, label]) => (
        <button
          key={value}
          onClick={() => send(value)}
          aria-label={label}
          title={label}
          className="rounded-lg border border-slate-200 px-2.5 py-1 transition hover:border-brand-300 hover:bg-brand-50"
        >
          {icon}
        </button>
      ))}
      {failed && <span className="text-red-600">Couldn't send. Try again?</span>}
    </div>
  )
}
