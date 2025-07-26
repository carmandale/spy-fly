Below is a concise but complete Product Specification for a web-based application that automates your daily SPY 0-DTE bull-call-spread workflow. It folds your existing logic into a lightweight, self-hosted tool with a simple browser UI, a Python back-end, and a daily scheduler.

⸻

1. Purpose & Goals

Goal	Detail
Automate your daily routine	Replicate the morning scan, spread selection, intraday monitoring, and EOD reporting with minimal clicks.
Educational / simulation focus	No order-routing; output is recommendations, P/L tracking, and alerts for paper trading.
Keep risk bounded	Enforce your 5 % buying-power and 1 : 1 R:R guard-rails programmatically.
Fast startup	Use widely-available free or inexpensive APIs and open-source libraries.
Low-friction UI	One-page dashboard you can load on laptop, tablet, or phone; no sign-up flows.


⸻

2. User Roles & Stories

Role	Key Stories
Trader (you)	1. “I open the dashboard at 9:45 ET and see whether today qualifies for a spread.”2. “I click ‘Recommend’ and instantly get 1–2 debit spreads sized to $5–10 k risk.”3. “I watch the live P/L meter; if target hits, I close manually.”4. “Every evening I get an email summarizing today’s hypothetical trade and a rolling equity curve.”
Observer (optional)	“I can read-only the dashboard to learn the process.”


⸻

3. Functional Requirements

3.1 Morning Scan (09:30-10:00 ET)
	•	Pull real-time SPY quote, VIX, overnight futures, and economic-calendar beats.
	•	Compute sentiment score (0-100) from:
	•	VIX level (< 16 → +20, 16-20 → +10, > 20 → 0).
	•	Overnight S&P futures direction (+20 if > 0.1 %).
	•	Rule-based news/X sentiment (+30).
	•	Technical “green” flags (RSI < 80, price > 50-MA, Bollinger squeeze) (+30).
	•	Decision gate: If score ≥ 60 and technicals bullish → continue; else terminate (“No trade today”).

3.2 Spread Selection
	•	Query 0-DTE option chain.
	•	Filter candidates:  • long strike ≈ spot + 0.5 % to 1 %  • short strike = long + 3-5 pts  • debit < 0.3 % of spot  • volume > 50 k; open interest > OI-threshold.
	•	Calculate probability-of-profit (> 40 %) with Black–Scholes (using VIX/100 for σ).
	•	Pick top two by Sharpe-like score = (max gain / max loss) × PoP.

3.3 Execution Checklist (Manual)
	•	Show recommended contracts & quantity to hit $5–10 k risk cap.
	•	Show break-even, max gain, and live Greeks.
	•	“Copy-to-clipboard” order ticket for broker.

3.4 Intraday Monitoring (Every 15 min)
	•	Refresh SPY price and spread mid-price.
	•	Visual P/L bar with green-to-red zones.
	•	Auto-alerts (browser push + email):  • +50 % of max profit → “Take partial profits?”  • –20 % of max risk → “Stop-loss reached.”

3.5 End-of-Day Report (16:10 ET)
	•	Append trade outcome to SQLite/PostgreSQL.
	•	E-mail summary: entry, exit, timestamps, P/L, running equity curve chart.
	•	Maintain CSV export for back-test comparison.

⸻

4. Non-Functional Requirements

Category	Spec
Latency	Dashboard load < 2 s; 15-min ticker poll completes < 2 s.
Scheduler accuracy	Jobs start within ±30 s (use APScheduler + timezone aware).
Security	No credentials stored in browser; API keys encrypted (.env + OS keyring).
Deployment	Docker-compose stack deployable to a $5/mo VPS or local Mac.
Observability	Log to rotating file; Prometheus metrics endpoint (/metrics).


⸻

5. System Architecture

┌────────────┐            HTTP/JSON           ┌─────────────┐
│  Browser    │  ────────────────►  ┌────────►│  FastAPI    │
│  (React)    │                     │          │  Backend    │
└────────────┘                     │          └─────▲───────┘
   ▲   ▲                           │                │
   │   │ WebSockets (live P/L)     │                │
   │   └───────────────────────────┘                │
   │                                                │
┌──┴───────┐  cron / APScheduler        SQL Alchemy │
│ Tasks    │  ────────────────►  ┌───────────────┐  │
│ (Morning │                     │  Database     │◄─┘
│  Scan,   │                     └───────────────┘
│  EOD)    │        REST/JSON  (quotes, chain, news)│
└──────────┘  ◄─────────────────────────────────────┘
                       External APIs

	•	Front-end: Vite + React + Tailwind.
	•	Back-end: Python 3.12, FastAPI, Pydantic, Starlette-WebSockets.
	•	Scheduler: APScheduler inside the FastAPI process (or Celery + Redis if scaling).
	•	DB: SQLite dev → PostgreSQL prod.
	•	APIs: Polygon.io (quote + options), FRED/AlphaVantage (VIX), NewsAPI/Twitter-scrape (sentiment).

⸻

6. UI / UX Outline

Screen	Components
Dashboard (default)	• Sentiment gauge (dial 0-100)• “Today’s Recommendation” card (strikes, debit, PoP, quantity)• Live P/L bar chart• ‘Execute’ copy-ticket button• Toggle to show Greek/time-decay graph
History	Table of past trades with sortable columns (date, strikes, risk, P/L%). CSV download.
Settings	API keys, risk % caps, alert e-mails, polling interval.
Logs	Scrollable text console + log-level filter.

Mobile friendly: single-column breakpoint < 768 px.

⸻

7. Key Modules & File Layout

spy-automator/
├─ backend/
│  ├─ main.py          # FastAPI entry
│  ├─ scheduler.py     # job definitions
│  ├─ spreads.py       # selection logic
│  ├─ data.py          # API wrappers, cache
│  ├─ models.py        # Pydantic + ORM
│  └─ emailer.py
├─ frontend/
│  ├─ src/
│  │  ├─ App.tsx
│  │  ├─ pages/
│  │  ├─ components/
│  │  └─ hooks/
│  └─ vite.config.ts
└─ docker-compose.yml


⸻

8. API Contract Example

GET /api/trade/today

{
  "sentimentScore": 67,
  "enabled": true,
  "spread": {
    "long": 637,
    "short": 640,
    "debit": 0.22,
    "pop": 0.45,
    "contracts": 200,
    "maxRisk": 4400,
    "maxGain": 55600
  }
}

WebSocket /ws/pl
	•	Server pushes { price, spreadPrice, pnlPct } every 15 min.

⸻

9. Risks & Mitigations

Risk	Mitigation
API rate limits	Local cache + exponential back-off; polygon free tier is ~5 calls/min.
Overnight spec changes (0-DTE rollout times, strike intervals)	Unit tests on chain parser; configurable strike-spacing.
Mis-scored sentiment	Use ensemble scoring; add fallback to “no trade.”
Legal/compliance	Appends “educational only / not financial advice” watermark in UI and e-mails.


⸻

10. Implementation Milestones (2-week MVP)

Day	Deliverable
1-2	Repo scaffold, Docker, FastAPI hello-world, React vite-init.
3-4	Polygon wrapper + basic sentiment calc.
5-6	Spread-selection algorithm w/ tests & mock chain.
7-8	Scheduler jobs + SQLite persistence.
9-10	Dashboard components & WebSocket live feed.
11	E-mail report + CSV export.
12	Settings page, env-var management.
13	End-to-end QA with paper-trade day.
14	VPS deploy, docs, hand-off.


⸻

Next Steps
	1.	Confirm tech stack & API provider preferences.
	2.	Decide hosting (local machine vs. VPS vs. container on existing infra).
	3.	Kick-off milestone 1 — scaffold and basic data pulls.

Let me know where you’d like deeper detail—wireframes, database schema, or initial code snippets—and we can proceed.