import { useState } from "react";
import { clearAuth, getToken, getUser, login, register, saveAuth } from "./api";
import ManagerPortal from "./ManagerPortal";
import EmployeePortal from "./EmployeePortal";

function Landing({ choose }) {
  return (
    <div className="landing">
      <header><div className="brand light"><span className="logo">T</span>TaskFlow</div></header>
      <main>
        <span className="pill">WELCOME TO OUR PLATFORM</span>
        <h1>Choose your portal</h1>
        <p>Plan projects, match the right people to the right work, and clear blockers together.</p>
        <div className="portals">
          <button className="portal" onClick={() => choose("manager")}><span className="p-icon">🧭</span><h2>Manager Portal</h2><p>Projects, tasks, skill-based matching and team overview.</p><b>Manager Login →</b></button>
          <button className="portal" onClick={() => choose("employee")}><span className="p-icon">🚀</span><h2>Employee Portal</h2><p>My tasks, daily planner, bottleneck detective and skill growth.</p><b>Employee Login →</b></button>
        </div>
      </main>
    </div>
  );
}

function AuthPage({ role, back, onAuth }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const label = role === "manager" ? "Manager" : "Employee";
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const r = mode === "login" ? await login(f.email, f.password, role) : await register(f.name, f.email, f.password, role);
      saveAuth(r); onAuth(r.user);
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <div className="landing auth">
      <button className="btn ghost back" onClick={back}>← Back to portal selection</button>
      <form className="auth-card" onSubmit={submit}>
        <span className="pill dark">{label.toUpperCase()} PORTAL</span>
        <h2>{mode === "login" ? `${label} Login` : `Register as ${label}`}</h2>
        {err && <div className="alert">{err}</div>}
        {mode === "register" && <label>Full name<input required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>}
        <label>Email<input type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
        <label>Password<input type="password" required minLength={mode === "register" ? 6 : 1} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></label>
        <button className="btn full" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
        <p className="switch">{mode === "login" ? "New here?" : "Already registered?"} <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>{mode === "login" ? "Register" : "Login"}</button></p>
        <small className="hint">Demo: {role === "manager" ? "manager@demo.com" : "arjun@demo.com"} / password123</small>
      </form>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(() => (getToken() ? getUser() : null));
  const [portal, setPortal] = useState(null);
  const logout = () => { clearAuth(); setUser(null); setPortal(null); };
  if (!user) return portal ? <AuthPage role={portal} back={() => setPortal(null)} onAuth={setUser} /> : <Landing choose={setPortal} />;
  return user.role === "manager"
    ? <ManagerPortal user={user} setUser={setUser} onLogout={logout} />
    : <EmployeePortal user={user} setUser={setUser} onLogout={logout} />;
}
