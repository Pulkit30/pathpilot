import { useState } from 'react'
import { Link } from 'react-router'
import { deleteSavedRoadmap, listSavedRoadmaps } from '../api.js'
import { useAuth } from '../auth.jsx'
import { ErrorMessage, Page, Spinner } from '../components/ui.jsx'
import { useAsync } from '../hooks.js'

export default function MyRoadmaps() {
  const { user } = useAuth()
  const [reload, setReload] = useState(0)
  const { data, error, loading } = useAsync(listSavedRoadmaps, `${user.id}|${reload}`)
  const [removeError, setRemoveError] = useState(null)

  const remove = async (r) => {
    if (!window.confirm(`Remove your ${r.career_name} roadmap? Your progress on it will be lost.`)) return
    setRemoveError(null)
    try {
      await deleteSavedRoadmap(r.career_id)
      setReload((n) => n + 1)
    } catch (err) {
      setRemoveError(err)
    }
  }

  return (
    <Page>
      <h1 className="text-3xl font-extrabold text-slate-900">My roadmaps</h1>
      <p className="mt-1 text-slate-600">Pick up where you left off.</p>

      {loading && <Spinner />}
      <div className="mt-4 space-y-2">
        <ErrorMessage error={error} />
        <ErrorMessage error={removeError} />
      </div>

      {data?.length === 0 && (
        <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="text-slate-600">You haven't saved any roadmaps yet.</p>
          <Link to="/" className="mt-4 inline-block rounded-xl bg-brand-600 px-5 py-2.5 font-semibold text-white hover:bg-brand-700">
            Find your path →
          </Link>
        </div>
      )}

      {data?.length > 0 && (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {data.map((r) => {
            const pct = Math.round(r.progress * 100)
            const url = `/roadmap/${r.career_id}?${new URLSearchParams({ known: r.known_skills.join(','), hours: r.hours_per_week })}`
            const finished = r.steps_done === r.steps_total
            return (
              <article key={r.career_id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">{r.career_name}</h2>
                    <p className="text-sm text-slate-500">
                      {r.steps_done} of {r.steps_total} steps done
                      {!finished && ` · ~${r.hours_left} hrs left (~${r.weeks_left} weeks at ${r.hours_per_week} hrs/week)`}
                    </p>
                  </div>
                  <span className={`text-2xl font-extrabold ${finished ? 'text-green-600' : 'text-brand-600'}`}>{pct}%</span>
                </div>
                <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-green-500" style={{ width: `${pct}%` }} />
                </div>
                {finished && <p className="mt-2 text-sm font-medium text-green-700">🎉 Roadmap complete!</p>}
                <div className="mt-4 flex items-center gap-2">
                  <Link to={url} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
                    {r.steps_done ? 'Continue →' : 'Start →'}
                  </Link>
                  <button onClick={() => remove(r)} className="ml-auto rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-red-50 hover:text-red-600">
                    Remove
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </Page>
  )
}
