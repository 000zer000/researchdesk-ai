"""v1.1 copy-contract regressions only. Not imported by the v1.2 request path."""

import json
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .grounding import json_object


class FinancialAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str
    company: str
    periods: list[str]
    scope: str
    value: Decimal
    unit: str
    definition: str
    direction: str
    citations: list[str]


class FinancialAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    abstain: bool
    assertions: list[FinancialAssertion] = Field(max_length=12)


def validate_financial(raw: str, measures: list[dict]) -> FinancialAnswer:
    answer = FinancialAnswer.model_validate_json(json_object(raw))
    if answer.abstain:
        if answer.assertions:
            raise ValueError("Abstention must not contain conclusions")
        return answer
    expected = {m["id"]: m for m in measures}
    if len({a.id for a in answer.assertions}) != len(answer.assertions) or {
        a.id for a in answer.assertions
    } != set(expected):
        raise ValueError("The proposal omitted, duplicated or invented a required measure")
    for assertion in answer.assertions:
        m = expected[assertion.id]
        for key in ("company", "periods", "scope", "unit", "definition", "direction"):
            if getattr(assertion, key) != m[key]:
                raise ValueError(f"Financial {key} does not match the verified contract")
        if set(assertion.citations) != set(m["citations"]):
            raise ValueError("Financial citations must cover exactly all verified inputs")
        if abs(assertion.value - Decimal(str(m["value"]))) > Decimal("0.005000001"):
            raise ValueError(
                "Financial value disagrees with the deterministic result (two-decimal tolerance)"
            )
    return answer


def proposal_context(measures: list[dict]) -> str:
    return json.dumps([{k: v for k, v in m.items() if k != "label"} for m in measures])
