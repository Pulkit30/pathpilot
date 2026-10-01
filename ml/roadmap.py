"""Roadmap builder: skill gap + topological sort over the prerequisite graph.

1. Required skills for the career            (from careers.json)
2. Minus what the user knows                  (said explicitly, or implied: knowing Pandas implies Python)
3. Ordered so every skill comes after its prerequisites (Kahn's algorithm), preferring the
   career's stage order (beginner -> intermediate -> advanced) when several skills are ready.
"""

import heapq
import math

from ml.kb import STAGES, load_kb


def implied_known(known, kb):
    """Known skills plus all of their prerequisites, recursively."""
    result, stack = set(), [s for s in known if s in kb.skills]
    while stack:
        sid = stack.pop()
        if sid not in result:
            result.add(sid)
            stack.extend(kb.skills[sid]["prereqs"])
    return result


def topological_order(skill_ids, priority, kb):
    """Order skill_ids so prerequisites come first; ties broken by `priority` (lower first)."""
    pending = set(skill_ids)
    indegree = {s: sum(p in pending for p in kb.skills[s]["prereqs"]) for s in pending}
    dependents = {s: [] for s in pending}
    for s in pending:
        for p in kb.skills[s]["prereqs"]:
            if p in pending:
                dependents[p].append(s)

    ready = [(priority[s], s) for s in pending if indegree[s] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        _, s = heapq.heappop(ready)
        order.append(s)
        for d in dependents[s]:
            indegree[d] -= 1
            if indegree[d] == 0:
                heapq.heappush(ready, (priority[d], d))
    if len(order) != len(pending):
        raise ValueError("prerequisite cycle detected; run data/validate.py")
    return order


def build_roadmap(career_id, known_skills=(), hours_per_week=10, kb=None):
    kb = kb or load_kb()
    if career_id not in kb.careers:
        raise ValueError(f"unknown career '{career_id}'")
    career = kb.careers[career_id]
    required = kb.required_skills(career_id)
    stage_of = kb.stage_of(career_id)

    explicit = {s for s in known_skills if s in kb.skills}
    known = implied_known(explicit, kb)
    already = [s for s in required if s in known]
    todo = [s for s in required if s not in known]

    priority = {s: (STAGES.index(stage_of[s]), required.index(s)) for s in todo}
    ordered = topological_order(todo, priority, kb)

    steps = []
    for i, sid in enumerate(ordered, start=1):
        skill = kb.skills[sid]
        steps.append({
            "step": i,
            "skill_id": sid,
            "name": skill["name"],
            "stage": stage_of[sid],
            "description": skill["description"],
            "difficulty": skill["difficulty"],
            "est_hours": skill["est_hours"],
            "prereqs": skill["prereqs"],
            "resources": kb.resources.get(sid, []),
        })

    total_hours = sum(s["est_hours"] for s in steps)
    return {
        "career_id": career_id,
        "career_name": career["name"],
        "steps": steps,
        "already_known": [{"skill_id": s, "name": kb.skills[s]["name"], "implied": s not in explicit}
                          for s in already],
        "optional_skills": [{"skill_id": s, "name": kb.skills[s]["name"]}
                            for s in career.get("optional_skills", []) if s not in known],
        "total_hours": total_hours,
        "hours_per_week": hours_per_week,
        "est_weeks": math.ceil(total_hours / hours_per_week) if hours_per_week > 0 else None,
        "progress": round(len(already) / len(required), 3) if required else 1.0,
    }
