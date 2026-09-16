export function Header({ eyebrow, title, sub, children }) {
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 data-testid="page-title">{title}</h1>
        <p data-testid="page-description">{sub}</p>
      </div>
      <div className="head-actions">{children}</div>
    </div>
  );
}
