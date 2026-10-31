from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from auth import get_current_user
from database import get_db
from models import Skill

router = APIRouter(prefix="/api/skills", tags=["Shared"])


@router.get("")
def all_skills(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return [{"id": s.id, "name": s.name} for s in db.query(Skill).order_by(Skill.name)]
