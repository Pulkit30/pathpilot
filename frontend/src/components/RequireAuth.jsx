import { Navigate, useLocation } from 'react-router'
import { useAuth } from '../auth.jsx'
import { Spinner } from './ui.jsx'

/** Show children only to logged-in users; others go to /login and come back afterwards. */
export default function RequireAuth({ children }) {
  const { user, checking } = useAuth()
  const location = useLocation()
  if (checking) return <Spinner />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return children
}
