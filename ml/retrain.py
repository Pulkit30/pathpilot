"""Retrain the model with real user feedback.

Run:  python -m ml.retrain                 read 👍/👎 from MongoDB (MONGODB_URI in .env), retrain, save if better
      python -m ml.retrain --dry-run       train and compare, but don't save anything
      python -m ml.retrain --from-file f.json   read feedback from an exported JSON list instead of MongoDB

How feedback becomes training data:
  👍 on a career  ->  (the user's question, that career) is a new labelled example
  👎              ->  kept in the database for analysis, but not used as a label: it only says which
                      career is wrong, not which one is right
Safeguards:
  - duplicates are removed, and each user contributes at most MAX_PER_USER examples
  - questions identical to the hand-written test set are skipped, so the test stays honest
  - quality gate: the new model is saved only if it scores at least as well as the current one
"""

import argparse
import json
from collections import Counter

from ml.dataset import FEEDBACK_PROFILES_PATH, load_eval_queries, load_feedback_profiles
from ml.kb import load_kb
from ml.nlp import normalize
from ml.recommender import ARTIFACTS_DIR
from ml.train import save_artifacts, train_model

REPEAT = 3          # a real user's example counts like 3 synthetic ones
MAX_PER_USER = 20   # one very active (or malicious) user can't dominate the data
SYNTHETIC_TOLERANCE = 0.01  # allow at most a 1-point drop on the synthetic test


def load_feedback_from_mongo():
    from pymongo import MongoClient

    from backend.app.config import get_settings

    settings = get_settings()
    if not settings.mongodb_uri:
        raise SystemExit("MONGODB_URI is not set (add it to .env), or use --from-file")
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    try:
        return list(client[settings.mongodb_db]["feedback"].find({}, {"_id": 0}))
    finally:
        client.close()


def feedback_to_profiles(feedback, kb=None, repeat=REPEAT, max_per_user=MAX_PER_USER):
    """Turn raw feedback documents into training profiles: [{"text", "career", "source"}]."""
    kb = kb or load_kb()
    eval_texts = {normalize(q["text"]) for q in load_eval_queries()}
    seen, per_user, unique = set(), Counter(), []
    for fb in sorted(feedback, key=lambda f: str(f.get("created_at", ""))):
        text = (fb.get("query") or "").strip()
        key = (normalize(text), fb.get("career_id"))
        user = fb.get("user_id") or "anonymous"
        if (fb.get("rating") != 1 or not text or fb.get("career_id") not in kb.careers
                or key in seen or key[0] in eval_texts or per_user[user] >= max_per_user):
            continue
        seen.add(key)
        per_user[user] += 1
        unique.append({"text": text, "career": fb["career_id"], "source": "feedback"})
    return [p for p in unique for _ in range(repeat)]


def passes_quality_gate(new, old):
    """New model must be at least as good on hand-written queries and not worse on synthetic test."""
    if old is None:
        return True, "no previous model"
    checks = [
        ("handwritten top-1", new["handwritten_eval"]["blended_top1"], old["handwritten_eval"]["blended_top1"], 0.0),
        ("synthetic top-1", new["synthetic_test"]["blended_top1"], old["synthetic_test"]["blended_top1"],
         SYNTHETIC_TOLERANCE),
    ]
    failed = [f"{name} {n:.1%} < {o:.1%}" for name, n, o, tol in checks if n < o - tol]
    return not failed, "; ".join(failed) or "ok"


def main():
    parser = argparse.ArgumentParser(description="Retrain PathPilot with user feedback.")
    parser.add_argument("--from-file", help="JSON file with a list of feedback documents")
    parser.add_argument("--dry-run", action="store_true", help="evaluate only, don't save")
    parser.add_argument("--force", action="store_true", help="save even if the quality gate fails")
    args = parser.parse_args()

    if args.from_file:
        with open(args.from_file, encoding="utf-8") as f:
            feedback = json.load(f)
    else:
        feedback = load_feedback_from_mongo()
    ratings = Counter(fb.get("rating") for fb in feedback)
    print(f"Feedback: {len(feedback)} total ({ratings.get(1, 0)} 👍, {ratings.get(-1, 0)} 👎)")

    profiles = feedback_to_profiles(feedback)
    print(f"Usable 👍 examples: {len(profiles) // REPEAT} unique (x{REPEAT} weight = {len(profiles)} rows)")
    if not profiles:
        print("Nothing new to learn from yet. Collect some 👍 feedback first.")
        return
    if len(profiles) == len(load_feedback_profiles()) and not args.force:
        print("Same feedback examples as the current model; nothing to retrain. (Use --force to retrain anyway.)")
        return

    old_metrics = None
    meta_path = ARTIFACTS_DIR / "metadata.json"
    if meta_path.exists():
        old_metrics = json.loads(meta_path.read_text())["metrics"]

    print()
    rec, _, metadata = train_model(extra_profiles=profiles)
    ok, reason = passes_quality_gate(metadata["metrics"], old_metrics)
    print(f"\nQuality gate: {'PASSED' if ok else 'FAILED'} ({reason})")

    if args.dry_run:
        print("Dry run: nothing saved.")
    elif ok or args.force:
        with open(FEEDBACK_PROFILES_PATH, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "profiles": profiles}, f, indent=0, ensure_ascii=False)
        save_artifacts(rec, metadata)
        print(f"Saved new model and {FEEDBACK_PROFILES_PATH.name}. Restart the API to use it, then commit "
              "ml/artifacts/ and data/feedback_profiles.json.")
    else:
        print("Kept the current model. Use --force to save anyway.")


if __name__ == "__main__":
    main()
