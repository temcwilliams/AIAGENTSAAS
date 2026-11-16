"""Retired public registration endpoint. Accounts are provisioned by admins."""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix='/auth')


@router.post('/register', include_in_schema=False)
async def register():
    # Reject legacy clients before validation, DB access, or password hashing.
    # Owner setup tokens also cannot reopen account creation over HTTP.
    raise HTTPException(403, 'Public account creation is disabled. Email the platform owner to request access.')
