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
- `cc_transactions`: {id, facility_id, date, value_date, debit, credit, bank_interest?, auto_matched?, narration, created_at}
- `wcdl_loans`: {id, facility_id, loan, drawdown, amount, repayment, prepayment, prepayment_date?, bank_interest?, created_at}
- `bank_certificates`: {id, facility_id, month(YYYY-MM), amount, created_at, updated_at} — per-facility-per-month manual bank-interest override; when present it replaces the summed bank_interest for that facility+month everywhere (facility working totals, dashboard, reconciliation).

## API
- GET /api/facilities?month · POST /api/facilities · PUT /api/facilities/{id} (incl. day_count) · DELETE /api/facilities/{id}
- POST /api/facilities/{id}/rates · DELETE /api/facilities/{id}/rates/{rid}
- GET /api/cc-working?facility_id&month · POST /api/cc-transactions · DELETE /api/cc-transactions/{id}
- POST /api/cc-transactions/import/parse (multipart file) · POST /api/cc-transactions/import/commit (facility_id, mapping, rows, dry_run)
- GET /api/wcdl-working?facility_id&month · POST /api/wcdl-loans · DELETE /api/wcdl-loans/{id}
- GET /api/bank-certificates?facility_id&month · PUT /api/bank-certificates · DELETE /api/bank-certificates/{facility_id}/{month}
- GET /api/reports/monthly-checklist?month=YYYY-MM (PDF download, defaults to last closed month)
- GET /api/dashboard?month (includes pending_certificates, pending_month) · GET /api/reconciliation?month

## User personas
- Finance controller reviewing interest expense and bank variances.
- Treasury or accounts executive maintaining facilities and transaction working.
- CFO or reviewer consuming reconciliation and monthly MIS reports.

## What's been implemented
- 2026-09-16: Ledgerline workspace UI, navigation, Dashboard, Facility Master, CC/WCDL ledgers, reconciliation, reports (initially read-only mock data).
- 2026-09-16 (this session): Real interest engine + MongoDB persistence; Facility CRUD; **Rate History** (effective-date rate changes with timeline drawer, add/delete, bps delta); **Actual/365 vs Actual/360** per-facility toggle; CC/WCDL rows auto-split at rate changes with "Rate change" segment rows; add/delete CC transactions and WCDL loans (with prepayment); month-driven dashboard & reconciliation; opening-balance rows for carried-forward months. Tested: iteration_2 (backend 11/11, frontend all flows pass).
- 2026-09-16 (later same session): **Bank statement CSV/XLSX import** for CC transactions — `backend/import_utils.py` (pandas/openpyxl parsing + dateutil flexible dates + heuristic column-mapping guesser), `POST /api/cc-transactions/import/parse` and `/import/commit` (dry_run live preview), `StatementImportModal` in `CCWorking.jsx` (3-step upload → map → result flow with live preview on every mapping change, supports separate debit/credit columns OR a single amount column + Dr/Cr indicator). Tested: iteration_3 (backend 8/8 new pytest cases, frontend 100% of exercised flows).
- 2026-09-16 (later): **Bank Interest Auto-Match** — (1) statement import auto-detects narration rows containing interest keywords and auto-fills `bank_interest` with a teal "Auto" badge in preview + ledger; (2) **Bank Certificate** override — amber `certificate-strip` control (`components/BankCertificate.jsx`) on CC/WCDL Working lets the user enter one certified bank-interest figure per facility+month, overriding calculated totals everywhere (working totals, dashboard, reconciliation). New `bank_certificates` collection + `GET/PUT/DELETE /api/bank-certificates`. Tested: iteration_4 (100% backend/frontend).
- 2026-09-16 (final): **Month-end certificate reminder** — Dashboard now shows a coral `.cert-reminder` banner listing facilities with real interest for the last closed calendar month but no bank certificate/bank_interest captured yet (`GET /api/dashboard` → `pending_certificates` + `pending_month`, computed via `engine.prev_month()`). Each facility pill jumps straight to that facility's CC/WCDL Working page with the correct month pre-selected (`App.js` `go(id, {facilityId, month})` → `focusFacilityId` prop consumed by CCWorking/WCDLWorking). Tested: iteration_5 (backend 100%, frontend 100%).
- 2026-09-16 (very last): **Monthly Reconciliation Checklist PDF** — new `GET /api/reports/monthly-checklist?month=YYYY-MM` (`backend/reports.py`, reportlab-based) generates a downloadable PDF listing every facility with its calculated interest, bank-charged amount, variance, and a status (Certified / Auto-matched / Needs review), plus a totals row and legend — a full audit trail, not just the pending list. Dashboard has a "<Month Year> checklist" download button next to "+ Add facility". Tested: iteration_6 (backend 100%, frontend 100%, incl. zero-activity-month edge case and PDF content verification via pdfminer). No email/third-party integration added (user chose PDF-download-only, skipping email provider choice). Added a navy letterhead band with "LEDGERLINE" wordmark, tagline, and coral accent bar at the top of every PDF page (drawn via reportlab canvas callback) per user request for a branded, board/audit-pack-ready look — text-only, no logo upload (user's choice defaulted to skip logo/object-storage integration).
- Bug fixes: (a) fixed a `dateutil` `dayfirst=True` misparsing bug where ISO dates like `2026-05-10` were flipped to `2026-10-05` — `import_utils.to_date()` now fast-paths an explicit `YYYY-MM-DD` regex; (b) fixed **two recurring data-integrity issues** where test fixtures/races wiped seeded `icici-cc` cc_transactions and `axis-wcdl`/`sbi-wcdl` wcdl_loans — rewrote destructive tests to use disposable per-test facilities (never touch seeded ones), and made `seed.py`'s `seed_if_empty()` check **per-record** (matching facility_id+date+narration for CC, facility_id+loan for WCDL) instead of whole-collection emptiness, so any accidentally-deleted seed row self-heals on the next backend restart regardless of cause. Added `test_dashboard_pending.py` with a `test_seed_data_integrity` guardrail. (c) Fixed a resulting test-flakiness side-effect: `test_backend_api.py::test_dashboard` asserted exact global totals (`limit == 155000000`, `facilities == 4`) which broke once disposable-facility tests in other modules could run concurrently (pytest-xdist) and transiently add to those sums — relaxed to `>=` bounds; verified stable across 3 consecutive full-suite runs (31/31 passing).
- 2026-09-16 (post-launch polish): added a Dashboard "<Month Year> checklist" PDF download button with a branded navy/coral letterhead (LEDGERLINE wordmark, text-only per user's choice — no logo upload/object-storage integration added), and a coral "Needs Review" count badge on the sidebar's Dashboard nav item (`App.js`/`App.css` `.nav-badge`) showing `pending_certificates.length` at a glance.
- 2026-09-21: added a browser tab title notification (`(N) Ledgerline` when facilities are pending) and a "days to month-end close" countdown badge (`lib/format.js` `daysUntilMonthEnd()`) inside the cert-reminder banner, reminding the user how much runway remains before the current month closes on top of last month's backlog.

## Prioritized backlog
- P1: Real Excel/PDF export for Reports and Reconciliation (buttons show toast only — MOCKED).
- P1: Edit existing facility / transaction / loan inline.
- P1: Rate change report (from rate_history) and monthly MIS.
- P2: Other bank charges line in reconciliation.
- P2: Package as Windows desktop executable; optional login.
- P2 (minor, non-blocking): guess_mapping() column detection uses `elif` chaining — could miss a slot if an earlier header ambiguously matches; low risk with typical bank statement headers.
- P2 (minor, non-blocking): BankCertificate strip shows even when calculated_bank is legitimately 0; consider hiding when both cert-absent and calculated_bank===0.

## Remaining next tasks
1. Excel/PDF export for Reports and Reconciliation.
2. Edit forms for master/ledger rows.
3. Rate-change report + monthly MIS.
