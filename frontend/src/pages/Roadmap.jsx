import { lazy, Suspense, useMemo, useState } from 'react'
import { Link, useLocation, useParams, useSearchParams } from 'react-router'
import { getRoadmap, getSavedRoadmap, saveRoadmap, setSkillDone } from '../api.js'
import { useAuth } from '../auth.jsx'
import SkillDrawer from '../components/SkillDrawer.jsx'
import { Badge, ErrorMessage, Page, Spinner, StageBadge } from '../components/ui.jsx'
import { STAGE_STYLE, STAGES } from '../constants.js'
import { splitList, useAsync, useSkills } from '../hooks.js'

// React Flow is the biggest library we use, so only load it when the graph view is opened.
const RoadmapGraph = lazy(() => import('../components/RoadmapGraph.jsx'))

const HOUR_OPTIONS = [5, 10, 15, 20, 30]
const sameSet = (a, b) => a.length === b.length && a.every((x) => b.includes(x))

export default function Roadmap() {
  const { careerId } = useParams()
  const [params, setParams] = useSearchParams()
  const known = splitList(params.get('known'))
  const hours = Number(params.get('hours')) || 10
  const [view, setView] = useState(() => (window.innerWidth < 768 ? 'list' : 'graph'))
  const [selectedId, setSelectedId] = useState(null)
  const skills = useSkills()
  const { user } = useAuth()

  const { data, error, loading } = useAsync(() => getRoadmap(careerId, known, hours), `${careerId}|${known.join(',')}|${hours}`)
  const saved = useSavedRoadmap(careerId, user)

  // Progress is tracked only when this page shows the same plan that was saved (same known skills).
  const tracking = Boolean(saved.value && sameSet(saved.value.known_skills, known))
  const completed = useMemo(() => new Set(tracking ? saved.value.completed_skills : []), [tracking, saved.value])

  const setHours = (h) => {
    const next = new URLSearchParams(params)
    next.set('hours', h)
    setParams(next, { replace: true })
  }

  const selected = data?.steps.find((s) => s.skill_id === selectedId) || null

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
              <Link to={`/careers/${careerId}`} className="text-sm font-medium text-brand-600 hover:underline">
                About this career →
              </Link>
            </div>
            <SaveButton saved={saved} user={user} known={known} hours={hours} />
          </header>

          {saved.error && (
            <div className="mt-4">
              <ErrorMessage error={saved.error} />
            </div>
          )}
          {saved.value && !tracking && (
            <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              This plan uses different known skills from the one you saved. Click <b>Update saved roadmap</b> to track
              progress here, or open it from{' '}
              <Link to="/my-roadmaps" className="font-medium underline">
                My roadmaps
              </Link>
              .
            </p>
          )}

          <Stats data={data} completed={completed} hours={hours} tracking={tracking} />

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
                <p className="mb-2 text-xs text-slate-500">
                  Arrows point from a skill to what it unlocks. Click any skill for details
                  {tracking ? ' and to mark it done.' : ' and resources.'}
                </p>
                <RoadmapGraph steps={data.steps} selectedId={selectedId} onSelect={(s) => setSelectedId(s.skill_id)} completed={completed} />
              </Suspense>
            ) : (
              <RoadmapList
                steps={data.steps}
                onSelect={(s) => setSelectedId(s.skill_id)}
                completed={completed}
                onToggleDone={tracking ? saved.toggle : null}
              />
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

          <SkillDrawer
            step={selected}
            skillNames={skills.byId}
            onClose={() => setSelectedId(null)}
            done={selected ? completed.has(selected.skill_id) : false}
            onToggleDone={tracking ? saved.toggle : null}
          />
        </>
      )}
    </Page>
  )
}

/**
 * The user's saved copy of this roadmap: {value (null = not saved), loading, error, busy, save(), toggle()}.
 * Local edits (save / mark done) replace the fetched value until the page changes.
 */
function useSavedRoadmap(careerId, user) {
  const key = `${careerId}|${user?.id ?? ''}`
  const fetched = useAsync(
    () => (user ? getSavedRoadmap(careerId).catch((e) => (e.status === 404 ? null : Promise.reject(e))) : Promise.resolve(null)),
    key,
  )
  const [local, setLocal] = useState({ key: null, value: null, error: null })
  const [busy, setBusy] = useState(false)
  const isLocal = local.key === key
  const value = isLocal ? local.value : fetched.data

  const run = async (request, optimistic) => {
    if (optimistic) setLocal({ key, value: optimistic, error: null }) // update the screen right away
    setBusy(true)
    try {
      setLocal({ key, value: await request(), error: null })
    } catch (error) {
      setLocal({ key, value, error }) // roll back the optimistic change
    } finally {
      setBusy(false)
    }
  }

  return {
    value,
    loading: fetched.loading,
    error: (isLocal ? local.error : null) || fetched.error,
    busy,
    save: (known, hours) => run(() => saveRoadmap(careerId, known, hours)),
    toggle: (skillId, done) => {
      const completed = done ? [...value.completed_skills, skillId] : value.completed_skills.filter((s) => s !== skillId)
      run(() => setSkillDone(careerId, skillId, done), { ...value, completed_skills: completed })
    },
  }
}

function SaveButton({ saved, user, known, hours }) {
  const location = useLocation()
  if (!user) {
    return (
      <Link
        to="/login"
        state={{ from: location.pathname + location.search }}
        className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
      >
        Log in to save &amp; track progress
      </Link>
    )
  }
  if (saved.loading) return null
  const v = saved.value
  if (v && sameSet(v.known_skills, known) && v.hours_per_week === hours) {
    return (
      <Link to="/my-roadmaps" className="rounded-xl border border-green-300 bg-green-50 px-4 py-2 text-sm font-semibold text-green-700">
        ✓ Saved · My roadmaps
      </Link>
    )
  }
  return (
    <button
      onClick={() => saved.save(known, hours)}
      disabled={saved.busy}
      className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
    >
      {saved.busy ? 'Saving…' : v ? 'Update saved roadmap' : 'Save roadmap'}
    </button>
  )
}

function Stats({ data, completed, hours, tracking }) {
  const doneSteps = data.steps.filter((s) => completed.has(s.skill_id))
  const hoursLeft = data.total_hours - doneSteps.reduce((t, s) => t + s.est_hours, 0)
  const required = data.already_known.length + data.steps.length
  const overall = required ? (data.already_known.length + doneSteps.length) / required : 1

  return (
    <section className="mt-6 space-y-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label={tracking ? 'Steps done' : 'Skills to learn'} value={tracking ? `${doneSteps.length} / ${data.steps.length}` : data.steps.length} />
        <Stat label={tracking ? 'Time left' : 'Total time'} value={`~${hoursLeft} hrs`} />
        <Stat label="At your pace" value={`~${Math.ceil(hoursLeft / hours)} weeks`} />
        <Stat label="Career progress" value={`${Math.round(overall * 100)}%`} />
      </div>
      {tracking && (
        <div
          className="h-3 overflow-hidden rounded-full bg-slate-200"
          role="progressbar"
          aria-valuenow={Math.round(overall * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${overall * 100}%` }} />
        </div>
      )}
    </section>
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

function RoadmapList({ steps, onSelect, completed, onToggleDone }) {
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
              {stageSteps.map((s) => {
                const done = completed.has(s.skill_id)
                return (
                  <li
                    key={s.skill_id}
                    className={`flex items-center gap-3 rounded-xl border p-4 transition ${
                      done ? 'border-green-200 bg-green-50' : 'border-slate-200 bg-white hover:border-brand-300'
                    }`}
                  >
                    {onToggleDone ? (
                      <input
                        type="checkbox"
                        checked={done}
                        onChange={(e) => onToggleDone(s.skill_id, e.target.checked)}
                        aria-label={`Mark ${s.name} as done`}
                        className="h-5 w-5 shrink-0 accent-green-600"
                      />
                    ) : (
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-600">
                        {s.step}
                      </span>
                    )}
                    <button onClick={() => onSelect(s)} className="flex min-w-0 flex-1 items-center gap-4 text-left">
                      <span className="min-w-0 flex-1">
                        <span className={`block font-semibold ${done ? 'text-slate-500 line-through' : 'text-slate-900'}`}>{s.name}</span>
                        <span className="block truncate text-sm text-slate-500">{s.description}</span>
                      </span>
                      <span className="shrink-0 text-sm text-slate-500">~{s.est_hours}h</span>
                    </button>
                  </li>
                )
              })}
            </ol>
          </section>
        )
      })}
    </div>
  )
}
