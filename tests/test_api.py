from datetime import date
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from researchdesk.api import app
from researchdesk.db import session_dependency
from researchdesk.finance import DCFInput
from researchdesk.report import make_report


@pytest.fixture
def client(populated):
    app.dependency_overrides[session_dependency] = lambda: populated
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_api_temporal_evidence_and_parameters(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/evidence/AAPL-2024-revenue?as_of=2024-10-31").status_code == 404
    r = client.get("/api/evidence/AAPL-2024-revenue?as_of=2024-11-01")
    assert r.status_code == 200 and r.json()["id"] == "AAPL-2024-revenue"
    assert (
        client.post("/api/research", json={"company": "TSLA", "question": "revenue"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/dcf", json={"base_revenue": 100, "discount_rate": 0.01, "terminal_growth": 0.03}
        ).status_code
        == 422
    )
    assert client.get("/api/unknown").status_code == 404


@pytest.mark.integration
def test_pdf_uses_same_scenario_and_updates(populated):
    args = DCFInput(base_revenue=110)
    first = make_report(populated, date(2024, 12, 31), args)
    second = make_report(
        populated, date(2024, 12, 31), args.model_copy(update={"discount_rate": 0.12})
    )
    a = PdfReader(BytesIO(first))
    b = PdfReader(BytesIO(second))
    assert len(a.pages) == 3 and len(b.pages) == 3
    t0 = a.pages[2].extract_text()
    t1 = b.pages[2].extract_text()
    assert "9.0%" in t0 and "12.0%" in t1 and t0 != t1
    assert "not a live model response" in " ".join(a.pages[0].extract_text().split())
    with pytest.raises(ValueError, match="Base revenue"):
        make_report(populated, date(2024, 12, 31), DCFInput(base_revenue=999))
