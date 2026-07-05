"""
tests/test_retrieval.py

Unit tests for PrecedentCapsule + SimplePrecedentStore (paper §4.3).

Coverage:
  - Capsule construction + immutability
  - Similarity helpers (token_jaccard, exact_match_similarity)
  - Store CRUD
  - Retrieval ranking (highest raw score first, tie-break by capsule_id)
  - Weight normalization (Σ w_i = 1) and w_max cap
  - lambda_s + lambda_a + lambda_g must sum to 1
  - Zero raw score fallback (uniform weights)
"""

from __future__ import annotations

import unittest

from precedentguard.retrieval import (
    PrecedentCapsule,
    RetrievedPrecedent,
    SimplePrecedentStore,
    exact_match_similarity,
    token_jaccard,
)
from precedentguard.types import Provenance


def mk_cap(cid: str, summary: str, action: str,
           label: int = 0, subgraph: str = "") -> PrecedentCapsule:
    return PrecedentCapsule(
        capsule_id=cid,
        trajectory_summary=summary,
        proposed_action=action,
        audited_label=label,
        subgraph_signature=subgraph,
    )


# ----------------------------------------------------------------------
# Similarity helpers
# ----------------------------------------------------------------------


class TestSimilarityHelpers(unittest.TestCase):

    def test_token_jaccard_identical(self):
        self.assertAlmostEqual(
            token_jaccard("hello world foo", "hello world foo"), 1.0
        )

    def test_token_jaccard_disjoint(self):
        self.assertAlmostEqual(
            token_jaccard("abc def", "ghi jkl"), 0.0
        )

    def test_token_jaccard_partial(self):
        # {a, b, c} vs {b, c, d} => inter=2, union=4, J=0.5
        self.assertAlmostEqual(token_jaccard("a b c", "b c d"), 0.5)

    def test_token_jaccard_case_insensitive(self):
        self.assertAlmostEqual(token_jaccard("Hello World", "hello world"), 1.0)

    def test_token_jaccard_empty_both(self):
        # Convention: both empty -> 1.0
        self.assertAlmostEqual(token_jaccard("", ""), 1.0)

    def test_exact_match_true(self):
        self.assertAlmostEqual(
            exact_match_similarity("send-email", "send-email"), 1.0
        )
        self.assertAlmostEqual(
            exact_match_similarity(" Send-Email ", "send-email"), 1.0
        )

    def test_exact_match_falls_back(self):
        # Not exact -> jaccard on tokens
        # "send email now" vs "send email later" -> {send,email,now}∩{send,email,later}=2 / union=4 = 0.5
        self.assertAlmostEqual(
            exact_match_similarity("send email now", "send email later"), 0.5
        )


# ----------------------------------------------------------------------
# PrecedentCapsule
# ----------------------------------------------------------------------


class TestPrecedentCapsule(unittest.TestCase):

    def test_construction_defaults(self):
        cap = PrecedentCapsule(
            capsule_id="c1", trajectory_summary="summary",
            proposed_action="a1", audited_label=1,
        )
        self.assertEqual(cap.capsule_id, "c1")
        self.assertEqual(cap.audited_label, 1)
        self.assertEqual(cap.justification, "")
        self.assertIsInstance(cap.trust, Provenance)

    def test_frozen(self):
        cap = mk_cap("c1", "s", "a")
        with self.assertRaises(Exception):
            cap.capsule_id = "c2"  # type: ignore[misc]


class TestRetrievedPrecedent(unittest.TestCase):

    def test_out_of_range_weight_rejected(self):
        cap = mk_cap("c1", "s", "a")
        with self.assertRaises(ValueError):
            RetrievedPrecedent(cap, 1.5)
        with self.assertRaises(ValueError):
            RetrievedPrecedent(cap, -0.1)

    def test_boundary_weights_ok(self):
        cap = mk_cap("c1", "s", "a")
        RetrievedPrecedent(cap, 0.0)
        RetrievedPrecedent(cap, 1.0)  # boundary OK


# ----------------------------------------------------------------------
# SimplePrecedentStore
# ----------------------------------------------------------------------


class TestStoreConstruction(unittest.TestCase):

    def test_default_lambdas_sum_to_one(self):
        store = SimplePrecedentStore()
        self.assertAlmostEqual(
            store.lambda_s + store.lambda_a + store.lambda_g, 1.0
        )

    def test_lambdas_not_summing_to_one_rejected(self):
        with self.assertRaises(ValueError):
            SimplePrecedentStore(lambda_s=0.5, lambda_a=0.3, lambda_g=0.3)

    def test_negative_lambda_rejected(self):
        with self.assertRaises(ValueError):
            SimplePrecedentStore(lambda_s=-0.1, lambda_a=0.6, lambda_g=0.5)

    def test_wmax_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            SimplePrecedentStore(w_max=0.0)
        with self.assertRaises(ValueError):
            SimplePrecedentStore(w_max=1.5)


class TestStoreCRUD(unittest.TestCase):

    def test_add_and_get(self):
        store = SimplePrecedentStore()
        cap = mk_cap("c1", "s", "a")
        store.add(cap)
        self.assertEqual(len(store), 1)
        self.assertIn("c1", store)
        self.assertIs(store.get("c1"), cap)

    def test_duplicate_id_rejected(self):
        store = SimplePrecedentStore()
        store.add(mk_cap("c1", "s", "a"))
        with self.assertRaises(ValueError):
            store.add(mk_cap("c1", "s2", "a2"))

    def test_add_many(self):
        store = SimplePrecedentStore()
        store.add_many([mk_cap(f"c{i}", f"s{i}", "a") for i in range(5)])
        self.assertEqual(len(store), 5)


class TestRetrievalRanking(unittest.TestCase):

    def test_ranked_by_similarity(self):
        store = SimplePrecedentStore(lambda_s=1.0, lambda_a=0.0, lambda_g=0.0)
        store.add(mk_cap("c1", "read email account", "send-email"))
        store.add(mk_cap("c2", "delete file backup", "delete-file"))
        store.add(mk_cap("c3", "read email inbox", "send-email"))
        # Query most similar to c1 and c3 (share "read email")
        results = store.retrieve(
            query_summary="read email history",
            query_action="send-email",
            top_k=3,
        )
        self.assertEqual(len(results), 3)
        # Top two should be c1 and c3 (both share 'read email' tokens)
        top_ids = {results[0].capsule.capsule_id, results[1].capsule.capsule_id}
        self.assertEqual(top_ids, {"c1", "c3"})

    def test_top_k_limits_result_count(self):
        store = SimplePrecedentStore()
        for i in range(10):
            store.add(mk_cap(f"c{i}", f"summary {i}", "action"))
        results = store.retrieve("summary 1", "action", top_k=3)
        self.assertEqual(len(results), 3)

    def test_weights_sum_to_one(self):
        store = SimplePrecedentStore()
        for i in range(5):
            store.add(mk_cap(f"c{i}", f"summary {i}", "action"))
        results = store.retrieve("summary 1", "action", top_k=5)
        total = sum(r.weight for r in results)
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_w_max_cap_enforced(self):
        # With w_max=0.4 and one very similar precedent, cap must bind
        store = SimplePrecedentStore(w_max=0.4)
        store.add(mk_cap("dominant", "exactly this query", "action"))
        # Add 4 dissimilar ones so raw scores are near zero
        for i in range(4):
            store.add(mk_cap(f"c{i}", "xyz", "zzz"))
        results = store.retrieve("exactly this query", "action", top_k=5)
        for r in results:
            self.assertLessEqual(r.weight, 0.4 + 1e-9,
                                 f"{r.capsule.capsule_id}: w={r.weight}")
        self.assertAlmostEqual(sum(r.weight for r in results), 1.0, places=6)

    def test_zero_similarity_falls_back_to_uniform(self):
        store = SimplePrecedentStore(
            lambda_s=1.0, lambda_a=0.0, lambda_g=0.0,
        )
        store.add(mk_cap("c1", "!!!", "$$$"))
        store.add(mk_cap("c2", "###", "@@@"))
        results = store.retrieve("query_with_no_overlap", "act_no_overlap",
                                 top_k=2)
        self.assertEqual(len(results), 2)
        for r in results:
            # Uniform with cap: min(w_max, 1/2) = 0.5 (default w_max=0.5)
            self.assertAlmostEqual(r.weight, 0.5, places=6)

    def test_deterministic_tie_break(self):
        # Same summary and action across two capsules -> same raw score;
        # tie-break should use capsule_id ascending
        store = SimplePrecedentStore()
        store.add(mk_cap("b", "same summary", "act"))
        store.add(mk_cap("a", "same summary", "act"))
        results = store.retrieve("same summary", "act", top_k=2)
        # Sort by (-score, capsule_id) => "a" before "b"
        self.assertEqual(results[0].capsule.capsule_id, "a")
        self.assertEqual(results[1].capsule.capsule_id, "b")

    def test_empty_store_returns_empty(self):
        store = SimplePrecedentStore()
        self.assertEqual(store.retrieve("any", "any"), [])

    def test_top_k_zero_rejected(self):
        store = SimplePrecedentStore()
        store.add(mk_cap("c1", "s", "a"))
        with self.assertRaises(ValueError):
            store.retrieve("q", "a", top_k=0)


class TestRawScore(unittest.TestCase):
    """Sanity-check the weighted combination in §4.3."""

    def test_pure_text_score(self):
        store = SimplePrecedentStore(lambda_s=1.0, lambda_a=0.0, lambda_g=0.0)
        cap = mk_cap("c1", "hello world", "some-action")
        # Query summary identical -> text_sim = 1.0 -> raw = 1.0
        self.assertAlmostEqual(
            store.raw_score(cap, "hello world", "different-action"), 1.0
        )

    def test_pure_action_score(self):
        store = SimplePrecedentStore(lambda_s=0.0, lambda_a=1.0, lambda_g=0.0)
        cap = mk_cap("c1", "summary", "send-email")
        self.assertAlmostEqual(
            store.raw_score(cap, "unrelated", "send-email"), 1.0
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
