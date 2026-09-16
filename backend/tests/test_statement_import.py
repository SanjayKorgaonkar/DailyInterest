"""Backend tests for CC bank-statement CSV/XLSX import (parse + commit)."""
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


def _icici_id():
    r = requests.get(f"{API}/facilities", timeout=30)
    for f in r.json():
        if f["id"] == "icici-cc":
            return f["id"]
    pytest.skip("icici-cc facility missing")


def _cleanup(fid):
    txns = requests.get(f"{API}/cc-working", params={"facility_id": fid, "month": "2026-05"}, timeout=30).json()["rows"]
    for r in txns:
        if r.get("id") and not r.get("segment") and not r.get("opening"):
            requests.delete(f"{API}/cc-transactions/{r['id']}", timeout=30)


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


def test_dry_run_and_commit_and_persistence():
    fid = _icici_id()
    _cleanup(fid)
    # parse
    files = {"file": ("stmt.csv", CSV_STANDARD, "text/csv")}
    parsed = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30).json()
    mapping = parsed["mapping"]
    rows = parsed["rows"]
    # dry_run
    dry = requests.post(f"{API}/cc-transactions/import/commit",
                       json={"facility_id": fid, "mapping": mapping, "rows": rows, "dry_run": True}, timeout=30)
    assert dry.status_code == 201
    dd = dry.json()
    assert dd["inserted"] == 0
    assert dd["skipped"] == 2  # invalid date + no amount
    assert len(dd["transactions"]) == 3
    # commit
    commit = requests.post(f"{API}/cc-transactions/import/commit",
                          json={"facility_id": fid, "mapping": mapping, "rows": rows, "dry_run": False}, timeout=30)
    assert commit.status_code == 201
    cd = commit.json()
    assert cd["inserted"] == 3
    assert cd["skipped"] == 2
    # verify persisted via cc-working
    working = requests.get(f"{API}/cc-working", params={"facility_id": fid, "month": "2026-05"}, timeout=30).json()
    real_rows = [r for r in working["rows"] if not r.get("segment") and not r.get("opening")]
    dates = sorted(r["date"] for r in real_rows)
    assert "2026-05-01" in dates
    assert "2026-05-05" in dates
    assert "2026-05-10" in dates
    _cleanup(fid)


def test_commit_without_date_col_rejected():
    fid = _icici_id()
    r = requests.post(f"{API}/cc-transactions/import/commit",
                     json={"facility_id": fid, "mapping": {"date_col": None}, "rows": [], "dry_run": False}, timeout=30)
    assert r.status_code == 400


def test_single_amount_column_with_drcr():
    fid = _icici_id()
    _cleanup(fid)
    files = {"file": ("s.csv", CSV_SINGLE_AMOUNT, "text/csv")}
    p = requests.post(f"{API}/cc-transactions/import/parse", files=files, timeout=30).json()
    # Override mapping to use amount_col + dr_cr_col path
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


def test_xlsx_parse_and_commit():
    pd = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
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
    fid = _icici_id()
    _cleanup(fid)
    c = requests.post(f"{API}/cc-transactions/import/commit",
                     json={"facility_id": fid, "mapping": d["mapping"], "rows": d["rows"], "dry_run": False}, timeout=30)
    assert c.status_code == 201
    assert c.json()["inserted"] == 2
    _cleanup(fid)


def test_commit_on_wcdl_rejected():
    r = requests.post(f"{API}/cc-transactions/import/commit",
                     json={"facility_id": "axis-wcdl", "mapping": {"date_col": "Date"}, "rows": [], "dry_run": False}, timeout=30)
    assert r.status_code == 400
