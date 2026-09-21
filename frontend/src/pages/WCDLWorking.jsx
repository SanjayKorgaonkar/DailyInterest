import { useEffect, useState } from "react";
import { Calculator, Check, CornerDownRight, Pencil, Trash2, X } from "lucide-react";
import { Header } from "../components/Header";
import { Modal, Field } from "../components/Modal";
import { BankCertificate } from "../components/BankCertificate";
import { api, errorText } from "../lib/api";
import { rupee, money, pct, fmtDate, monthLong, today } from "../lib/format";

export default function WCDLWorking({ facilities, month, onAction, refreshAll, focusFacilityId, autoOpenForm }) {
  const wcdlFacilities = facilities.filter((f) => f.type === "WCDL" || f.type === "GML");
  const [facilityId, setFacilityId] = useState("");
  const [working, setWorking] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [savingEdit, setSavingEdit] = useState(false);
  const load = () => api.get("/wcdl-working", { params: { month, ...(facilityId ? { facility_id: facilityId } : {}) } }).then((r) => setWorking(r.data)).catch((e) => onAction(errorText(e)));
  useEffect(() => { load(); }, [facilityId, month]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (focusFacilityId && autoOpenForm) setShowForm(true); }, [focusFacilityId, autoOpenForm]);
  useEffect(() => { if (focusFacilityId) setFacilityId(focusFacilityId); }, [focusFacilityId]);
  const remove = async (id) => {
    try { await api.delete(`/wcdl-loans/${id}`); onAction("Loan removed"); load(); refreshAll(); } catch (e) { onAction(errorText(e)); }
  };
  const startEdit = (r) => { setEditingId(r.id); setEditForm({ loan: r.loan, drawdown: r.drawdown, amount: r.amount, repayment: r.repayment, bank_interest: r.bank ?? "" }); };
  const cancelEdit = () => { setEditingId(null); setEditForm({}); };
  const saveEdit = async (id) => {
    setSavingEdit(true);
    try {
      await api.put(`/wcdl-loans/${id}`, { loan: editForm.loan, drawdown: editForm.drawdown, amount: Number(editForm.amount), repayment: editForm.repayment, bank_interest: editForm.bank_interest === "" ? null : Number(editForm.bank_interest) });
      onAction("Loan updated · interest recalculated");
      cancelEdit();
      load();
      refreshAll();
    } catch (e) { onAction(errorText(e)); } finally { setSavingEdit(false); }
  };
  const rows = working?.rows || [];
  const conventions = [...new Set(wcdlFacilities.filter((f) => !facilityId || f.id === facilityId).map((f) => f.day_count))];
  return (
    <>
      <Header eyebrow="INTEREST ENGINE · WCDL / GML" title="WCDL & gold loan working" sub="Term-loan principal, tenor and prepayment tracking with per-bank day-count conventions.">
        <select className="fac-select" data-testid="wcdl-facility-select" value={facilityId} onChange={(e) => setFacilityId(e.target.value)}>
          <option value="">All WCDL / GML facilities</option>
          {wcdlFacilities.map((f) => <option key={f.id} value={f.id}>{`${f.bank} · ${f.name}${f.type === "GML" ? " (GML)" : ""}`}</option>)}
        </select>
        <button className="primary" data-testid="add-working-row-button" onClick={() => setShowForm(true)} disabled={!wcdlFacilities.length}>+ Add loan</button>
      </Header>
      <div className="working-note">
        <Calculator size={17} />
        <span><b>Formula active:</b> Principal × applicable rate × days ÷ day-count (per facility)</span>
        <span className="note-right" data-testid="wcdl-convention-note">{conventions.map((c) => `Actual / ${c}`).join(" · ") || "Actual / 365"}</span>
      </div>
      {facilityId && <BankCertificate facilityId={facilityId} month={month} calculated={working?.calculated_bank || 0} onChanged={() => { load(); refreshAll(); }} onError={onAction} />}
      <div className="table-wrap">
        <div className="table-toolbar">
          <b>Loan ledger · {monthLong(month)}</b>
          <span className="toolbar-total">Our interest <strong data-testid="wcdl-total-interest">{rupee(working?.ours)}</strong> · Bank <strong data-testid="wcdl-total-bank">{rupee(working?.bank)}</strong> · Variance <strong className={working?.variance ? "danger-text" : "positive"} data-testid="wcdl-total-variance">{working?.variance > 0 ? "+" : ""}{rupee(working?.variance)}</strong></span>
        </div>
        <table>
          <thead><tr>{["Loan number", "Drawdown", "Amount", "Repayment", "Period", "Principal", "Days", "Rate", "Basis", "Our interest", "Bank interest", "Variance", ""].map((x) => <th key={x}>{x}</th>)}</tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={13} className="empty" data-testid="wcdl-empty-state">No loans outstanding in {monthLong(month)}.</td></tr>}
            {rows.map((r, i) => {
              const isEditing = !r.segment && editingId === r.id;
              return (
                <tr key={`${r.id}-${i}`} className={r.segment ? "segment-row" : isEditing ? "editing-row" : ""} data-testid={r.segment ? "wcdl-segment-row" : "wcdl-row"}>
                  <td>{isEditing ? <input className="inline-edit-input" data-testid={`wcdl-edit-loan-${r.id}`} value={editForm.loan} onChange={(e) => setEditForm({ ...editForm, loan: e.target.value })} /> : r.segment ? <span className="seg-label"><CornerDownRight size={12} /> {r.principal !== r.amount && r.prepayment ? "Prepayment" : "Rate change"}</span> : <><b>{r.loan}</b><small>{r.bank_name}</small></>}</td>
                  <td>{isEditing ? <input type="date" className="inline-edit-input" data-testid={`wcdl-edit-drawdown-${r.id}`} value={editForm.drawdown} onChange={(e) => setEditForm({ ...editForm, drawdown: e.target.value })} /> : r.segment ? "" : fmtDate(r.drawdown)}</td>
                  <td className="mono">{isEditing ? <input type="number" min="1" step="0.01" className="inline-edit-input mono" data-testid={`wcdl-edit-amount-${r.id}`} value={editForm.amount} onChange={(e) => setEditForm({ ...editForm, amount: e.target.value })} /> : r.segment ? "" : money(r.amount)}</td>
                  <td>{isEditing ? <input type="date" className="inline-edit-input" data-testid={`wcdl-edit-repayment-${r.id}`} value={editForm.repayment} onChange={(e) => setEditForm({ ...editForm, repayment: e.target.value })} /> : r.segment ? "" : fmtDate(r.repayment)}</td>
                  <td className="mono">{fmtDate(r.from)} → {fmtDate(r.to)}</td>
                  <td className="mono">{money(r.principal)}</td>
                  <td className="mono">{r.days}</td>
                  <td className="mono">{r.segment ? <span className="rate-pill">{pct(r.rate)}</span> : pct(r.rate)}</td>
                  <td><span className="conv">A/{r.day_count}</span></td>
                  <td className="mono">{rupee(r.interest)}</td>
                  <td className="mono">{isEditing ? <input type="number" min="0" step="0.01" className="inline-edit-input mono" data-testid={`wcdl-edit-bank-interest-${r.id}`} value={editForm.bank_interest} onChange={(e) => setEditForm({ ...editForm, bank_interest: e.target.value })} /> : (r.bank == null ? "—" : rupee(r.bank))}</td>
                  <td className={`mono ${r.variance ? "danger-text" : "positive"}`}>{r.variance == null ? "—" : r.variance ? `${r.variance > 0 ? "+" : ""}${rupee(r.variance)}` : "Nil"}</td>
                  <td>
                    {isEditing ? (
                      <div className="row-edit-actions">
                        <button className="icon-btn" data-testid={`save-wcdl-edit-${r.id}`} aria-label="Save" disabled={savingEdit} onClick={() => saveEdit(r.id)}><Check size={14} /></button>
                        <button className="icon-btn" data-testid={`cancel-wcdl-edit-${r.id}`} aria-label="Cancel" onClick={cancelEdit}><X size={14} /></button>
                      </div>
                    ) : !r.segment && (
                      <div className="row-edit-actions">
                        <button className="icon-btn" data-testid={`edit-wcdl-${r.id}`} aria-label="Edit" onClick={() => startEdit(r)}><Pencil size={13} /></button>
                        <button className="icon-btn" data-testid={`delete-wcdl-${r.id}`} aria-label="Delete" onClick={() => remove(r.id)}><Trash2 size={14} /></button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {showForm && <LoanForm facilities={wcdlFacilities} defaultFacility={facilityId || wcdlFacilities[0]?.id} onClose={() => setShowForm(false)} onSaved={() => { setShowForm(false); onAction("Loan added · interest recalculated"); load(); refreshAll(); }} onError={onAction} />}
    </>
  );
}

function LoanForm({ facilities, defaultFacility, onClose, onSaved, onError }) {
  const [form, setForm] = useState({ facility_id: defaultFacility, loan: "", drawdown: today(), amount: "", repayment: "", prepayment: "", prepayment_date: "", bank_interest: "" });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const selectedType = facilities.find((f) => f.id === form.facility_id)?.type;
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/wcdl-loans", { ...form, amount: Number(form.amount), prepayment: Number(form.prepayment) || 0, prepayment_date: form.prepayment_date || null, bank_interest: form.bank_interest === "" ? null : Number(form.bank_interest) });
      onSaved();
    } catch (err) { onError(errorText(err)); } finally { setSaving(false); }
  };
  return (
    <Modal title="Add loan" eyebrow="LOAN LEDGER" onClose={onClose} testId="wcdl-loan-form">
      <form onSubmit={submit} className="form-grid">
        <Field label="Facility">
          <select required data-testid="wcdl-form-facility-select" value={form.facility_id} onChange={set("facility_id")}>{facilities.map((f) => <option key={f.id} value={f.id}>{`${f.bank} · ${f.name}${f.type === "GML" ? " (GML)" : ""}`}</option>)}</select>
        </Field>
        <Field label="Loan number"><input required data-testid="wcdl-loan-input" value={form.loan} onChange={set("loan")} placeholder={selectedType === "GML" ? "e.g. GML-AX-2501" : "e.g. WCDL-AX-2501"} /></Field>
        <Field label="Drawdown date"><input required type="date" data-testid="wcdl-drawdown-input" value={form.drawdown} onChange={set("drawdown")} /></Field>
        <Field label="Repayment date"><input required type="date" data-testid="wcdl-repayment-input" value={form.repayment} onChange={set("repayment")} /></Field>
        <Field label="Amount (₹)"><input required type="number" min="1" step="0.01" data-testid="wcdl-amount-input" value={form.amount} onChange={set("amount")} /></Field>
        <Field label="Bank interest (₹)" hint="Optional · for reconciliation"><input type="number" min="0" step="0.01" data-testid="wcdl-bank-interest-input" value={form.bank_interest} onChange={set("bank_interest")} /></Field>
        <Field label="Prepayment (₹)"><input type="number" min="0" step="0.01" data-testid="wcdl-prepayment-input" value={form.prepayment} onChange={set("prepayment")} /></Field>
        <Field label="Prepayment date"><input type="date" data-testid="wcdl-prepayment-date-input" value={form.prepayment_date} onChange={set("prepayment_date")} /></Field>
        <div className="form-actions">
          <button type="button" className="outline" onClick={onClose} data-testid="wcdl-form-cancel-button">Cancel</button>
          <button type="submit" className="primary" disabled={saving} data-testid="wcdl-form-submit-button">{saving ? "Saving…" : "Add loan"}</button>
        </div>
      </form>
    </Modal>
  );
}
