from datetime import date


def month_bounds(month: str):
    y, m = map(int, month.split("-"))
    start = date(y, m, 1)
    end = date(y + (m == 12), m % 12 + 1, 1)
    return start, end


def fy_start(month: str):
    y, m = map(int, month.split("-"))
    return date(y if m >= 4 else y - 1, 4, 1)


def d(s):
    return date.fromisoformat(s)


def rate_on(history, day: date):
    if not history:
        return 0.0
    ordered = sorted(history, key=lambda h: h["effective_date"])
    applicable = [h for h in ordered if h["effective_date"] <= day.isoformat()]
    return float((applicable[-1] if applicable else ordered[0])["rate"])


def split_periods(start: date, end: date, history, extra_breaks=()):
    if end <= start:
        return [(start, start)]
    points = {start, end}
    points |= {d(h["effective_date"]) for h in history if start < d(h["effective_date"]) < end}
    points |= {b for b in extra_breaks if start < b < end}
    ordered = sorted(points)
    return list(zip(ordered, ordered[1:]))


def interest(balance, rate, days, day_count):
    return round(balance * rate / 100 * days / day_count, 2)


def cc_rows(facility, transactions, month):
    start, end = month_bounds(month)
    history = facility.get("rate_history", [])
    day_count = int(facility.get("day_count", 365))
    txs = sorted(transactions, key=lambda t: (t["value_date"], t["date"], t.get("created_at", "")))
    prior = [t for t in txs if d(t["value_date"]) < start]
    opening = round(sum(t["debit"] - t["credit"] for t in prior), 2)
    in_month = [t for t in txs if start <= d(t["value_date"]) < end]
    points = []
    if prior or not in_month:
        points.append({"id": "opening", "date": start.isoformat(), "value_date": start.isoformat(), "debit": 0, "credit": 0, "bank_interest": None, "opening": True})
    points += in_month
    rows, balance = [], opening
    for i, t in enumerate(points):
        if not t.get("opening"):
            balance = round(balance + t["debit"] - t["credit"], 2)
        seg_start = d(t["value_date"])
        seg_end = d(points[i + 1]["value_date"]) if i + 1 < len(points) else end
        periods = split_periods(seg_start, seg_end, history)
        segs = []
        for a, b in periods:
            r = rate_on(history, a)
            days = (b - a).days
            segs.append({"from": a.isoformat(), "to": b.isoformat(), "rate": r, "days": days, "interest": interest(max(balance, 0), r, days, day_count)})
        ours = round(sum(s["interest"] for s in segs), 2)
        bank = t.get("bank_interest")
        auto_matched = bool(t.get("auto_matched")) and not t.get("opening")
        for j, s in enumerate(segs):
            rows.append({
                "id": t["id"], "segment": j > 0, "opening": bool(t.get("opening")),
                "date": t["date"] if j == 0 else s["from"], "value_date": s["from"], "to": s["to"],
                "debit": t["debit"] if j == 0 else 0, "credit": t["credit"] if j == 0 else 0,
                "closing": balance, "days": s["days"], "rate": s["rate"], "interest": s["interest"],
                "bank": bank if j == 0 else None,
                "auto_matched": auto_matched if j == 0 else False,
                "difference": round(bank - ours, 2) if (j == 0 and bank is not None) else None,
                "rate_changed": j > 0,
            })
    total_ours = round(sum(r["interest"] for r in rows), 2)
    total_bank = round(sum(r["bank"] or 0 for r in rows), 2)
    closing = balance
    return {"rows": rows, "opening": opening, "closing": closing, "ours": total_ours, "bank": total_bank, "difference": round(total_bank - total_ours, 2), "day_count": day_count}


def cc_balance_at(transactions, end: date):
    return round(sum(t["debit"] - t["credit"] for t in transactions if d(t["value_date"]) < end), 2)


def wcdl_rows(facility, loans, month):
    start, end = month_bounds(month)
    history = facility.get("rate_history", [])
    day_count = int(facility.get("day_count", 365))
    rows = []
    for loan in sorted(loans, key=lambda l: l["drawdown"]):
        w_start = max(d(loan["drawdown"]), start)
        w_end = min(d(loan["repayment"]), end)
        if w_end <= w_start:
            continue
        prepay_date = d(loan["prepayment_date"]) if loan.get("prepayment") and loan.get("prepayment_date") else None
        periods = split_periods(w_start, w_end, history, [prepay_date] if prepay_date else [])
        segs = []
        for a, b in periods:
            principal = loan["amount"] - (loan["prepayment"] if prepay_date and a >= prepay_date else 0)
            r = rate_on(history, a)
            days = (b - a).days
            segs.append({"from": a.isoformat(), "to": b.isoformat(), "rate": r, "days": days, "principal": principal, "interest": interest(max(principal, 0), r, days, day_count)})
        ours = round(sum(s["interest"] for s in segs), 2)
        bank = loan.get("bank_interest")
        for j, s in enumerate(segs):
            rows.append({
                "id": loan["id"], "segment": j > 0, "loan": loan["loan"], "facility_id": facility["id"], "bank_name": facility["bank"],
                "drawdown": loan["drawdown"], "amount": loan["amount"], "repayment": loan["repayment"],
                "prepayment": loan.get("prepayment", 0) or 0, "prepayment_date": loan.get("prepayment_date"),
                "from": s["from"], "to": s["to"], "principal": s["principal"], "rate": s["rate"], "days": s["days"], "interest": s["interest"],
                "bank": bank if j == 0 else None,
                "variance": round(bank - ours, 2) if (j == 0 and bank is not None) else None,
            })
    return rows


def wcdl_outstanding_at(loans, end: date):
    total = 0
    for loan in loans:
        if d(loan["drawdown"]) < end <= d(loan["repayment"]):
            prepay = loan.get("prepayment", 0) or 0
            if prepay and loan.get("prepayment_date") and d(loan["prepayment_date"]) < end:
                total += loan["amount"] - prepay
            else:
                total += loan["amount"]
    return round(total, 2)
