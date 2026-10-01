import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import { recommend } from '../api.js'
import CareerCard from '../components/CareerCard.jsx'
import SkillPicker from '../components/SkillPicker.jsx'
import { Badge, ErrorMessage, Page, Spinner } from '../components/ui.jsx'
import { splitList, useAsync, useSkills } from '../hooks.js'

const CONFIDENCE_STYLE = {
  high: 'bg-green-50 text-green-700 ring-green-200',
  medium: 'bg-amber-50 text-amber-700 ring-amber-200',
  low: 'bg-slate-100 text-slate-600 ring-slate-200',
}

export default function Results() {
  const [params, setParams] = useSearchParams()
  const query = params.get('q') || ''
  // ?known=... means the user edited the skill chips: those replace what the NLP detected.
  const knownParam = params.get('known')
  const skills = useSkills()

  const key = `${query}|${knownParam}`
  const { data, error, loading } = useAsync(
    () => (query ? recommend(query, knownParam === null ? undefined : splitList(knownParam)) : Promise.resolve(null)),
    key,
  )

  if (!query) return <Navigate to="/" replace />

  return (
    <Page>
      {/* key: start the box with the new text whenever the question in the URL changes */}
      <AskAgain key={query} initial={query} />
      {loading && <Spinner label="Finding careers that fit you…" />}
      <ErrorMessage error={error} />
      {data && (
        <ResultsView
          key={key}
          data={data}
          skills={skills}
          onUpdateSkills={(chips) => setParams({ q: query, known: chips.join(',') })}
        />
      )}
    </Page>
  )
}

function AskAgain({ initial }) {
  const [text, setText] = useState(initial)
  const navigate = useNavigate()
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (text.trim()) navigate(`/results?${new URLSearchParams({ q: text.trim() })}`)
      }}
      className="mb-6 flex flex-col gap-2 sm:flex-row"
    >
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={1000}
        aria-label="Your question"
        className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
      />
      <button className="rounded-xl bg-brand-600 px-5 py-2.5 font-semibold text-white hover:bg-brand-700">Ask again</button>
    </form>
  )
}

function ResultsView({ data, skills, onUpdateSkills }) {
  const detected = data.parsed.known_skills
  const [chips, setChips] = useState(detected)
  const chipsChanged = chips.join(',') !== detected.join(',')
  const names = (ids) => ids.map((id) => skills.byId[id]?.name || id)

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <aside className="h-fit space-y-5 rounded-2xl border border-slate-200 bg-white p-5 lg:sticky lg:top-20">
        <div>
          <h2 className="font-semibold text-slate-900">What I understood</h2>
          <p className="mt-1 text-xs text-slate-500">Wrong or missing skills? Fix them and update.</p>
        </div>

        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Skills you know</h3>
          <SkillPicker value={chips} onChange={setChips} skills={skills} />
          {chipsChanged && (
            <button
              onClick={() => onUpdateSkills(chips)}
              className="mt-3 w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Update results
            </button>
          )}
        </div>

        <TagGroup title="Want to learn" items={names(data.parsed.goal_skills)} />
        <TagGroup title="Interests" items={data.parsed.interests} />
        <TagGroup title="Don't know yet" items={names(data.parsed.negated_skills)} />
      </aside>

      <section className="space-y-4">
        {data.status === 'need_more_info' ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
            <h2 className="font-semibold text-amber-900">Tell me a bit more</h2>
            <p className="mt-1 text-sm text-amber-800">{data.message}</p>
            <p className="mt-3 text-sm text-amber-800">
              For example: <em>"I know Excel and love numbers"</em> or <em>"I want to build mobile apps"</em>.
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900">Your top careers</h1>
              <Badge className={CONFIDENCE_STYLE[data.confidence]}>{data.confidence} confidence</Badge>
            </div>
            {data.recommendations.map((rec, i) => (
              <CareerCard key={rec.career_id} rec={rec} rank={i + 1} knownSkills={detected} />
            ))}
            {data.recommendations.length === 1 && (
              <p className="text-sm text-slate-500">
                Only one career is a strong match. Every other career scored under 5%.{' '}
                <Link to="/careers" className="text-brand-600 hover:underline">
                  Browse all careers
                </Link>
              </p>
            )}
          </>
        )}
      </section>
    </div>
  )
}

function TagGroup({ title, items }) {
  if (!items.length) return null
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</h3>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <Badge key={item}>{item}</Badge>
        ))}
      </div>
    </div>
  )
}
