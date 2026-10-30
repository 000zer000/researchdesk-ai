"""Reproducible ingestion. No web access is exposed through the question API."""

import hashlib
import json
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from .config import ROOT, settings
from .db import Document, Fact, Passage
from .embeddings import embedder

PARSER_VERSION = "html-normalized-v2"
MAPPING = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "da": [
        "DepreciationDepletionAndAmortization",
        "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
    ],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
}
INSTANT = {"cash", "current_assets", "current_liabilities"}


class SourceClient:
    def __init__(self, cache: Path | None = None):
        self.cache = cache or settings.data_dir / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        if not settings.sec_user_agent or "example.com" in settings.sec_user_agent:
            raise ValueError("Set SEC_USER_AGENT to your real name and contact before downloading")
        self.client = httpx.Client(
            headers={"User-Agent": settings.sec_user_agent}, timeout=45, follow_redirects=True
        )

    def get(self, url: str) -> tuple[bytes, str]:
        if not url.startswith(("https://www.sec.gov/", "https://data.sec.gov/")):
            raise ValueError("Only explicitly approved SEC origins are allowed")
        key = hashlib.sha256(url.encode()).hexdigest()
        target = self.cache / key
        metadata = self.cache / (key + ".json")
        if target.exists() and metadata.exists():
            return target.read_bytes(), json.loads(metadata.read_text())["retrieved"]
        for attempt in range(3):
            time.sleep(0.6 * (2**attempt))  # below SEC's 10 requests/s ceiling
            response = self.client.get(url)
            if response.status_code in (403, 401):
                raise RuntimeError(
                    f"Source access denied ({response.status_code}); stop, no bypass"
                )
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                continue
            response.raise_for_status()
            retrieved = datetime.now(UTC).isoformat()
            target.write_bytes(response.content)
            metadata.write_text(
                json.dumps(
                    {
                        "url": url,
                        "retrieved": retrieved,
                        "sha256": hashlib.sha256(response.content).hexdigest(),
                    },
                    indent=2,
                )
            )
            return response.content, retrieved
        raise RuntimeError("Source retry budget exhausted")


def parse_html(raw: bytes) -> tuple[str, list[dict]]:
    soup = BeautifulSoup(raw, "lxml")
    for tag in soup.find_all(["script", "style", "ix:header", "ix:hidden", "noscript"]):
        tag.decompose()
    body = soup.body or soup
    blocks = []
    # Leaf block elements avoid duplicated nested div/table content.
    for tag in body.find_all(["div", "p", "h1", "h2", "h3", "td"]):
        if tag.find(["div", "p", "td"]) is not None:
            continue
        value = " ".join(tag.get_text(" ", strip=True).split())
        if not value or re.fullmatch(
            r"Apple Inc\. \| \d{4} Form 10-K \| \d+|Table of Contents|\d{1,3}", value, re.I
        ):
            continue
        anchor = tag.get("id", "")
        if not anchor:
            parent = tag.find_parent(id=True)
            anchor = parent.get("id", "") if parent else ""
        blocks.append((value, anchor))
    text = "\n".join(x[0] for x in blocks)
    chunks = []
    offset, section = 0, "Form 10-K"
    for value, anchor in blocks:
        if re.match(r"^Item\s+\d+[A-C]?\.?", value, re.I) and len(value) < 160:
            section = value
        # Exact offsets refer to the versioned normalized text, never raw HTML bytes.
        for match in re.finditer(r"\S+(?:\s+\S+){0,149}", value):
            start, end = offset + match.start(), offset + match.end()
            chunks.append(
                {
                    "section": section,
                    "anchor": anchor,
                    "start": start,
                    "end": end,
                    "text": text[start:end],
                }
            )
        offset += len(value) + 1
    # Merge adjacent short blocks, preserving the first anchor and exact text offsets.
    merged = []
    for c in chunks:
        if (
            merged
            and merged[-1]["section"] == c["section"]
            and c["end"] - merged[-1]["start"] < 1100
        ):
            merged[-1]["end"] = c["end"]
            merged[-1]["text"] = text[merged[-1]["start"] : c["end"]]
        else:
            merged.append(c)
    return text, merged


def choose_fact(
    data: dict, concepts: list[str], accession: str, end: str, instant: bool
) -> tuple[str, dict] | None:
    for concept in concepts:
        records = (
            data.get("facts", {})
            .get("us-gaap", {})
            .get(concept, {})
            .get("units", {})
            .get("USD", [])
        )
        valid = []
        for row in records:
            if row.get("accn") != accession or row.get("end") != end or row.get("form") != "10-K":
                continue
            if instant:
                if row.get("start"):
                    continue
            else:
                if not row.get("start"):
                    continue
                days = (date.fromisoformat(end) - date.fromisoformat(row["start"])).days
                if not 350 <= days <= 380:
                    continue
            valid.append(row)
        # Duplicate frames with the same value are fine; ambiguity is never silently resolved.
        if valid:
            if len({(r.get("start"), r["val"]) for r in valid}) != 1:
                raise ValueError(f"Ambiguous annual consolidated fact: {concept} {accession}")
            return concept, valid[0]
    return None


def ingest(session: Session, sources: list[dict] | None = None, semantic: bool = True) -> dict:
    sources = sources or json.loads((ROOT / "data" / "sources.json").read_text())
    client = SourceClient()
    manifest = []
    for source in sources:
        doc_id = f"{source['company']}-{source['fiscal_year']}"
        raw, retrieved = client.get(source["url"])
        digest = hashlib.sha256(raw).hexdigest()
        existing = session.get(Document, doc_id)
        if existing:
            if existing.sha256 != digest:
                raise ValueError("Pinned source changed; review and version the parser/corpus")
            manifest.append(
                {
                    **source,
                    "sha256": digest,
                    "retrieved": existing.retrieved,
                    "parser_version": existing.parser_version,
                }
            )
            continue
        text, chunks = parse_html(raw)
        if len(text) < 20000:
            raise ValueError("Document is unexpectedly small; refusing an error page")
        normalized = settings.data_dir / "cache" / f"{doc_id}.txt"
        normalized.write_text(text)
        doc = Document(
            id=doc_id,
            company=source["company"],
            cik=source["cik"],
            fiscal_year=source["fiscal_year"],
            filed=date.fromisoformat(source["filed"]),
            accession=source["accession"],
            url=source["url"],
            sha256=digest,
            retrieved=retrieved,
            parser_version=PARSER_VERSION,
        )
        session.add(doc)
        session.flush()
        vectors = (
            embedder().encode([c["section"] + ": " + c["text"] for c in chunks])
            if semantic
            else [None] * len(chunks)
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            session.add(
                Passage(id=f"{doc_id}-p{index:04}", document_id=doc_id, **chunk, embedding=vector)
            )
        session.flush()
        facts_raw, facts_retrieved = client.get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{source['cik']}.json"
        )
        facts = json.loads(facts_raw)
        for metric, concepts in MAPPING.items():
            # HP explicitly labels PaymentsToAcquireProductiveAssets as investment in
            # property, plant and equipment in these two statements of cash flows.
            if source["company"] == "HPQ" and metric == "capex":
                concepts = ["PaymentsToAcquireProductiveAssets"]
            chosen = choose_fact(
                facts, concepts, source["accession"], source["end"], metric in INSTANT
            )
            if chosen is None:
                continue
            concept, row = chosen
            fact_id = f"{doc_id}-{metric}"
            # Fact evidence is explicitly XBRL, not a fabricated prose quote or HTML offset.
            evidence = (
                f"{source['company']} FY{source['fiscal_year']}, consolidated annual XBRL. "
                f"{metric} ({concept}) = {row['val']} USD. Period {row.get('start', 'instant')} to {row['end']}. "
                f"Filed {source['filed']}; accession {source['accession']}. Source: SEC Company Facts, exact accession and period filter."
            )
            vector = embedder().encode([evidence])[0] if semantic else None
            session.add(
                Passage(
                    id=fact_id,
                    document_id=doc_id,
                    section="XBRL / " + metric,
                    anchor="",
                    start=-1,
                    end=-1,
                    text=evidence,
                    embedding=vector,
                )
            )
            session.flush()
            session.add(
                Fact(
                    id=fact_id,
                    document_id=doc_id,
                    company=source["company"],
                    fiscal_year=source["fiscal_year"],
                    metric=metric,
                    concept="us-gaap:" + concept,
                    value=row["val"],
                    unit="USD",
                    currency="USD",
                    start=date.fromisoformat(row["start"]) if row.get("start") else None,
                    end=date.fromisoformat(row["end"]),
                    scope="consolidated",
                    evidence_id=fact_id,
                )
            )
        manifest.append(
            {
                **source,
                "sha256": digest,
                "retrieved": retrieved,
                "parser_version": PARSER_VERSION,
                "normalized_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "companyfacts_sha256": hashlib.sha256(facts_raw).hexdigest(),
                "companyfacts_retrieved": facts_retrieved,
            }
        )
        session.commit()
    # Preserve richer first-ingestion provenance on repeat runs.
    path = ROOT / "data" / "manifest.json"
    if not path.exists():
        path.write_text(json.dumps(manifest, indent=2) + "\n")
    return {
        "documents": session.query(Document).count(),
        "passages": session.query(Passage).count(),
        "facts": session.query(Fact).count(),
    }
