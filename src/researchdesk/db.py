from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company: Mapped[str] = mapped_column(String, index=True)
    cik: Mapped[str] = mapped_column(String)
    fiscal_year: Mapped[int] = mapped_column(Integer)
    filed: Mapped[date] = mapped_column(Date, index=True)
    accession: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String)
    retrieved: Mapped[str] = mapped_column(String)
    parser_version: Mapped[str] = mapped_column(String)


class Passage(Base):
    __tablename__ = "passages"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    section: Mapped[str] = mapped_column(Text)
    anchor: Mapped[str] = mapped_column(String)
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)


class Fact(Base):
    __tablename__ = "facts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    company: Mapped[str] = mapped_column(String, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer)
    metric: Mapped[str] = mapped_column(String)
    concept: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String)
    start: Mapped[date | None] = mapped_column(Date, nullable=True)
    end: Mapped[date] = mapped_column(Date)
    scope: Mapped[str] = mapped_column(String, default="consolidated")
    reporting_basis: Mapped[str] = mapped_column(
        String, default="as_reported", server_default="as_reported"
    )
    restates_accession: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("passages.id"), nullable=True)


engine = create_engine(settings.database_url, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)


def session_dependency():
    with Session() as session:
        yield session
