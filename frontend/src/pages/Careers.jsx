import { useState } from 'react'
import { Link } from 'react-router'
import { listCareers } from '../api.js'
import { Badge, ErrorMessage, Page, Spinner } from '../components/ui.jsx'
import { DEMAND_STYLE, formatSalary } from '../constants.js'
import { useAsync } from '../hooks.js'

export default function Careers() {
  const { data, error, loading } = useAsync(listCareers, 'careers')
  const [category, setCategory] = useState('All')

  const categories = ['All', ...new Set((data || []).map((c) => c.category))]
  const shown = (data || []).filter((c) => category === 'All' || c.category === category)

  return (
    <Page>
      <h1 className="text-3xl font-extrabold text-slate-900">Explore careers</h1>
      <p className="mt-1 text-slate-600">15 tech careers, each with a step-by-step roadmap.</p>

      {loading && <Spinner />}
      <ErrorMessage error={error} />

      {data && (
        <>
          <div className="mt-6 flex flex-wrap gap-2">
            {categories.map((c) => (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                  c === category ? 'bg-brand-600 text-white' : 'border border-slate-200 bg-white text-slate-600 hover:border-brand-300'
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {shown.map((c) => (
              <Link
                key={c.id}
                to={`/careers/${c.id}`}
                className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-brand-300 hover:shadow-md"
              >
                <span className="text-xs font-medium text-slate-400">{c.category}</span>
                <h2 className="mt-1 text-lg font-bold text-slate-900">{c.name}</h2>
                <p className="mt-1 flex-1 text-sm text-slate-600">{c.description}</p>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  <Badge className={DEMAND_STYLE[c.demand]}>{c.demand} demand</Badge>
                  <Badge>{formatSalary(c.salary_inr_lpa)}</Badge>
                  <Badge>
                    {c.skill_count} skills · ~{c.total_hours} hrs
                  </Badge>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </Page>
  )
}
