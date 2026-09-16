from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

@api_router.get("/")
async def root():
    return {"message": "Interest Working API ready"}

FACILITIES = [
    {"id":"icici-cc","bank":"ICICI Bank","type":"CC","name":"Cash Credit","limit":50000000,"outstanding":32000000,"rate":8.5,"start":"2026-04-01","maturity":"On demand","status":"Active"},
    {"id":"hdfc-cc","bank":"HDFC Bank","type":"CC","name":"Working Capital CC","limit":30000000,"outstanding":18400000,"rate":8.75,"start":"2026-01-15","maturity":"On demand","status":"Active"},
    {"id":"axis-wcdl","bank":"Axis Bank","type":"WCDL","name":"WCDL-AX-2409","limit":50000000,"outstanding":50000000,"rate":8.5,"start":"2026-04-01","maturity":"180 days","status":"Active"},
    {"id":"sbi-wcdl","bank":"SBI","type":"WCDL","name":"WCDL-SBI-1182","limit":25000000,"outstanding":12750000,"rate":8.25,"start":"2026-02-10","maturity":"120 days","status":"Active"},
]

@api_router.get("/dashboard")
async def dashboard():
    total_limit = sum(x["limit"] for x in FACILITIES)
    total_outstanding = sum(x["outstanding"] for x in FACILITIES)
    return {"facilities":len(FACILITIES),"limit":total_limit,"outstanding":total_outstanding,"available":total_limit-total_outstanding,"month_interest":512840,"ytd_interest":1842650,"variance":11200}

@api_router.get("/facilities")
async def facilities():
    return FACILITIES

@api_router.get("/cc-working")
async def cc_working():
    return [{"date":"2026-05-01","value_date":"2026-05-01","debit":32000000,"credit":0,"closing":32000000,"days":4,"rate":8.5,"interest":29753,"bank":30120,"difference":367},{"date":"2026-05-05","value_date":"2026-05-05","debit":1250000,"credit":0,"closing":33250000,"days":8,"rate":8.5,"interest":62055,"bank":61800,"difference":-255},{"date":"2026-05-13","value_date":"2026-05-13","debit":0,"credit":4250000,"closing":29000000,"days":10,"rate":8.5,"interest":67397,"bank":68120,"difference":723},{"date":"2026-05-23","value_date":"2026-05-23","debit":600000,"credit":0,"closing":29600000,"days":8,"rate":8.5,"interest":55123,"bank":55200,"difference":77}]

@api_router.get("/wcdl-working")
async def wcdl_working():
    return [{"loan":"WCDL-AX-2409","drawdown":"2026-04-01","amount":50000000,"rate":8.5,"repayment":"2026-09-28","prepayment":0,"principal":50000000,"days":45,"interest":523973,"bank":523973,"variance":0},{"loan":"WCDL-SBI-1182","drawdown":"2026-02-10","amount":12750000,"rate":8.25,"repayment":"2026-06-10","prepayment":0,"principal":12750000,"days":45,"interest":64852,"bank":65120,"variance":268}]

@api_router.get("/reconciliation")
async def reconciliation():
    return [{"particular":"CC Interest","ours":1245000,"bank":1251200,"difference":6200},{"particular":"WCDL Interest","ours":1875000,"bank":1875000,"difference":0},{"particular":"Other Charges","ours":25000,"bank":30000,"difference":5000},{"particular":"Total","ours":3145000,"bank":3156200,"difference":11200}]

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()