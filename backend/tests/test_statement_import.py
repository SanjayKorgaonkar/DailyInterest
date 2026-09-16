"""Backend tests for CC bank-statement CSV/XLSX import (parse + commit).

Uses a disposable CC facility created per-test (never the shared seeded
icici-cc/hdfc-cc facilities) so destructive import/commit operations can
never wipe real seed data.
"""
import io
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

CSV_STANDARD = (
    "Txn Date,Value Date,Withdrawal Amt,Deposit Amt,Narration\n"
    "01-05-2026,01-05-2026,\"1,00,000.00\",,Payment to vendor\n"
    "05-05-2026,05-05-2026,,\"50,000.00\",NEFT from client\n"
    "10-05-2026,10-05-2026,\"2,00,000\",,Utility bill\n"
    "invalid,invalid,100,,Bad row\n"
    "15-05-2026,15-05-2026,,,No amounts\n"
).encode()

CSV_SINGLE_AMOUNT = (
    "Date,Amount,Type,Description\n"
    "02-05-2026,25000,DR,Purchase\n"
    "06-05-2026,75000,CR,Deposit\n"
).encode()


@pytest.fixture
def temp_cc_facility():
    """Create a disposable CC facility for this test only; deleting it cascades to its cc_transactions."""
    payload = {"bank": "Test Bank", "type": "CC", "name": "Import Test CC",
               "limit": 10000000, "start": "2026-01-01", "rate": 9.0, "day_count": 365}
    r = requests.post(f"{API}/facilities", json=payload, timeout=30)
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    yield fid
    requests.delete(f"{API}/facilities/{fid}", timeout=30)


def test_parse_csv_auto_mapping():
    files = {"file": ("stmt.csv", CSV_STANDARD, "text/csv")}
    r = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["row_count"] == 5
    m = d["mapping"]
    assert m["date_col"] == "Txn Date"
    assert m["value_date_col"] == "Value Date"
    assert m["debit_col"] == "Withdrawal Amt"
    assert m["credit_col"] == "Deposit Amt"
    assert m["narration_col"] == "Narration"


def test_parse_empty_file_rejected():
    files = {"file": ("empty.csv", b"", "text/csv")}
    r = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30)
    assert r.status_code == 400


def test_parse_headers_only_rejected():
    files = {"file": ("h.csv", b"Date,Amount\n", "text/csv")}
    r = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30)
    assert r.status_code == 400


def test_dry_run_and_commit_and_persistence(temp_cc_facility):
    fid = temp_cc_facility
    files = {"file": ("stmt.csv", CSV_STANDARD, "text/csv")}
    parsed = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30).json()
    mapping = parsed["mapping"]
    rows = parsed["rows"]
    dry = requests.post(f"{API}/cc-transactions/import/commit",
                       json={"facility_id": fid, "mapping": mapping, "rows": rows, "dry_run": True}, timeout=30)
    assert dry.status_code == 201
    dd = dry.json()
    assert dd["inserted"] == 0
    assert dd["skipped"] == 2  # invalid date + no amount
    assert len(dd["transactions"]) == 3
    commit = requests.post(f"{API}/cc-transactions/import/commit",
                          json={"facility_id": fid, "mapping": mapping, "rows": rows, "dry_run": False}, timeout=30)
    assert commit.status_code == 201
    cd = commit.json()
    assert cd["inserted"] == 3
    assert cd["skipped"] == 2
    working = requests.get(f"{API}/cc-working", params={"facility_id": fid, "month": "2026-05"}, timeout=30).json()
    real_rows = [r for r in working["rows"] if not r.get("segment") and not r.get("opening")]
    dates = sorted(r["date"] for r in real_rows)
    assert "2026-05-01" in dates
    assert "2026-05-05" in dates
    assert "2026-05-10" in dates


def test_commit_without_date_col_rejected(temp_cc_facility):
    r = requests.post(f"{API}/cc-transactions/import/commit",
                     json={"facility_id": temp_cc_facility, "mapping": {"date_col": None}, "rows": [], "dry_run": False}, timeout=30)
    assert r.status_code == 400


def test_single_amount_column_with_drcr(temp_cc_facility):
    fid = temp_cc_facility
    files = {"file": ("s.csv", CSV_SINGLE_AMOUNT, "text/csv")}
    p = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30).json()
    mapping = {"date_col": "Date", "value_date_col": "Date", "debit_col": None, "credit_col": None,
               "amount_col": "Amount", "dr_cr_col": "Type", "narration_col": "Description", "bank_interest_col": None}
    dry = requests.post(f"{API}/cc-transactions/import/commit",
                       json={"facility_id": fid, "mapping": mapping, "rows": p["rows"], "dry_run": True}, timeout=30)
    assert dry.status_code == 201
    txns = dry.json()["transactions"]
    assert len(txns) == 2
    by_date = {t["date"]: t for t in txns}
    assert by_date["2026-05-02"]["debit"] == 25000 and by_date["2026-05-02"]["credit"] == 0
    assert by_date["2026-05-06"]["credit"] == 75000 and by_date["2026-05-06"]["debit"] == 0


def test_xlsx_parse_and_commit(temp_cc_facility):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    fid = temp_cc_facility
    df = pd.DataFrame([
        {"Txn Date": "03-05-2026", "Value Date": "03-05-2026", "Withdrawal Amt": 10000, "Deposit Amt": None, "Narration": "Cheque"},
        {"Txn Date": "07-05-2026", "Value Date": "07-05-2026", "Withdrawal Amt": None, "Deposit Amt": 40000, "Narration": "NEFT"},
    ])
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    files = {"file": ("s.xlsx", buf.getvalue(),
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["row_count"] == 2
    assert d["mapping"]["date_col"] == "Txn Date"
    c = requests.post(f"{API}/cc-transactions/import/commit",
                     json={"facility_id": fid, "mapping": d["mapping"], "rows": d["rows"], "dry_run": False}, timeout=30)
    assert c.status_code == 201
    assert c.json()["inserted"] == 2


def test_iso_date_not_misparsed_as_month_first(temp_cc_facility):
    """2026-05-10 must parse as 10 May, not 5 Oct (regression for dateutil dayfirst quirk)."""
    fid = temp_cc_facility
    csv_bytes = (
        "Date,Debit,Credit,Narration\n"
        "2026-05-10,5000,,ISO date row\n"
    ).encode()
    files = {"file": ("iso.csv", csv_bytes, "text/csv")}
    parsed = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30).json()
    commit = requests.post(f"{API}/cc-transactions/import/commit",
                          json={"facility_id": fid, "mapping": parsed["mapping"], "rows": parsed["rows"], "dry_run": False},
                          timeout=30)
    assert commit.status_code == 201
    txns = commit.json()["transactions"]
    assert txns[0]["date"] == "2026-05-10"


def test_commit_on_wcdl_rejected():
    r = requests.post(f"{API}/cc-transactions/import/commit",
                     json={"facility_id": "axis-wcdl", "mapping": {"date_col": "Date"}, "rows": [], "dry_run": False}, timeout=30)
    assert r.status_code == 400
