import hashlib
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from models import User

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "dev-only-change-me-please-0123456789abcdef"
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login-form")


def hash_password(p: str) -> str:
    # SHA-256 hex, same as SHA2('x',256) used in Task.sql so demo users can log in
    return hashlib.sha256(p.encode("utf-8")).hexdigest()


def verify_password(p: str, stored: str) -> bool:
    return hash_password(p) == (stored or "").lower()


def create_access_token(user_id: int, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired login. Please sign in again.",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        uid = int(jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub"))
    except (JWTError, ValueError, TypeError):
        raise err
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise err
    return user


def require_role(*roles):
    def dep(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "You do not have permission to access this resource.")
        return user
    return dep
