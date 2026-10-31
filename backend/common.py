from fastapi import HTTPException
from models import Notification, TaskHistory, Task, Project, Skill, TaskSkill, User

STATUS_TO_DB = {"Pending": "To Do", "In Progress": "In Progress", "Completed": "Done",
                "To Do": "To Do", "Done": "Done"}
STATUS_TO_API = {"To Do": "Pending", "In Progress": "In Progress", "Done": "Completed"}
PRIORITIES = ("Low", "Medium", "High")


def status_db(s):
    if s not in STATUS_TO_DB:
        raise HTTPException(400, "Status must be Pending, In Progress or Completed.")
    return STATUS_TO_DB[s]


def check_priority(p):
    if p not in PRIORITIES:
        raise HTTPException(400, "Priority must be Low, Medium or High.")
    return p


def notify(db, user_id, message):
    db.add(Notification(user_id=user_id, message=message[:300], is_read=False))


def log_history(db, task_id, actor_id, action, detail=""):
    db.add(TaskHistory(task_id=task_id, actor_id=actor_id, action=action, detail=detail[:300]))


def user_dict(u):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}


def task_dict(t, db):
    p = db.query(Project).get(t.project_id)
    a = db.query(User).get(t.assigned_to) if t.assigned_to else None
    skills = (db.query(Skill).join(TaskSkill, TaskSkill.skill_id == Skill.id)
              .filter(TaskSkill.task_id == t.id).all())
    return {
        "id": t.id, "project_id": t.project_id, "project_name": p.name if p else None,
        "title": t.title, "description": t.description, "priority": t.priority,
        "deadline": t.deadline.isoformat() if t.deadline else None,
        "status": STATUS_TO_API.get(t.status, t.status), "progress": t.progress or 0,
        "estimated_hours": t.estimated_hours or 0,
        "assigned_to": t.assigned_to, "assignee_name": a.name if a else None,
        "skills": [{"id": s.id, "name": s.name} for s in skills],
    }


def own_project(db, project_id, manager_id):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found.")
    return p
