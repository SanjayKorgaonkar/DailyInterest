import { useCallback, useEffect, useState } from "react";
import { BarChart3, Building2, Calculator, ChevronRight, CircleHelp, LayoutDashboard, Menu, RefreshCw, Scale, Settings, WalletCards, X } from "lucide-react";
import "@/App.css";
import { api } from "./lib/api";
import { monthLabel, monthOptions } from "./lib/format";
import Dashboard from "./pages/Dashboard";
import Facilities from "./pages/Facilities";
import CCWorking from "./pages/CCWorking";
import WCDLWorking from "./pages/WCDLWorking";
import { Reconciliation, Reports } from "./pages/Reports";

const EMPTY = { dashboard: { facilities: 0, banks: 0, limit: 0, outstanding: 0, available: 0, utilisation: 0, month_interest: 0, month_bank_interest: 0, ytd_interest: 0, variance: 0, rate_changes: 0 }, facilities: [], recon: [] };
const NAV = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "facilities", label: "Facility Master", icon: Building2 },
  { id: "cc", label: "CC Interest Working", icon: Calculator },
  { id: "wcdl", label: "WCDL Interest Working", icon: WalletCards },
  { id: "recon", label: "Bank Reconciliation", icon: Scale },
  { id: "reports", label: "Reports", icon: BarChart3 },
];
const MONTHS = monthOptions(12);

function App() {
  const [data, setData] = useState(EMPTY);
  const [page, setPage] = useState("dashboard");
  const [mobile, setMobile] = useState(false);
  const [month, setMonth] = useState(MONTHS[0]);
  const [toast, setToast] = useState("");
  const action = (text) => { setToast(text); setTimeout(() => setToast(""), 2800); };
  const reload = useCallback(() => {
    Promise.all(["dashboard", "facilities", "reconciliation"].map((k) => api.get(`/${k}`, { params: { month } }).then((r) => r.data)))
      .then(([dashboard, facilities, recon]) => setData({ dashboard, facilities, recon }))
      .catch(() => action("Could not reach the interest engine"));
  }, [month]);
  useEffect(() => { reload(); }, [reload]);
  const go = (id) => { setPage(id); setMobile(false); };
  return (
    <div className="app-shell">
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <div className="brand-mark">₹</div>
          <div><strong>Ledgerline</strong><span>Interest control room</span></div>
          <button className="icon-btn mobile-close" data-testid="close-navigation-button" onClick={() => setMobile(false)}><X size={18} /></button>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {NAV.map((n) => (
            <button key={n.id} data-testid={`${n.id}-navigation-button`} className={page === n.id ? "nav-item active" : "nav-item"} onClick={() => go(n.id)}>
              <n.icon size={17} /><span>{n.label}</span>{page === n.id && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button className="nav-item" data-testid="settings-navigation-button" onClick={() => go("facilities")}><Settings size={17} /><span>Settings</span></button>
          <div className="offline"><span className="pulse" />Engine connected<span>Actual/365 · Actual/360 per facility</span></div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" data-testid="open-navigation-button" onClick={() => setMobile(true)}><Menu size={20} /></button>
          <div className="crumb"><span>Finance /</span><b>{NAV.find((x) => x.id === page)?.label}</b></div>
          <div className="top-actions">
            <select data-testid="period-selector" value={month} onChange={(e) => setMonth(e.target.value)}>
              {MONTHS.map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}
            </select>
            <button className="icon-btn" data-testid="refresh-data-button" onClick={() => { reload(); action("Workspace refreshed"); }}><RefreshCw size={17} /></button>
            <button className="help" data-testid="help-button" onClick={() => action("Tip: add rate changes from Facility Master → Rate history.")}><CircleHelp size={16} /> Help</button>
            <div className="avatar" data-testid="user-avatar">AK</div>
          </div>
        </header>
        <section className="content">
          {page === "dashboard" && <Dashboard data={data} onNavigate={go} month={month} />}
          {page === "facilities" && <Facilities data={data.facilities} onAction={action} reload={reload} />}
          {page === "cc" && <CCWorking facilities={data.facilities} month={month} onAction={action} refreshAll={reload} />}
          {page === "wcdl" && <WCDLWorking facilities={data.facilities} month={month} onAction={action} refreshAll={reload} />}
          {page === "recon" && <Reconciliation rows={data.recon} month={month} onAction={action} />}
          {page === "reports" && <Reports onAction={action} month={month} />}
        </section>
      </main>
      {toast && <div className="toast" data-testid="toast-message">{toast}</div>}
    </div>
  );
}

export default App;
