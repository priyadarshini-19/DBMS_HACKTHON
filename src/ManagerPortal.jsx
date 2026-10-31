import { useEffect, useState } from "react";
import { api } from "./api";
import { Badge, BarChart, Card, Donut, Empty, Modal, Progress, Stat, fmtDate, fmtTime, useLoad } from "./ui";
import { Notifications, Profile, Shell } from "./Shared";

const MENU = [
  ["dashboard", "Dashboard", "▦"],
  ["projects", "Project Management", "📁"],
  ["tasks", "Task Management", "☑"],
  ["matching", "Skill-Based Matching", "✨"],
  ["team", "Team Overview", "👥"],
  ["notifications", "Notifications", "🔔"],
  ["profile", "Profile", "⚙"],
];

export default function ManagerPortal({ user, setUser, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [unread, setUnread] = useState(0);
  const refreshUnread = () => api("/notifications").then((n) => setUnread(n.filter((x) => !x.is_read).length)).catch(() => {});
  useEffect(() => { refreshUnread(); const t = setInterval(refreshUnread, 15000); return () => clearInterval(t); }, []);
  useEffect(() => { refreshUnread(); }, [page]);
  return (
    <Shell brand="Manager" tag="MANAGER PORTAL" menu={MENU} page={page} setPage={setPage} user={user} unread={unread} onLogout={onLogout}>
      {page === "dashboard" && <Dashboard />}
      {page === "projects" && <Projects />}
      {page === "tasks" && <Tasks />}
      {page === "matching" && <Matching />}
      {page === "team" && <Team />}
      {page === "notifications" && <Notifications onChange={refreshUnread} />}
      {page === "profile" && <Profile user={user} onUpdated={setUser} />}
    </Shell>
  );
}

function Dashboard() {
  const { data: d, error } = useLoad(() => api("/manager/dashboard"));
  if (error) return <div className="alert">{error}</div>;
  if (!d) return <Empty text="Loading…" />;
  return (
    <>
      <div className="grid4">
        <Stat label="Projects" value={d.projects} icon="📁" />
        <Stat label="Total tasks" value={d.tasks} icon="☑" tone="blue" />
        <Stat label="Completed" value={d.completed} icon="✓" tone="green" />
        <Stat label="Overdue" value={d.overdue} icon="⚠" tone="orange" />
      </div>
      <div className="grid2">
        <Card title="Task status" sub={`${d.unassigned} unassigned · ${d.employees} employees`}>
          <BarChart data={[{ label: "Pending", value: d.pending, color: "#f5a524" }, { label: "In Progress", value: d.in_progress, color: "#4f8cff" }, { label: "Completed", value: d.completed, color: "#22b573" }]} />
        </Card>
        <Card title="Overall completion"><div className="center"><Donut done={d.completed} total={d.tasks} /></div></Card>
      </div>
      <Card title="Project progress">
        {d.project_progress.length === 0 ? <Empty text="No projects yet. Create one in Project Management." /> : d.project_progress.map((p) => (
          <div key={p.id} className="prog-row"><div><strong>{p.name}</strong><small>{p.completed_tasks}/{p.task_count} tasks · due {fmtDate(p.deadline)}</small></div><Progress value={p.progress} /><b>{p.progress}%</b></div>
        ))}
      </Card>
    </>
  );
}

function Projects() {
  const { data, error, reload } = useLoad(() => api("/manager/projects"));
  const [edit, setEdit] = useState(null);
  const [err, setErr] = useState("");
  const save = async (e) => {
    e.preventDefault(); setErr("");
    const f = new FormData(e.target);
    const body = { name: f.get("name"), description: f.get("description"), status: f.get("status"), deadline: f.get("deadline") || null };
    try {
      if (edit.id) await api(`/manager/projects/${edit.id}`, "PUT", body); else await api("/manager/projects", "POST", body);
      setEdit(null); reload();
    } catch (x) { setErr(x.message); }
  };
  const del = async (p) => { if (confirm(`Delete project "${p.name}" and all its tasks?`)) { try { await api(`/manager/projects/${p.id}`, "DELETE"); reload(); } catch (x) { alert(x.message); } } };
  return (
    <Card title="Projects" sub="Create, edit, delete and monitor projects" actions={<button className="btn" onClick={() => { setErr(""); setEdit({}); }}>＋ New project</button>}>
      {error && <div className="alert">{error}</div>}
      {!data ? <Empty text="Loading…" /> : data.length === 0 ? <Empty text="No projects yet." /> : (
        <div className="grid2">
          {data.map((p) => (
            <div key={p.id} className="project">
              <div className="row between"><h4>{p.name}</h4><Badge value={p.status} /></div>
              <p>{p.description || "No description."}</p>
              <Progress value={p.progress} /><small>{p.progress}% · {p.completed_tasks}/{p.task_count} tasks · due {fmtDate(p.deadline)}</small>
              <div className="chips">{p.members.length ? p.members.map((m) => <span key={m.id} className="chip">{m.name}</span>) : <small>No team members yet</small>}</div>
              <div className="row"><button className="btn ghost sm" onClick={() => { setErr(""); setEdit(p); }}>Edit</button><button className="btn danger sm" onClick={() => del(p)}>Delete</button></div>
            </div>
          ))}
        </div>
      )}
      {edit && (
        <Modal title={edit.id ? "Edit project" : "New project"} onClose={() => setEdit(null)}>
          {err && <div className="alert">{err}</div>}
          <form className="form" onSubmit={save}>
            <label>Name<input name="name" required defaultValue={edit.name} /></label>
            <label>Description<textarea name="description" defaultValue={edit.description || ""} /></label>
            <div className="grid2"><label>Status<select name="status" defaultValue={edit.status || "Planning"}><option>Planning</option><option>Active</option><option>Completed</option></select></label>
              <label>Deadline<input type="date" name="deadline" defaultValue={edit.deadline || ""} /></label></div>
            <button className="btn">Save project</button>
          </form>
        </Modal>
      )}
    </Card>
  );
}

function Tasks() {
  const [filter, setFilter] = useState("");
  const { data, error, reload } = useLoad(() => api("/manager/tasks" + (filter ? `?project_id=${filter}` : "")), [filter]);
  const { data: projects } = useLoad(() => api("/manager/projects"));
  const { data: team } = useLoad(() => api("/manager/team"));
  const { data: skills, reload: reloadSkills } = useLoad(() => api("/skills"));
  const [edit, setEdit] = useState(null);
  const [hist, setHist] = useState(null);
  const [err, setErr] = useState("");
  const [picked, setPicked] = useState([]);
  const [newSkill, setNewSkill] = useState("");

  const open = (t) => { setErr(""); setEdit(t); setPicked(t.skills?.map((s) => s.id) || []); };
  const save = async (e) => {
    e.preventDefault(); setErr("");
    const f = new FormData(e.target);
    const body = {
      title: f.get("title"), description: f.get("description"), priority: f.get("priority"),
      deadline: f.get("deadline") || null, estimated_hours: Number(f.get("hours") || 0),
      assigned_to: f.get("assigned_to") ? Number(f.get("assigned_to")) : null, skill_ids: picked,
    };
    try {
      if (edit.id) await api(`/manager/tasks/${edit.id}`, "PUT", { ...body, status: f.get("status"), progress: Number(f.get("progress")) });
      else await api("/manager/tasks", "POST", { ...body, project_id: Number(f.get("project_id")) });
      setEdit(null); reload();
    } catch (x) { setErr(x.message); }
  };
  const del = async (t) => { if (confirm(`Delete task "${t.title}"?`)) { await api(`/manager/tasks/${t.id}`, "DELETE"); reload(); } };
  const showHist = async (t) => setHist({ task: t, rows: await api(`/manager/tasks/${t.id}/history`) });
  const addSkill = async () => { if (!newSkill.trim()) return; try { const s = await api("/manager/skills", "POST", { name: newSkill }); setNewSkill(""); await reloadSkills(); setPicked((p) => [...new Set([...p, s.id])]); } catch (x) { setErr(x.message); } };

  return (
    <Card title="Tasks" sub="Create, assign and monitor tasks"
      actions={<><select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="">All projects</option>{projects?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
        <button className="btn" disabled={!projects?.length} onClick={() => open({})}>＋ New task</button></>}>
      {error && <div className="alert">{error}</div>}
      {projects && !projects.length && <div className="alert">Create a project first.</div>}
      {!data ? <Empty text="Loading…" /> : data.length === 0 ? <Empty text="No tasks." /> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Task</th><th>Project</th><th>Assignee</th><th>Priority</th><th>Status</th><th>Progress</th><th>Deadline</th><th>Est.</th><th /></tr></thead>
          <tbody>{data.map((t) => (
            <tr key={t.id}>
              <td><strong>{t.title}</strong><div className="chips">{t.skills.map((s) => <span key={s.id} className="chip sm">{s.name}</span>)}</div></td>
              <td>{t.project_name}</td><td>{t.assignee_name || <em className="muted">Unassigned</em>}</td>
              <td><Badge value={t.priority} /></td><td><Badge value={t.status} /></td>
              <td style={{ minWidth: 110 }}><Progress value={t.progress} /><small>{t.progress}%</small></td>
              <td>{fmtDate(t.deadline)}</td><td>{t.estimated_hours}h</td>
              <td className="nowrap"><button className="btn ghost sm" onClick={() => open(t)}>Edit</button> <button className="btn ghost sm" onClick={() => showHist(t)}>History</button> <button className="btn danger sm" onClick={() => del(t)}>✕</button></td>
            </tr>))}</tbody>
        </table></div>
      )}
      {edit && (
        <Modal title={edit.id ? "Edit task" : "New task"} onClose={() => setEdit(null)}>
          {err && <div className="alert">{err}</div>}
          <form className="form" onSubmit={save}>
            {!edit.id && <label>Project<select name="project_id" required defaultValue="">{<option value="" disabled>Select…</option>}{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>}
            <label>Title<input name="title" required defaultValue={edit.title} /></label>
            <label>Description<textarea name="description" defaultValue={edit.description || ""} /></label>
            <div className="grid3">
              <label>Priority<select name="priority" defaultValue={edit.priority || "Medium"}><option>Low</option><option>Medium</option><option>High</option></select></label>
              <label>Deadline<input type="date" name="deadline" defaultValue={edit.deadline || ""} /></label>
              <label>Estimated hours<input type="number" step="0.5" min="0" name="hours" defaultValue={edit.estimated_hours ?? 0} /></label>
            </div>
            <label>Assign to<select name="assigned_to" defaultValue={edit.assigned_to || ""}><option value="">Unassigned</option>{team?.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.open_tasks} open · {m.open_hours}h)</option>)}</select></label>
            {edit.id && <div className="grid2"><label>Status<select name="status" defaultValue={edit.status}><option>Pending</option><option>In Progress</option><option>Completed</option></select></label>
              <label>Progress %<input type="number" min="0" max="100" name="progress" defaultValue={edit.progress} /></label></div>}
            <div><small className="lbl">Required skills</small>
              <div className="chips">{skills?.map((s) => <button type="button" key={s.id} className={`chip pick ${picked.includes(s.id) ? "on" : ""}`} onClick={() => setPicked((p) => p.includes(s.id) ? p.filter((x) => x !== s.id) : [...p, s.id])}>{s.name}</button>)}</div>
              <div className="row mt"><input placeholder="Add new skill…" value={newSkill} onChange={(e) => setNewSkill(e.target.value)} /><button type="button" className="btn ghost sm" onClick={addSkill}>Add</button></div></div>
            <button className="btn">Save task</button>
          </form>
        </Modal>
      )}
      {hist && (
        <Modal title={`History — ${hist.task.title}`} onClose={() => setHist(null)}>
          {hist.rows.length === 0 ? <Empty text="No history yet." /> : hist.rows.map((h) => <div key={h.id} className="hist"><b>{h.action}</b><span>{h.detail}</span><small>{h.actor} · {fmtTime(h.created_at)}</small></div>)}
        </Modal>
      )}
    </Card>
  );
}

function Matching() {
  const { data, error, reload } = useLoad(() => api("/manager/matching"));
  const [busy, setBusy] = useState(null);
  const confirmAssign = async (t, c) => {
    if (!confirm(`Assign "${t.title}" to ${c.name}?`)) return;
    setBusy(t.id + "-" + c.id);
    try { await api(`/manager/matching/${t.id}/confirm/${c.id}`, "POST"); reload(); } catch (x) { alert(x.message); } finally { setBusy(null); }
  };
  return (
    <Card title="Skill-based task matching" sub="Score = 50% skills · 20% experience · 30% availability (workload). Review, then confirm.">
      {error && <div className="alert">{error}</div>}
      {!data ? <Empty text="Loading…" /> : data.length === 0 ? <Empty text="No open tasks to match." /> : data.map(({ task, recommended }) => (
        <div key={task.id} className="match">
          <div className="row between"><div><h4>{task.title}</h4><small>{task.project_name} · {task.estimated_hours}h · due {fmtDate(task.deadline)}</small></div>
            <div className="row"><Badge value={task.priority} />{task.assignee_name ? <span className="chip">Currently: {task.assignee_name}</span> : <span className="chip warn">Unassigned</span>}</div></div>
          <div className="chips">{task.skills.length ? task.skills.map((s) => <span className="chip sm" key={s.id}>{s.name}</span>) : <small>No skills required</small>}</div>
          <div className="cands">
            {recommended.map((c, i) => (
              <div key={c.id} className={`cand ${i === 0 ? "best" : ""}`}>
                {i === 0 && <span className="tag">Best match</span>}
                <strong>{c.name}</strong><div className="score">{c.match_score}%</div>
                <small>Skills {c.skill_score}% · Exp {c.experience_score}% · Free {c.availability_score}%</small>
                <small>{c.open_tasks} open tasks · {c.open_hours}h</small>
                <button className="btn sm" disabled={task.assigned_to === c.id || busy === task.id + "-" + c.id} onClick={() => confirmAssign(task, c)}>{task.assigned_to === c.id ? "Assigned" : "Confirm assignment"}</button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </Card>
  );
}

function Team() {
  const { data, error } = useLoad(() => api("/manager/team"));
  const [open, setOpen] = useState(null);
  return (
    <Card title="Team overview" sub="Employee details, workloads and task completion">
      {error && <div className="alert">{error}</div>}
      {!data ? <Empty text="Loading…" /> : data.length === 0 ? <Empty text="No employees registered." /> : (
        <div className="grid2">{data.map((m) => (
          <div key={m.id} className="project">
            <div className="row"><span className="avatar">{m.name[0]}</span><div><h4>{m.name}</h4><small>{m.email}</small></div></div>
            <div className="grid4 mini"><div><b>{m.pending}</b><small>Pending</small></div><div><b>{m.in_progress}</b><small>In progress</small></div><div><b>{m.completed}</b><small>Done</small></div><div><b>{m.open_hours}h</b><small>Workload</small></div></div>
            <small>Completion rate {m.completion_rate}%</small><Progress value={m.completion_rate} color="#22b573" />
            <div className="chips">{m.skills.map((s) => <span key={s.name} className="chip sm">{s.name} · L{s.level}</span>)}</div>
            <div>{m.projects.map((p) => <div key={p.id} className="prog-row sm"><span>{p.name}</span><Progress value={p.progress} /><b>{p.progress}%</b></div>)}</div>
            <button className="btn ghost sm" onClick={() => setOpen(open === m.id ? null : m.id)}>{open === m.id ? "Hide tasks" : `View ${m.tasks.length} tasks`}</button>
            {open === m.id && m.tasks.map((t) => <div key={t.id} className="hist"><b>{t.title}</b><span><Badge value={t.status} /> {t.progress}%</span><small>{t.project_name} · due {fmtDate(t.deadline)}</small></div>)}
          </div>))}</div>
      )}
    </Card>
  );
}
