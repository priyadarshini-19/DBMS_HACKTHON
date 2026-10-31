from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from common import (status_db, check_priority, notify, log_history, user_dict, task_dict,
                    own_project, STATUS_TO_API)
from database import get_db
from auth import require_role
from models import (User, Skill, UserSkill, Project, Task, TaskSkill, TaskHistory, Notification)
from schemas import ProjectInput, ProjectUpdate, TaskInput, TaskEdit, SkillCreate

router = APIRouter(prefix="/api/manager", tags=["Manager"], dependencies=[Depends(require_role("manager"))])
M = Depends(require_role("manager"))


def project_dict(p, db):
    tasks = db.query(Task).filter(Task.project_id == p.id).all()
    done = sum(t.status == "Done" for t in tasks)
    avg = round(sum((t.progress or 0) for t in tasks) / len(tasks)) if tasks else 0
    member_ids = {t.assigned_to for t in tasks if t.assigned_to}
    members = db.query(User).filter(User.id.in_(member_ids)).all() if member_ids else []
    return {"id": p.id, "name": p.name, "description": p.description, "status": p.status,
            "deadline": p.deadline.isoformat() if p.deadline else None,
            "task_count": len(tasks), "completed_tasks": done, "progress": avg,
            "members": [user_dict(m) for m in members]}


# ---------------- Dashboard ----------------
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user=M):
    projects = db.query(Project).all()
    ids = [p.id for p in projects]
    tasks = db.query(Task).filter(Task.project_id.in_(ids)).all() if ids else []
    today = date.today()
    overdue = [t for t in tasks if t.deadline and t.deadline < today and t.status != "Done"]
    return {
        "projects": len(projects), "tasks": len(tasks),
        "pending": sum(t.status == "To Do" for t in tasks),
        "in_progress": sum(t.status == "In Progress" for t in tasks),
        "completed": sum(t.status == "Done" for t in tasks),
        "unassigned": sum(t.assigned_to is None for t in tasks),
        "overdue": len(overdue),
        "employees": db.query(User).filter(User.role == "employee").count(),
        "project_progress": [project_dict(p, db) for p in projects],
    }


# ---------------- Projects ----------------
@router.get("/projects")
def list_projects(db: Session = Depends(get_db), user=M):
    return [project_dict(p, db) for p in db.query(Project).order_by(Project.id.desc())]


@router.post("/projects", status_code=201)
def create_project(d: ProjectInput, db: Session = Depends(get_db), user=M):
    if d.status not in ("Planning", "Active", "Completed"):
        raise HTTPException(400, "Invalid project status.")
    p = Project(name=d.name.strip(), description=d.description, status=d.status, deadline=d.deadline, manager_id=user.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return project_dict(p, db)


@router.put("/projects/{pid}")
def edit_project(pid: int, d: ProjectUpdate, db: Session = Depends(get_db), user=M):
    p = own_project(db, pid, user.id)
    ch = d.model_dump(exclude_unset=True)
    if "status" in ch and ch["status"] not in ("Planning", "Active", "Completed"):
        raise HTTPException(400, "Invalid project status.")
    if "name" in ch and not (ch["name"] or "").strip():
        raise HTTPException(400, "Project name is required.")
    for k, v in ch.items():
        setattr(p, k, v)
    db.commit()
    return project_dict(p, db)


@router.delete("/projects/{pid}")
def delete_project(pid: int, db: Session = Depends(get_db), user=M):
    p = own_project(db, pid, user.id)
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---------------- Tasks ----------------
def _set_skills(db, task_id, skill_ids):
    db.query(TaskSkill).filter(TaskSkill.task_id == task_id).delete()
    for sid in set(skill_ids):
        if not db.query(Skill).get(sid):
            raise HTTPException(400, f"Skill {sid} does not exist.")
        db.add(TaskSkill(task_id=task_id, skill_id=sid))


def _check_employee(db, eid):
    if eid and not db.query(User).filter(User.id == eid, User.role == "employee").first():
        raise HTTPException(400, "Assigned user must be an employee.")


@router.get("/tasks")
def list_tasks(project_id: int | None = None, db: Session = Depends(get_db), user=M):
    q = db.query(Task)
    if project_id:
        q = q.filter(Task.project_id == project_id)
    return [task_dict(t, db) for t in q.order_by(Task.id.desc()).all()]


@router.post("/tasks", status_code=201)
def create_task(d: TaskInput, db: Session = Depends(get_db), user=M):
    own_project(db, d.project_id, user.id)
    check_priority(d.priority)
    _check_employee(db, d.assigned_to)
    t = Task(project_id=d.project_id, title=d.title.strip(), description=d.description, priority=d.priority,
             deadline=d.deadline, estimated_hours=d.estimated_hours, assigned_to=d.assigned_to,
             status="To Do", progress=0)
    db.add(t)
    db.flush()
    _set_skills(db, t.id, d.skill_ids)
    log_history(db, t.id, user.id, "created", f"Task created by {user.name}")
    if d.assigned_to:
        log_history(db, t.id, user.id, "assigned", f"Assigned to user #{d.assigned_to}")
        notify(db, d.assigned_to, f"New task assigned: {t.title}")
    db.commit()
    return task_dict(t, db)


def _get_task(db, tid, mid):
    t = db.query(Task).get(tid)
    if not t:
        raise HTTPException(404, "Task not found.")
    own_project(db, t.project_id, mid)
    return t


@router.put("/tasks/{tid}")
def edit_task(tid: int, d: TaskEdit, db: Session = Depends(get_db), user=M):
    t = _get_task(db, tid, user.id)
    ch = d.model_dump(exclude_unset=True)
    skills = ch.pop("skill_ids", None)
    if "priority" in ch:
        check_priority(ch["priority"])
    if "status" in ch:
        ch["status"] = status_db(ch["status"])
    if "assigned_to" in ch:
        _check_employee(db, ch["assigned_to"])
        if ch["assigned_to"] != t.assigned_to:
            log_history(db, t.id, user.id, "assigned", f"Assigned to user #{ch['assigned_to']}")
            if ch["assigned_to"]:
                notify(db, ch["assigned_to"], f"Task assigned to you: {t.title}")
    for k, v in ch.items():
        setattr(t, k, v)
    if t.status == "Done":
        t.progress = 100
    if skills is not None:
        _set_skills(db, t.id, skills)
    log_history(db, t.id, user.id, "updated", "Task edited by manager")
    db.commit()
    return task_dict(t, db)


@router.delete("/tasks/{tid}")
def delete_task(tid: int, db: Session = Depends(get_db), user=M):
    t = _get_task(db, tid, user.id)
    db.delete(t)
    db.commit()
    return {"ok": True}


@router.get("/tasks/{tid}/history")
def task_history(tid: int, db: Session = Depends(get_db), user=M):
    _get_task(db, tid, user.id)
    rows = db.query(TaskHistory).filter(TaskHistory.task_id == tid).order_by(TaskHistory.id.desc()).all()
    out = []
    for h in rows:
        a = db.query(User).get(h.actor_id) if h.actor_id else None
        out.append({"id": h.id, "action": h.action, "detail": h.detail, "actor": a.name if a else "System",
                    "created_at": h.created_at.isoformat() if h.created_at else None})
    return out


# ---------------- Skills (manager can add new skills) ----------------
@router.post("/skills", status_code=201)
def add_skill(d: SkillCreate, db: Session = Depends(get_db), user=M):
    name = d.name.strip()
    s = db.query(Skill).filter(Skill.name == name).first()
    if not s:
        s = Skill(name=name)
        db.add(s)
        db.commit()
        db.refresh(s)
    return {"id": s.id, "name": s.name}


# ---------------- Skill-based matching ----------------
def workload(db, uid):
    open_tasks = db.query(Task).filter(Task.assigned_to == uid, Task.status != "Done").all()
    return len(open_tasks), round(sum(t.estimated_hours or 0 for t in open_tasks), 1)


@router.get("/matching")
def matching(db: Session = Depends(get_db), user=M):
    """Bulk-loads everything once (fast even with many tasks/employees)."""
    tasks = (db.query(Task).filter(Task.status != "Done")
             .order_by(Task.assigned_to.is_(None).desc(), Task.id.desc()).all())
    emps = db.query(User).filter(User.role == "employee").all()
    skill_names = {s.id: s.name for s in db.query(Skill)}
    levels = {}
    for us in db.query(UserSkill):
        levels.setdefault(us.user_id, {})[us.skill_id] = us.level or 0
    task_skill = {}
    for ts in db.query(TaskSkill):
        task_skill.setdefault(ts.task_id, []).append(ts.skill_id)
    all_tasks = db.query(Task.id, Task.assigned_to, Task.status, Task.estimated_hours).filter(Task.assigned_to.isnot(None)).all()
    open_n, open_h, done_skill = {}, {}, {}
    for tid, uid, st, hrs in all_tasks:
        if st == "Done":
            for sid in task_skill.get(tid, []):
                done_skill[(uid, sid)] = done_skill.get((uid, sid), 0) + 1
        else:
            open_n[uid] = open_n.get(uid, 0) + 1
            open_h[uid] = open_h.get(uid, 0) + (hrs or 0)
    out = []
    for t in tasks:
        req = task_skill.get(t.id, [])
        cands = []
        for e in emps:
            lv = levels.get(e.id, {})
            if req:
                skill_pct = sum(min(lv.get(x, 0), 5) / 5 for x in req) / len(req) * 100
                exp_pct = min(sum(done_skill.get((e.id, x), 0) for x in req), 5) / 5 * 100
            else:
                skill_pct, exp_pct = 50, 50
            n, h = open_n.get(e.id, 0), open_h.get(e.id, 0)
            avail = max(0, 100 - min(h / 40, 1) * 70 - min(n, 6) / 6 * 30)
            cands.append({**user_dict(e), "match_score": round(skill_pct * 0.5 + exp_pct * 0.2 + avail * 0.3),
                          "skill_score": round(skill_pct), "experience_score": round(exp_pct),
                          "availability_score": round(avail), "open_tasks": n, "open_hours": round(h, 1)})
        cands.sort(key=lambda c: -c["match_score"])
        out.append({"task": task_dict(t, db), "recommended": cands[:5]})
    return out


@router.post("/matching/{tid}/confirm/{eid}")
def confirm(tid: int, eid: int, db: Session = Depends(get_db), user=M):
    t = _get_task(db, tid, user.id)
    _check_employee(db, eid)
    t.assigned_to = eid
    log_history(db, t.id, user.id, "assigned", f"Assigned via skill matching to user #{eid}")
    notify(db, eid, f"New task assigned: {t.title}")
    db.commit()
    return task_dict(t, db)


# ---------------- Team overview ----------------
@router.get("/team")
def team(db: Session = Depends(get_db), user=M):
    pids = [p.id for p in db.query(Project)]
    out = []
    for e in db.query(User).filter(User.role == "employee").all():
        tasks = db.query(Task).filter(Task.assigned_to == e.id).all()
        mine = [t for t in tasks if t.project_id in pids]
        skills = (db.query(Skill, UserSkill).join(UserSkill, UserSkill.skill_id == Skill.id)
                  .filter(UserSkill.user_id == e.id).all())
        n_open, hours = workload(db, e.id)
        proj_ids = {t.project_id for t in mine}
        projects = db.query(Project).filter(Project.id.in_(proj_ids)).all() if proj_ids else []
        out.append({**user_dict(e), "total_tasks": len(mine),
                    "pending": sum(t.status == "To Do" for t in mine),
                    "in_progress": sum(t.status == "In Progress" for t in mine),
                    "completed": sum(t.status == "Done" for t in mine),
                    "open_tasks": n_open, "open_hours": hours,
                    "completion_rate": round(100 * sum(t.status == "Done" for t in mine) / len(mine)) if mine else 0,
                    "skills": [{"name": s.name, "level": us.level} for s, us in skills],
                    "projects": [{"id": p.id, "name": p.name, "progress": project_dict(p, db)["progress"]} for p in projects],
                    "tasks": [task_dict(t, db) for t in mine]})
    return out
