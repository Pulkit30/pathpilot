"""Knowledge base: loads careers, skills, resources and synonyms from data/."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STAGES = ["beginner", "intermediate", "advanced"]


def _load(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class KnowledgeBase:
    careers: dict      # career id -> career dict
    skills: dict       # skill id -> skill dict
    resources: dict    # skill id -> list of resources
    skill_synonyms: dict     # variant -> skill id
    interest_synonyms: dict  # variant -> canonical interest

    @property
    def career_ids(self):
        return list(self.careers)

    def required_skills(self, career_id):
        """Required skills of a career in roadmap order (beginner -> advanced)."""
        stages = self.careers[career_id]["stages"]
        return [sid for stage in STAGES for sid in stages[stage]]

    def stage_of(self, career_id):
        """Map skill id -> stage name for a career's required skills."""
        return {sid: stage for stage in STAGES for sid in self.careers[career_id]["stages"][stage]}

    @property
    def interests(self):
        """All canonical interest words used by any career."""
        return sorted({i for c in self.careers.values() for i in c["interests"]})


@lru_cache(maxsize=1)
def load_kb():
    synonyms = _load("synonyms.json")
    return KnowledgeBase(
        careers={c["id"]: c for c in _load("careers.json")["careers"]},
        skills={s["id"]: s for s in _load("skills.json")["skills"]},
        resources=_load("resources.json")["resources"],
        skill_synonyms=synonyms["skills"],
        interest_synonyms=synonyms["interests"],
    )
