import { useMemo, useState } from 'react'

/**
 * Editable list of skill chips with search-as-you-type.
 * value: array of skill ids · onChange(newIds) · skills: {list, byId} from useSkills()
 */
export default function SkillPicker({ value, onChange, skills, placeholder = 'Add a skill you know…' }) {
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)

  const suggestions = useMemo(() => {
    const t = text.trim().toLowerCase()
    if (!t) return []
    return skills.list
      .filter((s) => !value.includes(s.id) && (s.name.toLowerCase().includes(t) || s.id.includes(t)))
      .slice(0, 8)
  }, [text, skills.list, value])

  const add = (id) => {
    onChange([...value, id])
    setText('')
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {value.map((id) => (
          <span key={id} className="inline-flex items-center gap-1 rounded-full bg-brand-50 py-1 pl-3 pr-1 text-sm text-brand-800 ring-1 ring-inset ring-brand-200">
            {skills.byId[id]?.name || id}
            <button
              type="button"
              onClick={() => onChange(value.filter((v) => v !== id))}
              className="flex h-5 w-5 items-center justify-center rounded-full text-brand-500 hover:bg-brand-200 hover:text-brand-900"
              aria-label={`Remove ${skills.byId[id]?.name || id}`}
            >
              ×
            </button>
          </span>
        ))}
        {value.length === 0 && <span className="text-sm text-slate-400">No skills yet</span>}
      </div>

      <div className="relative mt-3 max-w-sm">
        <input
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)} // let a click on a suggestion land first
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              if (suggestions[0]) add(suggestions[0].id)
            }
          }}
          placeholder={placeholder}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
        />
        {open && suggestions.length > 0 && (
          <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
            {suggestions.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => add(s.id)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-brand-50"
                >
                  {s.name}
                  <span className="text-xs text-slate-400">{s.category}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
