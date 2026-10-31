"""Original synthetic fixture for Compose persistence tests, never a real-data demo."""

from datetime import date

from .db import Document, Fact, Passage, Session

if __name__ == "__main__":
    with Session() as s:
        assert s.query(Document).count() in (0, 1), "Refusing to seed a populated demo database"
        assert s.query(Document).count() == 0 or s.get(Document, "AAPL-CI-ORIGINAL"), (
            "Only an empty or synthetic CI database is allowed"
        )
        if not s.get(Document, "AAPL-CI-ORIGINAL"):
            s.add(
                Document(
                    id="AAPL-CI-ORIGINAL",
                    company="AAPL",
                    cik="0000000000",
                    fiscal_year=2024,
                    filed=date(2024, 11, 1),
                    accession="SYNTHETIC-CI-NOT-SEC",
                    url="https://example.com/original-ci-fixture",
                    sha256="0" * 64,
                    retrieved="synthetic",
                    parser_version="original-ci-fixture",
                )
            )
            s.flush()
            s.add(
                Passage(
                    id="CI-revenue",
                    document_id="AAPL-CI-ORIGINAL",
                    section="SYNTHETIC CI",
                    anchor="",
                    start=-1,
                    end=-1,
                    text="Original synthetic revenue fixture, not a filing",
                )
            )
            s.flush()
            s.add(
                Fact(
                    id="CI-revenue",
                    document_id="AAPL-CI-ORIGINAL",
                    company="AAPL",
                    fiscal_year=2024,
                    metric="revenue",
                    concept="original:CIRevenue",
                    value=100e6,
                    unit="USD",
                    currency="USD",
                    start=date(2023, 10, 1),
                    end=date(2024, 9, 30),
                    scope="consolidated",
                    evidence_id="CI-revenue",
                )
            )
            s.commit()

        # Migrate only our explicitly identified synthetic CI fixture from v1.0.
        fact = s.get(Fact, "CI-revenue")
        if fact.scope == "synthetic":
            fact.scope = "consolidated"
            s.commit()
