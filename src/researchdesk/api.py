import json
import threading
from datetime import date
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .config import ROOT, settings
from .db import Document, Passage, session_dependency
from .finance import DCFInput, MissingData, dcf, historical, sensitivity
from .report import make_report
from .research import AskInput, research
from .search import serialize

app = FastAPI(title="ResearchDesk", version="1.0.0")
DB = Annotated[Session, Depends(session_dependency)]
inference_gate = threading.BoundedSemaphore(1)
export_gate = threading.BoundedSemaphore(2)


@app.get("/api/health")
def health(session: DB):
    session.execute(text("SELECT 1"))
    configured = (
        settings.data_dir / "runtime" / "llm.json"
    ).exists() or settings.llm_backend == "local-http"
    return {
        "database": "ok",
        "model_configured": configured,
        "model": settings.llm_model,
        "inference": "local only; availability verified on request",
        "backend": settings.llm_backend,
    }


@app.get("/api/financials")
def financials(session: DB, as_of: date = date(2024, 12, 31)):
    return {company: historical(session, company, as_of) for company in ["AAPL", "DELL", "HPQ"]}


@app.get("/api/sources")
def sources(session: DB, as_of: date = date(2024, 12, 31)):
    docs = session.scalars(
        select(Document).where(Document.filed <= as_of).order_by(Document.id)
    ).all()
    return [{c.name: str(getattr(d, c.name)) for c in Document.__table__.columns} for d in docs]


@app.get("/api/evidence/{passage_id}")
def evidence(passage_id: str, session: DB, as_of: date = date(2024, 12, 31)):
    if len(passage_id) > 100:
        raise HTTPException(404, "Evidence not found")
    row = session.execute(
        select(Passage, Document)
        .join(Document)
        .where(Passage.id == passage_id, Document.filed <= as_of)
    ).first()
    if not row:
        raise HTTPException(404, "Evidence is absent or was not published by the analysis date")
    p, d = row
    context = (
        session.scalars(
            select(Passage)
            .where(
                Passage.document_id == d.id,
                Passage.start >= max(0, p.start - 1200),
                Passage.start <= p.end + 1200,
                Passage.start >= 0,
            )
            .order_by(Passage.start)
            .limit(5)
        ).all()
        if p.start >= 0
        else []
    )
    return {**serialize(p, d), "context": [{"id": x.id, "text": x.text} for x in context]}


@app.post("/api/research")
def ask(args: AskInput, session: DB):
    if not inference_gate.acquire(blocking=False):
        raise HTTPException(429, "One local inference is already running. Retry shortly.")
    try:
        return research(session, args)
    except TimeoutError as error:
        raise HTTPException(504, str(error)) from error
    except (RuntimeError, FileNotFoundError, ImportError, OSError) as error:
        raise HTTPException(
            503, "Local AI unavailable. Check model setup and server logs."
        ) from error
    finally:
        inference_gate.release()


@app.post("/api/dcf")
def run_dcf_scenario(args: DCFInput):
    return {**dcf(args), "sensitivity": sensitivity(args)}


class ExportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: date = date(2024, 12, 31)
    assumptions: DCFInput
    company: Literal["AAPL"] = "AAPL"


@app.post("/api/export")
def export(args: ExportInput, session: DB):
    if not export_gate.acquire(blocking=False):
        raise HTTPException(429, "Export capacity reached; retry shortly")
    try:
        pdf = make_report(session, args.as_of, args.assumptions)
        return Response(
            pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="ResearchDesk-Apple-note.pdf"'},
        )
    except (ValueError, MissingData) as error:
        raise HTTPException(422, str(error)) from error
    finally:
        export_gate.release()


@app.get("/api/evaluation")
def evaluation():
    path = ROOT / "evaluation" / "summary.json"
    return (
        json.loads(path.read_text())
        if path.exists()
        else {"status": "not_run", "note": "No real-model evaluation recorded"}
    )


@app.get("/{path:path}")
def frontend(path: str):
    dist = ROOT / "frontend" / "dist"
    candidate = (dist / path).resolve()
    if not candidate.is_relative_to(dist.resolve()) or path.startswith("api/"):
        raise HTTPException(404, "Not found")
    if path and candidate.is_file():
        return FileResponse(candidate)
    index = dist / "index.html"
    if not index.exists():
        raise HTTPException(404, "Build the frontend first: cd frontend && npm ci && npm run build")
    return FileResponse(index)
