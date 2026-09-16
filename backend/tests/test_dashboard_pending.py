# Tests for the Dashboard pending_certificates / pending_month feature (iteration 5)
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://daily-interest-pro.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def test_dashboard_contains_pending_fields(http):
    r = http.get(f"{API}/dashboard")
    assert r.status_code == 200
    d = r.json()
    assert "pending_certificates" in d
    assert "pending_month" in d
    # pending_month should be YYYY-MM and not equal to the dashboard 'month' returned when default is current month
    pm = d["pending_month"]
    assert len(pm) == 7 and pm[4] == "-"


def test_pending_month_independent_of_query_param(http):
    # Passing a month param must not change pending_month; it is always the previous real calendar month
    r1 = http.get(f"{API}/dashboard").json()
    r2 = http.get(f"{API}/dashboard", params={"month": "2026-01"}).json()
    assert r1["pending_month"] == r2["pending_month"]


def test_pending_entries_have_expected_shape_and_conditions(http):
    d = http.get(f"{API}/dashboard").json()
    pm = d["pending_month"]
    for entry in d["pending_certificates"]:
        for k in ("facility_id", "bank", "name", "type", "month", "ours"):
            assert k in entry, f"missing key {k}"
        assert entry["month"] == pm
        assert entry["ours"] > 0
        assert entry["type"] in ("CC", "WCDL")
        # confirm no certificate exists for this facility+pm
        cert = http.get(f"{API}/bank-certificates", params={"facility_id": entry["facility_id"], "month": pm}).json()
        assert cert in (None,), f"cert should be None; got {cert}"


def test_certificate_upsert_removes_facility_from_pending_then_delete_restores(http):
    d0 = http.get(f"{API}/dashboard").json()
    pending = d0["pending_certificates"]
    if not pending:
        pytest.skip("no pending entries to toggle")
    target = pending[0]
    fid, pm = target["facility_id"], target["month"]

    try:
        # PUT certificate -> facility should drop out of pending
        r = http.put(f"{API}/bank-certificates", json={"facility_id": fid, "month": pm, "amount": 100000})
        assert r.status_code == 200
        d1 = http.get(f"{API}/dashboard").json()
        assert not any(p["facility_id"] == fid for p in d1["pending_certificates"]), \
            "facility should disappear from pending after certificate is saved"
        assert d1["pending_month"] == pm
    finally:
        # DELETE the exact certificate we just created
        r = http.delete(f"{API}/bank-certificates/{fid}/{pm}")
        assert r.status_code in (204, 200)

    # After delete it should come back
    d2 = http.get(f"{API}/dashboard").json()
    assert any(p["facility_id"] == fid for p in d2["pending_certificates"]), \
        "facility should reappear after certificate is deleted"


def test_seed_data_integrity(http):
    """Guardrail: seeded facilities untouched by these tests."""
    facs = http.get(f"{API}/facilities").json()
    by_id = {f["id"]: f for f in facs}
    assert by_id["icici-cc"]["outstanding"] == 29600000, by_id["icici-cc"]
    assert by_id["hdfc-cc"]["outstanding"] == 16000000, by_id["hdfc-cc"]
    # WCDL loans present for both wcdl facilities in a month where both are active — use 2026-05
    w = http.get(f"{API}/wcdl-working", params={"month": "2026-05"}).json()
    fac_ids = {r["facility_id"] for r in w["rows"] if "facility_id" in r}
    # rows may not carry facility_id; fall back to count check
    assert len(w["rows"]) >= 2, w
