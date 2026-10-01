"""Generate synthetic training profiles: (free-text sentence, career id) pairs.

Real users haven't used PathPilot yet, so we create labelled examples from the knowledge base:
for each career we sample skills the person knows, skills they want to learn, interests and
sometimes the job title, then render them with varied sentence templates and wording.
Noise (skills from other careers, missing signals) keeps the task from being trivially easy.

Run:  python -m ml.generate_data          -> writes data/training_profiles.json
"""

import argparse
import json
import random

from ml.kb import DATA_DIR, load_kb
from ml.nlp import _skill_variants

PER_CAREER = 160
SEED = 42
OUT_PATH = DATA_DIR / "training_profiles.json"

INTROS = [
    "I'm a student.", "I am a final year B.Tech student.", "I'm a commerce graduate.",
    "I work in customer support.", "I'm a fresher.", "I'm switching careers from teaching.",
    "I'm in 12th grade.", "I have 2 years of experience in IT.", "I'm a self-taught programmer.",
    "I'm a BCA student.", "I just finished college.", "I'm working as a sales executive.",
    "I'm a mechanical engineering student.", "I'm 25 and want a change.", "I'm a beginner.",
]
KNOWN = [
    "I know {x}.", "I'm comfortable with {x}.", "I have experience with {x}.", "I've worked with {x}.",
    "I'm familiar with {x}.", "My skills are {x}.", "{x}.", "I've used {x} in college projects.",
    "I already know {x}.", "I can use {x}.", "I did a course on {x}.", "Good at {x}.",
]
INTERESTS = [
    "I love {x}.", "I'm really into {x}.", "I enjoy {x}.", "I'm passionate about {x}.",
    "I'm fascinated by {x}.", "I like {x}.", "{x} excites me.", "I've always liked {x}.",
    "My hobbies involve {x}.", "I care about {x}.",
]
GOALS = [
    "I want to learn {x}.", "I'd like to get better at {x}.", "I'm curious about {x}.",
    "Planning to study {x}.", "I hope to master {x}.", "I want to explore {x}.",
    "Interested in learning {x}.",
]
CAREER = [
    "I want to become a {x}.", "My dream is to be a {x}.", "How do I become a {x}?",
    "Thinking of a career as a {x}.", "I want to work as a {x}.",
]
CLOSINGS = [
    "What should I do?", "Which career suits me?", "Where should I start?", "Suggest a path.",
    "What career fits me?", "Please guide me.", "What should I learn next?",
]
# Skills many people know regardless of target career: realistic cross-career noise.
COMMON = ["git", "excel", "python", "sql", "html", "programming_basics", "command_line", "javascript"]


def _join(items, rng):
    if len(items) == 1:
        return items[0]
    sep = rng.choice([", ", ", ", " and "])
    return sep.join(items[:-1]) + " and " + items[-1] if sep == ", " else " and ".join(items)


class Phrasebook:
    """Different ways to write a skill, interest or job title."""

    def __init__(self, kb):
        self.skill = {}
        for sid, skill in kb.skills.items():
            forms = _skill_variants(skill) | {k for k, v in kb.skill_synonyms.items() if v == sid}
            self.skill[sid] = sorted(f for f in forms if "(" not in f)
        self.base_name = {sid: s["name"].split(" (")[0] for sid, s in kb.skills.items()}
        self.interest = {i: [i] for i in kb.interests}
        for k, v in kb.interest_synonyms.items():
            self.interest[v].append(k)
        self.career = {cid: [c["name"].lower(), *c.get("aliases", [])] for cid, c in kb.careers.items()}

    def skill_text(self, sid, rng):
        # Usually the clean display name, sometimes a synonym/variant ("js", "sklearn", ...).
        return self.base_name[sid] if rng.random() < 0.6 else rng.choice(self.skill[sid])

    def interest_text(self, interest, rng):
        return rng.choice(self.interest[interest])

    def career_text(self, cid, rng):
        return rng.choice(self.career[cid])


def make_profile(career, kb, book, rng):
    stages = career["stages"]
    early = stages["beginner"] + stages["intermediate"]
    late = stages["intermediate"] + stages["advanced"]

    # Sample until the profile carries at least two signals.
    while True:
        known = rng.sample(early, k=min(len(early), rng.choice([0, 0, 1, 2, 2, 3])))
        goals = [s for s in rng.sample(late, k=min(len(late), rng.choice([0, 0, 1, 1, 2]))) if s not in known]
        interests = rng.sample(career["interests"], k=rng.choice([0, 1, 1, 2, 2, 3]))
        mention_career = rng.random() < 0.15
        if len(known) + len(goals) + len(interests) + mention_career >= 2:
            break

    if rng.random() < 0.25:  # noise: a common skill unrelated to this career
        noise = rng.choice(COMMON)
        if noise not in known:
            known.append(noise)

    parts = []
    if known:
        parts.append(rng.choice(KNOWN).format(x=_join([book.skill_text(s, rng) for s in known], rng)))
    if interests:
        parts.append(rng.choice(INTERESTS).format(x=_join([book.interest_text(i, rng) for i in interests], rng)))
    if goals:
        parts.append(rng.choice(GOALS).format(x=_join([book.skill_text(s, rng) for s in goals], rng)))
    if mention_career:
        parts.append(rng.choice(CAREER).format(x=book.career_text(career["id"], rng)))
    rng.shuffle(parts)
    if rng.random() < 0.35:
        parts.insert(0, rng.choice(INTROS))
    if rng.random() < 0.3:
        parts.append(rng.choice(CLOSINGS))

    text = " ".join(parts)
    if rng.random() < 0.3:
        text = text.lower()  # people often type in lowercase
    return {"text": text, "career": career["id"]}


def generate(per_career=PER_CAREER, seed=SEED):
    kb = load_kb()
    rng = random.Random(seed)
    book = Phrasebook(kb)
    rows = [make_profile(c, kb, book, rng) for c in kb.careers.values() for _ in range(per_career)]
    rng.shuffle(rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic training profiles.")
    parser.add_argument("--per-career", type=int, default=PER_CAREER)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    rows = generate(args.per_career, args.seed)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "seed": args.seed, "profiles": rows}, f, indent=0, ensure_ascii=False)
    print(f"Wrote {len(rows)} profiles to {OUT_PATH.relative_to(DATA_DIR.parent)}")
    for row in rows[:5]:
        print(f"  [{row['career']}] {row['text']}")


if __name__ == "__main__":
    main()
