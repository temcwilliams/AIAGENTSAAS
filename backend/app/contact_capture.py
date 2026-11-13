"""Capture voluntarily supplied email only when the request explicitly opts in."""
import re
from sqlalchemy import select
from .models import Lead

EMAIL=re.compile(r'(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w-])',re.I)

def capture(db,business_id,conversation_id,text,consent):
    if not consent:return None
    match=EMAIL.search(text)
    if not match:return None
    email=match.group(1).lower()
    if len(email)>254:return None
    existing=db.scalar(select(Lead).where(Lead.business_id==business_id,Lead.conversation_id==conversation_id,Lead.email==email))
    if existing:return existing.id
    name_match=re.search(r'\bmy name is ([A-Za-z][A-Za-z\x20\x27-]{0,79}?)(?:[.,;!\n]| and\b|$)',text,re.I)
    name=name_match.group(1).strip() if name_match else 'Chat contact'
    lead=Lead(business_id=business_id,conversation_id=conversation_id,name=name,email=email,source='chat',notes='Contact shared in chat with capture enabled.')
    db.add(lead);db.flush()
    return lead.id
