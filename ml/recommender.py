"""Hybrid recommender: blends the softmax classifier with TF-IDF cosine similarity.

    final = alpha * P_softmax + (1 - alpha) * softmax(temperature * cosine_similarity)

The classifier learns patterns from training examples; the similarity score compares the user
directly with each career's description, which helps on wording the classifier never saw.
alpha and temperature are tuned on the validation set in train.py.
"""

import json
from pathlib import Path

import numpy as np

from ml.kb import load_kb
from ml.nlp import parse
from ml.similarity import career_document, cosine_similarity
from ml.softmax import SoftmaxClassifier, softmax
from ml.tfidf import TfidfVectorizer

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


class Recommender:
    def __init__(self, vectorizer, classifier, classes, alpha=0.7, temperature=10.0, kb=None):
        self.kb = kb or load_kb()
        self.vectorizer = vectorizer
        self.classifier = classifier
        self.classes = list(classes)
        self.alpha = alpha
        self.temperature = temperature
        docs = [career_document(self.kb.careers[c], self.kb) for c in self.classes]
        self.career_matrix = vectorizer.transform(docs)

    @classmethod
    def load(cls, artifacts_dir=ARTIFACTS_DIR):
        artifacts_dir = Path(artifacts_dir)
        with open(artifacts_dir / "metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        vectorizer = TfidfVectorizer.load(artifacts_dir / "tfidf.npz", artifacts_dir / "vocab.json")
        classifier = SoftmaxClassifier.load(artifacts_dir / "model.npz")
        return cls(vectorizer, classifier, meta["classes"], meta["alpha"], meta["temperature"])

    # ------------------------------------------------------------- scoring ----

    def scores(self, X):
        """All three score matrices for TF-IDF rows X, each of shape (n, n_careers)."""
        p_soft = self.classifier.predict_proba(X)
        p_sim = softmax(self.temperature * cosine_similarity(X, self.career_matrix))
        return {"softmax": p_soft, "similarity": p_sim,
                "blended": self.alpha * p_soft + (1 - self.alpha) * p_sim}

    def recommend(self, text, top_k=3, known_skills=None):
        """Top careers for a free-text query.

        known_skills: optional list of skill ids that replaces what the NLP detected
        (the frontend's editable skill chips).
        """
        q = parse(text)
        if known_skills is not None:
            q.known_skills = [s for s in known_skills if s in self.kb.skills]
            q.goal_skills = [s for s in q.goal_skills if s not in q.known_skills]

        X = self.vectorizer.transform([q.features()])
        if not X.any():
            return {"status": "need_more_info", "parsed": _parsed_dict(q), "recommendations": [],
                    "message": "Tell me a bit more: which skills you have, what you enjoy, or what you'd like to learn."}

        s = self.scores(X)
        blended = s["blended"][0]
        top = np.argsort(-blended)[:top_k]
        recs = [self._explain(self.classes[i], q, blended[i], s["softmax"][0, i], s["similarity"][0, i])
                for i in top]
        top_score = blended[top[0]]
        confidence = "high" if top_score >= 0.5 else "medium" if top_score >= 0.25 else "low"
        return {"status": "ok", "confidence": confidence, "parsed": _parsed_dict(q), "recommendations": recs}

    def _explain(self, career_id, q, score, p_soft, p_sim):
        career = self.kb.careers[career_id]
        required = self.kb.required_skills(career_id)
        relevant = set(required) | set(career.get("optional_skills", []))
        name = lambda sid: self.kb.skills[sid]["name"]

        reasons = []
        if career_id in q.careers:
            reasons.append("You mentioned this role")
        interests = [i for i in q.interests if i in career["interests"]]
        if interests:
            reasons.append("Matches your interest in " + ", ".join(interests))
        have = [s for s in q.known_skills if s in relevant]
        if have:
            reasons.append("You already know " + ", ".join(name(s) for s in have))
        wants = [s for s in q.goal_skills if s in relevant]
        if wants:
            reasons.append("Includes skills you want to learn: " + ", ".join(name(s) for s in wants))
        if not reasons:
            reasons.append("Closest match to how you described yourself")

        known_required = [s for s in required if s in q.known_skills]
        return {
            "career_id": career_id,
            "name": career["name"],
            "description": career["description"],
            "match": round(float(score) * 100, 1),
            "scores": {"classifier": round(float(p_soft), 4), "similarity": round(float(p_sim), 4)},
            "reasons": reasons,
            "skills_known": len(known_required),
            "skills_total": len(required),
            "demand": career["demand"],
            "salary_inr_lpa": career["salary_inr_lpa"],
        }


def _parsed_dict(q):
    return {"known_skills": q.known_skills, "goal_skills": q.goal_skills,
            "negated_skills": q.negated_skills, "interests": q.interests, "careers": q.careers}
