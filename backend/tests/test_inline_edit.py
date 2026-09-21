"""Tests for the new inline-edit PUT endpoints (facilities, cc-transactions, wcdl-loans)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://daily-interest-pro.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s
    # Final cleanup: purge any TEST_ facilities that survived
    try:
        facs = s.get(f"{API}/facilities").json()
        for f in facs:
            if f.get("name", "").startswith("TEST_") or f.get("bank", "").startswith("TEST_"):
                s.delete(f"{API}/facilities/{f['id']}")
    except Exception:
        pass


def _create_cc(session):
    r = session.post(f"{API}/facilities", json={
        "bank": "TEST_Bank", "type": "CC", "name": "TEST_CC1",
        "limit": 1000000, "start": "2025-01-01", "maturity": "On demand",
        "day_count": 365, "rate": 9.5,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _create_wcdl(session, ftype="WCDL"):
    r = session.post(f"{API}/facilities", json={
        "bank": "TEST_Bank", "type": ftype, "name": f"TEST_{ftype}1",
        "limit": 2000000, "start": "2025-01-01", "maturity": "2026-12-31",
        "day_count": 365, "rate": 8.5,
    })
    assert r.status_code == 201, r.text
    return r.json()


class TestFacilityUpdate:
    def test_update_facility_persists(self, session):
        fac = _create_cc(session)
        fid = fac["id"]
        try:
            r = session.put(f"{API}/facilities/{fid}", json={
                "limit": 1500000, "maturity": "2027-03-31", "day_count": 360,
            })
            assert r.status_code == 200
            data = r.json()
            assert data["limit"] == 1500000
            assert data["maturity"] == "2027-03-31"
            assert data["day_count"] == 360
            # verify persisted
            g = session.get(f"{API}/facilities").json()
            match = next(f for f in g if f["id"] == fid)
            assert match["limit"] == 1500000
            assert match["day_count"] == 360
        finally:
            session.delete(f"{API}/facilities/{fid}")


class TestCCTransactionUpdate:
    def test_update_cc_tx_and_validation(self, session):
        fac = _create_cc(session)
        fid = fac["id"]
        try:
            r = session.post(f"{API}/cc-transactions", json={
                "facility_id": fid, "date": "2025-06-01", "debit": 100000, "credit": 0,
            })
            assert r.status_code == 201
            tid = r.json()["id"]

            # Update debit
            r2 = session.put(f"{API}/cc-transactions/{tid}", json={"debit": 200000})
            assert r2.status_code == 200
            assert r2.json()["debit"] == 200000

            # Validation: both zero => 400
            r3 = session.put(f"{API}/cc-transactions/{tid}", json={"debit": 0, "credit": 0})
            assert r3.status_code == 400
            assert "debit" in r3.json().get("detail", "").lower()

            # 404 for unknown id
            r4 = session.put(f"{API}/cc-transactions/does-not-exist", json={"debit": 1})
            assert r4.status_code == 404
        finally:
            session.delete(f"{API}/facilities/{fid}")


class TestWCDLLoanUpdate:
    @pytest.mark.parametrize("ftype", ["WCDL", "GML"])
    def test_update_loan_and_validation(self, session, ftype):
        fac = _create_wcdl(session, ftype)
        fid = fac["id"]
        try:
            r = session.post(f"{API}/wcdl-loans", json={
                "facility_id": fid, "loan": "L001",
                "drawdown": "2025-06-01", "amount": 500000, "repayment": "2025-09-01",
            })
            assert r.status_code == 201, r.text
            lid = r.json()["id"]

            # Update amount
            r2 = session.put(f"{API}/wcdl-loans/{lid}", json={"amount": 600000, "repayment": "2025-10-01"})
            assert r2.status_code == 200
            assert r2.json()["amount"] == 600000
            assert r2.json()["repayment"] == "2025-10-01"

            # Validation: repayment before drawdown
            r3 = session.put(f"{API}/wcdl-loans/{lid}", json={"repayment": "2025-05-01"})
            assert r3.status_code == 400
            assert "repayment" in r3.json().get("detail", "").lower()

            # 404
            r4 = session.put(f"{API}/wcdl-loans/does-not-exist", json={"amount": 1})
            assert r4.status_code == 404
        finally:
            session.delete(f"{API}/facilities/{fid}")


def test_db_empty_before_and_after(session):
    # Sanity that no residual TEST data remains
    facs = session.get(f"{API}/facilities").json()
    residual = [f for f in facs if f.get("name", "").startswith("TEST_")]
    assert residual == [], f"Residual test facilities: {residual}"
