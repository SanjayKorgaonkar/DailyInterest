# Ledgerline — Banking Facility Interest Working

## Original problem statement
Create a desktop application for Banking Facility – CC & WCDL Interest Working rather than only an Excel file. It should calculate CC interest day-wise from actual bank transactions/balances, WCDL interest from principal/rate/tenor, support multiple banks, facility master data, statement import, bank-vs-our-working reconciliation, reports, and an offline desktop-style experience.

## Architecture decisions
- React SPA (custom CSS, "Swiss & High-Contrast Financial" theme) → FastAPI `/api` → MongoDB (Motor).
- Pages split into `frontend/src/pages/*` (Dashboard, Facilities, CCWorking, WCDLWorking, Reports/Reconciliation); shared `components/Modal.jsx`, `components/Header.jsx`, `lib/api.js`, `lib/format.js`.
- Backend split: `server.py` (API), `engine.py` (pure interest maths), `seed.py` (idempotent per-collection sample data).
- Interest engine: Interest = balance × applicable rate × days ÷ day_count. Rates looked up by effective date from `facility.rate_history`; periods split into separate rows at every rate change (and at WCDL prepayment date). Month-wise working: last period ends on the 1st of the next month (exclusive), so May totals 31 days.
- Day-count convention is per facility (`day_count`: 365 or 360).
- Period selector = calendar month (YYYY-MM); default current month. Indian FY (Apr–Mar) used for YTD.
- IDs are UUID strings; `_id` never leaves the API. No login in the MVP.

## Data model (MongoDB)
- `facilities`: {id, bank, type(CC|WCDL), name, limit, start, maturity, status, day_count, rate_history:[{id, effective_date, rate, remarks}], created_at}
- `cc_transactions`: {id, facility_id, date, value_date, debit, credit, bank_interest?, narration, created_at}
- `wcdl_loans`: {id, facility_id, loan, drawdown, amount, repayment, prepayment, prepayment_date?, bank_interest?, created_at}

## API
- GET /api/facilities?month · POST /api/facilities · PUT /api/facilities/{id} (incl. day_count) · DELETE /api/facilities/{id}
- POST /api/facilities/{id}/rates · DELETE /api/facilities/{id}/rates/{rid}
- GET /api/cc-working?facility_id&month · POST /api/cc-transactions · DELETE /api/cc-transactions/{id}
- GET /api/wcdl-working?facility_id&month · POST /api/wcdl-loans · DELETE /api/wcdl-loans/{id}
- GET /api/dashboard?month · GET /api/reconciliation?month

## User personas
- Finance controller reviewing interest expense and bank variances.
- Treasury or accounts executive maintaining facilities and transaction working.
- CFO or reviewer consuming reconciliation and monthly MIS reports.

## What's been implemented
- 2026-09-16: Ledgerline workspace UI, navigation, Dashboard, Facility Master, CC/WCDL ledgers, reconciliation, reports (initially read-only mock data).
- 2026-09-16 (this session): Real interest engine + MongoDB persistence; Facility CRUD; **Rate History** (effective-date rate changes with timeline drawer, add/delete, bps delta); **Actual/365 vs Actual/360** per-facility toggle; CC/WCDL rows auto-split at rate changes with "Rate change" segment rows; add/delete CC transactions and WCDL loans (with prepayment); month-driven dashboard & reconciliation; opening-balance rows for carried-forward months. Tested: iteration_2 (backend 11/11, frontend all flows pass).

## Prioritized backlog
- P0: CSV/XLSX bank statement import with column mapping → cc_transactions (button currently shows toast only — MOCKED).
- P1: Real Excel/PDF export for Reports and Reconciliation (buttons show toast only — MOCKED).
- P1: Edit existing facility / transaction / loan inline.
- P1: Rate change report (from rate_history) and monthly MIS.
- P2: Other bank charges line in reconciliation.
- P2: Package as Windows desktop executable; optional login.

## Remaining next tasks
1. Statement import (CSV/XLSX) with preview + mapping.
2. Excel/PDF export.
3. Edit forms for master/ledger rows.
