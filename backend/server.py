from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Literal
import uuid
from datetime import datetime, timezone, date

from engine import cc_rows, wcdl_rows, cc_balance_at, wcdl_outstanding_at, rate_on, month_bounds, fy_start
from seed import seed_if_empty

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")
NO_ID = {"_id": 0}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def current_month():
    return date.today().strftime("%Y-%m")


class FacilityIn(BaseModel):
    bank: str
    type: Literal["CC", "WCDL"]
    name: str
    limit: float
    start: str
    maturity: str = "On demand"
    status: str = "Active"
    day_count: Literal[365, 360] = 365
    rate: Optional[float] = None


class FacilityUpdate(BaseModel):
    bank: Optional[str] = None
    name: Optional[str] = None
    limit: Optional[float] = None
    start: Optional[str] = None
    maturity: Optional[str] = None
    status: Optional[str] = None
    day_count: Optional[Literal[365, 360]] = None


class RateIn(BaseModel):
    effective_date: str
    rate: float = Field(gt=0)
    remarks: str = ""


class CCTransactionIn(BaseModel):
    facility_id: str
    date: str
    value_date: Optional[str] = None
    debit: float = 0
    credit: float = 0
    bank_interest: Optional[float] = None
    narration: str = ""


class WCDLLoanIn(BaseModel):
    facility_id: str
    loan: str
    drawdown: str
    amount: float = Field(gt=0)
    repayment: str
    prepayment: float = 0
    prepayment_date: Optional[str] = None
    bank_interest: Optional[float] = None


async def get_facility(fid: str):
    fac = await db.facilities.find_one({"id": fid}, NO_ID)
    if not fac:
        raise HTTPException(404, "Facility not found")
    return fac


async def decorate(fac, end: date):
    fac["rate_history"] = sorted(fac.get("rate_history", []), key=lambda h: h["effective_date"])
    fac["rate"] = rate_on(fac["rate_history"], end)
    if fac["type"] == "CC":
        txs = await db.cc_transactions.find({"facility_id": fac["id"]}, NO_ID).to_list(10000)
        fac["outstanding"] = cc_balance_at(txs, end)
    else:
        loans = await db.wcdl_loans.find({"facility_id": fac["id"]}, NO_ID).to_list(10000)
        fac["outstanding"] = wcdl_outstanding_at(loans, end)
    fac["available"] = round(fac["limit"] - fac["outstanding"], 2)
    return fac


async def month_totals(month: str):
    facs = await db.facilities.find({}, NO_ID).to_list(1000)
    cc_ours = cc_bank = wcdl_ours = wcdl_bank = 0.0
    for fac in facs:
        if fac["type"] == "CC":
            txs = await db.cc_transactions.find({"facility_id": fac["id"]}, NO_ID).to_list(10000)
            w = cc_rows(fac, txs, month)
            cc_ours += w["ours"]
            cc_bank += w["bank"]
        else:
            loans = await db.wcdl_loans.find({"facility_id": fac["id"]}, NO_ID).to_list(10000)
            rows = wcdl_rows(fac, loans, month)
            wcdl_ours += sum(r["interest"] for r in rows)
            wcdl_bank += sum(r["bank"] or 0 for r in rows)
    return {"cc_ours": round(cc_ours, 2), "cc_bank": round(cc_bank, 2), "wcdl_ours": round(wcdl_ours, 2), "wcdl_bank": round(wcdl_bank, 2)}


@api_router.get("/")
async def root():
    return {"message": "Interest Working API ready"}


@api_router.get("/facilities")
async def list_facilities(month: Optional[str] = None):
    _, end = month_bounds(month or current_month())
    facs = await db.facilities.find({}, NO_ID).sort("created_at", 1).to_list(1000)
    return [await decorate(f, end) for f in facs]


@api_router.post("/facilities", status_code=201)
async def create_facility(body: FacilityIn):
    doc = body.model_dump(exclude={"rate"})
    doc.update({"id": str(uuid.uuid4()), "created_at": now_iso(), "rate_history": []})
    if body.rate is not None:
        doc["rate_history"].append({"id": str(uuid.uuid4()), "effective_date": body.start, "rate": body.rate, "remarks": "Initial pricing"})
    await db.facilities.insert_one(doc)
    doc.pop("_id", None)
    return await decorate(doc, month_bounds(current_month())[1])


@api_router.put("/facilities/{fid}")
async def update_facility(fid: str, body: FacilityUpdate):
    await get_facility(fid)
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    if changes:
        await db.facilities.update_one({"id": fid}, {"$set": changes})
    return await decorate(await get_facility(fid), month_bounds(current_month())[1])


@api_router.delete("/facilities/{fid}", status_code=204)
async def delete_facility(fid: str):
    await get_facility(fid)
    await db.facilities.delete_one({"id": fid})
    await db.cc_transactions.delete_many({"facility_id": fid})
    await db.wcdl_loans.delete_many({"facility_id": fid})


@api_router.post("/facilities/{fid}/rates", status_code=201)
async def add_rate(fid: str, body: RateIn):
    fac = await get_facility(fid)
    if any(h["effective_date"] == body.effective_date for h in fac.get("rate_history", [])):
        raise HTTPException(400, "A rate is already effective on that date")
    entry = {"id": str(uuid.uuid4()), **body.model_dump()}
    await db.facilities.update_one({"id": fid}, {"$push": {"rate_history": entry}})
    return await decorate(await get_facility(fid), month_bounds(current_month())[1])


@api_router.delete("/facilities/{fid}/rates/{rid}")
async def delete_rate(fid: str, rid: str):
    fac = await get_facility(fid)
    if len(fac.get("rate_history", [])) <= 1:
        raise HTTPException(400, "A facility must keep at least one rate")
    await db.facilities.update_one({"id": fid}, {"$pull": {"rate_history": {"id": rid}}})
    return await decorate(await get_facility(fid), month_bounds(current_month())[1])


@api_router.get("/cc-working")
async def cc_working(facility_id: Optional[str] = None, month: Optional[str] = None):
    month = month or current_month()
    if facility_id:
        fac = await get_facility(facility_id)
    else:
        fac = await db.facilities.find_one({"type": "CC"}, NO_ID, sort=[("created_at", 1)])
        if not fac:
            return {"facility": None, "rows": [], "ours": 0, "bank": 0, "difference": 0, "opening": 0, "closing": 0, "day_count": 365}
    txs = await db.cc_transactions.find({"facility_id": fac["id"]}, NO_ID).to_list(10000)
    result = cc_rows(fac, txs, month)
    result["facility"] = await decorate(fac, month_bounds(month)[1])
    result["month"] = month
    return result


@api_router.post("/cc-transactions", status_code=201)
async def add_cc_transaction(body: CCTransactionIn):
    fac = await get_facility(body.facility_id)
    if fac["type"] != "CC":
        raise HTTPException(400, "Transactions can only be added to CC facilities")
    if body.debit <= 0 and body.credit <= 0:
        raise HTTPException(400, "Enter a debit or credit amount")
    doc = body.model_dump()
    doc["value_date"] = doc["value_date"] or doc["date"]
    doc.update({"id": str(uuid.uuid4()), "created_at": now_iso()})
    await db.cc_transactions.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.delete("/cc-transactions/{tid}", status_code=204)
async def delete_cc_transaction(tid: str):
    res = await db.cc_transactions.delete_one({"id": tid})
    if not res.deleted_count:
        raise HTTPException(404, "Transaction not found")


@api_router.get("/wcdl-working")
async def wcdl_working(facility_id: Optional[str] = None, month: Optional[str] = None):
    month = month or current_month()
    query = {"type": "WCDL"}
    if facility_id:
        query["id"] = facility_id
    facs = await db.facilities.find(query, NO_ID).sort("created_at", 1).to_list(1000)
    rows = []
    for fac in facs:
        loans = await db.wcdl_loans.find({"facility_id": fac["id"]}, NO_ID).to_list(10000)
        for r in wcdl_rows(fac, loans, month):
            r["day_count"] = int(fac.get("day_count", 365))
            rows.append(r)
    ours = round(sum(r["interest"] for r in rows), 2)
    bank = round(sum(r["bank"] or 0 for r in rows), 2)
    return {"rows": rows, "ours": ours, "bank": bank, "variance": round(bank - ours, 2), "month": month}


@api_router.post("/wcdl-loans", status_code=201)
async def add_wcdl_loan(body: WCDLLoanIn):
    fac = await get_facility(body.facility_id)
    if fac["type"] != "WCDL":
        raise HTTPException(400, "Loans can only be added to WCDL facilities")
    if body.repayment <= body.drawdown:
        raise HTTPException(400, "Repayment date must be after drawdown")
    doc = body.model_dump()
    doc.update({"id": str(uuid.uuid4()), "created_at": now_iso()})
    await db.wcdl_loans.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.delete("/wcdl-loans/{lid}", status_code=204)
async def delete_wcdl_loan(lid: str):
    res = await db.wcdl_loans.delete_one({"id": lid})
    if not res.deleted_count:
        raise HTTPException(404, "Loan not found")


@api_router.get("/dashboard")
async def dashboard(month: Optional[str] = None):
    month = month or current_month()
    _, end = month_bounds(month)
    facs = [await decorate(f, end) for f in await db.facilities.find({}, NO_ID).to_list(1000)]
    total_limit = round(sum(f["limit"] for f in facs), 2)
    total_out = round(sum(f["outstanding"] for f in facs), 2)
    this = await month_totals(month)
    ytd_ours = 0.0
    cursor = fy_start(month)
    while cursor < end:
        m = cursor.strftime("%Y-%m")
        t = this if m == month else await month_totals(m)
        ytd_ours += t["cc_ours"] + t["wcdl_ours"]
        cursor = month_bounds(m)[1]
    month_ours = round(this["cc_ours"] + this["wcdl_ours"], 2)
    month_bank = round(this["cc_bank"] + this["wcdl_bank"], 2)
    return {
        "month": month, "facilities": len(facs), "banks": len({f["bank"] for f in facs}),
        "limit": total_limit, "outstanding": total_out, "available": round(total_limit - total_out, 2),
        "utilisation": round(total_out / total_limit * 100, 1) if total_limit else 0,
        "month_interest": month_ours, "month_bank_interest": month_bank, "ytd_interest": round(ytd_ours, 2),
        "variance": round(month_bank - month_ours, 2),
        "rate_changes": sum(max(len(f.get("rate_history", [])) - 1, 0) for f in facs),
    }


@api_router.get("/reconciliation")
async def reconciliation(month: Optional[str] = None):
    month = month or current_month()
    t = await month_totals(month)
    rows = [
        {"particular": "CC Interest", "ours": t["cc_ours"], "bank": t["cc_bank"]},
        {"particular": "WCDL Interest", "ours": t["wcdl_ours"], "bank": t["wcdl_bank"]},
    ]
    for r in rows:
        r["difference"] = round(r["bank"] - r["ours"], 2)
    total = {"particular": "Total", "ours": round(sum(r["ours"] for r in rows), 2), "bank": round(sum(r["bank"] for r in rows), 2)}
    total["difference"] = round(total["bank"] - total["ours"], 2)
    return rows + [total]


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def seed():
    await seed_if_empty(db)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
