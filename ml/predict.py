"""Ask PathPilot from the terminal.

Run:  python -m ml.predict "I know python and like math, I want to work in AI"
      python -m ml.predict "I like designing apps" --hours 5 --career ui_ux_designer
      python -m ml.predict "..." --json      (raw output, the shape the API will return)
"""

import argparse
import json

from ml.recommender import Recommender
from ml.roadmap import build_roadmap


def main():
    parser = argparse.ArgumentParser(description="Get career recommendations and a roadmap.")
    parser.add_argument("query", help="describe your skills, interests and goals")
    parser.add_argument("--top", type=int, default=3, help="number of careers to show")
    parser.add_argument("--hours", type=int, default=10, help="study hours per week")
    parser.add_argument("--career", help="build the roadmap for this career id instead of the top match")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args()

    rec = Recommender.load()
    result = rec.recommend(args.query, top_k=args.top)
    if result["status"] != "ok":
        print(result["message"])
        return

    career_id = args.career or result["recommendations"][0]["career_id"]
    roadmap = build_roadmap(career_id, result["parsed"]["known_skills"], args.hours)
    if args.json:
        print(json.dumps({"recommendation": result, "roadmap": roadmap}, indent=2))
        return

    p = result["parsed"]
    print("\nWhat I understood")
    for label, key in [("Skills you know", "known_skills"), ("Want to learn", "goal_skills"),
                       ("Don't know", "negated_skills"), ("Interests", "interests"), ("Roles mentioned", "careers")]:
        if p[key]:
            print(f"  {label:<16} {', '.join(p[key])}")

    print(f"\nTop careers  (confidence: {result['confidence']})")
    for i, r in enumerate(result["recommendations"], 1):
        print(f"  {i}. {r['name']:<24} {r['match']:>5.1f}% match   "
              f"[classifier {r['scores']['classifier']:.2f} | similarity {r['scores']['similarity']:.2f}]")
        for reason in r["reasons"]:
            print(f"       - {reason}")

    print(f"\nRoadmap: {roadmap['career_name']}  "
          f"({len(roadmap['steps'])} skills, ~{roadmap['total_hours']} hrs, "
          f"~{roadmap['est_weeks']} weeks at {roadmap['hours_per_week']} hrs/week)")
    if roadmap["already_known"]:
        names = [k["name"] + (" (implied)" if k["implied"] else "") for k in roadmap["already_known"]]
        print(f"  Skipping, already known: {', '.join(names)}")
    stage = None
    for s in roadmap["steps"]:
        if s["stage"] != stage:
            stage = s["stage"]
            print(f"\n  [{stage.upper()}]")
        first = s["resources"][0]["url"] if s["resources"] else ""
        print(f"  {s['step']:>2}. {s['name']:<40} ~{s['est_hours']:>2} hrs   {first}")
    if roadmap["optional_skills"]:
        print(f"\n  Optional extras: {', '.join(o['name'] for o in roadmap['optional_skills'])}")
    print()


if __name__ == "__main__":
    main()
