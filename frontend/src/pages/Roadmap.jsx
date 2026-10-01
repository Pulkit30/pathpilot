import { lazy, Suspense, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { getRoadmap } from '../api.js'
import SkillDrawer from '../components/SkillDrawer.jsx'
import { Badge, ErrorMessage, Page, Spinner, StageBadge } from '../components/ui.jsx'
import { STAGE_STYLE, STAGES } from '../constants.js'
import { splitList, useAsync, useSkills } from '../hooks.js'

// React Flow is the biggest library we use, so only load it when the graph view is opened.
const RoadmapGraph = lazy(() => import('../components/RoadmapGraph.jsx'))

const HOUR_OPTIONS = [5, 10, 15, 20, 30]

export default function Roadmap() {
  const { careerId } = useParams()
  const [params, setParams] = useSearchParams()
  const known = splitList(params.get('known'))
  const hours = Number(params.get('hours')) || 10
  const [view, setView] = useState(() => (window.innerWidth < 768 ? 'list' : 'graph'))
  const [selected, setSelected] = useState(null)
  const skills = useSkills()

  const { data, error, loading } = useAsync(() => getRoadmap(careerId, known, hours), `${careerId}|${known.join(',')}|${hours}`)

  const setHours = (h) => {
    const next = new URLSearchParams(params)
    next.set('hours', h)
    setParams(next, { replace: true })
  }

  return (
    <Page>
      {loading && <Spinner label="Building your roadmap…" />}
      <ErrorMessage error={error}>
        {' '}
        <Link to="/careers" className="font-medium underline">
          Browse careers
        </Link>
      </ErrorMessage>

      {data && (
        <>
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-brand-600">Your roadmap</p>
              <h1 className="text-3xl font-extrabold text-slate-900">{data.career_name}</h1>
            </div>
            <Link to={`/careers/${careerId}`} className="text-sm font-medium text-brand-600 hover:underline">
              About this career →
            </Link>
          </header>

          <section className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Skills to learn" value={data.steps.length} />
            <Stat label="Total time" value={`~${data.total_hours} hrs`} />
            <Stat label="At your pace" value={data.est_weeks ? `~${data.est_weeks} weeks` : '—'} />
            <Stat label="Already done" value={`${Math.round(data.progress * 100)}%`} />
          </section>

          <section className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4">
            <label htmlFor="hours" className="text-sm font-medium text-slate-700">
              Study time per week
            </label>
            <select
              id="hours"
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm"
            >
              {HOUR_OPTIONS.map((h) => (
                <option key={h} value={h}>
                  {h} hours
                </option>
              ))}
            </select>
            {data.already_known.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 sm:ml-4">
                <span className="text-sm text-slate-500">Skipping:</span>
                {data.already_known.map((k) => (
                  <Badge key={k.skill_id} className="bg-green-50 text-green-700 ring-green-200">
                    ✓ {k.name}
                    {k.implied && <span className="text-green-500">(implied)</span>}
                  </Badge>
                ))}
              </div>
            )}
          </section>

          <div className="mt-6 flex items-center justify-between gap-3">
            <div className="flex gap-3 text-xs text-slate-500">
              {STAGES.map((s) => (
                <span key={s} className="flex items-center gap-1.5">
                  <span className={`h-2.5 w-2.5 rounded-full ${STAGE_STYLE[s].dot}`} />
                  {STAGE_STYLE[s].label}
                </span>
              ))}
            </div>
            <div className="flex rounded-lg border border-slate-200 bg-white p-0.5 text-sm">
              {['graph', 'list'].map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`rounded-md px-3 py-1 capitalize ${view === v ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-3">
            {data.steps.length === 0 ? (
              <div className="rounded-2xl border border-green-200 bg-green-50 p-6 text-green-800">
                🎉 You already know every required skill for this career!
              </div>
            ) : view === 'graph' ? (
              <Suspense fallback={<Spinner label="Drawing the graph…" />}>
                <p className="mb-2 text-xs text-slate-500">Arrows point from a skill to what it unlocks. Click any skill for details and resources.</p>
                <RoadmapGraph steps={data.steps} selectedId={selected?.skill_id} onSelect={setSelected} />
              </Suspense>
            ) : (
              <RoadmapList steps={data.steps} onSelect={setSelected} />
            )}
          </div>

          {data.optional_skills.length > 0 && (
            <section className="mt-6">
              <h2 className="mb-2 text-sm font-semibold text-slate-900">Nice to have later</h2>
              <div className="flex flex-wrap gap-1.5">
                {data.optional_skills.map((o) => (
                  <Badge key={o.skill_id}>{o.name}</Badge>
                ))}
              </div>
            </section>
          )}

          <SkillDrawer step={selected} skillNames={skills.byId} onClose={() => setSelected(null)} />
        </>
      )}
    </Page>
  )
}

function Stat({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-bold text-slate-900">{value}</div>
    </div>
  )
}

function RoadmapList({ steps, onSelect }) {
  return (
    <div className="space-y-6">
      {STAGES.map((stage) => {
        const stageSteps = steps.filter((s) => s.stage === stage)
        if (!stageSteps.length) return null
        return (
          <section key={stage}>
            <div className="mb-2 flex items-center gap-2">
              <StageBadge stage={stage} />
              <span className="text-xs text-slate-500">
                {stageSteps.length} skills · ~{stageSteps.reduce((t, s) => t + s.est_hours, 0)} hrs
              </span>
            </div>
            <ol className="space-y-2">
              {stageSteps.map((s) => (
                <li key={s.skill_id}>
                  <button
                    onClick={() => onSelect(s)}
                    className="flex w-full items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:border-brand-300 hover:shadow-sm"
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-600">
                      {s.step}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold text-slate-900">{s.name}</span>
                      <span className="block truncate text-sm text-slate-500">{s.description}</span>
                    </span>
                    <span className="shrink-0 text-sm text-slate-500">~{s.est_hours}h</span>
                  </button>
                </li>
              ))}
            </ol>
          </section>
        )
      })}
    </div>
  )
}
