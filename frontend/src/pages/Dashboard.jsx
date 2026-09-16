import { useState } from "react";
import { AlertTriangle, ChevronRight, FileDown, Upload } from "lucide-react";
import { Header } from "../components/Header";
import { money, rupee, monthLong, pct } from "../lib/format";
import { api, errorText } from "../lib/api";

export default function Dashboard({ data, onNavigate, month, onAction }) {
  const d = data.dashboard;
  const metrics = [
    ["Total facilities", d.facilities, `Across ${d.banks} banks`, "blue"],
    ["Sanctioned limit", money(d.limit), `${money(d.limit)} total capacity`, "navy"],
    ["Current outstanding", money(d.outstanding), `${pct(d.utilisation)} utilisation`, "orange"],
    ["Available limit", money(d.available), `${(100 - d.utilisation).toFixed(1)}% headroom`, "green"],
  ];
  const pending = d.pending_certificates || [];
  const [downloading, setDownloading] = useState(false);
  const downloadChecklist = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      const r = await api.get("/reports/monthly-checklist", { params: { month: d.pending_month }, responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = `reconciliation-checklist-${d.pending_month}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { onAction?.(errorText(e)); } finally { setDownloading(false); }
  };
  return (
    <>
      <Header eyebrow={`CONTROL CENTRE · ${monthLong(month).toUpperCase()}`} title="Good morning, Ankit" sub="Here’s the position across your working capital facilities.">
        <button className="outline" data-testid="download-checklist-button" disabled={downloading} onClick={downloadChecklist}>
          <FileDown size={15} /> {downloading ? "Preparing…" : `${monthLong(d.pending_month)} checklist`}
        </button>
        <button className="primary" data-testid="add-facility-button" onClick={() => onNavigate("facilities")}>+ Add facility</button>
      </Header>
      {pending.length > 0 && (
        <div className="cert-reminder" data-testid="pending-certificates-banner">
          <AlertTriangle size={18} />
          <div>
            <b>{pending.length} facilit{pending.length === 1 ? "y" : "ies"} missing a bank certificate for {monthLong(d.pending_month)}</b>
            <span>Enter last month's bank-charged interest so reconciliation is complete before you close the books.</span>
          </div>
          <div className="cert-reminder-pills">
            {pending.map((p) => (
              <button key={p.facility_id} className="cert-pill" data-testid={`pending-cert-${p.facility_id}`}
                onClick={() => onNavigate(p.type === "CC" ? "cc" : "wcdl", { facilityId: p.facility_id, month: p.month })}>
                {p.bank} <ChevronRight size={12} />
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="metric-grid">
        {metrics.map((x, i) => (
          <div className={`metric ${x[3]}`} key={x[0]} data-testid={`metric-${i}`}><span>{x[0]}</span><strong>{x[1]}</strong><small>{x[2]}</small></div>
        ))}
      </div>
      <div className="dashboard-grid">
        <div className="section-block">
          <div className="section-title">
            <div><span className="eyebrow">PORTFOLIO VIEW</span><h2>Interest at a glance</h2></div>
            <span className="formula" data-testid="rate-changes-badge">{d.rate_changes} rate change{d.rate_changes === 1 ? "" : "s"} on file</span>
          </div>
          <div className="interest-row">
            <div className="interest-main">
              <span>Interest for {monthLong(month)}</span>
              <strong data-testid="current-month-interest">{rupee(d.month_interest)}</strong>
              <em>Bank charged {rupee(d.month_bank_interest)}</em>
            </div>
            <div className="mini-bars" aria-label="Monthly interest trend">{[35, 48, 42, 65, 58, 78, 69, 90].map((h, i) => <i key={i} style={{ height: `${h}%` }} />)}</div>
          </div>
          <div className="split-stats">
            <div><span>FY-to-date interest</span><b data-testid="ytd-interest">{rupee(d.ytd_interest)}</b></div>
            <div><span>Bank variance this month</span><b className={d.variance ? "danger-text" : "positive"} data-testid="dashboard-variance">{d.variance > 0 ? "+" : ""}{rupee(d.variance)}</b></div>
          </div>
        </div>
        <div className="section-block bank-panel">
          <div className="section-title">
            <div><span className="eyebrow">BY BANK</span><h2>Facility exposure</h2></div>
            <button className="text-btn" data-testid="view-facilities-button" onClick={() => onNavigate("facilities")}>View all →</button>
          </div>
          {data.facilities.slice(0, 5).map((f) => (
            <div className="bank-line" key={f.id} data-testid={`bank-line-${f.id}`}>
              <span className="bank-logo">{f.bank.slice(0, 2)}</span>
              <div><b>{f.bank}</b><small>{f.type} · {pct(f.rate)} · Actual/{f.day_count}</small></div>
              <strong>{money(f.outstanding)}</strong>
              <span className="bar"><i style={{ width: `${Math.min(f.outstanding / f.limit * 100, 100)}%` }} /></span>
            </div>
          ))}
        </div>
      </div>
      <div className="quick-strip">
        <div><Upload size={18} /><div><b>Import bank statement</b><span>CSV or Excel · auto-map transactions</span></div></div>
        <button className="outline" data-testid="import-statement-button" onClick={() => onNavigate("cc")}>Start import</button>
      </div>
    </>
  );
}
