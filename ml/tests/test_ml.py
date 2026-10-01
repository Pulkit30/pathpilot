"""Unit tests for the ML engine.  Run:  python -m unittest discover -s ml/tests -t ."""

import math
import unittest

import numpy as np

from ml.kb import load_kb
from ml.nlp import parse, stem, tokenize
from ml.recommender import ARTIFACTS_DIR, Recommender
from ml.roadmap import build_roadmap, implied_known
from ml.softmax import SoftmaxClassifier, softmax
from ml.tfidf import TfidfVectorizer


class TestNLP(unittest.TestCase):
    def test_known_vs_goal_skills(self):
        q = parse("I know Python and SQL, and I want to learn machine learning.")
        self.assertEqual(q.known_skills, ["python", "sql"])
        self.assertEqual(q.goal_skills, ["machine_learning"])

    def test_negation(self):
        q = parse("I want to become a data scientist but I don't know python")
        self.assertIn("python", q.negated_skills)
        self.assertNotIn("python", q.known_skills)
        self.assertEqual(q.careers, ["data_scientist"])

    def test_synonyms_and_symbols(self):
        q = parse("js, ts, c++, c# and k8s")
        self.assertEqual(q.known_skills, ["javascript", "typescript", "cpp", "csharp", "kubernetes"])

    def test_dotted_names_are_not_sentence_breaks(self):
        q = parse("Familiar with React.js and Node.js")
        self.assertEqual(q.known_skills, ["react", "nodejs"])

    def test_interests(self):
        self.assertEqual(parse("I love maths and video games").interests, ["math", "games"])

    def test_career_alias_hides_inner_skill(self):
        q = parse("I want to be a machine learning engineer")
        self.assertEqual(q.careers, ["ml_engineer"])
        self.assertNotIn("machine_learning", q.skills)

    def test_stem_and_stopwords(self):
        self.assertEqual(stem("designing"), "design")
        self.assertEqual(stem("games"), "game")
        self.assertEqual(tokenize("I want to learn designing"), ["design"])


class TestTfidf(unittest.TestCase):
    def test_idf_and_normalisation(self):
        docs = [["a", "b"], ["a", "c"], ["a"]]
        vec = TfidfVectorizer().fit(docs)
        # idf = log((1 + N) / (1 + df)) + 1
        self.assertAlmostEqual(vec.idf[vec.vocab["a"]], math.log(4 / 4) + 1)
        self.assertAlmostEqual(vec.idf[vec.vocab["b"]], math.log(4 / 2) + 1)
        X = vec.transform(docs + [["unseen"]])
        np.testing.assert_allclose(np.linalg.norm(X[:3], axis=1), 1.0)
        self.assertFalse(X[3].any())  # unseen features are ignored -> zero row

    def test_rare_feature_weighs_more(self):
        vec = TfidfVectorizer().fit([["a", "b"], ["a", "c"], ["a"]])
        row = vec.transform([["a", "b"]])[0]
        self.assertGreater(row[vec.vocab["b"]], row[vec.vocab["a"]])


class TestSoftmax(unittest.TestCase):
    def test_softmax_rows_sum_to_one_and_are_stable(self):
        P = softmax(np.array([[1000.0, 1000.0], [-5.0, 5.0]]))
        np.testing.assert_allclose(P.sum(axis=1), 1.0)
        np.testing.assert_allclose(P[0], [0.5, 0.5])

    def test_gradient_matches_numerical_derivative(self):
        """Gradient check: analytic gradients vs finite differences of the loss."""
        rng = np.random.default_rng(0)
        X, y = rng.normal(size=(8, 5)), rng.integers(0, 3, size=8)
        clf = SoftmaxClassifier(l2=0.1)
        clf.W, clf.b = rng.normal(size=(5, 3)) * 0.1, rng.normal(size=3) * 0.1
        dW, db = clf.gradients(X, y)
        eps = 1e-6
        for param, grad in [(clf.W, dW), (clf.b, db)]:
            for idx in np.ndindex(param.shape):
                old = param[idx]
                param[idx] = old + eps
                up = clf.loss(X, y)
                param[idx] = old - eps
                down = clf.loss(X, y)
                param[idx] = old
                self.assertAlmostEqual((up - down) / (2 * eps), grad[idx], places=6)

    def test_learns_separable_data(self):
        rng = np.random.default_rng(1)
        centers = np.eye(3) * 4
        y = rng.integers(0, 3, size=300)
        X = centers[y] + rng.normal(size=(300, 3))
        clf = SoftmaxClassifier(lr=0.1, epochs=30)
        history = clf.fit(X, y, 3, verbose=False)
        self.assertLess(history[-1]["train_loss"], history[0]["train_loss"])
        self.assertGreater((clf.predict(X) == y).mean(), 0.95)


class TestRoadmap(unittest.TestCase):
    def setUp(self):
        self.kb = load_kb()

    def test_every_roadmap_respects_prerequisites(self):
        for cid in self.kb.career_ids:
            steps = build_roadmap(cid, kb=self.kb)["steps"]
            position = {s["skill_id"]: s["step"] for s in steps}
            for s in steps:
                for p in s["prereqs"]:
                    self.assertLess(position[p], s["step"], f"{cid}: {p} must come before {s['skill_id']}")

    def test_known_and_implied_skills_are_skipped(self):
        road = build_roadmap("data_scientist", ["pandas"], kb=self.kb)
        todo = {s["skill_id"] for s in road["steps"]}
        self.assertNotIn("pandas", todo)
        self.assertNotIn("python", todo)  # implied by pandas
        implied = {k["skill_id"]: k["implied"] for k in road["already_known"]}
        self.assertEqual(implied, {"python": True, "pandas": False})

    def test_implied_known_is_transitive(self):
        self.assertTrue({"rag", "vector_databases", "embeddings", "nlp", "machine_learning", "python"}
                        <= implied_known({"rag"}, self.kb))

    def test_hours_and_weeks(self):
        road = build_roadmap("qa_engineer", hours_per_week=5, kb=self.kb)
        self.assertEqual(road["total_hours"], sum(s["est_hours"] for s in road["steps"]))
        self.assertEqual(road["est_weeks"], math.ceil(road["total_hours"] / 5))

    def test_unknown_career(self):
        with self.assertRaises(ValueError):
            build_roadmap("astronaut", kb=self.kb)


@unittest.skipUnless((ARTIFACTS_DIR / "model.npz").exists(), "run python -m ml.train first")
class TestRecommender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = Recommender.load()

    def test_obvious_queries(self):
        cases = {
            "I want to build chatbots with LLMs and RAG": "ai_engineer",
            "I love video games and know Unity": "game_developer",
            "I know SQL and Excel and make dashboards in Power BI": "data_analyst",
            "Figma, wireframes, prototypes and user research": "ui_ux_designer",
        }
        for text, expected in cases.items():
            self.assertEqual(self.rec.recommend(text)["recommendations"][0]["career_id"], expected, text)

    def test_scores_are_probabilities(self):
        recs = self.rec.recommend("I know python", top_k=15)["recommendations"]
        self.assertAlmostEqual(sum(r["match"] for r in recs), 100.0, delta=0.5)

    def test_empty_query_asks_for_more(self):
        self.assertEqual(self.rec.recommend("hello there")["status"], "need_more_info")

    def test_skill_chips_override_detected_skills(self):
        result = self.rec.recommend("I like data", known_skills=["sql", "excel"])
        self.assertEqual(result["parsed"]["known_skills"], ["sql", "excel"])


if __name__ == "__main__":
    unittest.main()
