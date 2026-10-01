import { Background, Controls, Handle, MarkerType, Position, ReactFlow } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useMemo } from 'react'
import { STAGE_STYLE } from '../constants.js'

const COLUMN_WIDTH = 250
const ROW_HEIGHT = 92

/**
 * Lay skills out left-to-right by "depth": a skill sits one column to the right of its
 * deepest prerequisite. Steps arrive already topologically sorted, so prerequisites are
 * always placed before the skills that need them.
 */
function layout(steps, selectedId) {
  const inPlan = new Set(steps.map((s) => s.skill_id))
  const column = {}
  const rowsUsed = {}
  const nodes = steps.map((s) => {
    const prereqs = s.prereqs.filter((p) => inPlan.has(p))
    const col = prereqs.length ? 1 + Math.max(...prereqs.map((p) => column[p])) : 0
    column[s.skill_id] = col
    const row = (rowsUsed[col] = (rowsUsed[col] ?? -1) + 1)
    return {
      id: s.skill_id,
      type: 'skill',
      position: { x: col * COLUMN_WIDTH, y: row * ROW_HEIGHT },
      data: { step: s, selected: s.skill_id === selectedId },
    }
  })
  const edges = steps.flatMap((s) =>
    s.prereqs
      .filter((p) => inPlan.has(p))
      .map((p) => ({
        id: `${p}->${s.skill_id}`,
        source: p,
        target: s.skill_id,
        markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
        style: { stroke: '#94a3b8' },
      })),
  )
  return { nodes, edges }
}

function SkillNode({ data }) {
  const { step, selected } = data
  const stage = STAGE_STYLE[step.stage]
  return (
    <div
      className={`w-52 cursor-pointer rounded-xl border-2 bg-white px-3 py-2 shadow-sm transition hover:shadow-md ${
        selected ? 'border-brand-600 ring-2 ring-brand-200' : stage.border
      }`}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-slate-400" />
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 shrink-0 rounded-full ${stage.dot}`} />
        <span className="text-[11px] font-medium text-slate-400">Step {step.step}</span>
        <span className="ml-auto text-[11px] text-slate-400">~{step.est_hours}h</span>
      </div>
      <div className="mt-0.5 truncate text-sm font-semibold text-slate-800" title={step.name}>
        {step.name}
      </div>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-slate-400" />
    </div>
  )
}

const nodeTypes = { skill: SkillNode }

export default function RoadmapGraph({ steps, selectedId, onSelect }) {
  const { nodes, edges } = useMemo(() => layout(steps, selectedId), [steps, selectedId])

  return (
    <div className="h-[560px] overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect(node.data.step)}
        nodesDraggable={false}
        nodesConnectable={false}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.3}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} color="#e2e8f0" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
