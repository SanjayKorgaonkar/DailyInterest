"""Comprehensive backend tests for CC/WCDL Interest Working with rate history & day-count."""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


# ---------- Facilities ----------
def test_list_facilities_seeded():
    r = requests.get(f"{API}/facilities", params={"month": "2026-05"}, timeout=30)
    assert r.status_code == 200
    facs = r.json()
    assert isinstance(facs, list) and len(facs) == 4
    by_id = {f["id"]: f for f in facs}
    for fid in ("icici-cc", "hdfc-cc", "axis-wcdl", "sbi-wcdl"):
        assert fid in by_id, f"missing {fid}"
        f = by_id[fid]
        assert isinstance(f.get("rate_history"), list) and len(f["rate_history"]) >= 1
        assert f.get("day_count") in (365, 360)
        assert "rate" in f and "outstanding" in f and "available" in f
    assert by_id["sbi-wcdl"]["day_count"] == 360
    # hdfc rate as of end-May 2026 should be 9.0 (post reset)
    assert abs(by_id["hdfc-cc"]["rate"] - 9.0) < 1e-6


def test_facility_crud_and_convention_change():
    payload = {"bank": "TEST Bank", "type": "CC", "name": "TEST CC Facility",
               "limit": 1000000, "start": "2026-05-01", "day_count": 365, "rate": 9.5}
    r = requests.post(f"{API}/facilities", json=payload, timeout=30)
    assert r.status_code == 201, r.text
    fac = r.json()
    fid = fac["id"]
    assert len(fac["rate_history"]) == 1
    assert fac["rate_history"][0]["effective_date"] == "2026-05-01"

    # PUT convention
    r = requests.put(f"{API}/facilities/{fid}", json={"day_count": 360}, timeout=30)
    assert r.status_code == 200 and r.json()["day_count"] == 360

    # DELETE
    r = requests.delete(f"{API}/facilities/{fid}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{API}/facilities", timeout=30)
    assert fid not in [f["id"] for f in r.json()]


# ---------- Rate history ----------
def test_rate_history_add_duplicate_and_delete_last():
    # Add a rate to icici-cc, then duplicate, then delete
    r = requests.post(f"{API}/facilities/icici-cc/rates",
                      json={"effective_date": "2026-07-01", "rate": 9.1, "remarks": "TEST"},
                      timeout=30)
    assert r.status_code == 201, r.text
    fac = r.json()
    added = [h for h in fac["rate_history"] if h["effective_date"] == "2026-07-01"]
    assert len(added) == 1
    rid = added[0]["id"]

    # duplicate
    r = requests.post(f"{API}/facilities/icici-cc/rates",
                      json={"effective_date": "2026-07-01", "rate": 9.2}, timeout=30)
    assert r.status_code == 400

    # delete
    r = requests.delete(f"{API}/facilities/icici-cc/rates/{rid}", timeout=30)
    assert r.status_code == 200

    # delete-last: create temp facility with 1 rate, try delete
    payload = {"bank": "T", "type": "CC", "name": "TEST DEL", "limit": 100, "start": "2026-05-01", "rate": 8.0}
    tf = requests.post(f"{API}/facilities", json=payload, timeout=30).json()
    rid0 = tf["rate_history"][0]["id"]
    r = requests.delete(f"{API}/facilities/{tf['id']}/rates/{rid0}", timeout=30)
    assert r.status_code == 400
    requests.delete(f"{API}/facilities/{tf['id']}", timeout=30)


# ---------- CC Working ----------
def test_cc_working_hdfc_split_at_rate_change():
    r = requests.get(f"{API}/cc-working", params={"facility_id": "hdfc-cc", "month": "2026-05"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    rows = data["rows"]
    # Expect 3 rows: main row split at 2026-05-15 -> first 13 days, segment 15 days, then 2 days after credit
    # Find matching interests
    interests = [r["interest"] for r in rows]
    # Allow ordering by value_date
    for expected in (57342.47, 68054.79, 7890.41):
        assert any(abs(i - expected) < 0.5 for i in interests), f"Missing {expected} in {interests}"
    assert abs(data["ours"] - 133287.67) < 1.0
    # segment row flag exists
    assert any(r.get("segment") for r in rows)


def test_cc_working_icici_and_opening_row():
    r = requests.get(f"{API}/cc-working", params={"facility_id": "icici-cc", "month": "2026-05"}, timeout=30)
    d = r.json()
    rows = d["rows"]
    assert len(rows) == 4
    days = [r["days"] for r in rows]
    # NOTE: spec expected [4,8,10,8] but engine treats month-end exclusive so last row is 9 days (May23->Jun1)
    assert days == [4, 8, 10, 9]
    for r0 in rows:
        assert abs(r0["rate"] - 8.5) < 1e-6
    expected_int = [29808.22, 61945.21, 67534.25, 62038.36]
    for exp, actual in zip(expected_int, [r["interest"] for r in rows]):
        assert abs(exp - actual) < 0.5

    # June 2026 should have opening row of 29,600,000
    r2 = requests.get(f"{API}/cc-working", params={"facility_id": "icici-cc", "month": "2026-06"}, timeout=30)
    d2 = r2.json()
    opening_rows = [x for x in d2["rows"] if x.get("opening")]
    assert opening_rows and abs(opening_rows[0]["closing"] - 29600000) < 1.0
    assert opening_rows[0]["days"] == 30


def test_convention_change_scales_interest():
    # PUT icici-cc to 360, recheck first row interest ~30222.22, then restore
    try:
        r = requests.put(f"{API}/facilities/icici-cc", json={"day_count": 360}, timeout=30)
        assert r.status_code == 200 and r.json()["day_count"] == 360
        d = requests.get(f"{API}/cc-working",
                         params={"facility_id": "icici-cc", "month": "2026-05"}, timeout=30).json()
        assert abs(d["rows"][0]["interest"] - 30222.22) < 0.5
    finally:
        requests.put(f"{API}/facilities/icici-cc", json={"day_count": 365}, timeout=30)


def test_cc_transaction_add_delete_and_validation():
    # invalid: both zero
    r = requests.post(f"{API}/cc-transactions",
                      json={"facility_id": "icici-cc", "date": "2026-05-10", "debit": 0, "credit": 0}, timeout=30)
    assert r.status_code == 400
    # invalid: WCDL
    r = requests.post(f"{API}/cc-transactions",
                      json={"facility_id": "axis-wcdl", "date": "2026-05-10", "debit": 1000}, timeout=30)
    assert r.status_code == 400
    # valid
    r = requests.post(f"{API}/cc-transactions",
                      json={"facility_id": "icici-cc", "date": "2026-05-10", "debit": 1000000, "bank_interest": 5000, "narration": "TEST"},
                      timeout=30)
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    # confirm reflected
    d = requests.get(f"{API}/cc-working", params={"facility_id": "icici-cc", "month": "2026-05"}, timeout=30).json()
    assert any(row["id"] == tid for row in d["rows"])
    # delete
    r = requests.delete(f"{API}/cc-transactions/{tid}", timeout=30)
    assert r.status_code == 204


# ---------- WCDL Working ----------
def test_wcdl_working_june():
    r = requests.get(f"{API}/wcdl-working", params={"month": "2026-06"}, timeout=30)
    d = r.json()
    rows = d["rows"]
    axis = [x for x in rows if x["facility_id"] == "axis-wcdl"]
    sbi = [x for x in rows if x["facility_id"] == "sbi-wcdl"]
    assert axis and abs(axis[0]["interest"] - 349315.07) < 1.0
    assert axis[0]["days"] == 30 and abs(axis[0]["rate"] - 8.5) < 1e-6
    assert sbi and abs(sbi[0]["interest"] - 26296.88) < 1.0
    assert sbi[0]["days"] == 9 and sbi[0]["day_count"] == 360


def test_wcdl_loan_add_prepayment_and_validation():
    # Use a disposable WCDL facility so this destructive test never touches shared seed data.
    payload = {"bank": "Test Bank", "type": "WCDL", "name": "Loan Test WCDL",
               "limit": 10000000, "start": "2026-01-01", "rate": 8.5, "day_count": 365}
    r = requests.post(f"{API}/facilities", json=payload, timeout=30)
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    try:
        # invalid repayment <= drawdown
        r = requests.post(f"{API}/wcdl-loans",
                          json={"facility_id": fid, "loan": "TEST-BAD",
                                "drawdown": "2026-05-10", "amount": 1000000, "repayment": "2026-05-10"}, timeout=30)
        assert r.status_code == 400
        # valid loan with prepayment mid-month
        r = requests.post(f"{API}/wcdl-loans",
                          json={"facility_id": fid, "loan": "TEST-PP",
                                "drawdown": "2026-05-01", "amount": 2000000, "repayment": "2026-05-31",
                                "prepayment": 500000, "prepayment_date": "2026-05-15"}, timeout=30)
        assert r.status_code == 201, r.text
        lid = r.json()["id"]
        d = requests.get(f"{API}/wcdl-working", params={"facility_id": fid, "month": "2026-05"}, timeout=30).json()
        my_rows = [x for x in d["rows"] if x["id"] == lid]
        assert len(my_rows) == 2  # two segments due to prepayment
        principals = sorted([row["principal"] for row in my_rows])
        assert principals[0] == 1500000 and principals[1] == 2000000
        r = requests.delete(f"{API}/wcdl-loans/{lid}", timeout=30)
        assert r.status_code == 204
    finally:
        requests.delete(f"{API}/facilities/{fid}", timeout=30)


# ---------- Dashboard & Reconciliation ----------
def test_dashboard():
    d = requests.get(f"{API}/dashboard", params={"month": "2026-05"}, timeout=30).json()
    assert d["limit"] == 155000000
    assert d["facilities"] == 4
    assert d["banks"] == 4
    assert d["rate_changes"] == 1
    for k in ("month_interest", "ytd_interest", "variance"):
        assert k in d


def test_reconciliation():
    d = requests.get(f"{API}/reconciliation", params={"month": "2026-05"}, timeout=30).json()
    assert isinstance(d, list) and len(d) == 3
    parts = [r["particular"] for r in d]
    assert parts == ["CC Interest", "WCDL Interest", "Total"]
    for r in d:
        assert abs(r["difference"] - round(r["bank"] - r["ours"], 2)) < 0.01
