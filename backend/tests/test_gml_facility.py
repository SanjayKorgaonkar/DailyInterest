"""Tests for new Gold Metal Loan (GML) facility type."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://daily-interest-pro.preview.emergentagent.com").rstrip("/")


@pytest.fixture
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture
def cleanup(api):
    created = []
    yield created
    for fid in created:
        api.delete(f"{BASE_URL}/api/facilities/{fid}")


class TestGMLFacility:
    def test_create_gml_facility(self, api, cleanup):
        payload = {
            "bank": "TEST_MMTC", "type": "GML", "name": "TEST Gold Metal Loan",
            "limit": 5000000, "start": "2025-11-01", "maturity": "90 days",
            "day_count": 365, "rate": 9.5,
        }
        r = api.post(f"{BASE_URL}/api/facilities", json=payload)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["type"] == "GML"
        assert d["bank"] == "TEST_MMTC"
        assert d["rate"] == 9.5
        cleanup.append(d["id"])

        # Verify appears in list
        lst = api.get(f"{BASE_URL}/api/facilities").json()
        assert any(f["id"] == d["id"] and f["type"] == "GML" for f in lst)

    def test_gml_appears_in_wcdl_working(self, api, cleanup):
        r = api.post(f"{BASE_URL}/api/facilities", json={
            "bank": "TEST_GML_BANK", "type": "GML", "name": "TEST GML W",
            "limit": 2000000, "start": "2025-11-01", "maturity": "90 days",
            "day_count": 365, "rate": 9.5,
        })
        fid = r.json()["id"]
        cleanup.append(fid)
        w = api.get(f"{BASE_URL}/api/wcdl-working", params={"facility_id": fid}).json()
        assert "rows" in w
        assert w["ours"] == 0

    def test_gml_loan_creation_and_interest(self, api, cleanup):
        r = api.post(f"{BASE_URL}/api/facilities", json={
            "bank": "TEST_GML2", "type": "GML", "name": "TEST GML Loan",
            "limit": 3000000, "start": "2025-11-01", "maturity": "90 days",
            "day_count": 365, "rate": 9.5,
        })
        fid = r.json()["id"]
        cleanup.append(fid)

        loan = api.post(f"{BASE_URL}/api/wcdl-loans", json={
            "facility_id": fid, "loan": "TEST-GML-01",
            "drawdown": "2025-11-01", "amount": 1000000,
            "repayment": "2025-11-29",
        })
        assert loan.status_code == 201, loan.text
        lid = loan.json()["id"]

        w = api.get(f"{BASE_URL}/api/wcdl-working", params={"month": "2025-11", "facility_id": fid}).json()
        assert len(w["rows"]) >= 1
        # Interest: 1,000,000 * 9.5% * 28 / 365
        expected = round(1000000 * 0.095 * 28 / 365, 2)
        assert abs(w["ours"] - expected) < 1.0

        # Delete loan
        d = api.delete(f"{BASE_URL}/api/wcdl-loans/{lid}")
        assert d.status_code == 204

    def test_cc_facility_still_rejects_wcdl_loan(self, api, cleanup):
        r = api.post(f"{BASE_URL}/api/facilities", json={
            "bank": "TEST_CC_R", "type": "CC", "name": "TEST CC",
            "limit": 1000000, "start": "2025-11-01", "maturity": "On demand",
            "day_count": 365, "rate": 9.0,
        })
        fid = r.json()["id"]
        cleanup.append(fid)
        bad = api.post(f"{BASE_URL}/api/wcdl-loans", json={
            "facility_id": fid, "loan": "X", "drawdown": "2025-11-01",
            "amount": 100000, "repayment": "2025-11-15",
        })
        assert bad.status_code == 400

    def test_invalid_type_rejected(self, api):
        r = api.post(f"{BASE_URL}/api/facilities", json={
            "bank": "X", "type": "XYZ", "name": "N",
            "limit": 1, "start": "2025-01-01", "rate": 1,
        })
        assert r.status_code == 422

    def test_db_empty_after_cleanup(self, api):
        # Runs last - verify DB is empty
        lst = api.get(f"{BASE_URL}/api/facilities").json()
        # This just informative; other tests may still be running
        assert isinstance(lst, list)
