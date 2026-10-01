"""Validate PathPilot's knowledge base (careers, skills, resources, synonyms).

Usage:
    python data/validate.py                # structural checks
    python data/validate.py --check-links  # also verify every resource URL is reachable

Exits with status 1 if any error is found. Warnings never fail the run.
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
STAGES = ["beginner", "intermediate", "advanced"]
RESOURCE_TYPES = {"docs", "course", "tutorial", "book", "practice", "article", "video"}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def load(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- skills ----

def check_skills(skills, report):
    """Field checks, unique ids and valid prerequisite references."""
    by_id = {}
    for s in skills:
        sid = s.get("id", "<missing id>")
        for field, kind in [("id", str), ("name", str), ("category", str), ("description", str),
                            ("difficulty", int), ("est_hours", int), ("prereqs", list)]:
            if not isinstance(s.get(field), kind):
                report.error(f"skill '{sid}': field '{field}' missing or not {kind.__name__}")
        if not ID_PATTERN.match(str(sid)):
            report.error(f"skill '{sid}': id must be lowercase snake_case")
        if sid in by_id:
            report.error(f"skill '{sid}': duplicate id")
        by_id[sid] = s
        if isinstance(s.get("difficulty"), int) and not 1 <= s["difficulty"] <= 5:
            report.error(f"skill '{sid}': difficulty must be 1-5")
        if isinstance(s.get("est_hours"), int) and s["est_hours"] <= 0:
            report.error(f"skill '{sid}': est_hours must be positive")

    for sid, s in by_id.items():
        for p in s.get("prereqs", []):
            if p == sid:
                report.error(f"skill '{sid}': lists itself as a prerequisite")
            elif p not in by_id:
                report.error(f"skill '{sid}': unknown prerequisite '{p}'")
    return by_id


def find_cycle(by_id):
    """Return one prerequisite cycle as a list of ids, or None (iterative DFS, 3-colour)."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {sid: WHITE for sid in by_id}
    for start in by_id:
        if colour[start] != WHITE:
            continue
        stack = [(start, iter(by_id[start]["prereqs"]))]
        path = [start]
        colour[start] = GREY
        while stack:
            node, children = stack[-1]
            nxt = next(children, None)
            if nxt is None:
                colour[node] = BLACK
                stack.pop()
                path.pop()
            elif nxt not in by_id:
                continue
            elif colour[nxt] == GREY:
                return path[path.index(nxt):] + [nxt]
            elif colour[nxt] == WHITE:
                colour[nxt] = GREY
                stack.append((nxt, iter(by_id[nxt]["prereqs"])))
                path.append(nxt)
    return None


def longest_chain(by_id):
    """Longest prerequisite chain in the graph (assumes no cycles)."""
    memo = {}

    def depth(sid):
        if sid not in memo:
            prereqs = [p for p in by_id[sid]["prereqs"] if p in by_id]
            best = max((depth(p) for p in prereqs), key=len, default=[])
            memo[sid] = best + [sid]
        return memo[sid]

    return max((depth(s) for s in by_id), key=len, default=[])


# --------------------------------------------------------------- careers ----

def check_careers(careers, skills_by_id, report):
    seen = set()
    used_skills = set()
    for c in careers:
        cid = c.get("id", "<missing id>")
        if cid in seen:
            report.error(f"career '{cid}': duplicate id")
        seen.add(cid)
        if not ID_PATTERN.match(str(cid)):
            report.error(f"career '{cid}': id must be lowercase snake_case")
        for field in ["name", "category", "description", "interests", "stages", "demand", "salary_inr_lpa"]:
            if field not in c:
                report.error(f"career '{cid}': missing field '{field}'")
        if not c.get("interests"):
            report.error(f"career '{cid}': needs at least one interest keyword")

        stages = c.get("stages", {})
        if list(stages.keys()) != STAGES:
            report.error(f"career '{cid}': stages must be exactly {STAGES} in that order")

        # Map each required skill to the index of its stage.
        stage_of = {}
        for idx, stage in enumerate(STAGES):
            for sid in stages.get(stage, []):
                if sid not in skills_by_id:
                    report.error(f"career '{cid}': unknown skill '{sid}' in {stage}")
                    continue
                if sid in stage_of:
                    report.error(f"career '{cid}': skill '{sid}' appears more than once")
                stage_of[sid] = idx
        used_skills.update(stage_of)

        # Every prerequisite of a required skill must also be required, and not in a later stage.
        for sid, idx in stage_of.items():
            for p in skills_by_id[sid]["prereqs"]:
                if p not in stage_of:
                    report.error(f"career '{cid}': '{sid}' needs '{p}', which is not in this career")
                elif stage_of[p] > idx:
                    report.error(f"career '{cid}': '{sid}' ({STAGES[idx]}) needs '{p}', "
                                 f"which is in a later stage ({STAGES[stage_of[p]]})")

        for sid in c.get("optional_skills", []):
            if sid not in skills_by_id:
                report.error(f"career '{cid}': unknown optional skill '{sid}'")
            elif sid in stage_of:
                report.error(f"career '{cid}': '{sid}' is both required and optional")
            used_skills.add(sid)

        salary = c.get("salary_inr_lpa")
        if not (isinstance(salary, list) and len(salary) == 2 and 0 < salary[0] <= salary[1]):
            report.error(f"career '{cid}': salary_inr_lpa must be [min, max]")

    alias_owner = {}
    for c in careers:
        for alias in c.get("aliases", []):
            if alias != alias.lower():
                report.error(f"career '{c['id']}': alias '{alias}' must be lowercase")
            if alias in alias_owner and alias_owner[alias] != c["id"]:
                report.error(f"alias '{alias}' used by both '{alias_owner[alias]}' and '{c['id']}'")
            alias_owner[alias] = c["id"]

    for sid in skills_by_id:
        if sid not in used_skills:
            report.warn(f"skill '{sid}' is not used by any career")


# ------------------------------------------------------------- resources ----

def check_resources(resources, skills_by_id, report):
    for sid, items in resources.items():
        if sid not in skills_by_id:
            report.error(f"resources: unknown skill '{sid}'")
        urls = set()
        for r in items:
            url = r.get("url", "")
            if not r.get("title"):
                report.error(f"resources '{sid}': entry without a title")
            if not url.startswith(("http://", "https://")):
                report.error(f"resources '{sid}': invalid url '{url}'")
            elif url.startswith("http://"):
                report.warn(f"resources '{sid}': not https: {url}")
            if url in urls:
                report.error(f"resources '{sid}': duplicate url {url}")
            urls.add(url)
            if r.get("type") not in RESOURCE_TYPES:
                report.error(f"resources '{sid}': type '{r.get('type')}' not in {sorted(RESOURCE_TYPES)}")
    for sid in skills_by_id:
        if not resources.get(sid):
            report.error(f"skill '{sid}' has no learning resources")


def check_links(resources, report):
    """HTTP-check every unique URL in parallel. Failures are warnings (sites can be flaky)."""
    urls = sorted({r["url"] for items in resources.values() for r in items})

    def probe(url):
        headers = {"User-Agent": "Mozilla/5.0 (PathPilot link checker)"}
        status = None
        for attempt in range(3):  # retry: one flaky connection shouldn't fail the run
            if attempt:
                time.sleep(2 * attempt)
            for method in ("HEAD", "GET"):  # some sites reject HEAD
                try:
                    req = urllib.request.Request(url, method=method, headers=headers)
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        return url, resp.status
                except urllib.error.HTTPError as e:
                    status = e.code
                except urllib.error.URLError as e:  # DNS, refused, TLS...
                    status = f"URLError: {e.reason}"
                except Exception as e:  # timeouts etc.
                    status = f"{type(e).__name__}: {e}"
            if status in (404, 410):  # definitely gone, no point retrying
                break
        return url, status

    print(f"Checking {len(urls)} links (this takes about a minute)...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        for url, status in pool.map(probe, urls):
            # 401/403/429 usually mean bot protection, not a dead page.
            if status in (401, 403, 429):
                report.warn(f"link blocked automated check ({status}): {url}")
            elif not (isinstance(status, int) and status < 400):
                report.error(f"broken link ({status}): {url}")


# -------------------------------------------------------------- synonyms ----

def check_synonyms(synonyms, skills_by_id, careers, report):
    interests = {i for c in careers for i in c.get("interests", [])}
    for term, sid in synonyms.get("skills", {}).items():
        if term != term.lower():
            report.error(f"synonym '{term}' must be lowercase")
        if sid not in skills_by_id:
            report.error(f"synonym '{term}' -> unknown skill '{sid}'")
    for term, interest in synonyms.get("interests", {}).items():
        if term != term.lower():
            report.error(f"interest synonym '{term}' must be lowercase")
        if interest not in interests:
            report.error(f"interest synonym '{term}' -> '{interest}' is not used by any career")


# ------------------------------------------------------------------ main ----

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check-links", action="store_true", help="verify resource URLs over the network")
    args = parser.parse_args()

    report = Report()
    skills = load("skills.json")["skills"]
    careers = load("careers.json")["careers"]
    resources = load("resources.json")["resources"]
    synonyms = load("synonyms.json")

    skills_by_id = check_skills(skills, report)
    cycle = find_cycle(skills_by_id)
    if cycle:
        report.error("prerequisite cycle: " + " -> ".join(cycle))
    check_careers(careers, skills_by_id, report)
    check_resources(resources, skills_by_id, report)
    check_synonyms(synonyms, skills_by_id, careers, report)
    if args.check_links:
        check_links(resources, report)

    # Summary
    n_resources = sum(len(v) for v in resources.values())
    print("PathPilot data summary")
    print(f"  careers:   {len(careers)}")
    print(f"  skills:    {len(skills)}")
    print(f"  resources: {n_resources}")
    print(f"  synonyms:  {len(synonyms.get('skills', {}))} skill, {len(synonyms.get('interests', {}))} interest")
    if not cycle:
        chain = longest_chain(skills_by_id)
        print(f"  longest prerequisite chain ({len(chain)}): {' -> '.join(chain)}")
    print("\n  Roadmap size per career:")
    for c in careers:
        ids = [s for stage in STAGES for s in c.get("stages", {}).get(stage, []) if s in skills_by_id]
        hours = sum(skills_by_id[s]["est_hours"] for s in ids)
        print(f"    {c['name']:<24} {len(ids):>2} skills  ~{hours} hrs")

    for w in report.warnings:
        print(f"WARNING: {w}")
    for e in report.errors:
        print(f"ERROR: {e}")
    if report.errors:
        print(f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        sys.exit(1)
    print(f"\nAll good: 0 errors, {len(report.warnings)} warning(s)")


if __name__ == "__main__":
    main()
