import json

import pytest

from researchdesk.research import AskInput, research


@pytest.mark.integration
def test_structural_repair_is_bounded_and_usage_includes_both_calls(populated):
    class ExplicitRetryTestDouble:
        calls = 0

        def generate(self, messages, timeout_seconds=None):
            self.calls += 1
            if self.calls == 1:
                return json.dumps(
                    {"abstain": True, "claims": [], "limitations": [{"text": "bad shape"}]}
                ), {"generation_tokens": 11, "prompt_tokens": 22}
            assert len(messages) == 4 and timeout_seconds <= 90
            return json.dumps(
                {"abstain": True, "claims": [], "limitations": ["Missing evidence"]}
            ), {"generation_tokens": 7, "prompt_tokens": 33}

    simulated = ExplicitRetryTestDouble()
    result = research(populated, AskInput(question="revenue", method="lexical"), simulated)
    assert simulated.calls == 2
    assert result["model"]["generation_tokens"] == 18
    assert result["model"]["prompt_tokens"] == 55
    assert result["status"] == "abstained"
