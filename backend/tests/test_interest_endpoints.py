"""Regression coverage for the offline interest working read endpoints."""
import os
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def test_interest_read_endpoints_have_expected_data():
    expected = {
        "dashboard": dict,
        "facilities": list,
        "cc-working": list,
        "wcdl-working": list,
        "reconciliation": list,
    }
    for endpoint, response_type in expected.items():
        response = requests.get(f"{BASE_URL}/api/{endpoint}", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, response_type)
        assert data