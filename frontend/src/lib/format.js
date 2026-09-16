export const money = (v) => `₹${((v || 0) / 10000000).toFixed(2)} Cr`;
export const rupee = (v) => `${v < 0 ? "-" : ""}₹${Math.abs(Number(v || 0)).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
export const pct = (v) => `${Number(v || 0).toFixed(2)}%`;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const monthLabel = (ym) => { const [y, m] = ym.split("-"); return `${MONTHS[+m - 1]} ${y}`; };
export const monthLong = (ym) => { const [y, m] = ym.split("-"); return new Date(+y, +m - 1, 1).toLocaleString("en-IN", { month: "long", year: "numeric" }); };
export const monthEnd = (ym) => { const [y, m] = ym.split("-").map(Number); return new Date(y, m, 0).toISOString().slice(0, 10); };

export const monthOptions = (count = 12) => {
  const now = new Date();
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
};

export const today = () => new Date().toISOString().slice(0, 10);
export const fmtDate = (s) => (s ? new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—");
