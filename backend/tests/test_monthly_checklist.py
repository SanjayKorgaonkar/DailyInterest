"""Tests for GET /api/reports/monthly-checklist PDF endpoint."""
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def _get(month=None):
    params = {"month": month} if month else {}
    return requests.get(f"{BASE_URL}/api/reports/monthly-checklist", params=params, timeout=30)


def test_default_month_returns_pdf():
    r = _get()
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd and "reconciliation-checklist-" in cd and ".pdf" in cd
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 500


def test_specific_month_returns_pdf():
    r = _get("2026-05")
    assert r.status_code == 200
    assert 'reconciliation-checklist-2026-05.pdf' in r.headers.get("content-disposition", "")
    assert r.content[:4] == b"%PDF"


def test_month_with_no_activity_still_returns_pdf():
    # a far-future or far-past month with no data - should still produce a valid PDF (zero totals)
    r = _get("2019-01")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_pdf_contains_title_and_totals():
    # Best-effort text extraction using pdfminer if available; else just sanity-check size
    r = _get("2026-05")
    assert r.status_code == 200
    try:
        from pdfminer.high_level import extract_text
        import io
        text = extract_text(io.BytesIO(r.content))
        assert "Monthly Reconciliation Checklist" in text
        assert "TOTAL" in text
        assert "Status legend" in text
    except ImportError:
        assert len(r.content) > 1000


def test_dashboard_pending_month_matches_checklist_default():
    d = requests.get(f"{BASE_URL}/api/dashboard", timeout=15).json()
    assert "pending_month" in d and d["pending_month"]
    # Downloading with the dashboard's pending month should work
    r = _get(d["pending_month"])
    assert r.status_code == 200
    assert f'reconciliation-checklist-{d["pending_month"]}.pdf' in r.headers.get("content-disposition", "")
