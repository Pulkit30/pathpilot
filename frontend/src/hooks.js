import { useEffect, useMemo, useRef, useState } from 'react'
import { listSkills } from './api.js'

/**
 * Run an async function and track its result: {data, error, loading}.
 * It re-runs whenever `key` (a string describing the inputs) changes.
 */
export function useAsync(fn, key) {
  const fnRef = useRef(fn)
  useEffect(() => {
    fnRef.current = fn
  })

  const [result, setResult] = useState({ key: null, data: null, error: null })

  useEffect(() => {
    let active = true // ignore answers that arrive after the inputs changed
    fnRef
      .current()
      .then((data) => active && setResult({ key, data, error: null }))
      .catch((error) => active && setResult({ key, data: null, error }))
    return () => {
      active = false
    }
  }, [key])

  const loading = result.key !== key
  return { data: loading ? null : result.data, error: loading ? null : result.error, loading }
}

/** All skills as a list plus a lookup by id: {list, byId}. */
export function useSkills() {
  const { data } = useAsync(listSkills, 'skills')
  return useMemo(() => {
    const list = data || []
    return { list, byId: Object.fromEntries(list.map((s) => [s.id, s])) }
  }, [data])
}

/** Comma-separated URL value -> array. */
export const splitList = (value) => (value ? value.split(',').filter(Boolean) : [])
