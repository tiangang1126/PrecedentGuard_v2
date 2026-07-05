import importlib.util
from pathlib import Path
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
        self.assertIn("tool: query_google_search", retrieval_node.payload)
        self.assertIn("result: tool_plan::summarize", observation_node.payload)
        self.assertNotEqual(retrieval_node.payload, retrieval_node.content_hash)

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
            store.get("ah-ex-1")
        self.assertIsNotNone(store.get("ah-ex-2"))


if __name__ == "__main__":
    unittest.main()
