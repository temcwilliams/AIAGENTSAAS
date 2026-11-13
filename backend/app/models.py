import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class Business(Base):
    __tablename__ = "businesses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(default=now)

class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin','client')"), CheckConstraint("role = 'admin' OR business_id IS NOT NULL"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10))
    business_id: Mapped[str | None] = mapped_column(ForeignKey("businesses.id"))

class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime]

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    reset_at: Mapped[datetime]

class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("id", "business_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(100))
    system_prompt: Mapped[str] = mapped_column(Text)
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_tokens: Mapped[int] = mapped_column(default=512)
    enabled: Mapped[bool] = mapped_column(default=True)

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (ForeignKeyConstraint(["agent_id", "business_id"], ["agents.id", "agents.business_id"]), UniqueConstraint("id", "business_id"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), default="ai")
    handoff_reason: Mapped[str] = mapped_column(Text, default="")
    handoff_requested_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=now)

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (ForeignKeyConstraint(["conversation_id", "business_id"], ["conversations.id", "conversations.business_id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=now)

class Usage(Base):
    __tablename__ = "usage"
    __table_args__ = (ForeignKeyConstraint(["conversation_id", "business_id"], ["conversations.id", "conversations.business_id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(36))
    model: Mapped[str] = mapped_column(String(100))
    prompt_tokens: Mapped[int]
    completion_tokens: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=now)

class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        ForeignKeyConstraint(["conversation_id", "business_id"], ["conversations.id", "conversations.business_id"], name="fk_lead_conversation_tenant"),
        Index("uq_conversation_lead_email", "business_id", "conversation_id", "email", unique=True),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    notes: Mapped[str] = mapped_column(Text, default="")
    conversation_id: Mapped[str | None] = mapped_column(String(36))
    source: Mapped[str] = mapped_column(String(12), default="manual")
    created_at: Mapped[datetime] = mapped_column(default=now)

class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (CheckConstraint("count >= 0"),)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    reset_at: Mapped[datetime]

class OwnerSetup(Base):
    __tablename__ = "owner_setup"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    completed_at: Mapped[datetime]

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=now)
