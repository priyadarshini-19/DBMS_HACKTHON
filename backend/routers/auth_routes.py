from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import hash_password, verify_password, create_access_token, get_current_user
from common import user_dict
from database import get_db
from models import User, Notification
from schemas import RegisterInput, LoginInput, ProfileUpdate

router = APIRouter(prefix="/api/auth", tags=["Auth & Profile"])


def _token_response(u):
    return {"access_token": create_access_token(u.id, u.role), "token_type": "bearer", "user": user_dict(u)}


@router.post("/register", status_code=201)
def register(data: RegisterInput, db: Session = Depends(get_db)):
    role = data.role.lower().strip()
    if role not in ("manager", "employee"):
        raise HTTPException(400, "Role must be manager or employee.")
    email = data.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Enter a valid email address.")
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "An account with this email already exists.")
    u = User(name=data.name.strip(), email=email, password=hash_password(data.password), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return _token_response(u)


@router.post("/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    u = db.query(User).filter(func.lower(User.email) == data.email.strip().lower()).first()
    if not u or not verify_password(data.password, u.password):
        raise HTTPException(401, "Incorrect email or password.")
    if data.role and u.role != data.role:
        raise HTTPException(403, f"This account is a {u.role} account. Please use the {u.role.title()} Portal.")
    return _token_response(u)


@router.post("/login-form", include_in_schema=True)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Used by the Swagger 'Authorize' button."""
    u = db.query(User).filter(func.lower(User.email) == form.username.strip().lower()).first()
    if not u or not verify_password(form.password, u.password):
        raise HTTPException(401, "Incorrect email or password.")
    return _token_response(u)


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user_dict(user)


@router.put("/me")
def update_profile(data: ProfileUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if data.name:
        user.name = data.name.strip()
    if data.password:
        user.password = hash_password(data.password)
    db.commit()
    return user_dict(user)


# ---- Notifications (shared by both roles; each user only sees their own) ----
notif_router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@notif_router.get("")
def list_notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (db.query(Notification).filter(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(100).all())
    return [{"id": n.id, "message": n.message, "is_read": bool(n.is_read),
             "created_at": n.created_at.isoformat() if n.created_at else None} for n in rows]


@notif_router.post("/read-all")
def read_all(db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False)\
        .update({"is_read": True})  # noqa: E712
    db.commit()
    return {"ok": True}


@notif_router.patch("/{nid}/read")
def read_one(nid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == nid, Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(404, "Notification not found.")
    n.is_read = True
    db.commit()
    return {"ok": True}
