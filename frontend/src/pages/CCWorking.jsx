import { useEffect, useRef, useState } from "react";
import { Calculator, CheckCircle2, CornerDownRight, FileWarning, Trash2, Upload, UploadCloud } from "lucide-react";
import { Header } from "../components/Header";
import { Modal, Field } from "../components/Modal";
import { api, errorText } from "../lib/api";
import { rupee, pct, fmtDate, monthLong, today } from "../lib/format";

export default function CCWorking({ facilities, month, onAction, refreshAll }) {
  const ccFacilities = facilities.filter((f) => f.type === "CC");
  const [facilityId, setFacilityId] = useState(ccFacilities[0]?.id || "");
  const [working, setWorking] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  useEffect(() => { if (!facilityId && ccFacilities[0]) setFacilityId(ccFacilities[0].id); }, [ccFacilities, facilityId]);
  const load = () => { if (facilityId) api.get("/cc-working", { params: { facility_id: facilityId, month } }).then((r) => setWorking(r.data)).catch((e) => onAction(errorText(e))); };
  useEffect(load, [facilityId, month]); // eslint-disable-line react-hooks/exhaustive-deps
  const remove = async (id) => {
    try { await api.delete(`/cc-transactions/${id}`); onAction("Transaction removed"); load(); refreshAll(); } catch (e) { onAction(errorText(e)); }
  };
  const fac = working?.facility;
  const rows = working?.rows || [];
  return (
    <>
      <Header eyebrow="INTEREST ENGINE · CASH CREDIT" title="CC interest working" sub="Daily debit balance calculation with value-date control and effective-date rate changes.">
        <select className="fac-select" data-testid="cc-facility-select" value={facilityId} onChange={(e) => setFacilityId(e.target.value)}>
          {ccFacilities.map((f) => <option key={f.id} value={f.id}>{f.bank} · {f.name}</option>)}
        </select>
        <button className="outline" data-testid="import-working-button" onClick={() => setShowImport(true)} disabled={!facilityId}><Upload size={15} /> Import statement</button>
        <button className="primary" data-testid="add-working-row-button" onClick={() => setShowForm(true)} disabled={!facilityId}>+ Add row</button>
      </Header>
      <div className="working-note">
        <Calculator size={17} />
        <span><b>Formula active:</b> Closing outstanding × applicable rate × days ÷ {working?.day_count || 365}</span>
        <span className="note-right" data-testid="cc-convention-note">{fac ? `Actual / ${fac.day_count} · ${fac.rate_history.length} rate${fac.rate_history.length === 1 ? "" : "s"} on file` : "Value date basis"}</span>
      </div>
      <div className="table-wrap">
        <div className="table-toolbar">
          <b>CC transaction ledger · {monthLong(month)}</b>
          <span className="toolbar-total">Our interest <strong data-testid="cc-total-interest">{rupee(working?.ours)}</strong> · Bank <strong data-testid="cc-total-bank">{rupee(working?.bank)}</strong> · Diff <strong className={working?.difference ? "danger-text" : "positive"} data-testid="cc-total-difference">{working?.difference > 0 ? "+" : ""}{rupee(working?.difference)}</strong></span>
        </div>
        <table>
          <thead><tr>{["Transaction date", "Value date", "Period to", "Debit", "Credit", "Closing outstanding", "Days", "Rate", "Our interest", "Bank charged", "Difference", ""].map((x) => <th key={x}>{x}</th>)}</tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={12} className="empty" data-testid="cc-empty-state">No transactions for {monthLong(month)}. Add a row to start the working.</td></tr>}
            {rows.map((r, i) => (
              <tr key={`${r.id}-${i}`} className={r.segment ? "segment-row" : ""} data-testid={r.segment ? "cc-segment-row" : "cc-row"}>
                <td>{r.segment ? <span className="seg-label"><CornerDownRight size={12} /> Rate change</span> : r.opening ? <span className="seg-label">Opening balance</span> : fmtDate(r.date)}</td>
                <td>{fmtDate(r.value_date)}</td>
                <td>{fmtDate(r.to)}</td>
                <td className="mono">{r.debit ? rupee(r.debit) : "—"}</td>
                <td className="mono positive">{r.credit ? rupee(r.credit) : "—"}</td>
                <td className="mono">{rupee(r.closing)}</td>
                <td className="mono">{r.days}</td>
                <td className="mono">{r.segment ? <span className="rate-pill">{pct(r.rate)}</span> : pct(r.rate)}</td>
                <td className="mono">{rupee(r.interest)}</td>
                <td className="mono">{r.bank == null ? "—" : rupee(r.bank)}</td>
                <td className={`mono ${r.difference > 0 ? "danger-text" : "positive"}`}>{r.difference == null ? "—" : `${r.difference > 0 ? "+" : ""}${rupee(r.difference)}`}</td>
                <td>{!r.segment && !r.opening && <button className="icon-btn" data-testid={`delete-cc-${r.id}`} aria-label="Delete" onClick={() => remove(r.id)}><Trash2 size={14} /></button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showForm && <TransactionForm facilityId={facilityId} onClose={() => setShowForm(false)} onSaved={() => { setShowForm(false); onAction("Transaction added · interest recalculated"); load(); refreshAll(); }} onError={onAction} />}
      {showImport && <StatementImportModal facilityId={facilityId} onClose={() => setShowImport(false)} onImported={(n) => { setShowImport(false); onAction(`${n} transaction${n === 1 ? "" : "s"} imported · interest recalculated`); load(); refreshAll(); }} onError={onAction} />}
    </>
  );
}

function TransactionForm({ facilityId, onClose, onSaved, onError }) {
  const [form, setForm] = useState({ date: today(), value_date: "", debit: "", credit: "", bank_interest: "", narration: "" });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/cc-transactions", { facility_id: facilityId, date: form.date, value_date: form.value_date || form.date, debit: Number(form.debit) || 0, credit: Number(form.credit) || 0, bank_interest: form.bank_interest === "" ? null : Number(form.bank_interest), narration: form.narration });
      onSaved();
    } catch (err) { onError(errorText(err)); } finally { setSaving(false); }
  };
  return (
    <Modal title="Add CC transaction" eyebrow="CC LEDGER" onClose={onClose} testId="cc-transaction-form">
      <form onSubmit={submit} className="form-grid">
        <Field label="Transaction date"><input required type="date" data-testid="cc-date-input" value={form.date} onChange={set("date")} /></Field>
        <Field label="Value date" hint="Defaults to transaction date"><input type="date" data-testid="cc-value-date-input" value={form.value_date} onChange={set("value_date")} /></Field>
        <Field label="Debit (₹)"><input type="number" min="0" step="0.01" data-testid="cc-debit-input" value={form.debit} onChange={set("debit")} /></Field>
        <Field label="Credit (₹)"><input type="number" min="0" step="0.01" data-testid="cc-credit-input" value={form.credit} onChange={set("credit")} /></Field>
        <Field label="Bank charged interest (₹)" hint="Optional · for reconciliation"><input type="number" min="0" step="0.01" data-testid="cc-bank-interest-input" value={form.bank_interest} onChange={set("bank_interest")} /></Field>
        <Field label="Narration"><input data-testid="cc-narration-input" value={form.narration} onChange={set("narration")} /></Field>
        <div className="form-actions">
          <button type="button" className="outline" onClick={onClose} data-testid="cc-form-cancel-button">Cancel</button>
          <button type="submit" className="primary" disabled={saving} data-testid="cc-form-submit-button">{saving ? "Saving…" : "Add transaction"}</button>
        </div>
      </form>
    </Modal>
  );
}

const MAPPING_FIELDS = [
  { key: "date_col", label: "Transaction date column", required: true },
  { key: "value_date_col", label: "Value date column", hint: "Defaults to transaction date" },
  { key: "debit_col", label: "Debit / withdrawal column" },
  { key: "credit_col", label: "Credit / deposit column" },
  { key: "amount_col", label: "Single amount column", hint: "Use instead of separate debit/credit columns" },
  { key: "dr_cr_col", label: "Dr / Cr indicator column", hint: "Optional · used with single amount column" },
  { key: "narration_col", label: "Narration / description column" },
  { key: "bank_interest_col", label: "Bank charged interest column", hint: "Optional · for reconciliation" },
];

function StatementImportModal({ facilityId, onClose, onImported, onError }) {
  const [step, setStep] = useState("upload");
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState("");
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [mapping, setMapping] = useState({});
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const fileInput = useRef(null);

  const upload = async (file) => {
    setBusy(true);
    setFileName(file.name);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/cc-transactions/import/parse", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setColumns(r.data.columns);
      setRows(r.data.rows);
      setMapping(r.data.mapping);
      setStep("map");
    } catch (e) { onError(errorText(e)); } finally { setBusy(false); }
  };

  const runPreview = async (nextMapping) => {
    try {
      const r = await api.post("/cc-transactions/import/commit", { facility_id: facilityId, mapping: nextMapping, rows: rows.slice(0, 8), dry_run: true });
      setPreview(r.data);
    } catch (e) { onError(errorText(e)); }
  };

  useEffect(() => { if (step === "map" && rows.length) runPreview(mapping); }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  const setField = (key) => (e) => {
    const next = { ...mapping, [key]: e.target.value || null };
    setMapping(next);
    runPreview(next);
  };

  const commit = async () => {
    setBusy(true);
    try {
      const r = await api.post("/cc-transactions/import/commit", { facility_id: facilityId, mapping, rows, dry_run: false });
      setResult(r.data);
      setStep("result");
    } catch (e) { onError(errorText(e)); } finally { setBusy(false); }
  };

  return (
    <Modal title="Import bank statement" eyebrow="CC LEDGER · CSV / XLSX" onClose={onClose} testId="import-statement-modal" wide>
      {step === "upload" && (
        <div className="dropzone" data-testid="import-dropzone" onClick={() => fileInput.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) upload(f); }}>
          <UploadCloud size={28} />
          <b>{busy ? "Reading file…" : "Click or drop a CSV / XLSX statement"}</b>
          <span>Columns are auto-detected — you can adjust the mapping on the next step.</span>
          <input ref={fileInput} type="file" hidden accept=".csv,.xlsx,.xls" data-testid="import-file-input"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); }} />
        </div>
      )}
      {step === "map" && (
        <div data-testid="import-mapping-step">
          <div className="import-file-line"><FileWarning size={14} /> {fileName} · {rows.length} row{rows.length === 1 ? "" : "s"} detected</div>
          <div className="mapping-grid">
            {MAPPING_FIELDS.map((f) => (
              <Field key={f.key} label={f.required ? `${f.label} *` : f.label} hint={f.hint}>
                <select data-testid={`import-map-${f.key}`} value={mapping[f.key] || ""} onChange={setField(f.key)}>
                  <option value="">— none —</option>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </Field>
            ))}
          </div>
          <div className="import-preview">
            <b>Preview (first {preview?.transactions?.length || 0} rows)</b>
            <table>
              <thead><tr><th>Date</th><th>Value date</th><th>Debit</th><th>Credit</th><th>Narration</th></tr></thead>
              <tbody>
                {(preview?.transactions || []).map((t, i) => (
                  <tr key={i} data-testid="import-preview-row">
                    <td>{fmtDate(t.date)}</td><td>{fmtDate(t.value_date)}</td>
                    <td className="mono">{t.debit ? rupee(t.debit) : "—"}</td>
                    <td className="mono positive">{t.credit ? rupee(t.credit) : "—"}</td>
                    <td>{t.narration}</td>
                  </tr>
                ))}
                {preview && preview.transactions.length === 0 && <tr><td colSpan={5} className="empty">No valid rows with this mapping — adjust the columns above.</td></tr>}
              </tbody>
            </table>
            {preview?.errors?.length > 0 && <div className="import-warnings" data-testid="import-warnings">{preview.errors.length} row(s) will be skipped, e.g. {preview.errors[0]}</div>}
          </div>
          <div className="form-actions">
            <button type="button" className="outline" onClick={onClose} data-testid="import-cancel-button">Cancel</button>
            <button type="button" className="primary" disabled={busy || !mapping.date_col} onClick={commit} data-testid="import-commit-button">
              {busy ? "Importing…" : `Import ${rows.length} row${rows.length === 1 ? "" : "s"}`}
            </button>
          </div>
        </div>
      )}
      {step === "result" && result && (
        <div className="import-result" data-testid="import-result">
          <CheckCircle2 size={30} />
          <b data-testid="import-result-inserted">{result.inserted} transaction{result.inserted === 1 ? "" : "s"} imported</b>
          {result.skipped > 0 && <span>{result.skipped} row(s) skipped — {result.errors.slice(0, 3).join("; ")}</span>}
          <button type="button" className="primary" onClick={() => onImported(result.inserted)} data-testid="import-done-button">Done</button>
        </div>
      )}
    </Modal>
  );
}
