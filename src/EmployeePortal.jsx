import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Badge, BarChart, Card, Donut, Empty, Progress, Stat, fmtDate, fmtTime, today, useLoad } from "./ui";
import { Notifications, Profile, Shell } from "./Shared";

const MENU = [
  ["dashboard", "Dashboard", "▦"],
  ["tasks", "My Tasks", "☑"],
  ["planner", "Daily Planner", "🗓"],
  ["blockers", "Bottleneck Detective", "🕵"],
  ["skills", "Skill Growth Tracker", "📈"],
  ["notifications", "Notifications", "🔔"],
  ["profile", "Profile", "⚙"],
];

export default function EmployeePortal({ user, setUser, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [unread, setUnread] = useState(0);
  const refreshUnread = () => api("/notifications").then((n) => setUnread(n.filter((x) => !x.is_read).length)).catch(() => {});
  useEffect(() => { refreshUnread(); const t = setInterval(refreshUnread, 15000); return () => clearInterval(t); }, []);
  useEffect(() => { refreshUnread(); }, [page]);
  return (
    <Shell brand="Employee" tag="EMPLOYEE PORTAL" menu={MENU} page={page} setPage={setPage} user={user} unread={unread} onLogout={onLogout}>
      {page === "dashboard" && <Dashboard go={setPage} />}
      {page === "tasks" && <MyTasks />}
      {page === "planner" && <Planner />}
      {page === "blockers" && <Blockers user={user} />}
      {page === "skills" && <Skills />}
      {page === "notifications" && <Notifications onChange={refreshUnread} />}
      {page === "profile" && <Profile user={user} onUpdated={setUser} />}
    </Shell>
  );
}

function Dashboard({ go }) {
  const { data: d, error } = useLoad(() => api("/employee/dashboard"));
  if (error) return <div className="alert">{error}</div>;
  if (!d) return <Empty text="Loading…" />;
  return (
    <>
      <div className="grid4">
        <Stat label="My tasks" value={d.tasks} icon="☑" />
        <Stat label="In progress" value={d.in_progress} icon="⏳" tone="blue" />
        <Stat label="Completed" value={d.completed} icon="✓" tone="green" />
        <Stat label="Open blockers" value={d.open_blockers} icon="🚧" tone="orange" />
      </div>
      <div className="grid2">
        <Card title="My progress"><div className="center"><Donut done={d.completed} total={d.tasks} /></div></Card>
        <Card title="Task status"><BarChart data={[{ label: "Pending", value: d.pending, color: "#f5a524" }, { label: "In Progress", value: d.in_progress, color: "#4f8cff" }, { label: "Completed", value: d.completed, color: "#22b573" }]} /></Card>
      </div>
      <div className="grid2">
        <Card title="Today's plan" actions={<button className="btn ghost sm" onClick={() => go("planner")}>Open planner</button>}>
          <strong>{d.today_done}/{d.today_plans} done today</strong><Progress value={d.today_plans ? (d.today_done / d.today_plans) * 100 : 0} color="#22b573" />
          {d.overdue > 0 && <div className="alert mt">{d.overdue} overdue task(s)</div>}
        </Card>
        <Card title="Upcoming deadlines">
          {d.upcoming.length === 0 ? <Empty text="No pending tasks 🎉" /> : d.upcoming.map((t) => <div key={t.id} className="prog-row sm"><span>{t.title}</span><small>{fmtDate(t.deadline)}</small><Badge value={t.priority} /></div>)}
        </Card>
      </div>
    </>
  );
}

function MyTasks() {
  const { data, error, reload } = useLoad(() => api("/employee/tasks"));
  const [draft, setDraft] = useState({});
  const [err, setErr] = useState("");
  const send = async (t, body) => { setErr(""); try { await api(`/employee/tasks/${t.id}`, "PATCH", body); reload(); } catch (x) { setErr(x.message); } };
  return (
    <Card title="My tasks" sub="Update your status and completion percentage">
      {(error || err) && <div className="alert">{error || err}</div>}
      {!data ? <Empty text="Loading…" /> : data.length === 0 ? <Empty text="No tasks assigned yet." /> : data.map((t) => {
        const pct = draft[t.id] ?? t.progress;
        return (
          <div key={t.id} className="task">
            <div className="row between"><div><h4>{t.title}</h4><small>{t.project_name} · due {fmtDate(t.deadline)} · {t.estimated_hours}h est.</small></div><div className="row"><Badge value={t.priority} /><Badge value={t.status} /></div></div>
            <p>{t.description || "No description."}</p>
            <div className="chips">{t.skills.map((s) => <span key={s.id} className="chip sm">{s.name}</span>)}</div>
            <div className="row task-ctl">
              <select value={t.status} onChange={(e) => send(t, { status: e.target.value })}><option>Pending</option><option>In Progress</option><option>Completed</option></select>
              <input type="range" min="0" max="100" step="5" value={pct} onChange={(e) => setDraft({ ...draft, [t.id]: Number(e.target.value) })}
                onMouseUp={() => send(t, { progress: pct })} onTouchEnd={() => send(t, { progress: pct })} onKeyUp={() => send(t, { progress: pct })} />
              <b>{pct}%</b>
            </div>
            <Progress value={pct} color="#22b573" />
          </div>
        );
      })}
    </Card>
  );
}

function Planner() {
  const [date, setDate] = useState("");
  const { data, error, reload } = useLoad(() => api("/employee/planner" + (date ? `?plan_date=${date}` : "")), [date]);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("Medium");
  const [err, setErr] = useState("");
  const add = async (e) => { e.preventDefault(); setErr(""); try { await api("/employee/planner", "POST", { title, priority, plan_date: date || today() }); setTitle(""); reload(); } catch (x) { setErr(x.message); } };
  const toggle = async (p) => { await api(`/employee/planner/${p.id}`, "PATCH", { done: !p.done }); reload(); };
  const del = async (p) => { await api(`/employee/planner/${p.id}`, "DELETE"); reload(); };
  const done = data?.filter((p) => p.done).length || 0;
  return (
    <Card title="Daily planner" sub="Your personal to-do list" actions={<><button className={`btn sm ${date ? "ghost" : ""}`} onClick={() => setDate("")}>All dates</button><button className={`btn sm ${date === today() ? "" : "ghost"}`} onClick={() => setDate(today())}>Today</button><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></>}>
      {(error || err) && <div className="alert">{error || err}</div>}
      <form className="row" onSubmit={add}>
        <input className="grow" required placeholder="Add a to-do…" value={title} onChange={(e) => setTitle(e.target.value)} />
        <select value={priority} onChange={(e) => setPriority(e.target.value)}><option>Low</option><option>Medium</option><option>High</option></select>
        <button className="btn">Add</button>
      </form>
      {data && <div className="mt"><small>{done}/{data.length} completed</small><Progress value={data.length ? (done / data.length) * 100 : 0} color="#22b573" /></div>}
      {!data ? <Empty text="Loading…" /> : data.length === 0 ? <Empty text={date ? "Nothing planned for this day. Click All dates to see everything." : "Nothing planned yet. Add your first to-do above."} /> : data.map((p) => (
        <div key={p.id} className="todo"><input type="checkbox" checked={p.done} onChange={() => toggle(p)} /><span className={p.done ? "done" : ""}>{p.title}</span><small>{fmtDate(p.plan_date)}</small><Badge value={p.priority} /><button className="icon-btn" onClick={() => del(p)}>🗑</button></div>
      ))}
    </Card>
  );
}

function Blockers({ user }) {
  const { data, error, reload } = useLoad(() => api("/employee/blockers"));
  const { data: tasks } = useLoad(() => api("/employee/tasks"));
  const { data: skills } = useLoad(() => api("/skills"));
  const [sel, setSel] = useState(null);
  const [form, setForm] = useState({ title: "", description: "", skill_id: "", task_id: "" });
  const [reply, setReply] = useState("");
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const end = useRef(null);
  const current = data?.find((b) => b.id === sel) || null;
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [current?.messages.length, sel]);

  const report = async (e) => {
    e.preventDefault(); setErr(""); setInfo("");
    try {
      const b = await api("/employee/blockers", "POST", { title: form.title, description: form.description, skill_id: form.skill_id ? Number(form.skill_id) : null, task_id: form.task_id ? Number(form.task_id) : null });
      setForm({ title: "", description: "", skill_id: "", task_id: "" });
      setInfo(b.notified.length ? `Notified: ${b.notified.join(", ")}` : "Reported (no teammates found to notify).");
      await reload(); setSel(b.id);
    } catch (x) { setErr(x.message); }
  };
  const send = async (e) => { e.preventDefault(); if (!reply.trim()) return; try { await api(`/employee/blockers/${sel}/messages`, "POST", { message: reply }); setReply(""); reload(); } catch (x) { setErr(x.message); } };
  const setStatus = async (s) => { try { await api(`/employee/blockers/${sel}/status`, "PATCH", { status: s }); reload(); } catch (x) { setErr(x.message); } };

  return (
    <div className="grid-chat">
      <Card title="Report a blocker" sub="We'll notify teammates with matching skills">
        {(error || err) && <div className="alert">{error || err}</div>}{info && <div className="alert ok">{info}</div>}
        <form className="form" onSubmit={report}>
          <label>What's blocking you?<input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
          <label>Details<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
          <label>Related task<select value={form.task_id} onChange={(e) => setForm({ ...form, task_id: e.target.value })}><option value="">None</option>{tasks?.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}</select></label>
          <label>Skill needed<select value={form.skill_id} onChange={(e) => setForm({ ...form, skill_id: e.target.value })}><option value="">Any</option>{skills?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
          <button className="btn">Report blocker</button>
        </form>
        <h4 className="mt">Conversations</h4>
        {!data ? <Empty text="Loading…" /> : data.length === 0 ? <Empty text="No blockers." /> : data.map((b) => (
          <button key={b.id} className={`thread ${sel === b.id ? "on" : ""}`} onClick={() => setSel(b.id)}>
            <div className="row between"><strong>{b.title}</strong><Badge value={b.status} /></div>
            <small>{b.mine ? "You" : b.user_name} · {b.skill_name || "any skill"} · {b.messages.length} msgs</small>
          </button>
        ))}
      </Card>
      <Card title={current ? current.title : "Chat"} sub={current ? `${current.mine ? "Reported by you" : "Help requested by " + current.user_name}${current.project_name ? " · " + current.project_name : ""}` : "Select a conversation"}
        actions={current?.mine && <button className="btn ghost sm" onClick={() => setStatus(current.status === "Open" ? "Resolved" : "Open")}>{current.status === "Open" ? "Mark resolved" : "Reopen"}</button>}>
        {!current ? <Empty text="Pick a blocker to view its conversation." /> : (
          <div className="chat">
            <div className="msgs">{current.messages.map((m) => (
              <div key={m.id} className={`msg ${m.mine ? "me" : ""}`}><small>{m.mine ? "You" : m.user_name} · {fmtTime(m.created_at)}</small><div>{m.message}</div></div>
            ))}<div ref={end} /></div>
            {current.status === "Open" ? (
              <form className="row" onSubmit={send}><input className="grow" placeholder={current.mine ? "Add an update…" : "Offer help…"} value={reply} onChange={(e) => setReply(e.target.value)} /><button className="btn">Send</button></form>
            ) : <div className="alert ok">This blocker is resolved.</div>}
          </div>
        )}
      </Card>
    </div>
  );
}

function Skills() {
  const { data, error, reload } = useLoad(() => api("/employee/skills"));
  const [sk, setSk] = useState({ skill_id: "", level: 3, target: 5 });
  const [err, setErr] = useState("");
  const save = async (e) => { e.preventDefault(); setErr(""); try { await api("/employee/skills", "POST", { skill_id: Number(sk.skill_id), level: Number(sk.level), target: Number(sk.target) }); reload(); } catch (x) { setErr(x.message); } };
  if (error) return <div className="alert">{error}</div>;
  if (!data) return <Empty text="Loading…" />;
  return (
    <div className="grid2">
      <Card title="My skills" sub="Levels grow as you complete tasks that need them">
        {data.skills.length === 0 ? <Empty text="No skills yet — add one." /> : data.skills.map((s) => (
          <div key={s.skill_id} className="skill"><div className="row between"><strong>{s.name}</strong><small>Level {s.level}/{s.target} · {s.tasks_completed} tasks done</small></div><Progress value={(s.level / s.target) * 100} /></div>
        ))}
        {err && <div className="alert">{err}</div>}
        <form className="row mt" onSubmit={save}>
          <select required value={sk.skill_id} onChange={(e) => setSk({ ...sk, skill_id: e.target.value })}><option value="">Skill…</option>{data.all_skills.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
          <select value={sk.level} onChange={(e) => setSk({ ...sk, level: e.target.value })}>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>Level {n}</option>)}</select>
          <select value={sk.target} onChange={(e) => setSk({ ...sk, target: e.target.value })}>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>Target {n}</option>)}</select>
          <button className="btn sm">Save</button>
        </form>
      </Card>
      <div>
        <Card title="Recommended to improve" sub="Based on open tasks in your projects">
          {data.recommendations.length === 0 ? <Empty text="You're well covered for current project needs." /> : data.recommendations.map((r) => (
            <div key={r.skill_id} className="rec"><strong>{r.name}</strong><small>{r.reason}</small><Progress value={(r.current_level / 5) * 100} color="#f5a524" /></div>
          ))}
        </Card>
        <Card title="Growth history">
          {data.history.length === 0 ? <Empty text="No history yet." /> : data.history.map((h, i) => <div key={i} className="hist"><b>{h.skill}</b><span>Reached level {h.level}</span><small>{fmtTime(h.logged_at)}</small></div>)}
        </Card>
      </div>
    </div>
  );
}
