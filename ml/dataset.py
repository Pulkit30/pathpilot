"""Loading training profiles / evaluation queries and making a reproducible train/val/test split."""

import json

import numpy as np

from ml.kb import DATA_DIR

PROFILES_PATH = DATA_DIR / "training_profiles.json"
EVAL_PATH = DATA_DIR / "eval_queries.json"
SPLIT_SEED = 7


def load_profiles():
    if not PROFILES_PATH.exists():
        from ml.generate_data import generate
        rows = generate()
        with open(PROFILES_PATH, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "profiles": rows}, f, indent=0, ensure_ascii=False)
    with open(PROFILES_PATH, encoding="utf-8") as f:
        return json.load(f)["profiles"]


def load_eval_queries():
    with open(EVAL_PATH, encoding="utf-8") as f:
        return json.load(f)["queries"]


def stratified_split(labels, fractions=(0.7, 0.15, 0.15), seed=SPLIT_SEED):
    """Split indices so every career keeps the same proportions in train / val / test."""
    rng = np.random.default_rng(seed)
    labels = np.asarray(labels)
    parts = [[] for _ in fractions]
    for label in np.unique(labels):
        idx = rng.permutation(np.flatnonzero(labels == label))
        cuts = np.cumsum([round(f * len(idx)) for f in fractions[:-1]])
        for part, chunk in zip(parts, np.split(idx, cuts)):
            part.extend(chunk.tolist())
    return [np.array(sorted(p)) for p in parts]


def split_profiles(profiles, classes):
    """The one train/val/test split used by both train.py and evaluate.py."""
    index = {c: i for i, c in enumerate(classes)}
    return stratified_split([index[p["career"]] for p in profiles])
