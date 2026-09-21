import { useState } from "react";
import { Check, CheckCircle2, History, Pencil, Trash2, X } from "lucide-react";
import { Header } from "../components/Header";
import { Modal, Field, Segmented } from "../components/Modal";
import { api, errorText } from "../lib/api";
import { money, pct, fmtDate, today } from "../lib/format";

const DAY_COUNT = [{ value: 365, label: "Actual / 365" }, { value: 360, label: "Actual / 360" }];

export default function Facilities({ data, onAction, reload, onNavigate }) {
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [rateFor, setRateFor] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [savingEdit, setSavingEdit] = useState(false);
  const filtered = data.filter((f) => `${f.bank} ${f.name} ${f.type}`.toLowerCase().includes(query.toLowerCase()));
  const selected = rateFor && data.find((f) => f.id === rateFor);
  const startEdit = (f) => { setEditingId(f.id); setEditForm({ bank: f.bank, name: f.name, limit: f.limit, start: f.start, maturity: f.maturity, status: f.status, day_count: f.day_count }); };
  const cancelEdit = () => { setEditingId(null); setEditForm({}); };
  const saveEdit = async (id) => {
    setSavingEdit(true);
    try {
      await api.put(`/facilities/${id}`, { bank: editForm.bank.trim(), name: editForm.name.trim(), limit: Number(editForm.limit), start: editForm.start, maturity: editForm.maturity, status: editForm.status, day_count: Number(editForm.day_count) });
      onAction("Facility updated");
      cancelEdit();
      reload();
    } catch (e) { onAction(errorText(e)); } finally { setSavingEdit(false); }
  };
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
            {filtered.map((f) => {
              const isEditing = editingId === f.id;
              return (
                <tr key={f.id} className={isEditing ? "editing-row" : ""} data-testid={`facility-row-${f.id}`}>
                  <td>{isEditing ? (
                    <div className="inline-edit-stack">
                      <input className="inline-edit-input" data-testid={`facility-edit-bank-${f.id}`} value={editForm.bank} onChange={(e) => setEditForm({ ...editForm, bank: e.target.value })} placeholder="Bank" />
                      <input className="inline-edit-input" data-testid={`facility-edit-name-${f.id}`} value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} placeholder="Facility name" />
                    </div>
                  ) : <><b>{f.bank}</b><small>{f.name}</small></>}</td>
                  <td><span className={`tag ${f.type.toLowerCase()}`}>{f.type}</span></td>
                  <td className="mono">{isEditing ? <input type="number" min="1" step="1" className="inline-edit-input mono" data-testid={`facility-edit-limit-${f.id}`} value={editForm.limit} onChange={(e) => setEditForm({ ...editForm, limit: e.target.value })} /> : money(f.limit)}</td>
                  <td className="mono">{money(f.outstanding)}</td>
                  <td className="mono" data-testid={`facility-rate-${f.id}`}>{pct(f.rate)}<small>{f.rate_history.length > 1 ? `${f.rate_history.length - 1} change${f.rate_history.length > 2 ? "s" : ""}` : "no changes"}</small></td>
                  <td>{isEditing ? (
                    <select className="inline-edit-input" data-testid={`facility-edit-daycount-${f.id}`} value={editForm.day_count} onChange={(e) => setEditForm({ ...editForm, day_count: e.target.value })}>
                      {DAY_COUNT.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                    </select>
                  ) : <span className="conv" data-testid={`facility-convention-${f.id}`}>Actual/{f.day_count}</span>}</td>
                  <td>{isEditing ? <input type="date" className="inline-edit-input" data-testid={`facility-edit-start-${f.id}`} value={editForm.start} onChange={(e) => setEditForm({ ...editForm, start: e.target.value })} /> : fmtDate(f.start)}</td>
                  <td>{isEditing ? <input className="inline-edit-input" data-testid={`facility-edit-maturity-${f.id}`} value={editForm.maturity} onChange={(e) => setEditForm({ ...editForm, maturity: e.target.value })} /> : f.maturity}</td>
                  <td>{isEditing ? (
                    <select className="inline-edit-input" data-testid={`facility-edit-status-${f.id}`} value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                      <option value="Active">Active</option>
                      <option value="Closed">Closed</option>
                    </select>
                  ) : <span className="status">● {f.status}</span>}</td>
                  <td>
                    {isEditing ? (
                      <div className="row-edit-actions">
                        <button className="icon-btn" data-testid={`save-facility-edit-${f.id}`} aria-label="Save" disabled={savingEdit} onClick={() => saveEdit(f.id)}><Check size={14} /></button>
                        <button className="icon-btn" data-testid={`cancel-facility-edit-${f.id}`} aria-label="Cancel" onClick={cancelEdit}><X size={14} /></button>
                      </div>
                    ) : (
                      <div className="row-edit-actions">
                        <button className="icon-btn" data-testid={`edit-facility-${f.id}`} aria-label="Edit" onClick={() => startEdit(f)}><Pencil size={13} /></button>
                        <button className="text-btn row-btn" data-testid={`rate-history-button-${f.id}`} onClick={() => setRateFor(f.id)}><History size={14} /> Rate history</button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {showForm && <FacilityForm onClose={() => setShowForm(false)} onSaved={(f, jump) => {
        setShowForm(false);
        onAction(`${f.bank} · ${f.name} created`);
        reload();
        if (jump) onNavigate?.(f.type === "CC" ? "cc" : "wcdl", { facilityId: f.id, autoOpenForm: true });
      }} onError={onAction} />}
      {selected && <RateHistory facility={selected} onClose={() => setRateFor(null)} onAction={onAction} reload={reload} />}
    </>
  );
}

function FacilityForm({ onClose, onSaved, onError }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ bank: "", type: "CC", name: "", limit: "", start: today(), maturity: "On demand", status: "Active", day_count: 365, rate: "" });
  const [saving, setSaving] = useState(false);
  const [created, setCreated] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const STEPS = [
    { n: 1, label: "Basics" },
    { n: 2, label: "Limit & tenure" },
    { n: 3, label: "Pricing" },
  ];
  const valid = {
    1: form.bank.trim() && form.name.trim(),
    2: Number(form.limit) > 0 && form.start && form.maturity.trim(),
    3: Number(form.rate) > 0,
  };
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const r = await api.post("/facilities", { ...form, bank: form.bank.trim(), name: form.name.trim(), limit: Number(form.limit), rate: Number(form.rate) });
      setCreated(r.data);
    } catch (err) { onError(errorText(err)); } finally { setSaving(false); }
  };
  if (created) {
    return (
      <Modal title="New facility" eyebrow="FACILITY MASTER · QUICK-START" onClose={() => onSaved(created, false)} testId="facility-form">
        <div className="wizard-success" data-testid="wizard-success">
          <CheckCircle2 size={32} />
          <b>{created.bank} · {created.name} created</b>
          <span>Want to log its first transaction now so the Dashboard shows real numbers right away?</span>
          <div className="form-actions">
            <button type="button" className="outline" data-testid="wizard-skip-transaction-button" onClick={() => onSaved(created, false)}>I'll do this later</button>
            <button type="button" className="primary" data-testid="wizard-add-transaction-button" onClick={() => onSaved(created, true)}>Add first transaction</button>
          </div>
        </div>
      </Modal>
    );
  }
  return (
    <Modal title="New facility" eyebrow="FACILITY MASTER · QUICK-START" onClose={onClose} testId="facility-form">
      <div className="wizard-progress" data-testid="wizard-progress">
        {STEPS.map((s) => (
          <div key={s.n} className={`wizard-step${step === s.n ? " active" : step > s.n ? " done" : ""}`} data-testid={`wizard-step-${s.n}`}>
            <span className="wizard-dot">{step > s.n ? "✓" : s.n}</span>
            <small>{s.label}</small>
          </div>
        ))}
      </div>
      <form onSubmit={submit} className="form-grid wizard-body">
        {step === 1 && (
          <>
            <Field label="Bank"><input required autoFocus data-testid="facility-bank-input" value={form.bank} onChange={set("bank")} placeholder="e.g. Kotak Mahindra Bank" /></Field>
            <Field label="Facility name"><input required data-testid="facility-name-input" value={form.name} onChange={set("name")} placeholder="e.g. Cash Credit" /></Field>
            <Field label="Type">
              <Segmented testId="facility-type" value={form.type} options={[{ value: "CC", label: "Cash Credit" }, { value: "WCDL", label: "WCDL" }, { value: "GML", label: "Gold Metal Loan" }]} onChange={(v) => setForm({ ...form, type: v, maturity: v === "CC" ? "On demand" : "90 days" })} />
            </Field>
          </>
        )}
        {step === 2 && (
          <>
            <Field label="Sanctioned limit (₹)"><input required autoFocus type="number" min="1" step="1" data-testid="facility-limit-input" value={form.limit} onChange={set("limit")} /></Field>
            <Field label="Start date"><input required type="date" data-testid="facility-start-input" value={form.start} onChange={set("start")} /></Field>
            <Field label="Maturity"><input required data-testid="facility-maturity-input" value={form.maturity} onChange={set("maturity")} /></Field>
          </>
        )}
        {step === 3 && (
          <>
            <Field label="Initial rate (% p.a.)" hint="Effective from the start date"><input required autoFocus type="number" min="0.01" step="0.01" data-testid="facility-rate-input" value={form.rate} onChange={set("rate")} /></Field>
            <Field label="Day-count convention">
              <Segmented testId="facility-day-count" value={form.day_count} options={DAY_COUNT} onChange={(v) => setForm({ ...form, day_count: v })} />
            </Field>
            <div className="wizard-preview" data-testid="wizard-formula-preview">
              <b>Formula preview</b>
              <span className="mono">Outstanding × {form.rate || "0"}% × Days ÷ {form.day_count}</span>
            </div>
          </>
        )}
        <div className="form-actions">
          {step > 1 ? (
            <button type="button" className="outline" data-testid="wizard-back-button" onClick={() => setStep(step - 1)}>Back</button>
          ) : (
            <button type="button" className="outline" onClick={onClose} data-testid="facility-form-cancel-button">Cancel</button>
          )}
          {step < 3 ? (
            <button type="button" className="primary" disabled={!valid[step]} data-testid="wizard-next-button" onClick={() => setStep(step + 1)}>Next</button>
          ) : (
            <button type="submit" className="primary" disabled={saving || !valid[3]} data-testid="facility-form-submit-button">{saving ? "Saving…" : "Create facility"}</button>
          )}
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
