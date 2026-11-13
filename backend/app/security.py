import hashlib, secrets
from datetime import datetime, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession
from .db import get_db
from .models import Session, User, Business

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def verify(password, hashed):
    try: return hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError): return False

def current_user(request: Request, db: DBSession = Depends(get_db)):
    session = db.get(Session, digest(request.cookies.get("session", "")))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Authentication required")
    user = db.get(User, session.user_id)
    if not user: raise HTTPException(401, "Authentication required")
    return user

def admin(user=Depends(current_user)):
    if user.role != "admin": raise HTTPException(403, "Administrator required")
    return user

def tenant(business_id: str, user=Depends(current_user), db: DBSession=Depends(get_db)):
    if user.role != "admin" and user.business_id != business_id:
        raise HTTPException(404, "Business not found")
    if not db.get(Business, business_id): raise HTTPException(404, "Business not found")
    return business_id
