import { Link } from 'react-router'
import { Page } from '../components/ui.jsx'

export default function NotFound() {
  return (
    <Page className="max-w-md text-center">
      <p className="text-6xl font-extrabold text-brand-600">404</p>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">This page went off the map</h1>
      <p className="mt-2 text-slate-600">Let's get you back on a path.</p>
      <Link to="/" className="mt-6 inline-block rounded-xl bg-brand-600 px-5 py-2.5 font-semibold text-white hover:bg-brand-700">
        Go home
      </Link>
    </Page>
  )
}
