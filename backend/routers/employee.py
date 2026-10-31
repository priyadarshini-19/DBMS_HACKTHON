from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_role
from common import status_db, check_priority, notify, log_history, user_dict, task_dict
from database import get_db
from models import (User, Skill, UserSkill, SkillLog, Project, Task, TaskSkill, Planner,
                    Bottleneck, Reply)
from schemas import (TaskProgress, PlannerInput, PlannerUpdate, BlockerInput, MessageInput,
                     BlockerStatus, SkillUpdate)

router = APIRouter(prefix="/api/employee", tags=["Employee"], dependencies=[Depends(require_role("employee"))])
E = Depends(require_role("employee"))


# ---------------- Dashboard ----------------
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user=E):
    tasks = db.query(Task).filter(Task.assigned_to == user.id).all()
    today = date.today()
    plans = db.query(Planner).filter(Planner.user_id == user.id, Planner.plan_date == today).all()
    return {
        "tasks": len(tasks),
        "pending": sum(t.status == "To Do" for t in tasks),
        "in_progress": sum(t.status == "In Progress" for t in tasks),
        "completed": sum(t.status == "Done" for t in tasks),
        "overdue": sum(1 for t in tasks if t.deadline and t.deadline < today and t.status != "Done"),
        "today_plans": len(plans), "today_done": sum(bool(p.done) for p in plans),
        "open_blockers": db.query(Bottleneck).filter(Bottleneck.user_id == user.id, Bottleneck.status == "Open").count(),
        "upcoming": [task_dict(t, db) for t in sorted((x for x in tasks if x.status != "Done"),
                     key=lambda x: (x.deadline or date.max))[:5]],
    }


# ---------------- My tasks ----------------
@router.get("/tasks")
def my_tasks(db: Session = Depends(get_db), user=E):
    return [task_dict(t, db) for t in db.query(Task).filter(Task.assigned_to == user.id).order_by(Task.deadline, Task.id)]


def _bump_skills(db, task, user):
    """Completing a task grows the skills it required."""
    for ts in db.query(TaskSkill).filter(TaskSkill.task_id == task.id).all():
        us = db.query(UserSkill).filter(UserSkill.user_id == user.id, UserSkill.skill_id == ts.skill_id).first()
        if not us:
            us = UserSkill(user_id=user.id, skill_id=ts.skill_id, level=1, target=5)
            db.add(us)
        elif (us.level or 1) < 5:
            us.level = (us.level or 1) + 1
        db.add(SkillLog(user_id=user.id, skill_id=ts.skill_id, level=us.level))


@router.patch("/tasks/{tid}")
def update_my_task(tid: int, d: TaskProgress, db: Session = Depends(get_db), user=E):
    t = db.query(Task).filter(Task.id == tid, Task.assigned_to == user.id).first()
    if not t:
        raise HTTPException(404, "Task not found or not assigned to you.")
    was_done = t.status == "Done"
    ch = d.model_dump(exclude_unset=True)
    if "status" in ch and ch["status"] is not None:
        t.status = status_db(ch["status"])
        if t.status == "Done":
            t.progress = 100
        elif t.status == "To Do":
            t.progress = 0
        elif (t.progress or 0) in (0, 100):
            t.progress = 10 if t.progress == 0 else 90
    if "progress" in ch and ch["progress"] is not None:
        t.progress = ch["progress"]
        if t.progress == 100:
            t.status = "Done"
        elif t.progress > 0 and t.status in ("To Do", "Done"):
            t.status = "In Progress"
        elif t.progress == 0 and t.status != "Done":
            t.status = "To Do"
    log_history(db, t.id, user.id, "progress", f"{user.name}: {t.status}, {t.progress}%")
    proj = db.query(Project).get(t.project_id)
    if t.status == "Done" and not was_done:
        _bump_skills(db, t, user)
        if proj and proj.manager_id:
            notify(db, proj.manager_id, f"{user.name} completed task: {t.title}")
    elif proj and proj.manager_id and "status" in ch:
        notify(db, proj.manager_id, f"{user.name} set '{t.title}' to {d.status}")
    db.commit()
    return task_dict(t, db)


# ---------------- Daily planner ----------------
def _plan(x):
    return {"id": x.id, "title": x.title, "priority": x.priority,
            "plan_date": x.plan_date.isoformat() if x.plan_date else None, "done": bool(x.done)}


@router.get("/planner")
def planner(plan_date: date | None = None, db: Session = Depends(get_db), user=E):
    q = db.query(Planner).filter(Planner.user_id == user.id)
    if plan_date:
        q = q.filter(Planner.plan_date == plan_date)
    rows = q.order_by(Planner.plan_date.desc(), Planner.done, Planner.id.desc()).all()
    order = {"High": 0, "Medium": 1, "Low": 2}
    return [_plan(x) for x in sorted(rows, key=lambda r: (r.done, order.get(r.priority, 1)))] if plan_date else [_plan(x) for x in rows]


@router.post("/planner", status_code=201)
def add_plan(d: PlannerInput, db: Session = Depends(get_db), user=E):
    check_priority(d.priority)
    p = Planner(user_id=user.id, title=d.title.strip(), priority=d.priority, plan_date=d.plan_date, done=d.done)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _plan(p)


@router.patch("/planner/{pid}")
def edit_plan(pid: int, d: PlannerUpdate, db: Session = Depends(get_db), user=E):
    p = db.query(Planner).filter(Planner.id == pid, Planner.user_id == user.id).first()
    if not p:
        raise HTTPException(404, "Planner entry not found.")
    ch = d.model_dump(exclude_unset=True)
    if "priority" in ch:
        check_priority(ch["priority"])
    for k, v in ch.items():
        setattr(p, k, v)
    db.commit()
    return _plan(p)


@router.delete("/planner/{pid}")
def delete_plan(pid: int, db: Session = Depends(get_db), user=E):
    p = db.query(Planner).filter(Planner.id == pid, Planner.user_id == user.id).first()
    if not p:
        raise HTTPException(404, "Planner entry not found.")
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---------------- Bottleneck Detective ----------------
def _helper_candidates(db, owner, skill_id, task_id):
    """Teammates of the same project (via task) who have the needed skill; falls back gracefully."""
    team_ids = set()
    if task_id:
        t = db.query(Task).get(task_id)
        if t:
            team_ids = {x.assigned_to for x in db.query(Task).filter(Task.project_id == t.project_id, Task.assigned_to.isnot(None))}
    else:
        my_projects = {x.project_id for x in db.query(Task).filter(Task.assigned_to == owner.id)}
        if my_projects:
            team_ids = {x.assigned_to for x in db.query(Task).filter(Task.project_id.in_(my_projects), Task.assigned_to.isnot(None))}
    team_ids.discard(owner.id)
    skilled = set()
    if skill_id:
        skilled = {u.user_id for u in db.query(UserSkill).filter(UserSkill.skill_id == skill_id, UserSkill.level >= 3)}
        skilled.discard(owner.id)
    chosen = (team_ids & skilled) or skilled or team_ids
    if not chosen:
        chosen = {u.id for u in db.query(User).filter(User.role == "employee", User.id != owner.id)}
    return db.query(User).filter(User.id.in_(chosen), User.role == "employee").all()


def _can_help(db, user, b):
    if b.user_id == user.id:
        return True
    return any(h.id == user.id for h in _helper_candidates(db, db.query(User).get(b.user_id), b.skill_id, b.task_id))


def _blocker_dict(b, db, user):
    owner = db.query(User).get(b.user_id)
    skill = db.query(Skill).get(b.skill_id) if b.skill_id else None
    task = db.query(Task).get(b.task_id) if b.task_id else None
    proj = db.query(Project).get(task.project_id) if task else None
    msgs = db.query(Reply).filter(Reply.bottleneck_id == b.id).order_by(Reply.id).all()
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_({m.user_id for m in msgs} | {b.user_id}))}
    return {"id": b.id, "title": b.title, "description": b.description, "status": b.status,
            "user_id": b.user_id, "user_name": owner.name if owner else None, "mine": b.user_id == user.id,
            "skill_id": b.skill_id, "skill_name": skill.name if skill else None,
            "task_title": task.title if task else None, "project_name": proj.name if proj else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "messages": [{"id": m.id, "user_id": m.user_id, "user_name": names.get(m.user_id), "mine": m.user_id == user.id,
                          "message": m.message, "created_at": m.created_at.isoformat() if m.created_at else None} for m in msgs]}


@router.get("/blockers")
def blockers(db: Session = Depends(get_db), user=E):
    """My blockers + blockers from teammates that I was matched to help with."""
    rows = db.query(Bottleneck).order_by(Bottleneck.id.desc()).all()
    return [_blocker_dict(b, db, user) for b in rows if _can_help(db, user, b)]


@router.post("/blockers", status_code=201)
def report_blocker(d: BlockerInput, db: Session = Depends(get_db), user=E):
    if d.task_id:
        t = db.query(Task).filter(Task.id == d.task_id, Task.assigned_to == user.id).first()
        if not t:
            raise HTTPException(400, "That task is not assigned to you.")
    b = Bottleneck(user_id=user.id, title=d.title.strip(), description=d.description, skill_id=d.skill_id,
                   task_id=d.task_id, status="Open")
    db.add(b)
    db.flush()
    if d.description:
        db.add(Reply(bottleneck_id=b.id, user_id=user.id, message=d.description))
    helpers = _helper_candidates(db, user, d.skill_id, d.task_id)
    for h in helpers:
        notify(db, h.id, f"{user.name} needs help: {b.title}")
    db.commit()
    out = _blocker_dict(b, db, user)
    out["notified"] = [h.name for h in helpers]
    return out


@router.post("/blockers/{bid}/messages", status_code=201)
def post_message(bid: int, d: MessageInput, db: Session = Depends(get_db), user=E):
    b = db.query(Bottleneck).get(bid)
    if not b or not _can_help(db, user, b):
        raise HTTPException(404, "Blocker not found.")
    db.add(Reply(bottleneck_id=b.id, user_id=user.id, message=d.message.strip()))
    others = {r.user_id for r in db.query(Reply).filter(Reply.bottleneck_id == b.id)} | {b.user_id}
    others.discard(user.id)
    for uid in others:
        notify(db, uid, f"{user.name} replied on blocker: {b.title}")
    db.commit()
    return _blocker_dict(b, db, user)


@router.patch("/blockers/{bid}/status")
def blocker_status(bid: int, d: BlockerStatus, db: Session = Depends(get_db), user=E):
    b = db.query(Bottleneck).get(bid)
    if not b or not _can_help(db, user, b):
        raise HTTPException(404, "Blocker not found.")
    if d.status not in ("Open", "Resolved"):
        raise HTTPException(400, "Status must be Open or Resolved.")
    if b.user_id != user.id:
        raise HTTPException(403, "Only the person who reported the blocker can change its status.")
    b.status = d.status
    helpers = {r.user_id for r in db.query(Reply).filter(Reply.bottleneck_id == b.id)} - {user.id}
    for uid in helpers:
        notify(db, uid, f"Blocker '{b.title}' is now {b.status}")
    db.commit()
    return _blocker_dict(b, db, user)


# ---------------- Skill growth tracker ----------------
@router.get("/skills")
def my_skills(db: Session = Depends(get_db), user=E):
    rows = (db.query(Skill, UserSkill).join(UserSkill, UserSkill.skill_id == Skill.id)
            .filter(UserSkill.user_id == user.id).all())
    done_ids = [t.id for t in db.query(Task).filter(Task.assigned_to == user.id, Task.status == "Done")]
    gained = {}
    if done_ids:
        for ts in db.query(TaskSkill).filter(TaskSkill.task_id.in_(done_ids)):
            gained[ts.skill_id] = gained.get(ts.skill_id, 0) + 1
    names = {s.id: s.name for s in db.query(Skill)}
    logs = db.query(SkillLog).filter(SkillLog.user_id == user.id).order_by(SkillLog.logged_at.desc(), SkillLog.id.desc()).limit(30).all()
    mine = {s.id: us.level or 1 for s, us in rows}

    # Recommend: skills required by tasks in my projects where my level is below 4
    my_projects = {t.project_id for t in db.query(Task).filter(Task.assigned_to == user.id)}
    need = {}
    if my_projects:
        task_ids = [t.id for t in db.query(Task).filter(Task.project_id.in_(my_projects), Task.status != "Done")]
        if task_ids:
            for ts in db.query(TaskSkill).filter(TaskSkill.task_id.in_(task_ids)):
                need[ts.skill_id] = need.get(ts.skill_id, 0) + 1
    recs = [{"skill_id": sid, "name": names[sid], "current_level": mine.get(sid, 0), "tasks_needing": n,
             "reason": f"{n} open task(s) in your projects need {names[sid]}" + (" - you haven't started it yet" if sid not in mine else "")}
            for sid, n in sorted(need.items(), key=lambda kv: (mine.get(kv[0], 0), -kv[1])) if mine.get(sid, 0) < 4]
    return {
        "skills": [{"skill_id": s.id, "name": s.name, "level": us.level or 1, "target": us.target or 5,
                    "tasks_completed": gained.get(s.id, 0)} for s, us in rows],
        "history": [{"skill": names.get(l.skill_id), "level": l.level,
                     "logged_at": l.logged_at.isoformat() if l.logged_at else None} for l in logs],
        "recommendations": recs,
        "all_skills": [{"id": k, "name": v} for k, v in names.items()],
    }


@router.post("/skills")
def save_skill(d: SkillUpdate, db: Session = Depends(get_db), user=E):
    if not db.query(Skill).get(d.skill_id):
        raise HTTPException(404, "Skill not found.")
    us = db.query(UserSkill).filter(UserSkill.user_id == user.id, UserSkill.skill_id == d.skill_id).first()
    if us:
        us.level, us.target = d.level, d.target
    else:
        db.add(UserSkill(user_id=user.id, skill_id=d.skill_id, level=d.level, target=d.target))
    db.add(SkillLog(user_id=user.id, skill_id=d.skill_id, level=d.level))
    db.commit()
    return {"ok": True}


@router.get("/profile")
def profile(db: Session = Depends(get_db), user=E):
    return user_dict(user)
