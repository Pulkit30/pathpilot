// The only place the frontend talks to the backend. Every call goes to /api/* on the same origin.

const TOKEN_KEY = 'pathpilot_token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // storage blocked (private mode): stay logged in for this tab only
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

// FastAPI errors look like {detail: "text"} or {detail: [{loc, msg}, ...]} for validation errors.
function detailMessage(detail) {
  if (!detail) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = d.loc?.slice(1).join('.')
        return field ? `${field}: ${d.msg}` : d.msg
      })
      .join('; ')
  }
  return null
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError("Can't reach the PathPilot server. Is the backend running?", 0)
  }
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(detailMessage(data?.detail) || `Request failed (${res.status})`, res.status)
  }
  return data
}

export const recommend = (query, knownSkills) =>
  api('/recommend', {
    method: 'POST',
    body: { query, ...(knownSkills ? { known_skills: knownSkills } : {}) },
  })

export const getRoadmap = (careerId, knownSkills, hoursPerWeek) =>
  api('/roadmap', {
    method: 'POST',
    body: { career_id: careerId, known_skills: knownSkills, hours_per_week: hoursPerWeek },
  })

export const listCareers = () => api('/careers')
export const getCareer = (id) => api(`/careers/${encodeURIComponent(id)}`)

let skillsPromise
export function listSkills() {
  // Skills never change while the app runs, so fetch them once and share the result.
  if (!skillsPromise) {
    skillsPromise = api('/skills').catch((err) => {
      skillsPromise = null
      throw err
    })
  }
  return skillsPromise
}

export const register = (email, name, password) =>
  api('/auth/register', { method: 'POST', body: { email, name, password } })
export const login = (email, password) => api('/auth/login', { method: 'POST', body: { email, password } })
export const me = () => api('/auth/me')
