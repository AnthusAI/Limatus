from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from limatus.editorial_llm import (
    EditorialResponseTruncationError,
    call_structured_responses_api,
)
from limatus.editorial_rewrite_options import (
    _suggestion_output_budget,
    suggestions_contain_evasion_tactics,
)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class EditorialLlmTests(unittest.TestCase):
    def test_normal_article_gets_document_sized_bounded_budget(self):
        budget = _suggestion_output_budget("word " * 1000)
        self.assertGreaterEqual(budget, 8000)
        self.assertLessEqual(budget, 32000)

    def test_explicit_budget_is_validated_and_bounded(self):
        self.assertEqual(_suggestion_output_budget("draft", 6000), 6000)
        with self.assertRaises(ValueError):
            _suggestion_output_budget("draft", 0)
        with self.assertRaises(ValueError):
            _suggestion_output_budget("draft", 32001)

    def test_incomplete_response_raises_without_returning_partial_json(self):
        response = _Response({
            "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
            "output_text": '{"candidates":[{"candidateText":"partial',
        })
        with patch.dict("os.environ", {"OPENAI_API_KEY": "offline-test"}), patch(
            "limatus.editorial_llm.urllib.request.urlopen", return_value=response
        ):
            with self.assertRaisesRegex(EditorialResponseTruncationError, "max_output_tokens"):
                call_structured_responses_api(
                    model="offline-test",
                    system_prompt="system",
                    user_prompt="draft",
                    schema_name="test",
                    schema={"type": "object"},
                    max_output_tokens=10,
                )

    def test_safety_allows_approved_colloquial_candidate_language(self):
        payload = {
            "candidates": [{
                "candidateText": "The short version is ngl, the rollout worked.",
                "rationale": "Preserve the source author's colloquial register.",
            }]
        }
        self.assertFalse(suggestions_contain_evasion_tactics(payload))

    def test_safety_rejects_detector_evasion_instructions(self):
        payload = {
            "candidates": [{
                "candidateText": "Add slang and say 'in my experience' to evade AI detection.",
                "rationale": "Make the text look human and avoid detector flags.",
            }]
        }
        self.assertTrue(suggestions_contain_evasion_tactics(payload))


if __name__ == "__main__":
    unittest.main()
