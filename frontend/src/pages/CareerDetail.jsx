import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { getCareer } from '../api.js'
import SkillPicker from '../components/SkillPicker.jsx'
import { Badge, ErrorMessage, Page, Spinner, StageBadge } from '../components/ui.jsx'
import { DEMAND_STYLE, formatSalary, STAGES } from '../constants.js'
import { useAsync, useSkills } from '../hooks.js'

export default function CareerDetail() {
  const { careerId } = useParams()
  const navigate = useNavigate()
  const { data: career, error, loading } = useAsync(() => getCareer(careerId), careerId)
  const skills = useSkills()
  const [known, setKnown] = useState([])

  const buildRoadmap = () => navigate(`/roadmap/${careerId}?${new URLSearchParams({ known: known.join(',') })}`)

  return (
    <Page>
      <Link to="/careers" className="text-sm font-medium text-brand-600 hover:underline">
        ← All careers
      </Link>
      {loading && <Spinner />}
      <ErrorMessage error={error} />

      {career && (
        <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_340px]">
          <div>
            <span className="text-sm font-medium text-slate-400">{career.category}</span>
            <h1 className="text-3xl font-extrabold text-slate-900">{career.name}</h1>
            <p className="mt-2 text-lg text-slate-600">{career.description}</p>

            <div className="mt-4 flex flex-wrap gap-2">
              <Badge className={DEMAND_STYLE[career.demand]}>{career.demand} demand</Badge>
              <Badge>{formatSalary(career.salary_inr_lpa)}</Badge>
              <Badge>
                {career.skill_count} skills · ~{career.total_hours} hrs
              </Badge>
              {career.interests.map((i) => (
                <Badge key={i} className="bg-brand-50 text-brand-700 ring-brand-200">
                  {i}
                </Badge>
              ))}
            </div>

            <div className="mt-8 space-y-6">
              {STAGES.map((stage) => (
                <section key={stage}>
                  <StageBadge stage={stage} />
                  <ol className="mt-2 grid gap-2 sm:grid-cols-2">
                    {career.stages[stage].map((s) => (
                      <li key={s.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3">
                        <span className="font-medium text-slate-800">{s.name}</span>
                        <span className="text-sm text-slate-500">~{s.est_hours}h</span>
                      </li>
                    ))}
                  </ol>
                </section>
              ))}
              {career.optional_skills.length > 0 && (
                <section>
                  <h2 className="text-sm font-semibold text-slate-900">Nice to have</h2>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {career.optional_skills.map((o) => (
                      <Badge key={o.skill_id}>{o.name}</Badge>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </div>

          <aside className="h-fit rounded-2xl border border-brand-200 bg-white p-5 shadow-sm lg:sticky lg:top-20">
            <h2 className="font-semibold text-slate-900">Build your roadmap</h2>
            <p className="mt-1 text-sm text-slate-600">Add skills you already have and we'll skip them.</p>
            <div className="mt-4">
              <SkillPicker value={known} onChange={setKnown} skills={skills} />
            </div>
            <button onClick={buildRoadmap} className="mt-4 w-full rounded-xl bg-brand-600 px-4 py-2.5 font-semibold text-white hover:bg-brand-700">
              Show my roadmap →
            </button>
          </aside>
        </div>
      )}
    </Page>
  )
}
