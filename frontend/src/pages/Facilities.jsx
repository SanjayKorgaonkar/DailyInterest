import { useState } from "react";
import { History, Trash2 } from "lucide-react";
import { Header } from "../components/Header";
import { Modal, Field, Segmented } from "../components/Modal";
import { api, errorText } from "../lib/api";
import { money, pct, fmtDate, today } from "../lib/format";

const DAY_COUNT = [{ value: 365, label: "Actual / 365" }, { value: 360, label: "Actual / 360" }];

export default function Facilities({ data, onAction, reload }) {
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [rateFor, setRateFor] = useState(null);
  const filtered = data.filter((f) => `${f.bank} ${f.name} ${f.type}`.toLowerCase().includes(query.toLowerCase()));
  const selected = rateFor && data.find((f) => f.id === rateFor);
  return (
    <>
      <Header eyebrow={`MASTER DATA · ${String(data.length).padStart(2, "0")} FACILITIES`} title="Facility master" sub="Keep limits, pricing history and day-count conventions in one controlled register.">
        <button className="primary" data-testid="new-facility-button" onClick={() => setShowForm(true)}>+ New facility</button>
      </Header>
      <div className="table-wrap">
        <div className="table-toolbar">
          <b>All facilities <span className="count">{filtered.length}</span></b>
          <input data-testid="facility-search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search bank or facility…" />
        </div>
        <table>
          <thead><tr><th>Bank / facility</th><th>Type</th><th>Sanctioned limit</th><th>Outstanding</th><th>Current rate</th><th>Convention</th><th>Start date</th><th>Maturity</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {filtered.map((f) => (
              <tr key={f.id} data-testid={`facility-row-${f.id}`}>
                <td><b>{f.bank}</b><small>{f.name}</small></td>
                <td><span className={`tag ${f.type.toLowerCase()}`}>{f.type}</span></td>
                <td className="mono">{money(f.limit)}</td>
                <td className="mono">{money(f.outstanding)}</td>
                <td className="mono" data-testid={`facility-rate-${f.id}`}>{pct(f.rate)}<small>{f.rate_history.length > 1 ? `${f.rate_history.length - 1} change${f.rate_history.length > 2 ? "s" : ""}` : "no changes"}</small></td>
                <td><span className="conv" data-testid={`facility-convention-${f.id}`}>Actual/{f.day_count}</span></td>
                <td>{fmtDate(f.start)}</td>
                <td>{f.maturity}</td>
                <td><span className="status">● {f.status}</span></td>
                <td><button className="text-btn row-btn" data-testid={`rate-history-button-${f.id}`} onClick={() => setRateFor(f.id)}><History size={14} /> Rate history</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showForm && <FacilityForm onClose={() => setShowForm(false)} onSaved={(f) => { setShowForm(false); onAction(`${f.bank} · ${f.name} saved`); reload(); }} onError={onAction} />}
      {selected && <RateHistory facility={selected} onClose={() => setRateFor(null)} onAction={onAction} reload={reload} />}
    </>
  );
}

function FacilityForm({ onClose, onSaved, onError }) {
  const [form, setForm] = useState({ bank: "", type: "CC", name: "", limit: "", start: today(), maturity: "On demand", status: "Active", day_count: 365, rate: "" });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const r = await api.post("/facilities", { ...form, limit: Number(form.limit), rate: Number(form.rate) });
      onSaved(r.data);
    } catch (err) { onError(errorText(err)); } finally { setSaving(false); }
  };
  return (
    <Modal title="New facility" eyebrow="FACILITY MASTER" onClose={onClose} testId="facility-form">
      <form onSubmit={submit} className="form-grid">
        <Field label="Bank"><input required data-testid="facility-bank-input" value={form.bank} onChange={set("bank")} placeholder="e.g. Kotak Mahindra Bank" /></Field>
        <Field label="Facility name"><input required data-testid="facility-name-input" value={form.name} onChange={set("name")} placeholder="e.g. Cash Credit" /></Field>
        <Field label="Type">
          <Segmented testId="facility-type" value={form.type} options={[{ value: "CC", label: "Cash Credit" }, { value: "WCDL", label: "WCDL" }]} onChange={(v) => setForm({ ...form, type: v, maturity: v === "CC" ? "On demand" : "90 days" })} />
        </Field>
        <Field label="Day-count convention">
          <Segmented testId="facility-day-count" value={form.day_count} options={DAY_COUNT} onChange={(v) => setForm({ ...form, day_count: v })} />
        </Field>
        <Field label="Sanctioned limit (₹)"><input required type="number" min="1" step="1" data-testid="facility-limit-input" value={form.limit} onChange={set("limit")} /></Field>
        <Field label="Initial rate (% p.a.)" hint="Effective from the start date"><input required type="number" min="0.01" step="0.01" data-testid="facility-rate-input" value={form.rate} onChange={set("rate")} /></Field>
        <Field label="Start date"><input required type="date" data-testid="facility-start-input" value={form.start} onChange={set("start")} /></Field>
        <Field label="Maturity"><input required data-testid="facility-maturity-input" value={form.maturity} onChange={set("maturity")} /></Field>
        <div className="form-actions">
          <button type="button" className="outline" onClick={onClose} data-testid="facility-form-cancel-button">Cancel</button>
          <button type="submit" className="primary" disabled={saving} data-testid="facility-form-submit-button">{saving ? "Saving…" : "Save facility"}</button>
        </div>
      </form>
    </Modal>
  );
}

function RateHistory({ facility, onClose, onAction, reload }) {
  const [form, setForm] = useState({ effective_date: today(), rate: "", remarks: "" });
  const [busy, setBusy] = useState(false);
  const history = [...facility.rate_history].sort((a, b) => b.effective_date.localeCompare(a.effective_date));
  const run = async (fn, msg) => {
    setBusy(true);
    try { await fn(); onAction(msg); reload(); } catch (err) { onAction(errorText(err)); } finally { setBusy(false); }
  };
  const addRate = (e) => {
    e.preventDefault();
    run(() => api.post(`/facilities/${facility.id}/rates`, { ...form, rate: Number(form.rate) }).then(() => setForm({ effective_date: today(), rate: "", remarks: "" })), `Rate ${form.rate}% effective ${fmtDate(form.effective_date)} added`);
  };
  return (
    <Modal title={`${facility.bank} · ${facility.name}`} eyebrow="RATE HISTORY & CONVENTION" onClose={onClose} testId="rate-history-drawer" wide>
      <div className="conv-row">
        <div><b>Day-count convention</b><small>Interest = outstanding × rate × days ÷ {facility.day_count}</small></div>
        <Segmented testId="day-count-toggle" value={facility.day_count} options={DAY_COUNT} onChange={(v) => run(() => api.put(`/facilities/${facility.id}`, { day_count: v }), `Convention set to Actual/${v}`)} />
      </div>
      <div className="timeline" data-testid="rate-timeline">
        {history.map((h, i) => (
          <div className={i === 0 ? "tl-item current" : "tl-item"} key={h.id} data-testid={`rate-entry-${h.id}`}>
            <span className="dot" />
            <div className="tl-body">
              <div className="tl-top"><b className="mono">{pct(h.rate)}</b>{i === 0 && <span className="tag cc">Current</span>}{i < history.length - 1 && <span className="delta mono">{h.rate - history[i + 1].rate > 0 ? "+" : ""}{((h.rate - history[i + 1].rate) * 100).toFixed(0)} bps</span>}</div>
              <small>Effective {fmtDate(h.effective_date)}{h.remarks ? ` · ${h.remarks}` : ""}</small>
            </div>
            <button className="icon-btn" disabled={busy || history.length <= 1} data-testid={`delete-rate-${h.id}`} aria-label="Delete rate" onClick={() => run(() => api.delete(`/facilities/${facility.id}/rates/${h.id}`), "Rate entry removed")}><Trash2 size={15} /></button>
          </div>
        ))}
      </div>
      <form onSubmit={addRate} className="rate-form">
        <Field label="Effective date"><input required type="date" data-testid="rate-effective-date-input" value={form.effective_date} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} /></Field>
        <Field label="New rate (% p.a.)"><input required type="number" step="0.01" min="0.01" data-testid="rate-value-input" value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} /></Field>
        <Field label="Remarks"><input data-testid="rate-remarks-input" value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} placeholder="e.g. MCLR reset" /></Field>
        <button type="submit" className="primary" disabled={busy} data-testid="add-rate-button">+ Add rate change</button>
      </form>
    </Modal>
  );
}
