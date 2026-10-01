"""From-scratch NLP: turn a free-text question into tokens, skills, interests and career mentions.

    "I know Python and SQL, and I want to learn machine learning. I love maths."
      -> known_skills = [python, sql]
         goal_skills  = [machine_learning]
         interests    = [math]
         tokens       = [python, sql, machine, learn, love, math]

No NLP libraries: phrase matching uses regular expressions built from the knowledge base
(skill names, ids, synonyms, interests, career aliases).
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

from ml.kb import load_kb

STOPWORDS = set("""
a about above after again against all also am an and any are as at be because been before being
below between both but by can could did do does doing done down during each else even ever every
few for from further get got had has have having he her here hers him his how i i'm im if in into
is it its itself just let me more most much my myself no nor not now of off on once only or other
our out over own really same she should so some such than that the their them then there these
they this those through to too under until up very was we were what when where which while who
whom why will with would you your yours yourself thing things lot lots bit kind sort stuff way
want wants wanted learn learning learnt know knows knew become becoming interested interest
career careers job jobs role field path start started starting like likes liked love loves enjoy
enjoys pretty quite something someone anything everything currently already still new good
great well basic basics bit little some year years month months
""".split())

# A cue word decides whether the skills after it are already known or are a goal.
GOAL_CUES = {"want", "wants", "wanna", "learn", "learning", "become", "becoming", "interested",
             "curious", "wish", "hope", "plan", "planning", "goal", "dream", "aspire", "explore",
             "exploring", "switch", "transition", "into", "pursue", "master", "study", "studying"}
KNOWN_CUES = {"know", "knows", "knew", "familiar", "experience", "experienced", "worked", "work",
              "working", "use", "used", "using", "comfortable", "good", "studied", "completed",
              "built", "made", "skilled", "proficient", "expert", "background", "have", "did",
              "done", "certified", "intern", "internship"}
NEGATIONS = {"not", "no", "dont", "don't", "never", "without", "zero", "nothing", "haven't",
             "havent", "cannot", "can't", "cant"}

WORD_RE = re.compile(r"[a-z0-9+#']+")
CLAUSE_SPLIT_RE = re.compile(r"[.;!?](?=\s|$)|\n|\bbut\b|\bhowever\b|\bthough\b")


def normalize(text):
    """Lowercase, unify quotes, turn hyphens into spaces and collapse whitespace."""
    text = text.lower().replace("’", "'").replace("‘", "'")
    text = re.sub(r"(?<=\w)-(?=\w)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stem(word):
    """Tiny suffix stripper so 'designing'/'designs'/'designed' all become 'design'."""
    if len(word) <= 4 or not word.isalpha():
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("sses"):
        return word[:-2]
    if word.endswith("ing") and len(word) > 5:
        return word[:-3]
    if word.endswith("ed") and len(word) > 5:
        return word[:-2]
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def tokenize(text):
    """Normalized, stopword-free, stemmed word tokens."""
    tokens = []
    for w in WORD_RE.findall(normalize(text)):
        w = w.strip("'")
        if w and w not in STOPWORDS and w not in NEGATIONS:
            w = stem(w)
            if w not in STOPWORDS:  # "wanting" -> "want"
                tokens.append(w)
    return tokens


# ------------------------------------------------------------ phrase tables ----

def _skill_variants(skill):
    """Phrases that refer to a skill, derived from its id and display name."""
    name = normalize(skill["name"])
    variants = {skill["id"].replace("_", " "), name}
    base = re.sub(r"\s*\(.*?\)", "", name).strip()          # "data visualization (matplotlib/seaborn)"
    variants.add(base)
    for inner in re.findall(r"\((.*?)\)", name):            # "matplotlib/seaborn"
        variants.update(p.strip() for p in re.split(r"[/,]", inner))
    for part in re.split(r"\s+/\s+|\s+&\s+", base):         # "power bi / tableau", "git & github"
        variants.add(part.strip())
    return {v for v in variants if len(v) >= 2}


def _compile(phrases):
    """One regex matching any phrase as whole words, longest phrase first."""
    ordered = sorted(phrases, key=len, reverse=True)
    body = "|".join(re.escape(p) for p in ordered)
    return re.compile(rf"(?<![a-z0-9])(?:{body})(?![a-z0-9])")


@lru_cache(maxsize=1)
def _tables():
    kb = load_kb()
    skill_map = {}
    for skill in kb.skills.values():
        for v in _skill_variants(skill):
            skill_map.setdefault(v, skill["id"])
    skill_map.update({normalize(k): v for k, v in kb.skill_synonyms.items()})  # explicit synonyms win

    interest_map = {i: i for i in kb.interests}
    interest_map.update({normalize(k): v for k, v in kb.interest_synonyms.items()})

    career_map = {}
    for c in kb.careers.values():
        for alias in [c["name"].lower(), *c.get("aliases", [])]:
            career_map[normalize(alias)] = c["id"]

    return {
        "skill": (skill_map, _compile(skill_map)),
        "interest": (interest_map, _compile(interest_map)),
        "career": (career_map, _compile(career_map)),
    }


# ------------------------------------------------------------------ parsing ----

@dataclass
class ParsedQuery:
    text: str
    tokens: list = field(default_factory=list)
    known_skills: list = field(default_factory=list)
    goal_skills: list = field(default_factory=list)
    negated_skills: list = field(default_factory=list)
    interests: list = field(default_factory=list)
    careers: list = field(default_factory=list)

    @property
    def skills(self):
        return self.known_skills + [s for s in self.goal_skills if s not in self.known_skills]

    def features(self):
        """Feature strings fed to the TF-IDF vectorizer."""
        return (self.tokens
                + [f"skill:{s}" for s in self.skills]
                + [f"interest:{i}" for i in self.interests]
                + [f"career:{c}" for c in self.careers])

    def is_empty(self):
        return not (self.tokens or self.skills or self.interests or self.careers)


def _matches(kind, text):
    mapping, regex = _tables()[kind]
    return [(m.start(), m.end(), mapping[m.group(0)]) for m in regex.finditer(text)]


def _intent(clause, start):
    """'known', 'goal' or 'negated' for a skill mentioned at `start` inside `clause`."""
    words = WORD_RE.findall(clause[:start])
    if any(w in NEGATIONS for w in words[-4:]):
        return "negated"
    for w in reversed(words):  # the nearest cue before the skill wins
        if w in GOAL_CUES:
            return "goal"
        if w in KNOWN_CUES:
            return "known"
    return "known"  # a bare list like "python, sql, excel" is assumed known


def _add(lst, item):
    if item not in lst:
        lst.append(item)


def parse(text):
    """Parse free text into a ParsedQuery."""
    norm = normalize(text)
    q = ParsedQuery(text=text, tokens=tokenize(text))

    for clause in CLAUSE_SPLIT_RE.split(norm):
        career_spans = _matches("career", clause)
        for _, _, cid in career_spans:
            _add(q.careers, cid)
        for _, _, interest in _matches("interest", clause):
            _add(q.interests, interest)
        for start, end, sid in _matches("skill", clause):
            # "machine learning engineer" is a career mention, not the skill "machine learning"
            if any(cs <= start and end <= ce for cs, ce, _ in career_spans):
                continue
            intent = _intent(clause, start)
            target = {"known": q.known_skills, "goal": q.goal_skills, "negated": q.negated_skills}[intent]
            _add(target, sid)

    # A skill both known and negated/goal in different clauses: the explicit "known" wins.
    q.goal_skills = [s for s in q.goal_skills if s not in q.known_skills]
    q.negated_skills = [s for s in q.negated_skills if s not in q.known_skills]
    return q
