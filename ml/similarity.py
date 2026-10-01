"""Content-based matching: compare the user's TF-IDF vector with a 'profile' vector of each career."""

import numpy as np

from ml.kb import STAGES
from ml.nlp import tokenize


def cosine_similarity(A, B):
    """Cosine similarity between every row of A and every row of B -> shape (len(A), len(B))."""
    A_norm = np.linalg.norm(A, axis=1, keepdims=True)
    B_norm = np.linalg.norm(B, axis=1, keepdims=True)
    A = A / np.where(A_norm == 0, 1.0, A_norm)
    B = B / np.where(B_norm == 0, 1.0, B_norm)
    return A @ B.T


def career_document(career, kb):
    """Describe a career with the same kind of features a parsed user query produces."""
    skill_ids = [s for stage in STAGES for s in career["stages"][stage]]
    text = " ".join([career["name"], career["description"], *(kb.skills[s]["name"] for s in skill_ids)])
    return (tokenize(text)
            + [f"skill:{s}" for s in skill_ids]
            + [f"interest:{i}" for i in career["interests"]] * 2   # interests count double
            + [f"career:{career['id']}"])
