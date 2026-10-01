// Shared constants and formatting helpers (kept out of component files so hot reload works).

export const STAGES = ['beginner', 'intermediate', 'advanced']

export const STAGE_STYLE = {
  beginner: { label: 'Beginner', dot: 'bg-emerald-500', chip: 'bg-emerald-50 text-emerald-700 ring-emerald-200', border: 'border-emerald-300' },
  intermediate: { label: 'Intermediate', dot: 'bg-sky-500', chip: 'bg-sky-50 text-sky-700 ring-sky-200', border: 'border-sky-300' },
  advanced: { label: 'Advanced', dot: 'bg-rose-500', chip: 'bg-rose-50 text-rose-700 ring-rose-200', border: 'border-rose-300' },
}

export const DEMAND_STYLE = {
  high: 'bg-green-50 text-green-700 ring-green-200',
  medium: 'bg-sky-50 text-sky-700 ring-sky-200',
  low: 'bg-slate-100 text-slate-600 ring-slate-200',
}

export const formatSalary = ([min, max]) => `₹${min}–${max} LPA`
