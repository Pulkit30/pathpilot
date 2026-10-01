import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as apiClient from './api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(() => Boolean(apiClient.getToken()))

  // On page load, turn a saved token back into a user (or drop it if it expired).
  useEffect(() => {
    if (!apiClient.getToken()) return
    apiClient
      .me()
      .then(setUser)
      .catch(() => apiClient.setToken(null))
      .finally(() => setChecking(false))
  }, [])

  const finish = useCallback(({ access_token, user }) => {
    apiClient.setToken(access_token)
    setUser(user)
    return user
  }, [])

  const value = useMemo(
    () => ({
      user,
      checking,
      login: (email, password) => apiClient.login(email, password).then(finish),
      register: (email, name, password) => apiClient.register(email, name, password).then(finish),
      logout: () => {
        apiClient.setToken(null)
        setUser(null)
      },
    }),
    [user, checking, finish],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
