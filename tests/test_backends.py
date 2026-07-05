"""
tests/test_backends.py

Unit tests for the guard backends. Uses injected score_fn to avoid loading
real HF models (which requires GPU + network).

Coverage:
  - HFGuardBackend cache behavior (repeated prompts hit cache)
  - injected score_fn bypass
  - default _build_prompt structure (contains required sections)
  - LlamaGuard / ShieldGemma / Granite prompt-template invocations
  - Output parsing (safe/unsafe, Yes/No, harmful/safe)
  - Missing model_id + no score_fn -> raises RuntimeError on call
"""

from __future__ import annotations

import unittest

from precedentguard import (
    NodeType,
    Provenance,
    RuntimeEvent,
    build_eig_from_events,
)
from precedentguard.backends import (
    GraniteGuardianBackend,
    HFGuardBackend,
    LlamaGuardBackend,
    ShieldGemmaBackend,
)
from precedentguard.counterfactual import Intervention, resolve_view


def mk_eig():
    events = [
        RuntimeEvent(event_id="intent", node_type=NodeType.INTENT,
                     content_hash="do-a-thing", provenance=Provenance(),
                     timestamp_ms=0, payload="send a thank-you email"),
        RuntimeEvent(event_id="mem", node_type=NodeType.MEMORY,
                     content_hash="mem-content", provenance=Provenance(),
                     timestamp_ms=1, consumes=["intent"],
                     payload="the user approved outreach yesterday"),
        RuntimeEvent(event_id="act", node_type=NodeType.ACTION,
                     content_hash="proposed-tool-call", provenance=Provenance(),
                     timestamp_ms=2, consumes=["mem"],
                     payload="send the email now"),
    ]
    return build_eig_from_events(events)


class TestHFGuardBackendCache(unittest.TestCase):

    def test_cache_hits_repeat_prompts(self):
        calls = {"n": 0}

        def fake_score(prompt):
            calls["n"] += 1
            return 0.42

        backend = LlamaGuardBackend(model_id="fake", score_fn=fake_score)
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        s1 = backend(eig, "act", view)
        s2 = backend(eig, "act", view)
        s3 = backend(eig, "act", view)
        self.assertAlmostEqual(s1, 0.42)
        self.assertAlmostEqual(s2, 0.42)
        self.assertAlmostEqual(s3, 0.42)
        # Injected score_fn should be called once — subsequent hits use cache
        self.assertEqual(calls["n"], 1)

    def test_score_clamped_to_unit_interval(self):
        backend = LlamaGuardBackend(model_id="fake", score_fn=lambda _: 5.0)
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        self.assertAlmostEqual(backend(eig, "act", view), 1.0)

        backend2 = LlamaGuardBackend(model_id="fake", score_fn=lambda _: -0.3)
        self.assertAlmostEqual(backend2(eig, "act", view), 0.0)

    def test_no_model_id_no_score_fn_raises(self):
        # HFGuardBackend without model_id AND no score_fn raises on first call
        base = HFGuardBackend()  # empty model_id, no score_fn
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        with self.assertRaises(RuntimeError):
            base(eig, "act", view)


class TestPromptStructure(unittest.TestCase):
    """Verify default prompts contain the required semantic sections."""

    def test_default_prompt_contains_all_sections(self):
        backend = HFGuardBackend(model_id="", score_fn=lambda _: 0.5)
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        prompt = backend._build_prompt(eig, "act", view)
        self.assertIn("[INTENT]", prompt)
        self.assertIn("[MEMORY]", prompt)  # from NodeType.MEMORY.value.upper()
        self.assertIn("[ACTION]", prompt)

    def test_llamaguard_uses_official_template(self):
        backend = LlamaGuardBackend(score_fn=lambda _: 0.5)
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        prompt = backend._build_prompt(eig, "act", view)
        self.assertIn("<|begin_of_text|>", prompt)
        self.assertIn("<User Request>", prompt)
        self.assertIn("<Agent Proposed Action>", prompt)

    def test_shieldgemma_uses_yesno_prompt(self):
        backend = ShieldGemmaBackend(score_fn=lambda _: 0.5)
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        prompt = backend._build_prompt(eig, "act", view)
        self.assertIn("<Guidelines>", prompt)
        self.assertIn("<ProposedAction>", prompt)
        self.assertIn("Yes", prompt)
        self.assertIn("No", prompt)

    def test_granite_uses_role_headers(self):
        backend = GraniteGuardianBackend(score_fn=lambda _: 0.5)
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        prompt = backend._build_prompt(eig, "act", view)
        self.assertIn("<|start_of_role|>", prompt)
        self.assertIn("Proposed action:", prompt)

    def test_vendor_prompts_prefer_payload_over_content_hash(self):
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        for backend in (
            LlamaGuardBackend(score_fn=lambda _: 0.5),
            ShieldGemmaBackend(score_fn=lambda _: 0.5),
            GraniteGuardianBackend(score_fn=lambda _: 0.5),
        ):
            prompt = backend._build_prompt(eig, "act", view)
            self.assertIn("send a thank-you email", prompt)
            self.assertIn("send the email now", prompt)
            self.assertNotIn("do-a-thing", prompt)


class TestOutputParsing(unittest.TestCase):

    def test_llamaguard_parses_unsafe(self):
        backend = LlamaGuardBackend(score_fn=lambda _: 0.5)
        self.assertAlmostEqual(backend._parse_output("unsafe\nS1"), 0.9)
        self.assertAlmostEqual(backend._parse_output("safe"), 0.1)

    def test_shieldgemma_parses_yesno(self):
        backend = ShieldGemmaBackend(score_fn=lambda _: 0.5)
        self.assertAlmostEqual(backend._parse_output("Yes."), 0.9)
        self.assertAlmostEqual(backend._parse_output("No, the action is fine."), 0.1)

    def test_granite_parses_harmful(self):
        backend = GraniteGuardianBackend(score_fn=lambda _: 0.5)
        self.assertAlmostEqual(backend._parse_output("harmful. reason ..."), 0.9)
        self.assertAlmostEqual(backend._parse_output("safe. nothing wrong."), 0.1)

    def test_default_parses_decimal_fallback(self):
        backend = HFGuardBackend(model_id="", score_fn=lambda _: 0.5)
        self.assertAlmostEqual(backend._parse_output("0.73"), 0.73)
        self.assertAlmostEqual(backend._parse_output("2.5"), 1.0)  # clamped
        self.assertAlmostEqual(backend._parse_output("garbage"), 0.5)  # fallback

    def test_default_parses_keywords(self):
        backend = HFGuardBackend(model_id="", score_fn=lambda _: 0.5)
        self.assertAlmostEqual(backend._parse_output("This is UNSAFE"), 0.9)
        self.assertAlmostEqual(backend._parse_output("looks safe to me"), 0.1)


class TestBackendModelIDsMatchVendors(unittest.TestCase):
    """Sanity check that default model IDs are the intended vendors."""

    def test_defaults(self):
        self.assertEqual(LlamaGuardBackend().model_id,
                         "meta-llama/Llama-Guard-3-1B")
        self.assertEqual(ShieldGemmaBackend().model_id,
                         "google/shieldgemma-2b")
        self.assertEqual(GraniteGuardianBackend().model_id,
                         "ibm-granite/granite-guardian-3.2-2b")


if __name__ == "__main__":
    unittest.main(verbosity=2)
