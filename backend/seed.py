import uuid
from datetime import datetime, timezone


def _id():
    return str(uuid.uuid4())


def _now(offset):
    return datetime(2026, 1, 1, tzinfo=timezone.utc).replace(second=offset).isoformat()


FACILITIES = [
    {"id": "icici-cc", "bank": "ICICI Bank", "type": "CC", "name": "Cash Credit", "limit": 50000000, "start": "2026-04-01", "maturity": "On demand", "status": "Active", "day_count": 365,
     "rate_history": [{"id": _id(), "effective_date": "2026-04-01", "rate": 8.5, "remarks": "Sanction pricing"}]},
    {"id": "hdfc-cc", "bank": "HDFC Bank", "type": "CC", "name": "Working Capital CC", "limit": 30000000, "start": "2026-01-15", "maturity": "On demand", "status": "Active", "day_count": 365,
     "rate_history": [{"id": _id(), "effective_date": "2026-01-15", "rate": 8.75, "remarks": "Sanction pricing"},
                      {"id": _id(), "effective_date": "2026-05-15", "rate": 9.0, "remarks": "MCLR reset +25 bps"}]},
    {"id": "axis-wcdl", "bank": "Axis Bank", "type": "WCDL", "name": "WCDL-AX-2409", "limit": 50000000, "start": "2026-04-01", "maturity": "180 days", "status": "Active", "day_count": 365,
     "rate_history": [{"id": _id(), "effective_date": "2026-04-01", "rate": 8.5, "remarks": "Drawdown pricing"}]},
    {"id": "sbi-wcdl", "bank": "SBI", "type": "WCDL", "name": "WCDL-SBI-1182", "limit": 25000000, "start": "2026-02-10", "maturity": "120 days", "status": "Active", "day_count": 360,
     "rate_history": [{"id": _id(), "effective_date": "2026-02-10", "rate": 8.25, "remarks": "Drawdown pricing"}]},
]

CC_TRANSACTIONS = [
    {"facility_id": "icici-cc", "date": "2026-05-01", "value_date": "2026-05-01", "debit": 32000000, "credit": 0, "bank_interest": 30120, "narration": "Opening utilisation"},
    {"facility_id": "icici-cc", "date": "2026-05-05", "value_date": "2026-05-05", "debit": 1250000, "credit": 0, "bank_interest": 61800, "narration": "Vendor payment"},
    {"facility_id": "icici-cc", "date": "2026-05-13", "value_date": "2026-05-13", "debit": 0, "credit": 4250000, "bank_interest": 68120, "narration": "Customer receipt"},
    {"facility_id": "icici-cc", "date": "2026-05-23", "value_date": "2026-05-23", "debit": 600000, "credit": 0, "bank_interest": 55200, "narration": "Salary transfer"},
    {"facility_id": "hdfc-cc", "date": "2026-05-02", "value_date": "2026-05-02", "debit": 18400000, "credit": 0, "bank_interest": 123500, "narration": "Opening utilisation"},
    {"facility_id": "hdfc-cc", "date": "2026-05-30", "value_date": "2026-05-30", "debit": 0, "credit": 2400000, "bank_interest": 7900, "narration": "Customer receipt"},
]

WCDL_LOANS = [
    {"facility_id": "axis-wcdl", "loan": "WCDL-AX-2409", "drawdown": "2026-04-01", "amount": 50000000, "repayment": "2026-09-28", "prepayment": 0, "prepayment_date": None, "bank_interest": 361000},
    {"facility_id": "sbi-wcdl", "loan": "WCDL-SBI-1182", "drawdown": "2026-02-10", "amount": 12750000, "repayment": "2026-06-10", "prepayment": 0, "prepayment_date": None, "bank_interest": 90800},
]


async def seed_if_empty(db):
    if not await db.facilities.count_documents({}):
        for i, f in enumerate(FACILITIES):
            await db.facilities.insert_one({**f, "created_at": _now(i)})
    for i, t in enumerate(CC_TRANSACTIONS):
        if not await db.cc_transactions.count_documents({"facility_id": t["facility_id"], "date": t["date"], "narration": t["narration"]}):
            await db.cc_transactions.insert_one({**t, "id": _id(), "created_at": _now(i)})
    for i, l in enumerate(WCDL_LOANS):
        if not await db.wcdl_loans.count_documents({"facility_id": l["facility_id"], "loan": l["loan"]}):
            await db.wcdl_loans.insert_one({**l, "id": _id(), "created_at": _now(i)})
