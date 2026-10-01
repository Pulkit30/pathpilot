import { Route, Routes } from 'react-router'
import Navbar from './components/Navbar.jsx'
import RequireAuth from './components/RequireAuth.jsx'
import AuthPage from './pages/AuthPage.jsx'
import CareerDetail from './pages/CareerDetail.jsx'
import Careers from './pages/Careers.jsx'
import Home from './pages/Home.jsx'
import MyRoadmaps from './pages/MyRoadmaps.jsx'
import NotFound from './pages/NotFound.jsx'
import Results from './pages/Results.jsx'
import Roadmap from './pages/Roadmap.jsx'

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
        <Route path="/roadmap/:careerId" element={<Roadmap />} />
        <Route path="/careers" element={<Careers />} />
        <Route path="/careers/:careerId" element={<CareerDetail />} />
        <Route
          path="/my-roadmaps"
          element={
            <RequireAuth>
              <MyRoadmaps />
            </RequireAuth>
          }
        />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <footer className="mt-auto border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        PathPilot · career recommendations from a model built from scratch with NumPy
      </footer>
    </div>
  )
}
