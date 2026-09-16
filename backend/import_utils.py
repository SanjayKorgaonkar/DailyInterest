"""Bank statement (CSV/XLSX) parsing and column-mapping helpers for CC transaction import."""
import io
import re
from datetime import date

import pandas as pd
from dateutil import parser as dateparser

DATE_KEYWORDS = ["value date", "valuedate", "value dt"]
TXN_DATE_KEYWORDS = ["txn date", "transaction date", "posting date", "date"]
DEBIT_KEYWORDS = ["debit", "withdrawal", "dr amt", "amount debited"]
CREDIT_KEYWORDS = ["credit", "deposit", "cr amt", "amount credited"]
AMOUNT_KEYWORDS = ["amount", "amt"]
DRCR_KEYWORDS = ["dr/cr", "dr / cr", "type", "indicator", "cr/dr"]
NARRATION_KEYWORDS = ["narration", "description", "particulars", "remarks", "details"]
INTEREST_KEYWORDS = ["interest"]
INTEREST_NARRATION_MARKERS = ["interest debited", "int debited", "interest chgd", "int chgd", "interest charged",
                              "int charged", "interest chg", "int.chrg", "int chrg", "interest debit", "int deb"]


def _match(col: str, keywords) -> bool:
    c = col.strip().lower()
    return any(k in c for k in keywords)


def parse_statement_file(filename: str, content: bytes):
    """Read a CSV or XLSX bank statement into (columns, rows-as-dicts). All values are kept as strings."""
    name = (filename or "").lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(content), dtype=str, keep_default_na=False, engine="openpyxl" if name.endswith(".xlsx") else None)
    else:
        try:
            df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False, encoding="latin-1")
    df = df.dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    rows = [{k: (v if v is not None else "") for k, v in r.items()} for r in df.to_dict(orient="records")]
    return list(df.columns), rows


def guess_mapping(columns):
    mapping = {"date_col": None, "value_date_col": None, "debit_col": None, "credit_col": None,
               "amount_col": None, "dr_cr_col": None, "narration_col": None, "bank_interest_col": None}
    for col in columns:
        if mapping["value_date_col"] is None and _match(col, DATE_KEYWORDS):
            mapping["value_date_col"] = col
        elif mapping["date_col"] is None and _match(col, TXN_DATE_KEYWORDS):
            mapping["date_col"] = col
        elif mapping["debit_col"] is None and _match(col, DEBIT_KEYWORDS):
            mapping["debit_col"] = col
        elif mapping["credit_col"] is None and _match(col, CREDIT_KEYWORDS):
            mapping["credit_col"] = col
        elif mapping["dr_cr_col"] is None and _match(col, DRCR_KEYWORDS):
            mapping["dr_cr_col"] = col
        elif mapping["amount_col"] is None and _match(col, AMOUNT_KEYWORDS):
            mapping["amount_col"] = col
        elif mapping["narration_col"] is None and _match(col, NARRATION_KEYWORDS):
            mapping["narration_col"] = col
        elif mapping["bank_interest_col"] is None and _match(col, INTEREST_KEYWORDS):
            mapping["bank_interest_col"] = col
    if not mapping["date_col"]:
        mapping["date_col"] = mapping["value_date_col"]
    if not mapping["value_date_col"]:
        mapping["value_date_col"] = mapping["date_col"]
    return mapping


def to_float(raw) -> float:
    if raw is None:
        return 0.0
    s = str(raw).strip()
    if not s:
        return 0.0
    negative = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[,()₹\s]", "", s)
    if not s or s in {"-", "."}:
        return 0.0
    try:
        val = float(s)
    except ValueError:
        return 0.0
    return -abs(val) if negative else val


def to_date(raw) -> str:
    s = str(raw).strip()
    if not s:
        return None
    try:
        return dateparser.parse(s, dayfirst=True).date().isoformat()
    except (ValueError, OverflowError):
        return None


def normalize_rows(rows, mapping):
    """Turn raw parsed rows + a column mapping into cc_transaction-ready dicts. Returns (transactions, errors)."""
    date_col = mapping.get("date_col")
    value_date_col = mapping.get("value_date_col") or date_col
    debit_col = mapping.get("debit_col")
    credit_col = mapping.get("credit_col")
    amount_col = mapping.get("amount_col")
    dr_cr_col = mapping.get("dr_cr_col")
    narration_col = mapping.get("narration_col")
    interest_col = mapping.get("bank_interest_col")
    txns, errors = [], []

    for idx, row in enumerate(rows, start=2):  # row 1 is header
        raw_date = row.get(date_col) if date_col else None
        txn_date = to_date(raw_date)
        if not txn_date:
            errors.append(f"Row {idx}: could not read a date from '{raw_date}' — skipped")
            continue
        value_date = to_date(row.get(value_date_col)) or txn_date

        if debit_col or credit_col:
            debit = to_float(row.get(debit_col)) if debit_col else 0.0
            credit = to_float(row.get(credit_col)) if credit_col else 0.0
        elif amount_col:
            amt = to_float(row.get(amount_col))
            if dr_cr_col:
                indicator = str(row.get(dr_cr_col, "")).strip().lower()
                is_debit = any(k in indicator for k in ["dr", "debit", "withdraw"])
                debit = abs(amt) if is_debit else 0.0
                credit = 0.0 if is_debit else abs(amt)
            else:
                debit = abs(amt) if amt < 0 else 0.0
                credit = amt if amt > 0 else 0.0
        else:
            debit = credit = 0.0

        if debit <= 0 and credit <= 0:
            errors.append(f"Row {idx}: no debit or credit amount — skipped")
            continue

        narration = str(row.get(narration_col, "")).strip() if narration_col else ""
        bank_interest = to_float(row.get(interest_col)) if interest_col and str(row.get(interest_col, "")).strip() else None
        auto_matched = False
        if bank_interest is None and debit > 0 and narration:
            low = narration.lower()
            if "interest" in low or any(m in low for m in INTEREST_NARRATION_MARKERS):
                bank_interest = debit
                auto_matched = True

        txns.append({
            "date": txn_date,
            "value_date": value_date,
            "debit": round(debit, 2),
            "credit": round(credit, 2),
            "bank_interest": bank_interest,
            "auto_matched": auto_matched,
            "narration": narration,
        })
    return txns, errors
