import { ChevronRight, FileSpreadsheet } from "lucide-react";
import { Header } from "../components/Header";
import { rupee, monthLong } from "../lib/format";

export function Reconciliation({ rows, month, onAction }) {
  const total = rows[rows.length - 1] || { ours: 0, bank: 0, difference: 0 };
  return (
    <>
      <Header eyebrow={`CONTROL CHECK · ${monthLong(month).toUpperCase()}`} title="Bank reconciliation" sub="Compare your calculated interest against bank debits before posting.">
        <button className="primary" data-testid="export-reconciliation-button" onClick={() => onAction("Export arrives in the next release")}>Export report</button>
      </Header>
      <div className="recon-summary">
        <div><span>Our working</span><strong data-testid="recon-ours">{rupee(total.ours)}</strong></div>
        <div><span>Bank debit</span><strong data-testid="recon-bank">{rupee(total.bank)}</strong></div>
        <div className="variance-box"><span>Total variance</span><strong data-testid="recon-variance">{total.difference > 0 ? "+" : ""}{rupee(total.difference)}</strong><small>{total.difference ? "Needs review" : "Fully matched"}</small></div>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Particular</th><th>Our working</th><th>Bank debit</th><th>Difference</th><th>Review</th></tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.particular} className={i === rows.length - 1 ? "total-row" : ""} data-testid={`recon-row-${i}`}>
                <td><b>{r.particular}</b></td>
                <td className="mono">{rupee(r.ours)}</td>
                <td className="mono">{rupee(r.bank)}</td>
                <td className={`mono ${r.difference ? "danger-text" : "positive"}`}>{r.difference ? `${r.difference > 0 ? "+" : ""}${rupee(r.difference)}` : "Nil"}</td>
                <td>{r.difference ? <span className="review">Review</span> : <span className="matched">Matched</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function Reports({ onAction, month }) {
  const items = ["Bank-wise interest report", "Facility-wise report", "Monthly interest MIS", "Daily outstanding", "Rate change report", "Excess / short interest"];
  return (
    <>
      <Header eyebrow="REPORTING · EXPORT CENTRE" title="Reports" sub="Turn your interest working into a monthly MIS in a few clicks." />
      <div className="report-grid">
        {items.map((x, i) => (
          <button className="report-item" data-testid={`report-${i}-button`} onClick={() => onAction(`${x} prepared`)} key={x}>
            <FileSpreadsheet size={22} /><div><b>{x}</b><span>{monthLong(month)} · Excel / PDF</span></div><ChevronRight size={17} />
          </button>
        ))}
      </div>
    </>
  );
}
