"""Tests for the SEED_DEMO_DATA env-var gate in backend/seed.py."""
import os
import sys
import uuid
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
from seed import seed_if_empty  # noqa: E402

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().strip('"')
                break
BASE_URL = BASE_URL.rstrip("/")


@pytest.fixture
def fresh_db():
    """Yield a brand-new throwaway MongoDB database, then drop it."""
    db_name = f"test_seed_gate_{uuid.uuid4().hex[:8]}"
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[db_name]
    yield db
    # cleanup
    asyncio.get_event_loop().run_until_complete(client.drop_database(db_name))
    client.close()


@pytest.fixture(autouse=True)
def clear_env():
    """Ensure SEED_DEMO_DATA doesn't leak between tests."""
    old = os.environ.pop("SEED_DEMO_DATA", None)
    yield
    os.environ.pop("SEED_DEMO_DATA", None)
    if old is not None:
        os.environ["SEED_DEMO_DATA"] = old


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestSeedGate:
    def test_seed_unset_does_nothing(self, fresh_db):
        """SEED_DEMO_DATA unset -> zero inserts."""
        assert "SEED_DEMO_DATA" not in os.environ
        _run(seed_if_empty(fresh_db))
        assert _run(fresh_db.facilities.count_documents({})) == 0
        assert _run(fresh_db.cc_transactions.count_documents({})) == 0
        assert _run(fresh_db.wcdl_loans.count_documents({})) == 0

    def test_seed_false_does_nothing(self, fresh_db):
        os.environ["SEED_DEMO_DATA"] = "false"
        _run(seed_if_empty(fresh_db))
        assert _run(fresh_db.facilities.count_documents({})) == 0
        assert _run(fresh_db.cc_transactions.count_documents({})) == 0
        assert _run(fresh_db.wcdl_loans.count_documents({})) == 0

    def test_seed_true_populates(self, fresh_db):
        """SEED_DEMO_DATA=true on fresh empty DB seeds 4 facilities + txns + loans."""
        os.environ["SEED_DEMO_DATA"] = "true"
        _run(seed_if_empty(fresh_db))
        assert _run(fresh_db.facilities.count_documents({})) == 4
        assert _run(fresh_db.cc_transactions.count_documents({})) == 6
        assert _run(fresh_db.wcdl_loans.count_documents({})) == 2
        # sanity: banks match hardcoded demo list
        banks = _run(fresh_db.facilities.distinct("bank"))
        assert set(banks) == {"ICICI Bank", "HDFC Bank", "Axis Bank", "SBI"}

    def test_seed_true_but_db_flag_disables(self, fresh_db):
        """Even with SEED_DEMO_DATA=true, existing app_meta.seed_disabled blocks seeding."""
        _run(fresh_db.app_meta.insert_one({"key": "seed_disabled", "value": True}))
        os.environ["SEED_DEMO_DATA"] = "true"
        _run(seed_if_empty(fresh_db))
        assert _run(fresh_db.facilities.count_documents({})) == 0
        assert _run(fresh_db.cc_transactions.count_documents({})) == 0
        assert _run(fresh_db.wcdl_loans.count_documents({})) == 0


# Regression: live preview must remain unseeded
class TestLivePreviewRegression:
    def test_health_ok(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=10)
        assert r.status_code == 200

    def test_facilities_still_empty(self):
        r = requests.get(f"{BASE_URL}/api/facilities", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert data == [], f"Live preview DB got seeded! Found: {data}"
