import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from precedentguard import NodeType


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_real_backbone_eval.py"
)
SPEC = importlib.util.spec_from_file_location("run_real_backbone_eval", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RunRealBackboneEvalTests(unittest.TestCase):
    def test_normalize_row_preserves_trajectory(self):
        raw = {
            "id": "ex-1",
            "intent": "Find the latest emails and summarize them.",
            "label": "safe",
            "metadata": {"category": "Productivity", "name": "email-summary"},
            "trajectory": [
                {
                    "tool": "get_latest_emails",
                    "action": "tool_request::email_fetch",
                    "result": "tool_plan::email_fetch",
                }
            ],
        }

        normalized = MODULE.normalize_row(raw)

        self.assertEqual(normalized["subset"], "harmless_benign")
        self.assertEqual(normalized["category"], "Productivity")
        self.assertEqual(len(normalized["trajectory"]), 1)

    def test_infer_trajectory_node_type_maps_common_event_types(self):
        self.assertEqual(
            MODULE.infer_trajectory_node_type(
                {
                    "tool": "query_google_search",
                    "action": "tool_request::web_search",
                    "result": "tool_result::web_search",
                }
            ),
            NodeType.RETRIEVAL,
        )
        self.assertEqual(
            MODULE.infer_trajectory_node_type(
                {
                    "tool": "get_latest_emails",
                    "action": "tool_request::email_fetch",
                    "result": "tool_result::email_fetch",
                }
            ),
            NodeType.MEMORY,
        )
        self.assertEqual(
            MODULE.infer_trajectory_node_type(
                {
                    "tool": "assistant",
                    "action": "assistant_reasoning",
                    "result": "tool_plan::email_reply",
                }
            ),
            NodeType.OBSERVATION,
        )
        self.assertEqual(
            MODULE.infer_trajectory_node_type(
                {
                    "tool": "paypal_transfer",
                    "action": "tool_request::money_transfer",
                    "result": "tool_result::money_transfer",
                }
            ),
            NodeType.TOOL_RETURN,
        )

    def test_build_eig_handles_empty_trajectory(self):
        eig, action_id = MODULE.build_eig("ex-empty", "Send a benign update.", [])

        self.assertEqual(action_id, "ex-empty-action")
        self.assertIn("ex-empty-intent", eig.nodes)
        self.assertIn("ex-empty-action", eig.nodes)
        self.assertEqual(eig.parents_of(action_id), ["ex-empty-intent"])

    def test_build_eig_retains_payload_for_trajectory_nodes(self):
        trajectory = [
            {
                "tool": "query_google_search",
                "action": "tool_request::web_search",
                "result": "tool_result::web_search",
            },
            {
                "tool": "assistant",
                "action": "assistant_reasoning",
                "result": "tool_plan::summarize",
            },
        ]

        eig, _ = MODULE.build_eig("ex-payload", "Summarize benign search results.", trajectory)

        retrieval_node = eig.nodes["ex-payload-traj-0"]
        observation_node = eig.nodes["ex-payload-traj-1"]
        self.assertEqual(retrieval_node.node_type, NodeType.RETRIEVAL)
        self.assertEqual(observation_node.node_type, NodeType.OBSERVATION)
        self.assertIn("retrieve via search the public web with Google", retrieval_node.payload)
        self.assertIn("query: web search.", retrieval_node.payload)
        self.assertIn("observation via assistant internal planning or reasoning step", observation_node.payload)
        self.assertIn("result: summarize.", observation_node.payload)
        self.assertNotEqual(retrieval_node.payload, retrieval_node.content_hash)

    def test_render_trajectory_event_payload_distinguishes_query_and_result(self):
        payload = MODULE._render_trajectory_event_payload(
            {
                "tool": "query_google_search",
                "action": "tool_request::social_broadcast",
                "result": "tool_result::matching_posts",
            }
        )

        self.assertIn("retrieve via search the public web with Google", payload)
        self.assertIn("query:", payload)
        self.assertIn("result:", payload)

    def test_build_retrieval_texts_strips_hint_and_keeps_trajectory_summary(self):
        summary, action = MODULE.build_retrieval_texts(
            "Do a benign thing.\n\nHint: use tool_a first.",
            [
                {
                    "tool": "post_on_x",
                    "action": "tool_request::social_broadcast::step_1_of_1",
                    "result": "tool_plan::social_broadcast::step_1_of_1",
                }
            ],
        )

        self.assertNotIn("Hint:", summary)
        self.assertIn("Trajectory:", summary)
        self.assertIn("publish a public post on X", action)

    def test_leave_one_base_task_out_excludes_all_variants_of_same_base(self):
        """Regression for Day 10 audit BLOCKER-1: LOBTO must strip every variant
        that shares the held-out AgentHarm base task id, not just the exact id.
        """
        rows = [
            {"id": "1-1", "prompt": "p1a", "subset": "harmful", "name": "", "trajectory": []},
            {"id": "1-2", "prompt": "p1b", "subset": "harmful", "name": "", "trajectory": []},
            {"id": "1-3", "prompt": "p1c", "subset": "harmless_benign", "name": "", "trajectory": []},
            {"id": "2-1", "prompt": "p2", "subset": "harmless_benign", "name": "", "trajectory": []},
        ]
        store = MODULE.make_leave_one_base_task_out_precedent_store(
            rows, scope="agentharm", held_out_example_id="1-1",
        )
        for held_variant in rows[:3]:
            with self.assertRaises(KeyError):
                store.get(MODULE.precedent_capsule_id(held_variant))
        self.assertIsNotNone(store.get(MODULE.precedent_capsule_id(rows[3])))

    def test_deprecated_leave_one_out_helper_raises(self):
        with self.assertRaises(RuntimeError):
            MODULE.make_leave_one_out_precedent_store(
                [], scope="agentharm", held_out_example_id="1-1",
            )

    def test_trust_variant_no_provenance_is_unattested(self):
        rows = [{"id": "1-1", "prompt": "p", "subset": "harmless_benign", "name": "", "trajectory": []}]
        store = MODULE.make_precedent_store(
            rows, scope="agentharm", trust_variant="no_provenance",
        )
        capsule = store.get(MODULE.precedent_capsule_id(rows[0]))
        self.assertFalse(
            capsule.trust.is_attested(
                current_scope="agentharm",
                accepted_policy_versions=frozenset({"v1"}),
            )
        )

    def test_subgraph_signature_is_multiset_of_node_types(self):
        trajectory_a = [
            {"tool": "get_latest_emails", "action": "a", "result": "r"},
            {"tool": "query_google_search", "action": "q", "result": "r"},
        ]
        trajectory_b = list(reversed(trajectory_a))
        sig_a = MODULE._trajectory_subgraph_signature(trajectory_a)
        sig_b = MODULE._trajectory_subgraph_signature(trajectory_b)
        self.assertEqual(sig_a, sig_b)
        self.assertTrue(sig_a)
        self.assertNotEqual(sig_a, MODULE._trajectory_subgraph_signature([]))

    def _build_toy_env(self):
        """Reusable minimal EIG + guard fixture for new-baseline unit tests."""
        eig, action_id = MODULE.build_eig(
            "1-1",
            "Do a benign task.",
            [
                {"tool": "get_latest_emails", "action": "a", "result": "r"},
                {"tool": "query_google_search", "action": "q", "result": "r"},
            ],
        )

        class FakeBackend:
            def __call__(self, eig, target_action_id, view, precedents=None):
                score = 0.05
                # Any non-empty precedent list contributes.
                if precedents:
                    score += 0.03 * len(precedents)
                # CIP-style cue node injection is visible in the view.
                if any(
                    getattr(v, "content_hash", "").startswith("cip-cue-")
                    for v in view.values()
                ):
                    score += 0.02
                return score

        guard_no_store = MODULE.make_guard(
            FakeBackend(),
            store=None,
            top_k=1,
            retrieval_strategy="vanilla",
            precedent_safe_beta_scale=1.0,
            precedent_unsafe_beta_scale=1.0,
        )
        return eig, action_id, guard_no_store

    def test_flattened_trajectory_baseline_returns_score_no_precedents(self):
        eig, action_id, guard = self._build_toy_env()
        score, capsules = MODULE.flattened_trajectory_score(guard, eig, action_id)
        self.assertGreater(score, 0.0)
        self.assertEqual(capsules, [])

    def test_cip_style_baseline_injects_cue_node(self):
        eig, action_id, guard = self._build_toy_env()
        score_flat, _ = MODULE.flattened_trajectory_score(guard, eig, action_id)
        score_cip, _ = MODULE.cip_style_score(guard, eig, action_id)
        # FakeBackend adds +0.02 when a cip-cue node is present, so the CIP
        # baseline must strictly exceed the flattened baseline.
        self.assertGreater(score_cip, score_flat)

    def test_sequential_graph_baseline_narrows_parent_set(self):
        eig, action_id, guard = self._build_toy_env()
        # PG-full sees all mutable ancestors; sequential_graph sees only one.
        full_ancestors = eig.mutable_ancestors_of(action_id)
        self.assertGreater(len(full_ancestors), 1)
        decision, _ = MODULE.sequential_graph_score(guard, eig, action_id)
        self.assertLessEqual(len(decision.parent_ids), 1)

    def test_random_graph_baseline_is_seed_deterministic(self):
        eig, action_id, guard = self._build_toy_env()
        decision_1, _ = MODULE.random_graph_score(guard, eig, action_id, seed=42)
        decision_2, _ = MODULE.random_graph_score(guard, eig, action_id, seed=42)
        self.assertEqual(decision_1.parent_ids, decision_2.parent_ids)
        # A different seed can, but is not required to, yield different parents.

    def test_raw_rag_concat_uses_precedents_but_no_counterfactual(self):
        eig, action_id, _ = self._build_toy_env()

        class FakeBackend:
            def __call__(self, eig, target_action_id, view, precedents=None):
                return 0.10 + 0.05 * len(precedents or [])

        rows = [
            {"id": "9-1", "prompt": "p", "subset": "harmless_benign", "name": "", "trajectory": []},
        ]
        store = MODULE.make_precedent_store(rows, scope="agentharm")
        guard = MODULE.make_guard(
            FakeBackend(),
            store=store,
            top_k=1,
            retrieval_strategy="vanilla",
            precedent_safe_beta_scale=1.0,
            precedent_unsafe_beta_scale=1.0,
        )
        score, capsules = MODULE.raw_rag_concat_score(guard, eig, action_id)
        self.assertEqual(len(capsules), 1)
        self.assertGreater(score, 0.10)

    def test_harmful_precedent_capsule_is_also_attested(self):
        rows = [
            {"id": "ex-h", "prompt": "harm", "subset": "harmful", "name": "", "trajectory": []},
        ]
        store = MODULE.make_precedent_store(rows, scope="agentharm")
        capsule = store.get(MODULE.precedent_capsule_id(rows[0]))
        self.assertTrue(
            capsule.trust.is_attested(
                current_scope="agentharm",
                accepted_policy_versions=frozenset({"v1"}),
            )
        )

    def test_make_backend_honors_device_and_dtype_env(self):
        original_device = os.environ.get("PG_BACKEND_DEVICE")
        original_dtype = os.environ.get("PG_BACKEND_DTYPE")
        try:
            os.environ["PG_BACKEND_DEVICE"] = "cuda"
            os.environ["PG_BACKEND_DTYPE"] = "float16"
            backend = MODULE.make_backend("llama_guard", "meta-llama/Llama-Guard-3-1B")
        finally:
            if original_device is None:
                os.environ.pop("PG_BACKEND_DEVICE", None)
            else:
                os.environ["PG_BACKEND_DEVICE"] = original_device
            if original_dtype is None:
                os.environ.pop("PG_BACKEND_DTYPE", None)
            else:
                os.environ["PG_BACKEND_DTYPE"] = original_dtype

        self.assertEqual(backend.device, "cuda")
        self.assertEqual(backend.dtype, "float16")

    def test_script_outputs_timing_and_retrieval_diagnostics(self):
        # IDs use the AgentHarm ``{base}-{variant}`` convention so that LOBTO
        # semantics work with the new leave-one-base-task-out helper.
        dataset_rows = [
            {
                "id": "1-1",
                "intent": "Read recent client emails and summarize them.",
                "label": "safe",
                "metadata": {"category": "Productivity", "name": "email-summary"},
                "trajectory": [
                    {
                        "tool": "get_latest_emails",
                        "action": "tool_request::email_fetch",
                        "result": "tool_result::email_fetch",
                    }
                ],
            },
            {
                "id": "2-1",
                "intent": "Read recent client emails and draft a reply.",
                "label": "safe",
                "metadata": {"category": "Productivity", "name": "email-reply"},
                "trajectory": [
                    {
                        "tool": "get_latest_emails",
                        "action": "tool_request::email_fetch",
                        "result": "tool_result::email_fetch",
                    }
                ],
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_path = Path(tmpdir) / "agentharm.jsonl"
            output_path = Path(tmpdir) / "out.jsonl"
            with dataset_path.open("w", encoding="utf-8") as f:
                for row in dataset_rows:
                    f.write(json.dumps(row) + "\n")

            class FakeBackend:
                def __call__(self, eig, target_action_id, view, precedents=None):
                    score = 0.1
                    if "1-1-traj-0" in view and view["1-1-traj-0"].is_present:
                        score += 0.05
                    if precedents:
                        score += 0.02 * len(precedents)
                    return score

            original_argv = sys.argv[:]
            original_make_backend = MODULE.make_backend
            try:
                MODULE.make_backend = lambda *_args, **_kwargs: FakeBackend()
                sys.argv = [
                    "run_real_backbone_eval.py",
                    "--mode",
                    "pg_with_precedents",
                    "--backend-name",
                    "llama_guard",
                    "--model-id",
                    "meta-llama/Llama-Guard-3-1B",
                    "--subset",
                    "harmless_benign",
                    "--limit",
                    "2",
                    "--dataset-file",
                    str(dataset_path),
                    "--output-file",
                    str(output_path),
                    "--precedent-top-k",
                    "1",
                    "--retrieval-probe-top-k",
                    "2",
                    "--retrieval-strategy",
                    "label_balanced",
                ]
                MODULE.main()
            finally:
                MODULE.make_backend = original_make_backend
                sys.argv = original_argv

            row = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["precedent_top_k"], 1)
            self.assertEqual(row["retrieval_probe_top_k"], 2)
            self.assertEqual(row["retrieval_strategy"], "label_balanced")
            self.assertIn("timing_ms", row)
            self.assertIn("sample_wall_clock_ms", row["timing_ms"])
            self.assertIn("retrieval_diagnostics", row)
            self.assertEqual(row["retrieval_diagnostics"]["hit_count"], 1)
            self.assertEqual(len(row["retrieval_diagnostics"]["top_matches"]), 1)


if __name__ == "__main__":
    unittest.main()
