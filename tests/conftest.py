import os
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from researchdesk.db import Base, Document, Fact, Passage


@pytest.fixture
def pg_session():
    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://researchdesk:researchdesk@127.0.0.1:55432/researchdesk_test",
    )
    engine = create_engine(url)
    if not engine.url.database or not engine.url.database.endswith("_test"):
        pytest.fail(
            "Integration tests require a separate database ending in _test; no production fallback"
        )
    schema = "test_" + uuid.uuid4().hex
    # A missing database is an error, never a skip. Every test gets an isolated schema.
    with engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(text(f'SET search_path TO "{schema}"'))
        Base.metadata.create_all(connection)
        connection.commit()
        with Session(connection) as session:
            yield session
            session.rollback()
        connection.execute(text("SET search_path TO public"))
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        connection.commit()
    engine.dispose()


@pytest.fixture
def populated(pg_session):
    s = pg_session
    for year, revenue, op, filed in [
        (2023, 100e6, 20e6, "2023-11-03"),
        (2024, 110e6, 24.2e6, "2024-11-01"),
    ]:
        doc_id = f"AAPL-{year}"
        s.add(
            Document(
                id=doc_id,
                company="AAPL",
                cik="0000320193",
                fiscal_year=year,
                filed=date.fromisoformat(filed),
                accession=f"original-{year}",
                url="https://www.sec.gov/example.htm",
                sha256="0" * 64,
                retrieved="2026-10-30T12:00:00Z",
                parser_version="test-original",
            )
        )
        s.flush()
        for metric, value in [
            ("revenue", revenue),
            ("operating_income", op),
            ("cfo", 30e6),
            ("capex", 5e6),
        ]:
            fact_id = f"{doc_id}-{metric}"
            s.add(
                Passage(
                    id=fact_id,
                    document_id=doc_id,
                    text=f"Apple annual {year} {metric} {value} USD. Supply chain risk in outsourced manufacturing.",
                    section="Original test fixture",
                    anchor="test-anchor",
                    start=0,
                    end=80,
                    embedding=None,
                )
            )
            s.flush()
            s.add(
                Fact(
                    id=fact_id,
                    document_id=doc_id,
                    company="AAPL",
                    fiscal_year=year,
                    metric=metric,
                    concept="us-gaap:OriginalTestFact",
                    value=value,
                    unit="USD",
                    currency="USD",
                    start=date(year - 1, 10, 1),
                    end=date(year, 9, 30),
                    scope="consolidated",
                    evidence_id=fact_id,
                )
            )
    s.commit()
    return s
