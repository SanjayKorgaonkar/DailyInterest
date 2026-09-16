import { useEffect, useState } from "react";
import { BadgeCheck, PencilLine, X } from "lucide-react";
import { api, errorText } from "../lib/api";
import { rupee } from "../lib/format";

export function BankCertificate({ facilityId, month, calculated, onChanged, onError }) {
  const [cert, setCert] = useState(null);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => {
    if (!facilityId) { setCert(null); return; }
    api.get("/bank-certificates", { params: { facility_id: facilityId, month } }).then((r) => setCert(r.data)).catch(() => setCert(null));
  };
  useEffect(load, [facilityId, month]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/bank-certificates", { facility_id: facilityId, month, amount: Number(value) });
      setEditing(false);
      load();
      onChanged?.();
    } catch (e) { onError?.(errorText(e)); } finally { setSaving(false); }
  };

  const remove = async () => {
    try { await api.delete(`/bank-certificates/${facilityId}/${month}`); setCert(null); onChanged?.(); } catch (e) { onError?.(errorText(e)); }
  };

  if (!facilityId) return null;

  return (
    <div className="certificate-strip" data-testid="bank-certificate-strip">
      {cert ? (
        <>
          <BadgeCheck size={15} />
          <span>Bank certificate on file: <b data-testid="certificate-amount">{rupee(cert.amount)}</b> · overriding calculated {rupee(calculated)}</span>
          <button className="text-btn" data-testid="edit-certificate-button" onClick={() => { setValue(cert.amount); setEditing(true); }}><PencilLine size={13} /> Edit</button>
          <button className="text-btn" data-testid="remove-certificate-button" onClick={remove}><X size={13} /> Remove</button>
        </>
      ) : editing ? (
        <>
          <BadgeCheck size={15} />
          <input type="number" min="0" step="0.01" autoFocus data-testid="certificate-amount-input" value={value} onChange={(e) => setValue(e.target.value)} placeholder="Bank certified interest (₹)" />
          <button className="text-btn" data-testid="save-certificate-button" disabled={saving || value === ""} onClick={save}>{saving ? "Saving…" : "Save"}</button>
          <button className="text-btn" data-testid="cancel-certificate-button" onClick={() => setEditing(false)}>Cancel</button>
        </>
      ) : (
        <>
          <BadgeCheck size={15} />
          <button className="text-btn" data-testid="add-certificate-button" onClick={() => { setValue(""); setEditing(true); }}>+ Enter bank certificate for this month · overrides calculated {rupee(calculated)}</button>
        </>
      )}
    </div>
  );
}
