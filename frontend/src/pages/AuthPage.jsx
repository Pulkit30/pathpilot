import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../auth.jsx'
import { ErrorMessage, Page } from '../components/ui.jsx'

export default function AuthPage({ mode }) {
  const isRegister = mode === 'register'
  const { user, login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={location.state?.from || '/'} replace />

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      if (isRegister) await register(form.email, form.name, form.password)
      else await login(form.email, form.password)
      navigate(location.state?.from || '/', { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Page className="max-w-md">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-slate-900">{isRegister ? 'Create your account' : 'Welcome back'}</h1>
        <p className="mt-1 text-sm text-slate-600">
          {isRegister ? 'Save your roadmaps and track progress (coming soon).' : 'Log in to PathPilot.'}
        </p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          {isRegister && (
            <Field label="Name" id="name" value={form.name} onChange={update('name')} autoComplete="name" required maxLength={80} />
          )}
          <Field label="Email" id="email" type="email" value={form.email} onChange={update('email')} autoComplete="email" required />
          <Field
            label="Password"
            id="password"
            type="password"
            value={form.password}
            onChange={update('password')}
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            required
            minLength={isRegister ? 8 : 1}
            hint={isRegister ? 'At least 8 characters' : null}
          />
          <ErrorMessage error={error} />
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-xl bg-brand-600 px-4 py-2.5 font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {busy ? 'Please wait…' : isRegister ? 'Create account' : 'Log in'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600">
          {isRegister ? 'Already have an account? ' : 'New to PathPilot? '}
          <Link to={isRegister ? '/login' : '/register'} state={location.state} className="font-medium text-brand-600 hover:underline">
            {isRegister ? 'Log in' : 'Create an account'}
          </Link>
        </p>
      </div>
    </Page>
  )
}

function Field({ label, id, hint, ...props }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={id}
        {...props}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
      />
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
