"""Request and response shapes. FastAPI validates against these and shows them on /docs."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ------------------------------------------------------------- recommend ----

class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000,
                       examples=["I know Python and SQL, and I love numbers"])
    known_skills: list[str] | None = Field(
        None, max_length=100,
        description="Skill ids that replace what the NLP detected (the editable skill chips).")
    top_k: int = Field(3, ge=1, le=15)
    min_match: float = Field(5.0, ge=0, le=100,
                             description="Hide careers below this match % (the top career is always shown).")


class ParsedQuery(BaseModel):
    known_skills: list[str]
    goal_skills: list[str]
    negated_skills: list[str]
    interests: list[str]
    careers: list[str]


class Scores(BaseModel):
    classifier: float
    similarity: float


class Recommendation(BaseModel):
    career_id: str
    name: str
    description: str
    match: float
    scores: Scores
    reasons: list[str]
    skills_known: int
    skills_total: int
    demand: str
    salary_inr_lpa: list[int]


class RecommendResponse(BaseModel):
    status: Literal["ok", "need_more_info"]
    confidence: Literal["high", "medium", "low"] | None = None
    message: str | None = None
    parsed: ParsedQuery
    recommendations: list[Recommendation]


# --------------------------------------------------------------- roadmap ----

class RoadmapRequest(BaseModel):
    career_id: str = Field(..., examples=["data_analyst"])
    known_skills: list[str] = Field(default_factory=list, max_length=100, examples=[["python", "sql"]])
    hours_per_week: int = Field(10, ge=1, le=80)


class Resource(BaseModel):
    title: str
    url: str
    type: str


class RoadmapStep(BaseModel):
    step: int
    skill_id: str
    name: str
    stage: str
    description: str
    difficulty: int
    est_hours: int
    prereqs: list[str]
    resources: list[Resource]


class KnownSkill(BaseModel):
    skill_id: str
    name: str
    implied: bool


class SkillRef(BaseModel):
    skill_id: str
    name: str


class RoadmapResponse(BaseModel):
    career_id: str
    career_name: str
    steps: list[RoadmapStep]
    already_known: list[KnownSkill]
    optional_skills: list[SkillRef]
    total_hours: int
    hours_per_week: int
    est_weeks: int | None
    progress: float


# --------------------------------------------------------------- catalog ----

class CareerSummary(BaseModel):
    id: str
    name: str
    category: str
    description: str
    demand: str
    salary_inr_lpa: list[int]
    skill_count: int
    total_hours: int


class StageSkill(BaseModel):
    id: str
    name: str
    est_hours: int


class CareerDetail(CareerSummary):
    interests: list[str]
    stages: dict[str, list[StageSkill]]
    optional_skills: list[SkillRef]


class SkillSummary(BaseModel):
    id: str
    name: str
    category: str


# ------------------------------------------------------------------ auth ----

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
