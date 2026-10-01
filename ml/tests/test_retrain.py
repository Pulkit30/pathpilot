"""Tests for turning feedback into training data and the retraining quality gate."""

import unittest

from ml.dataset import load_eval_queries
from ml.retrain import feedback_to_profiles, passes_quality_gate


def fb(query, career="game_developer", rating=1, user="u1", t="2026-10-01"):
    return {"query": query, "career_id": career, "rating": rating, "user_id": user, "created_at": t}


class TestFeedbackToProfiles(unittest.TestCase):
    def test_only_thumbs_up_become_examples(self):
        rows = feedback_to_profiles([fb("I love games"), fb("I hate maths", rating=-1)], repeat=1)
        self.assertEqual(rows, [{"text": "I love games", "career": "game_developer", "source": "feedback"}])

    def test_duplicates_removed_ignoring_case_and_spacing(self):
        rows = feedback_to_profiles([fb("I love games"), fb("i love   GAMES", user="u2")], repeat=1)
        self.assertEqual(len(rows), 1)

    def test_same_text_for_two_careers_is_kept(self):
        rows = feedback_to_profiles([fb("python and math"), fb("python and math", career="data_scientist")], repeat=1)
        self.assertEqual({r["career"] for r in rows}, {"game_developer", "data_scientist"})

    def test_unknown_careers_and_empty_queries_skipped(self):
        self.assertEqual(feedback_to_profiles([fb("x", career="astronaut"), fb("   ")], repeat=1), [])

    def test_handwritten_eval_queries_never_leak_into_training(self):
        q = load_eval_queries()[0]
        self.assertEqual(feedback_to_profiles([fb(q["text"], career=q["career"])], repeat=1), [])

    def test_per_user_cap(self):
        many = [fb(f"games idea {i}") for i in range(30)]
        self.assertEqual(len(feedback_to_profiles(many, repeat=1, max_per_user=5)), 5)

    def test_repeat_weight(self):
        self.assertEqual(len(feedback_to_profiles([fb("I love games")], repeat=3)), 3)


class TestQualityGate(unittest.TestCase):
    OLD = {"handwritten_eval": {"blended_top1": 0.95}, "synthetic_test": {"blended_top1": 0.94}}

    def gate(self, hand, syn):
        new = {"handwritten_eval": {"blended_top1": hand}, "synthetic_test": {"blended_top1": syn}}
        return passes_quality_gate(new, self.OLD)[0]

    def test_better_or_equal_passes(self):
        self.assertTrue(self.gate(0.97, 0.95))
        self.assertTrue(self.gate(0.95, 0.94))

    def test_worse_on_handwritten_fails(self):
        self.assertFalse(self.gate(0.93, 0.99))

    def test_small_synthetic_drop_tolerated_big_drop_fails(self):
        self.assertTrue(self.gate(0.95, 0.935))
        self.assertFalse(self.gate(0.95, 0.90))

    def test_first_model_always_passes(self):
        self.assertTrue(passes_quality_gate({}, None)[0])


if __name__ == "__main__":
    unittest.main()
