import importlib.util
import json
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

    def test_leave_one_out_precedent_store_excludes_current_example(self):
        rows = [
            {"id": "ex-1", "prompt": "p1", "subset": "harmful", "name": ""},
            {"id": "ex-2", "prompt": "p2", "subset": "harmless_benign", "name": ""},
        ]

        store = MODULE.make_leave_one_out_precedent_store(
            rows,
            scope="agentharm",
            held_out_example_id="ex-1",
        )

        with self.assertRaises(KeyError):
            store.get(MODULE.precedent_capsule_id(rows[0]))
        self.assertIsNotNone(store.get(MODULE.precedent_capsule_id(rows[1])))

    def test_script_outputs_timing_and_retrieval_diagnostics(self):
        dataset_rows = [
            {
                "id": "safe-1",
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
                "id": "safe-2",
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
                    if "safe-1-traj-0" in view and view["safe-1-traj-0"].is_present:
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
