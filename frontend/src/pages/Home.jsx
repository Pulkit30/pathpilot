import { useState } from 'react'
import { useNavigate } from 'react-router'
import { Page } from '../components/ui.jsx'

const EXAMPLES = [
  'I know Python and SQL, and I love working with numbers',
  "I love video games and I've started learning C#",
  "I'm a commerce student who likes Excel and business reports",
  'I enjoy drawing and want to design apps people love',
  'Curious about AI chatbots, RAG and LLMs',
  "I like hacking challenges and know a bit of Linux",
]

const STEPS = [
  { title: 'Describe yourself', text: 'Skills you have, what you enjoy, what you want to learn. Plain English is fine.' },
  { title: 'Get matched', text: 'Our model, built from scratch, ranks 15 tech careers and explains why each one fits.' },
  { title: 'Follow your roadmap', text: 'A step-by-step plan that skips what you already know, with free resources for each skill.' },
]

export default function Home() {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  const submit = (e) => {
    e?.preventDefault()
    const q = query.trim()
    if (q) navigate(`/results?${new URLSearchParams({ q })}`)
  }

  return (
    <Page className="max-w-3xl">
      <section className="py-8 text-center sm:py-14">
        <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          Find your path in <span className="text-brand-600">tech</span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-slate-600">
          Tell PathPilot what you know and what you enjoy. Get the careers that fit you and a personal roadmap to get there.
        </p>
      </section>

      <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <label htmlFor="query" className="mb-2 block text-sm font-semibold text-slate-700">
          What do you know, and what do you enjoy?
        </label>
        <textarea
          id="query"
          rows={4}
          maxLength={1000}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(e)
          }}
          placeholder="e.g. I know Python and some SQL, I love math, and I want to work in AI"
          className="w-full resize-y rounded-xl border border-slate-300 p-3 text-base outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-slate-500">{query.length}/1000 · Ctrl/⌘ + Enter to submit</span>
          <button
            type="submit"
            disabled={!query.trim()}
            className="rounded-xl bg-brand-600 px-6 py-2.5 font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Find my path →
          </button>
        </div>
      </form>

      <div className="mt-6">
        <p className="mb-2 text-sm font-medium text-slate-500">Or try an example:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setQuery(ex)}
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-left text-sm text-slate-600 hover:border-brand-300 hover:text-brand-700"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      <section className="mt-16 grid gap-4 sm:grid-cols-3">
        {STEPS.map((s, i) => (
          <div key={s.title} className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 font-bold text-brand-700">
              {i + 1}
            </div>
            <h2 className="font-semibold text-slate-900">{s.title}</h2>
            <p className="mt-1 text-sm text-slate-600">{s.text}</p>
          </div>
        ))}
      </section>
    </Page>
  )
}
