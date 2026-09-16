# Ledgerline — Banking Facility Interest Working

## Original problem statement
Create a desktop application for Banking Facility – CC & WCDL Interest Working rather than only an Excel file. It should calculate CC interest day-wise from actual bank transactions/balances, WCDL interest from principal/rate/tenor, support multiple banks, facility master data, statement import, bank-vs-our-working reconciliation, reports, and an offline desktop-style experience.

## Architecture decisions
- Desktop-style responsive React workspace with a dark navigation rail and high-contrast financial tables.
- FastAPI `/api` read endpoints provide the controlled sample portfolio and working ledgers.
- Frontend uses the configured `REACT_APP_BACKEND_URL` and has a local fallback so the workspace remains usable offline.
- Default calculation convention shown in the product is Actual days / 365.
- No login in the MVP.

## User personas
- Finance controller reviewing interest expense and bank variances.
- Treasury or accounts executive maintaining facilities and transaction working.
- CFO or reviewer consuming reconciliation and monthly MIS reports.

## Core requirements (static)
- Dashboard with sanctioned limit, outstanding, available limit, current month/YTD interest, bank exposure, and variance.
- Facility Master for CC and WCDL facilities across multiple banks.
- CC Interest Working with date, value date, debit, credit, closing outstanding, days, rate, calculated interest, bank interest, and difference.
- WCDL Interest Working with loan, drawdown, principal, tenor, repayment, prepayment, interest, bank interest, and variance.
- Bank reconciliation and report centre.
- Import/export entry points for the next persistence phase.

## What's been implemented
- 2026-09-16: Replaced starter splash with Ledgerline workspace and responsive navigation.
- 2026-09-16: Added Dashboard, Facility Master, CC and WCDL working ledgers, reconciliation, and reports screens with realistic INR sample data.
- 2026-09-16: Added FastAPI endpoints for dashboard, facilities, CC working, WCDL working, and reconciliation.
- 2026-09-16: Added period selector, facility search filtering, mobile navigation, action feedback, and required test IDs.

## Prioritized backlog
- P0: Persist facility, transaction, and working edits in MongoDB.
- P0: Implement CSV/XLSX upload parsing and transaction mapping.
- P1: Add actual export generation for Excel and PDF.
- P1: Add configurable day-count convention and rate-change history.
- P2: Package the responsive workspace as a Windows desktop executable.

## Remaining next tasks
1. Build add/edit facility forms and save them through FastAPI.
2. Add CSV/XLSX import preview with column mapping and validation.
3. Replace local feedback-only report actions with downloadable Excel/PDF files.
4. Add monthly filters and bank/facility drill-down charts.