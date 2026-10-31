from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field

Priority = str


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=100)
    role: str


class LoginInput(BaseModel):
    email: str
    password: str
    role: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    password: Optional[str] = Field(default=None, min_length=6, max_length=100)


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    status: str = "Planning"
    deadline: Optional[date] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[date] = None


class TaskInput(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    priority: str = "Medium"
    deadline: Optional[date] = None
    estimated_hours: float = 0
    assigned_to: Optional[int] = None
    skill_ids: List[int] = []


class TaskEdit(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[date] = None
    estimated_hours: Optional[float] = None
    status: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    assigned_to: Optional[int] = None
    skill_ids: Optional[List[int]] = None


class TaskProgress(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)


class PlannerInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: str = "Medium"
    plan_date: date
    done: bool = False


class PlannerUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    plan_date: Optional[date] = None
    done: Optional[bool] = None


class BlockerInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    skill_id: Optional[int] = None
    task_id: Optional[int] = None


class MessageInput(BaseModel):
    message: str = Field(min_length=1)


class BlockerStatus(BaseModel):
    status: str


class SkillUpdate(BaseModel):
    skill_id: int
    level: int = Field(ge=1, le=5)
    target: int = Field(default=5, ge=1, le=5)


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
