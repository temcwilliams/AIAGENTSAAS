import hashlib, secrets
from threading import BoundedSemaphore
from datetime import datetime, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession
from .db import get_db
from .models import Session, User, Business

class BoundedPasswordHasher:
    """Bound Argon2 memory use across every hash and verification in this worker."""
    def __init__(self):
        self._hasher = PasswordHasher()
        self._slot = BoundedSemaphore(1)

    def _call(self, operation, *args):
        if not self._slot.acquire(blocking=False):
            raise HTTPException(429, "Authentication busy; retry shortly", headers={"Retry-After": "1"})
        try:
            return operation(*args)
        finally:
            self._slot.release()

    def hash(self, password):
        return self._call(self._hasher.hash, password)

    def verify(self, hashed, password):
        return self._call(self._hasher.verify, hashed, password)

hasher = BoundedPasswordHasher()
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
