import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  BookOpen,
  ChartNoAxesCombined,
  Check,
  ChevronRight,
  CircleHelp,
  Download,
  FileText,
  FlaskConical,
  LoaderCircle,
  PanelRightOpen,
  Search,
  ShieldCheck,
  Square,
  X,
} from "lucide-react";
import "./style.css";

type Fact = {
  value: number;
  concept: string;
  document_id: string;
  evidence_id: string;
  start: string | null;
  end: string;
};
type Year = {
  fiscal_year: number;
  end: string;
  facts: Record<string, Fact>;
  operating_margin?: number;
  revenue_growth?: number;
  cfo_margin?: number;
  cfo_less_capex?: number;
};
type Financials = Record<string, Year[]>;
type Source = {
  id: string;
  filed: string;
  url: string;
  sha256: string;
  accession: string;
  parser_version: string;
  retrieved: string;
  cik: string;
};
type Evidence = {
  id: string;
  section: string;
  text: string;
  company: string;
  fiscal_year: number;
  filed: string;
  url: string;
  start: number;
  end: number;
  offset_basis: string;
  context?: { id: string; text: string }[];
};
type Answer = {
  status: string;
  origin: string;
  error?: string;
  answer: {
    abstain: boolean;
    claims: { text: string; citations: string[] }[];
    limitations: string[];
  } | null;
  evidence: Evidence[];
  trace: unknown[];
  calculations: Record<string, number | string> | null;
  model?: { model: string; elapsed_seconds: number; generation_tokens: number };
  elapsed_seconds: number;
};
type Assumptions = {
  base_revenue: number;
  growth: number[];
  operating_margin: number;
  tax_rate: number;
  da_ratio: number;
  capex_ratio: number;
  nwc_ratio: number;
  discount_rate: number;
  terminal_growth: number;
};
type Valuation = {
  enterprise_value: number;
  terminal_share: number;
  terminal_present_value: number;
  years: {
    year: number;
    revenue: number;
    fcff: number;
    present_value: number;
  }[];
  sensitivity: {
    discount_rate: number;
    terminal_growth: number;
    enterprise_value: number | null;
  }[];
};
const names: Record<string, string> = {
  AAPL: "Apple Inc.",
  DELL: "Dell Technologies",
  HPQ: "HP Inc.",
};
const money = (n: number | undefined, d = 0) =>
  n === undefined
    ? "Unavailable"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: d }).format(n);
const pct = (n: number | undefined, d = 1) =>
  n === undefined ? "n/a" : `${(n * 100).toFixed(d)}%`;
const defaults: Assumptions = {
  base_revenue: 0,
  growth: [0.04, 0.04, 0.04, 0.04, 0.04],
  operating_margin: 0.3,
  tax_rate: 0.21,
  da_ratio: 0.03,
  capex_ratio: 0.03,
  nwc_ratio: 0.02,
  discount_rate: 0.09,
  terminal_growth: 0.02,
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(
      typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail),
    );
  }
  return r.json();
}
const post = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
  signal,
});

function App() {
  const [tab, setTab] = useState("Research");
  const [company, setCompany] = useState("AAPL");
  const [asOf, setAsOf] = useState("2024-12-31");
  const [financials, setFinancials] = useState<Financials>({});
  const [sources, setSources] = useState<Source[]>([]);
  const [health, setHealth] = useState<{
    model_configured: boolean;
    model: string;
  } | null>(null);
  const [loadError, setLoadError] = useState("");
  const [dataLoading, setDataLoading] = useState(true);
  const [question, setQuestion] = useState(
    "Which supply-chain risks does Apple disclose in its 2024 annual report?",
  );
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [researchError, setResearchError] = useState("");
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [assumptions, setAssumptions] = useState<Assumptions>(defaults);
  const [valuation, setValuation] = useState<Valuation | null>(null);
  const [valuationError, setValuationError] = useState("");
  const [calculating, setCalculating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [evaluation, setEvaluation] = useState<Record<string, unknown> | null>(
    null,
  );
  const [scenario, setScenario] = useState("Base case");
  const controller = useRef<AbortController | null>(null);
  const currentQuery = useRef(0);
  const years = financials[company] || [];
  const latest = years.at(-1);
  const primary = financials.AAPL?.at(-1);
  useEffect(() => {
    const c = new AbortController();
    setLoadError("");
    setDataLoading(true);
    setFinancials({});
    setSources([]);
    setValuation(null);
    setAssumptions((a) => ({ ...a, base_revenue: 0 }));
    Promise.all([
      request<Financials>(`/api/financials?as_of=${asOf}`, {
        signal: c.signal,
      }),
      request<Source[]>(`/api/sources?as_of=${asOf}`, { signal: c.signal }),
    ])
      .then(([f, s]) => {
        setFinancials(f);
        setSources(s);
        setAssumptions((a) => ({
          ...a,
          base_revenue: f.AAPL?.at(-1)?.facts.revenue?.value || 0,
        }));
      })
      .catch((e) => {
        if (e.name !== "AbortError") setLoadError(e.message);
      })
      .finally(() => {
        if (!c.signal.aborted) setDataLoading(false);
      });
    return () => c.abort();
  }, [asOf]);
  useEffect(() => {
    request<typeof health>("/api/health")
      .then(setHealth)
      .catch(() => setHealth(null));
    request<Record<string, unknown>>("/api/evaluation")
      .then(setEvaluation)
      .catch(() => {});
  }, []);
  useEffect(() => {
    controller.current?.abort();
    currentQuery.current++;
    setBusy(false);
    setAnswer(null);
    setEvidence(null);
    setResearchError("");
  }, [company, asOf]);
  useEffect(() => {
    if (!assumptions.base_revenue) {
      setValuation(null);
      return;
    }
    const c = new AbortController();
    setCalculating(true);
    const timer = setTimeout(
      () =>
        request<Valuation>("/api/dcf", post(assumptions, c.signal))
          .then((v) => {
            setValuation(v);
            setValuationError("");
          })
          .catch((e) => {
            if (e.name !== "AbortError") {
              setValuation(null);
              setValuationError(e.message);
            }
          })
          .finally(() => {
            if (!c.signal.aborted) setCalculating(false);
          }),
      180,
    );
    return () => {
      clearTimeout(timer);
      c.abort();
    };
  }, [assumptions]);
  async function ask(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    const sequence = ++currentQuery.current;
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    setResearchError("");
    setAnswer(null);
    setEvidence(null);
    const timeout = setTimeout(() => c.abort("timeout"), 100000);
    try {
      const a = await request<Answer>(
        "/api/research",
        post(
          { company, as_of: asOf, question, method: "hybrid", k: 5 },
          c.signal,
        ),
      );
      if (sequence === currentQuery.current) {
        setAnswer(a);
        setEvidence(a.evidence[0] || null);
      }
    } catch (e) {
      if (sequence === currentQuery.current)
        setResearchError(
          c.signal.aborted
            ? c.signal.reason === "timeout"
              ? "Request timed out. The local service may still be finishing its bounded inference."
              : "Stopped waiting. The server may finish the current inference within its time budget."
            : (e as Error).message,
        );
    } finally {
      clearTimeout(timeout);
      if (sequence === currentQuery.current) setBusy(false);
    }
  }
  async function openEvidence(id: string) {
    try {
      setEvidence(
        await request<Evidence>(
          `/api/evidence/${encodeURIComponent(id)}?as_of=${asOf}`,
        ),
      );
    } catch (e) {
      setResearchError((e as Error).message);
    }
  }
  async function download() {
    setExporting(true);
    setValuationError("");
    try {
      const r = await fetch("/api/export", post({ as_of: asOf, assumptions }));
      if (!r.ok) {
        const e = await r.json();
        throw new Error(
          typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail),
        );
      }
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "ResearchDesk-Apple-note.pdf";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setValuationError((e as Error).message);
    } finally {
      setExporting(false);
    }
  }
  function selectScenario(value: string) {
    setScenario(value);
    const p =
      value === "Conservative"
        ? { g: 0.01, m: 0.27, w: 0.11 }
        : value === "Expansion"
          ? { g: 0.07, m: 0.33, w: 0.09 }
          : { g: 0.04, m: 0.3, w: 0.09 };
    setAssumptions((a) => ({
      ...a,
      growth: Array(5).fill(p.g),
      operating_margin: p.m,
      discount_rate: p.w,
    }));
  }
  const setRate = (key: keyof Assumptions, value: number) => {
    setScenario("Custom");
    setAssumptions((a) => ({ ...a, [key]: value / 100 }));
  };
  const field = (
    label: string,
    key: Exclude<keyof Assumptions, "growth" | "base_revenue">,
    min: number,
    max: number,
    step = 0.5,
  ) => (
    <label className="assumption" key={key}>
      <span>{label}</span>
      <div>
        <input
          aria-label={label}
          type="number"
          min={min}
          max={max}
          step={step}
          value={+(assumptions[key] * 100).toFixed(3)}
          onChange={(e) => setRate(key, Number(e.target.value))}
        />
        <span>%</span>
      </div>
    </label>
  );
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("Research");
          }}
        >
          <span className="brand-mark">
            r<span>.</span>
          </span>
          <div>
            ResearchDesk<small>FINANCIAL INTELLIGENCE</small>
          </div>
        </a>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {[
            { label: "Research", icon: Search },
            { label: "Financials & Valuation", icon: ChartNoAxesCombined },
            { label: "Sources & Evaluation", icon: BookOpen },
          ].map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={tab === label ? "nav-item selected" : "nav-item"}
              aria-current={tab === label ? "page" : undefined}
              onClick={() => setTab(label)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {tab === label && <ChevronRight size={14} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-rule" />
        <div className="workspace-label">COVERED COMPANIES</div>
        {Object.entries(names).map(([ticker, name]) => (
          <button
            key={ticker}
            className={`company-link ${company === ticker ? "active" : ""}`}
            onClick={() => setCompany(ticker)}
          >
            <span className="company-avatar">
              {ticker === "AAPL" ? "A" : ticker === "DELL" ? "D" : "H"}
            </span>
            <span>
              {name}
              <small>
                {ticker} ·{" "}
                {ticker === "AAPL" ? "Primary coverage" : "Operating peer"}
              </small>
            </span>
            {company === ticker && <span className="tiny-dot" />}
          </button>
        ))}
        <div className="sidebar-bottom">
          <ShieldCheck size={20} />
          <div>
            Evidence before opinion
            <small>Local AI. Explicit assumptions.</small>
          </div>
          <span className="version">V1</span>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} /> <strong>{tab}</strong>
          </div>
          <div className="service">
            <span
              className={`status-dot ${health?.model_configured ? "" : "offline"}`}
            />
            {health?.model_configured
              ? "Local model configured"
              : "AI setup required"}
          </div>
        </header>
        <div className="page">
          <div className="page-heading">
            <div>
              <div className="eyebrow">THE RESEARCH WORKSPACE</div>
              <h1>
                {tab === "Research"
                  ? "From filings to findings."
                  : tab === "Financials & Valuation"
                    ? "Make the assumptions visible."
                    : "Show your working."}
              </h1>
              <p className="subtitle">
                {tab === "Research"
                  ? "Ask a focused question. Follow every answer back to its source."
                  : tab === "Financials & Valuation"
                    ? "Published financials and a five-year, assumption-driven DCF."
                    : "A bounded corpus, traceable provenance and measured model behavior."}
              </p>
            </div>
            <button
              className="button secondary"
              disabled={!valuation || calculating || exporting}
              onClick={download}
            >
              <Download size={16} />
              {exporting ? "Exporting…" : "Export Apple note"}
            </button>
          </div>
          <div className="coverage-bar">
            <div className="company-badge">{company[0]}</div>
            <div className="coverage-name">
              <strong>{names[company]}</strong>
              <select
                className="mobile-company"
                aria-label="Covered company"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              >
                {Object.entries(names).map(([ticker, name]) => (
                  <option key={ticker} value={ticker}>
                    {name}
                  </option>
                ))}
              </select>
              <span>
                {company} <span className="separator">/</span> SEC annual
                filings
              </span>
            </div>
            <span className="coverage-pill">
              {dataLoading
                ? "Loading annual data…"
                : years.length
                  ? `${years.length} annual periods`
                  : "No published periods"}
            </span>
            <label className="date-label">
              Analysis date
              <input
                aria-label="Analysis date"
                type="date"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
              />
            </label>
          </div>
          {loadError && (
            <div className="error" role="alert">
              Data service unavailable: {loadError}
            </div>
          )}
          <div className="metrics">
            <Metric
              label="REVENUE"
              value={money(latest?.facts.revenue?.value)}
              suffix="USD million"
              detail={
                latest
                  ? `FY${latest.fiscal_year} · ended ${latest.end}`
                  : "No annual fact at this date"
              }
            />
            <Metric
              label="OPERATING MARGIN"
              value={pct(latest?.operating_margin, 2)}
              detail="Operating income ÷ revenue"
            />
            <Metric
              label="OPERATING CASH FLOW"
              value={money(latest?.facts.cfo?.value)}
              suffix="USD million"
              detail="Consolidated annual cash flow"
            />
            <Metric
              label="SOURCE COVERAGE"
              value={String(
                sources.filter((s) => s.id.startsWith(company)).length,
              )}
              suffix="official filings"
              detail="Filtered by publication date"
            />
          </div>
          {tab === "Research" && (
            <div className="research-grid">
              <section className="research-main">
                <div className="card question-card">
                  <div className="section-heading">
                    <span className="icon-tile">
                      <Search size={18} />
                    </span>
                    <div>
                      <h2>Ask the filings</h2>
                      <p>Research within {names[company]}'s published corpus</p>
                    </div>
                    <span className="small-tag">HYBRID SEARCH</span>
                  </div>
                  <form onSubmit={ask}>
                    <label className="sr-only" htmlFor="question">
                      Research question
                    </label>
                    <textarea
                      id="question"
                      maxLength={1200}
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      rows={3}
                    />
                    <div className="question-actions">
                      <span>
                        <ShieldCheck size={14} /> Grounded in selected documents
                      </span>
                      {busy ? (
                        <button
                          className="button secondary"
                          type="button"
                          onClick={() => controller.current?.abort()}
                        >
                          <Square size={13} />
                          Cancel
                        </button>
                      ) : (
                        <button
                          className="button primary"
                          disabled={!question.trim() || dataLoading}
                          type="submit"
                        >
                          Research question <ArrowUpRight size={17} />
                        </button>
                      )}
                    </div>
                  </form>
                  <div className="suggestions">
                    <span>Try asking</span>
                    {[
                      "How did revenue and operating margin change between 2023 and 2024?",
                      "What supply-chain risks are disclosed?",
                      "Does the report disclose next year’s exact revenue?",
                    ].map((q, i) => (
                      <button key={q} onClick={() => setQuestion(q)}>
                        {
                          [
                            "Revenue & margins",
                            "Supply-chain risk",
                            "Missing information",
                          ][i]
                        }{" "}
                        <ArrowUpRight size={12} />
                      </button>
                    ))}
                  </div>
                </div>
                <div className="card answer-card" aria-live="polite">
                  <div className="card-header">
                    <h2>Research findings</h2>
                    {answer && (
                      <span className="small-tag">{answer.origin}</span>
                    )}
                  </div>
                  {busy ? (
                    <div className="empty-state">
                      <LoaderCircle className="spin" size={30} />
                      <h3>Reading the evidence</h3>
                      <p>
                        Retrieving passages and generating locally. Inference is
                        bounded to 90 seconds.
                      </p>
                    </div>
                  ) : researchError ? (
                    <div className="error" role="alert">
                      {researchError}
                    </div>
                  ) : !answer ? (
                    <div className="empty-state">
                      <span className="empty-icon">
                        <FileText size={28} />
                      </span>
                      <h3>A clear answer starts with a good source.</h3>
                      <p>
                        Ask a question to generate a real local-model response.
                        Evidence and calculation traces will appear here.
                      </p>
                      <span className="quiet-pill">
                        No answer has been generated yet
                      </span>
                    </div>
                  ) : (
                    <>
                      <div
                        className={`result-status ${answer.status === "answered" ? "" : "muted"}`}
                      >
                        <Check size={15} />
                        {answer.status.replaceAll("_", " ")}
                        <span>{answer.elapsed_seconds.toFixed(1)}s</span>
                      </div>
                      {answer.error && <p className="error">{answer.error}</p>}
                      {answer.answer?.claims.map((c, i) => (
                        <div className="claim" key={i}>
                          <p>{c.text}</p>
                          <div className="citations">
                            {c.citations.map((id) => (
                              <button key={id} onClick={() => openEvidence(id)}>
                                <FileText size={12} />
                                {id}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                      {answer.answer?.limitations.length ? (
                        <div className="limitations">
                          <CircleHelp size={15} />
                          <div>
                            {answer.answer.limitations.map((l, i) => (
                              <p key={i}>{l}</p>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      {answer.calculations && (
                        <div className="calculation">
                          <h3>Deterministic calculation</h3>
                          <p>
                            Revenue growth:{" "}
                            {pct(Number(answer.calculations.revenue_growth), 2)}{" "}
                            · Margin change:{" "}
                            {money(
                              Number(answer.calculations.margin_change_pp),
                              2,
                            )}{" "}
                            percentage points
                          </p>
                          <small>
                            {String(answer.calculations.from_year)} →{" "}
                            {String(answer.calculations.to_year)} · Units: USD
                            millions
                          </small>
                        </div>
                      )}
                      <p className="support-note">
                        Citation IDs are validated. Whether each citation
                        supports its claim still needs independent review.
                      </p>
                      {answer.model && (
                        <div className="model-meta">
                          {answer.model.model} ·{" "}
                          {answer.model.generation_tokens} output tokens · live
                          local inference
                        </div>
                      )}
                      <details className="trace">
                        <summary>Inspect tool trace</summary>
                        <pre>{JSON.stringify(answer.trace, null, 2)}</pre>
                      </details>
                    </>
                  )}
                </div>
              </section>
              <aside className="card evidence-panel">
                <div className="card-header">
                  <h2>
                    <PanelRightOpen size={17} /> Evidence desk
                  </h2>
                  {evidence && (
                    <button
                      className="icon-button"
                      aria-label="Close evidence"
                      onClick={() => setEvidence(null)}
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
                {evidence ? (
                  <>
                    <div className="evidence-meta">
                      <span className="quiet-pill">
                        FY{evidence.fiscal_year}
                      </span>
                      <span>Filed {evidence.filed}</span>
                    </div>
                    <h3 className="evidence-title">{evidence.section}</h3>
                    <code className="evidence-id">{evidence.id}</code>
                    <blockquote>{evidence.text}</blockquote>
                    <p className="offset">
                      {evidence.offset_basis}
                      {evidence.start >= 0
                        ? ` · ${evidence.start}–${evidence.end}`
                        : ""}
                    </p>
                    <a
                      className="source-link"
                      href={evidence.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open official filing <ArrowUpRight size={15} />
                    </a>
                    {evidence.context?.length ? (
                      <details>
                        <summary>Read surrounding context</summary>
                        {evidence.context.map((c) => (
                          <p className="context" key={c.id}>
                            {c.text}
                          </p>
                        ))}
                      </details>
                    ) : null}
                    {answer && answer.evidence.length > 1 && (
                      <div className="more-evidence">
                        <h4>Retrieved evidence</h4>
                        {answer.evidence.map((p) => (
                          <button
                            key={p.id}
                            className={p.id === evidence.id ? "active" : ""}
                            onClick={() => openEvidence(p.id)}
                          >
                            <FileText size={14} />
                            <span>
                              {p.id}
                              <small>{p.section}</small>
                            </span>
                            <ChevronRight size={13} />
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="evidence-empty">
                    <BookOpen size={28} />
                    <h3>Keep the source in view.</h3>
                    <p>
                      Open a citation to inspect its original passage,
                      publication date and surrounding context.
                    </p>
                    <div className="evidence-steps">
                      <span>
                        01 <b>Retrieve</b> relevant passages
                      </span>
                      <span>
                        02 <b>Generate</b> with local AI
                      </span>
                      <span>
                        03 <b>Inspect</b> every claim
                      </span>
                    </div>
                  </div>
                )}
              </aside>
            </div>
          )}
          {tab === "Financials & Valuation" && (
            <>
              <section className="card">
                <div className="card-header">
                  <h2>Historical financials</h2>
                  <span className="small-tag">USD MILLIONS / CONSOLIDATED</span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Published metric</th>
                        {years.map((y) => (
                          <th key={y.fiscal_year}>
                            FY{y.fiscal_year}
                            <small>Ended {y.end}</small>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries({
                        revenue: "Revenue",
                        operating_income: "Operating income",
                        cfo: "Cash from operations",
                        capex: "Capital expenditure (outflow)",
                        da: "Depreciation & amortization",
                        cash: "Cash & equivalents",
                        current_assets: "Current assets",
                        current_liabilities: "Current liabilities",
                      }).map(([key, label]) => (
                        <tr key={key}>
                          <td>{label}</td>
                          {years.map((y) => (
                            <td key={y.fiscal_year}>
                              {y.facts[key] ? (
                                <button
                                  className="fact-link"
                                  onClick={() => {
                                    openEvidence(y.facts[key].evidence_id);
                                    setTab("Research");
                                  }}
                                >
                                  {money(y.facts[key].value)}{" "}
                                  <ArrowUpRight size={11} />
                                </button>
                              ) : (
                                "Not mapped"
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="table-note">
                  Positive capex values represent cash outflows. Annual facts
                  use the exact original filing accession; no later restatement
                  is substituted.
                </p>
              </section>
              <section className="card">
                <div className="card-header">
                  <h2>Operating peer comparison</h2>
                  <span className="small-tag">FISCAL CALENDARS DIFFER</span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Company / latest year end</th>
                        <th>Revenue growth</th>
                        <th>Operating margin</th>
                        <th>CFO / revenue</th>
                        <th>CFO − capex</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(financials).map(([c, h]) => {
                        const y = h.at(-1);
                        return (
                          <tr key={c}>
                            <td>
                              <strong>{names[c]}</strong>
                              <small>{y?.end || "No published data"}</small>
                            </td>
                            <td>{pct(y?.revenue_growth)}</td>
                            <td>{pct(y?.operating_margin)}</td>
                            <td>{pct(y?.cfo_margin)}</td>
                            <td>{money(y?.cfo_less_capex)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <p className="table-note">
                  Operating comparisons, without trading multiples. Apple
                  services, Dell infrastructure and HP printing have different
                  economics. CFO less capex is a cash-flow proxy, not FCFF.
                  Apple and Dell FY2023 contain 53 weeks.
                </p>
              </section>
              <div className="valuation-heading">
                <div>
                  <div className="eyebrow">SCENARIO LAB / APPLE</div>
                  <h2>What do your assumptions imply?</h2>
                  <p>
                    Five forecast years. Every cash flow calculated in Python.
                  </p>
                </div>
                <label className="scenario-label">
                  Scenario
                  <select
                    aria-label="Scenario"
                    value={scenario}
                    onChange={(e) => selectScenario(e.target.value)}
                  >
                    {["Base case", "Conservative", "Expansion", "Custom"].map(
                      (v) => (
                        <option key={v}>{v}</option>
                      ),
                    )}
                  </select>
                </label>
              </div>
              {!primary ? (
                <div className="error">
                  No published Apple base-year revenue at this date.
                </div>
              ) : (
                <div className="valuation-grid">
                  <section className="card assumption-card">
                    <div className="card-header">
                      <h2>Explicit assumptions</h2>
                      <span className="small-tag">ANALYST INPUTS</span>
                    </div>
                    <p className="base-label">
                      Published base: FY{primary.fiscal_year} revenue{" "}
                      <strong>{money(assumptions.base_revenue)}</strong>
                    </p>
                    <label className="growth-label">
                      Revenue growth by forecast year (%)
                    </label>
                    <div className="growth-inputs">
                      {assumptions.growth.map((g, i) => (
                        <label key={i}>
                          Y{i + 1}
                          <input
                            aria-label={`Year ${i + 1} growth`}
                            type="number"
                            step=".5"
                            min="-50"
                            max="50"
                            value={+(g * 100).toFixed(2)}
                            onChange={(e) => {
                              setScenario("Custom");
                              setAssumptions((a) => ({
                                ...a,
                                growth: a.growth.map((x, j) =>
                                  j === i ? Number(e.target.value) / 100 : x,
                                ),
                              }));
                            }}
                          />
                        </label>
                      ))}
                    </div>
                    {field("Operating margin", "operating_margin", -50, 80)}
                    {field("Operating tax rate", "tax_rate", 0, 60)}
                    {field("D&A / revenue", "da_ratio", 0, 50)}
                    {field("Capex / revenue", "capex_ratio", 0, 50)}
                    {field("Operating NWC / revenue", "nwc_ratio", -50, 50)}
                    {field("Discount rate", "discount_rate", 0.1, 50)}
                    {field("Terminal growth", "terminal_growth", -5, 10)}
                    <p className="table-note">
                      All forecast values are assumptions. No tax credit for
                      losses. NWC excludes cash and debt conceptually; the ratio
                      is an input, not total current assets less liabilities.
                    </p>
                  </section>
                  <section className="card valuation-result">
                    <div className="card-header">
                      <h2>Enterprise value</h2>
                      <span className="small-tag">
                        {calculating ? "CALCULATING…" : "SCENARIO OUTPUT"}
                      </span>
                    </div>
                    {valuationError && (
                      <p className="error" role="alert">
                        {valuationError}
                      </p>
                    )}
                    {valuation && (
                      <>
                        <div
                          className="ev-number"
                          data-testid="enterprise-value"
                        >
                          {money(valuation.enterprise_value)}
                        </div>
                        <div className="ev-unit">
                          USD million · no equity bridge or per-share value
                        </div>
                        <div className="terminal-note">
                          {pct(valuation.terminal_share)} from discounted
                          terminal value{" "}
                          <span>Year-end discount convention</span>
                        </div>
                        <h3 className="chart-label">
                          Forecast free cash flow to the firm
                        </h3>
                        <div className="bars">
                          {valuation.years.map((y) => (
                            <div className="bar-column" key={y.year}>
                              <span>{money(y.fcff)}</span>
                              <div
                                className={y.fcff < 0 ? "bar negative" : "bar"}
                                style={{
                                  height: `${Math.max(3, (Math.abs(y.fcff) / Math.max(1, ...valuation.years.map((x) => Math.abs(x.fcff)))) * 95)}px`,
                                }}
                              />
                              <small>Year {y.year}</small>
                            </div>
                          ))}
                        </div>
                        <p className="chart-footnote">
                          Bar height shows magnitude. Negative cash flows are
                          red and labeled with a minus sign.
                        </p>
                        <p className="formula">
                          FCFF = EBIT − operating tax + D&A − capex − ΔNWC
                        </p>
                        <h3 className="chart-label">
                          Sensitivity / enterprise value
                        </h3>
                        <div className="table-scroll">
                          <table className="sensitivity">
                            <thead>
                              <tr>
                                <th>Discount rate ↓ / g →</th>
                                {Array.from(
                                  new Set(
                                    valuation.sensitivity.map(
                                      (c) => c.terminal_growth,
                                    ),
                                  ),
                                ).map((g) => (
                                  <th key={g}>{pct(g)}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {Array.from(
                                new Set(
                                  valuation.sensitivity.map(
                                    (c) => c.discount_rate,
                                  ),
                                ),
                              ).map((w) => (
                                <tr key={w}>
                                  <th>{pct(w)}</th>
                                  {valuation.sensitivity
                                    .filter((c) => c.discount_rate === w)
                                    .map((c) => (
                                      <td
                                        key={c.terminal_growth}
                                        className={
                                          Math.abs(
                                            w - assumptions.discount_rate,
                                          ) < 0.00001 &&
                                          Math.abs(
                                            c.terminal_growth -
                                              assumptions.terminal_growth,
                                          ) < 0.00001
                                            ? "base-cell"
                                            : ""
                                        }
                                      >
                                        {c.enterprise_value === null
                                          ? "Invalid"
                                          : money(c.enterprise_value)}
                                      </td>
                                    ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        <p className="table-note">
                          Terminal year-six cash flow is recomputed using
                          terminal growth. Discount rate must exceed terminal
                          growth. This educational model omits acquisitions,
                          lease adjustments and a market-price comparison.
                        </p>
                        <button
                          className="button primary"
                          onClick={download}
                          disabled={calculating || exporting}
                        >
                          <Download size={16} />
                          Export this scenario to PDF
                        </button>
                      </>
                    )}
                  </section>
                </div>
              )}
            </>
          )}
          {tab === "Sources & Evaluation" && (
            <>
              <div className="source-intro">
                <ShieldCheck size={24} />
                <p>
                  <strong>
                    Small enough to inspect. Explicit enough to reproduce.
                  </strong>
                  <br />
                  Six annual filings, three companies and two fiscal years. Full
                  reports and model weights stay in the local cache.
                </p>
              </div>
              <section className="card">
                <div className="card-header">
                  <h2>Official source register</h2>
                  <span className="small-tag">PUBLICATION-DATE FILTERED</span>
                </div>
                {sources.length ? (
                  sources.map((s) => (
                    <div className="source-row" key={s.id}>
                      <span className="file-icon">
                        <FileText size={20} />
                      </span>
                      <div>
                        <h3>
                          {s.id} <span>Form 10-K</span>
                        </h3>
                        <p>
                          Filed {s.filed} · CIK {s.cik} · {s.accession}
                        </p>
                        <details>
                          <summary>Provenance & fingerprint</summary>
                          <code>SHA-256 {s.sha256}</code>
                          <p>
                            Retrieved {s.retrieved}
                            <br />
                            Parser {s.parser_version}
                          </p>
                        </details>
                      </div>
                      <a
                        aria-label={`Open ${s.id} source`}
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <ArrowUpRight size={19} />
                      </a>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">
                    {dataLoading
                      ? "Loading official sources…"
                      : "No source was published by the selected date."}
                  </div>
                )}
              </section>
              <div className="sources-grid">
                <section className="card method-card">
                  <FlaskConical size={22} />
                  <h2>Evaluation, without shortcuts</h2>
                  <p>
                    Lexical PostgreSQL search is compared with MiniLM + lexical
                    reciprocal-rank fusion on the same questions. The real local
                    model is evaluated separately from deterministic CI.
                  </p>
                  <p>
                    Reference evidence is source-reviewed by the coding agent.
                    Independent human review remains outstanding. Citation-ID
                    validity does not establish semantic support.
                  </p>
                  <details open>
                    <summary>Recorded evaluation results</summary>
                    <pre className="evaluation-json">
                      {JSON.stringify(evaluation, null, 2)}
                    </pre>
                  </details>
                </section>
                <section className="card method-card">
                  <BookOpen size={22} />
                  <h2>Scope & limitations</h2>
                  <p>
                    Research is restricted to cached 2023–2024 annual filings,
                    as published by your analysis date (end of day). It performs
                    no live web search.
                  </p>
                  <p>
                    Qwen 1.5B is a small local model. It can misinterpret
                    evidence. Use the evidence desk to check every material
                    claim.
                  </p>
                  <p>
                    The DCF is an educational scenario in USD millions.
                    Forecasts are explicit assumptions; no share price,
                    investment recommendation or valuation multiple is supplied.
                  </p>
                  <div className="license-note">
                    Local models: Qwen2.5 1.5B + MiniLM
                    <br />
                    Apache-2.0 licenses · no paid API
                  </div>
                </section>
              </div>
            </>
          )}
          <footer>
            <span>
              RESEARCHDESK <b>/</b> Evidence before opinion.
            </span>
            <span>Educational research · No investment recommendation</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
function Metric({
  label,
  value,
  suffix,
  detail,
}: {
  label: string;
  value: string;
  suffix?: string;
  detail: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>
        {value}
        <small>{suffix}</small>
      </strong>
      <p>{detail}</p>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
