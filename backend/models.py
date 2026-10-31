from sqlalchemy import (Column, Integer, String, Text, Date, DateTime, Boolean,
                        ForeignKey, Enum, Float, func)
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(64), nullable=False)
    role = Column(Enum("manager", "employee"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(60), unique=True, nullable=False)


class UserSkill(Base):
    __tablename__ = "user_skills"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    level = Column(Integer, default=1)
    target = Column(Integer, default=5)


class SkillLog(Base):
    __tablename__ = "skill_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"))
    level = Column(Integer)
    logged_at = Column(DateTime, server_default=func.now())


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    status = Column(Enum("Planning", "Active", "Completed"), default="Planning")
    deadline = Column(Date)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text)
    priority = Column(Enum("Low", "Medium", "High"), default="Medium")
    deadline = Column(Date)
    # DB stores To Do / In Progress / Done; API shows Pending / In Progress / Completed
    status = Column(Enum("To Do", "In Progress", "Done"), default="To Do")
    progress = Column(Integer, default=0)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    estimated_hours = Column(Float, default=0)          # added by migrate.py
    created_at = Column(DateTime, server_default=func.now())


class TaskSkill(Base):
    __tablename__ = "task_skills"
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)


class TaskHistory(Base):
    """Tracks task creation, assignments and progress changes."""
    __tablename__ = "task_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(40), nullable=False)
    detail = Column(String(300))
    created_at = Column(DateTime, server_default=func.now())


class Planner(Base):
    __tablename__ = "planner"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    priority = Column(Enum("Low", "Medium", "High"), default="Medium")
    plan_date = Column(Date)
    done = Column(Boolean, default=False)


class Bottleneck(Base):
    __tablename__ = "bottlenecks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)  # migrate.py
    status = Column(Enum("Open", "Resolved"), default="Open")
    created_at = Column(DateTime, server_default=func.now())


class Reply(Base):
    __tablename__ = "replies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bottleneck_id = Column(Integer, ForeignKey("bottlenecks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(String(300), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
