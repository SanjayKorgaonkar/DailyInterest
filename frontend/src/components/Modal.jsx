import { X } from "lucide-react";

export function Modal({ title, eyebrow, onClose, children, testId = "modal", wide }) {
  return (
    <div className="overlay" onClick={onClose} data-testid={`${testId}-overlay`}>
      <div className={wide ? "modal wide" : "modal"} onClick={(e) => e.stopPropagation()} data-testid={testId} role="dialog">
        <div className="modal-head">
          <div>
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            <h2>{title}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} data-testid={`${testId}-close-button`} aria-label="Close"><X size={18} /></button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}

export function Segmented({ value, options, onChange, testId }) {
  return (
    <div className="segmented" data-testid={testId}>
      {options.map((o) => (
        <button key={o.value} type="button" className={value === o.value ? "on" : ""} onClick={() => onChange(o.value)} data-testid={`${testId}-${o.value}`}>{o.label}</button>
      ))}
    </div>
  );
}
