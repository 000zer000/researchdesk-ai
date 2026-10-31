"""Independent cross-check against original inline XBRL (not Company Facts)."""

import json
from datetime import UTC, datetime
from decimal import Decimal

from bs4 import BeautifulSoup
from sqlalchemy import select

from researchdesk.config import ROOT
from researchdesk.db import Fact, Session
from researchdesk.ingestion import SourceClient

client = SourceClient()
checks = []
with Session() as session:
    for source in json.loads((ROOT / "data/sources.json").read_text()):
        raw, _ = client.get(source["url"])
        soup = BeautifulSoup(raw, "lxml")
        contexts = {c["id"]: c for c in soup.find_all("xbrli:context")}
        units = {u["id"]: u.get_text(strip=True) for u in soup.find_all("xbrli:unit")}
        for fact in session.scalars(
            select(Fact).where(Fact.document_id == f"{source['company']}-{source['fiscal_year']}")
        ):
            matches = []
            for tag in soup.find_all("ix:nonfraction", attrs={"name": fact.concept}):
                context = contexts.get(tag.get("contextref"))
                if context is None or context.find(["xbrldi:explicitmember", "xbrldi:typedmember"]):
                    continue
                end = context.find("xbrli:enddate") or context.find("xbrli:instant")
                start = context.find("xbrli:startdate")
                if (
                    not end
                    or end.text != str(fact.end)
                    or (start.text if start else None) != (str(fact.start) if fact.start else None)
                ):
                    continue
                if units.get(tag.get("unitref")) != "iso4217:USD":
                    continue
                value_text = tag.get_text(strip=True).replace(",", "").replace("—", "0")
                value = Decimal(value_text) * 10 ** int(tag.get("scale", "0"))
                if tag.get("sign") == "-":
                    value = -value
                if value == Decimal(str(fact.value)):
                    matches.append(
                        {
                            "context": tag.get("contextref"),
                            "element_id": tag.get("id"),
                            "value": float(value),
                        }
                    )
            checks.append(
                {
                    "fact_id": fact.id,
                    "concept": fact.concept,
                    "unit": "USD",
                    "start": str(fact.start) if fact.start else None,
                    "end": str(fact.end),
                    "original_inline_xbrl_matches": matches,
                    "verified": bool(matches),
                }
            )
assert checks and all(c["verified"] for c in checks), [c for c in checks if not c["verified"]]
target = ROOT / "evaluation/v1.1/financial-source-checks.json"
target.write_text(
    json.dumps(
        {
            "checked_at": datetime.now(UTC).isoformat(),
            "method": "Independent inline XBRL parser; exact dates, consolidated context, USD unit, value, scale and sign; not independent human review",
            "checks": checks,
        },
        indent=2,
    )
    + "\n"
)
print(f"Verified {len(checks)} facts against original inline XBRL")
