"""Train the PathPilot model and save it to ml/artifacts/.

Run:  python -m ml.train

Steps: load profiles -> parse text -> split train/val/test -> fit TF-IDF on train ->
       train softmax -> tune blend (alpha, temperature) on val -> report test metrics -> save.
"""

import json
from datetime import datetime, timezone

import numpy as np

from ml.dataset import load_eval_queries, load_profiles, split_profiles
from ml.evaluate import evaluate_rows, print_table
from ml.kb import load_kb
from ml.nlp import parse
from ml.recommender import ARTIFACTS_DIR, Recommender
from ml.softmax import SoftmaxClassifier
from ml.tfidf import TfidfVectorizer

HYPERPARAMS = {"min_df": 2, "lr": 0.5, "l2": 1e-5, "epochs": 100, "batch_size": 64, "momentum": 0.9}
ALPHAS = [round(a, 1) for a in np.arange(0.0, 1.01, 0.1)]
TEMPERATURES = [5.0, 10.0, 20.0, 40.0, 80.0, 160.0]


def log_loss(P, y):
    return float(-np.log(P[np.arange(len(y)), y] + 1e-12).mean())


def main():
    kb = load_kb()
    classes = kb.career_ids
    class_index = {c: i for i, c in enumerate(classes)}

    print("1. Loading and parsing training profiles")
    profiles = load_profiles()
    docs = [parse(p["text"]).features() for p in profiles]
    y = np.array([class_index[p["career"]] for p in profiles])
    train_idx, val_idx, test_idx = split_profiles(profiles, classes)
    print(f"   {len(profiles)} profiles -> train {len(train_idx)} / val {len(val_idx)} / test {len(test_idx)}")

    print("2. Fitting TF-IDF vectorizer (train split only)")
    vectorizer = TfidfVectorizer(min_df=HYPERPARAMS["min_df"]).fit([docs[i] for i in train_idx])
    X = vectorizer.transform(docs)
    print(f"   vocabulary: {len(vectorizer.vocab)} features")

    print("3. Training softmax classifier (gradient descent)")
    clf = SoftmaxClassifier(**{k: HYPERPARAMS[k] for k in ["lr", "l2", "epochs", "batch_size", "momentum"]})
    history = clf.fit(X[train_idx], y[train_idx], len(classes), X[val_idx], y[val_idx])

    print("4. Tuning blend of classifier + similarity on validation set")
    rec = Recommender(vectorizer, clf, classes, kb=kb)
    best = None
    for t in TEMPERATURES:
        rec.temperature = t
        s = rec.scores(X[val_idx])
        for a in ALPHAS:
            loss = log_loss(a * s["softmax"] + (1 - a) * s["similarity"], y[val_idx])
            if best is None or loss < best[0]:
                best = (loss, a, t)
    _, rec.alpha, rec.temperature = best
    print(f"   best alpha={rec.alpha} (classifier weight), temperature={rec.temperature}, val log-loss={best[0]:.4f}")

    print("5. Evaluating")
    test_rows = [profiles[i] for i in test_idx]
    metrics = {
        "synthetic_test": evaluate_rows(rec, test_rows),
        "handwritten_eval": evaluate_rows(rec, load_eval_queries()),
    }
    print_table(metrics)

    print("6. Saving artifacts")
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    clf.save(ARTIFACTS_DIR / "model.npz")
    vectorizer.save(ARTIFACTS_DIR / "tfidf.npz", ARTIFACTS_DIR / "vocab.json")
    metadata = {
        "version": 1,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "classes": classes,
        "alpha": rec.alpha,
        "temperature": rec.temperature,
        "hyperparams": HYPERPARAMS,
        "n_profiles": {"train": len(train_idx), "val": len(val_idx), "test": len(test_idx)},
        "vocab_size": len(vectorizer.vocab),
        "final_epoch": history[-1],
        "metrics": {name: {m: v for m, v in result.items() if m != "misses"} for name, result in metrics.items()},
    }
    with open(ARTIFACTS_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"   saved to {ARTIFACTS_DIR.relative_to(ARTIFACTS_DIR.parent.parent)}/")


if __name__ == "__main__":
    main()
