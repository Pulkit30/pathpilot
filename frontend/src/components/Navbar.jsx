import { Link, NavLink } from 'react-router'
import { useAuth } from '../auth.jsx'

const linkClass = ({ isActive }) =>
  `rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`

export default function Navbar() {
  const { user, logout } = useAuth()

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3 sm:px-6">
        <Link to="/" className="mr-4 flex items-center gap-2 text-lg font-bold text-slate-900">
          <img src="/favicon.svg" alt="" className="h-7 w-7" />
          PathPilot
        </Link>
        <NavLink to="/" end className={linkClass}>
          Ask
        </NavLink>
        <NavLink to="/careers" className={linkClass}>
          Careers
        </NavLink>

        <div className="ml-auto flex items-center gap-2">
          {user ? (
            <>
              <span className="hidden text-sm text-slate-600 sm:inline">Hi, {user.name}</span>
              <button onClick={logout} className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={linkClass}>
                Log in
              </NavLink>
              <Link to="/register" className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700">
                Sign up
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
