"""Database-backed, shared-worker limits. Reservations survive provider failures."""
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import case
from .models import RateLimitBucket, now
from .security import digest


def consume(db, key: str, limit: int, seconds: int):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = sqlite_insert if db.bind.dialect.name == 'sqlite' else pg_insert
    current = now()
    expired = RateLimitBucket.reset_at <= current
    stmt = insert(RateLimitBucket).values(key=digest(key), count=1, reset_at=current+timedelta(seconds=seconds))
    stmt = stmt.on_conflict_do_update(
        index_elements=[RateLimitBucket.key],
        set_={
            'count': case((expired, 1), else_=RateLimitBucket.count+1),
            'reset_at': case((expired, current+timedelta(seconds=seconds)), else_=RateLimitBucket.reset_at),
        },
        where=(expired | (RateLimitBucket.count < limit)),
    ).returning(RateLimitBucket.count)
    count = db.scalar(stmt)
    # Reserve before calling an external provider; never refund ambiguous failures.
    db.commit()
    if count is None:
        raise HTTPException(429, 'Request limit reached; try again after the window resets', headers={'Retry-After':str(seconds)})
