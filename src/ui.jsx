import { useEffect, useRef, useState } from "react";

export function Badge({ value }) {
  return <span className={`badge b-${String(value).toLowerCase().replace(/\s+/g, "-")}`}>{value}</span>;
}

export function Progress({ value, color }) {
  return (
    <div className="bar"><span style={{ width: `${Math.min(100, value || 0)}%`, background: color }} /></div>
  );
}

export function Stat({ label, value, tone = "purple", icon }) {
  return (
    <div className="stat"><div className={`stat-icon ${tone}`}>{icon}</div><div><small>{label}</small><strong>{value}</strong></div></div>
  );
}

export function Card({ title, sub, actions, children }) {
  return (
    <section className="card">
      {(title || actions) && (
        <div className="card-head"><div><h3>{title}</h3>{sub && <p>{sub}</p>}</div><div className="row">{actions}</div></div>
      )}
      {children}
    </section>
  );
}

export function Empty({ text = "Nothing here yet." }) {
  return <div className="empty">{text}</div>;
}

export function Modal({ title, onClose, children }) {
  return (
    <div className="modal-bg" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal"><div className="card-head"><h3>{title}</h3><button className="icon-btn" onClick={onClose}>✕</button></div>{children}</div>
    </div>
  );
}

export function BarChart({ data }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="chart">
      {data.map((d) => (
        <div className="chart-col" key={d.label}>
          <span className="chart-val">{d.value}</span>
          <div className="chart-bar" style={{ height: `${(d.value / max) * 100}%`, background: d.color }} />
          <small>{d.label}</small>
        </div>
      ))}
    </div>
  );
}

export function Donut({ done, total }) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  return (
    <div className="donut" style={{ background: `conic-gradient(#6d5dfc ${pct * 3.6}deg, #e8e6f7 0)` }}><div><b>{pct}%</b><small>complete</small></div></div>
  );
}

export function useLoad(fn, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);
  const busy = useRef(false);
  useEffect(() => {
    let live = true;
    busy.current = true;
    fn().then((d) => live && (setData(d), setError(""))).catch((e) => live && setError(e.message)).finally(() => { busy.current = false; });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  useEffect(() => {
    const t = setInterval(() => { if (!document.hidden && !busy.current) setTick((x) => x + 1); }, 5000);
    return () => clearInterval(t);
  }, []);
  return { data, error, reload: () => setTick((t) => t + 1), setData };
}

export const fmtDate = (d) => (d ? new Date(d).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—");
export const fmtTime = (d) => (d ? new Date(d.endsWith("Z") ? d : d + "Z").toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "");
export const today = () => new Date().toISOString().slice(0, 10);
