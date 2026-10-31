import { useState } from "react";
import { api, saveAuth, getToken } from "./api";
import { Card, Empty, useLoad, fmtTime } from "./ui";

export function Notifications({ onChange }) {
  const { data, error, reload } = useLoad(() => api("/notifications"));
  const readAll = async () => { await api("/notifications/read-all", "POST"); reload(); onChange?.(); };
  const readOne = async (id) => { await api(`/notifications/${id}/read`, "PATCH"); reload(); onChange?.(); };
  return (
    <Card title="Notifications" sub="Task assignments, deadlines, help requests and blocker updates"
      actions={<button className="btn ghost" onClick={readAll}>Mark all read</button>}>
      {error && <div className="alert">{error}</div>}
      {!data ? <Empty text="Loading…" /> : data.length === 0 ? <Empty text="No notifications." /> : data.map((n) => (
        <div key={n.id} className={`notif ${n.is_read ? "" : "unread"}`}>
          <span className="dot" /><div><strong>{n.message}</strong><small>{fmtTime(n.created_at)}</small></div>
          {!n.is_read && <button className="btn ghost sm" onClick={() => readOne(n.id)}>Mark read</button>}
        </div>
      ))}
    </Card>
  );
}

export function Profile({ user, onUpdated }) {
  const [name, setName] = useState(user.name);
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const save = async (e) => {
    e.preventDefault(); setErr(""); setMsg("");
    try {
      const u = await api("/auth/me", "PUT", { name, ...(password ? { password } : {}) });
      saveAuth({ access_token: getToken(), user: u });
      onUpdated(u); setPassword(""); setMsg("Profile updated.");
    } catch (x) { setErr(x.message); }
  };
  return (
    <Card title="My profile" sub={`${user.role === "manager" ? "Manager" : "Employee"} account`}>
      {msg && <div className="alert ok">{msg}</div>}{err && <div className="alert">{err}</div>}
      <form className="form" onSubmit={save}>
        <label>Email<input value={user.email} disabled /></label>
        <label>Full name<input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label>New password (optional)<input type="password" minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Leave blank to keep current" /></label>
        <button className="btn">Save changes</button>
      </form>
    </Card>
  );
}

export function Shell({ brand, menu, page, setPage, user, unread, onLogout, children, tag }) {
  return (
    <div className="layout">
      <aside className={`sidebar ${user.role}`}>
        <div className="brand"><span className="logo">T</span>TaskFlow</div>
        <div className="side-tag">{tag}</div>
        <nav>
          {menu.map(([key, label, icon]) => (
            <button key={key} className={page === key ? "active" : ""} onClick={() => setPage(key)}>
              <span>{icon}</span>{label}{key === "notifications" && unread > 0 && <em>{unread}</em>}
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <div className="who"><span className="avatar">{user.name[0].toUpperCase()}</span><div><strong>{user.name}</strong><small>{brand}</small></div></div>
          <button className="btn ghost full" onClick={onLogout}>Sign out</button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <h2>{menu.find((m) => m[0] === page)?.[1]}</h2>
          <button className="bell" onClick={() => setPage("notifications")} title="Notifications">🔔{unread > 0 && <em>{unread}</em>}</button>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
