"""Evaluate the saved model.

Run:  python -m ml.evaluate

Reports top-1 and top-3 accuracy for the classifier alone, similarity alone, and the blend, on
  - synthetic test split: held-out generated profiles (same style as training data)
  - hand-written eval set: realistic queries never used for training (the honest number)
and lists the hand-written queries the model got wrong.
"""

from collections import Counter

import numpy as np

from ml.nlp import parse

METHODS = ["softmax", "similarity", "blended"]


def topk_accuracy(P, y, k):
    topk = np.argsort(-P, axis=1)[:, :k]
    return float(np.mean([y[i] in topk[i] for i in range(len(y))]))


def evaluate_rows(rec, rows):
    """rows: [{"text": ..., "career": ...}] -> metrics dict."""
    index = {c: i for i, c in enumerate(rec.classes)}
    X = rec.vectorizer.transform([parse(r["text"]).features() for r in rows])
    y = np.array([index[r["career"]] for r in rows])
    s = rec.scores(X)
    result = {"n": len(rows)}
    for m in METHODS:
        result[f"{m}_top1"] = round(topk_accuracy(s[m], y, 1), 4)
        result[f"{m}_top3"] = round(topk_accuracy(s[m], y, 3), 4)
    pred = s["blended"].argmax(axis=1)
    result["misses"] = [(rows[i]["text"], rows[i]["career"], rec.classes[pred[i]])
                        for i in range(len(rows)) if pred[i] != y[i]]
    return result


def print_table(metrics):
    print(f"   {'dataset':<18} {'n':>4}  " + "  ".join(f"{m + ' top1/top3':>22}" for m in METHODS))
    for name, r in metrics.items():
        cells = "  ".join(f"{r[m + '_top1']:>10.1%} / {r[m + '_top3']:<9.1%}" for m in METHODS)
        print(f"   {name:<18} {r['n']:>4}  {cells}")


def main():
    from ml.dataset import load_eval_queries, load_profiles, split_profiles
    from ml.recommender import Recommender

    rec = Recommender.load()
    profiles = load_profiles()
    _, _, test_idx = split_profiles(profiles, rec.classes)
    metrics = {
        "synthetic_test": evaluate_rows(rec, [profiles[i] for i in test_idx]),
        "handwritten_eval": evaluate_rows(rec, load_eval_queries()),
    }
    print(f"Model: alpha={rec.alpha} (classifier weight), temperature={rec.temperature}\n")
    print_table(metrics)

    test = metrics["synthetic_test"]
    if test["misses"]:
        print("\nMost common confusions on synthetic test (expected -> predicted):")
        for (exp, got), n in Counter((e, g) for _, e, g in test["misses"]).most_common(5):
            print(f"   {n:>3}x  {exp} -> {got}")

    misses = metrics["handwritten_eval"]["misses"]
    print(f"\nHand-written queries predicted wrong (top-1): {len(misses)}")
    for text, exp, got in misses:
        print(f"   expected {exp:<22} got {got:<22} | {text}")


if __name__ == "__main__":
    main()
