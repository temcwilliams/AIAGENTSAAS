import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Text, JSON, Index, DateTime
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
    __table_args__ = (CheckConstraint("role IN ('admin','client')"), CheckConstraint("role = 'admin' OR business_id IS NOT NULL"), UniqueConstraint('id','business_id',name='uq_users_id_business'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10))
    business_id: Mapped[str | None] = mapped_column(ForeignKey("businesses.id"))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled: Mapped[bool] = mapped_column(default=False, server_default='false')

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
    __table_args__ = (UniqueConstraint('id','business_id',name='uq_knowledge_id_business'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=now)

class Membership(Base):
    __tablename__ = 'memberships'
    __table_args__ = (
        ForeignKeyConstraint(['user_id','business_id'],['users.id','users.business_id']),
        CheckConstraint("role IN ('viewer','responder','manager')"),
    )
    business_id: Mapped[str] = mapped_column(ForeignKey('businesses.id'),primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36),primary_key=True)
    role: Mapped[str] = mapped_column(String(12),default='viewer')

class ActionToken(Base):
    __tablename__ = 'action_tokens'
    __table_args__ = (CheckConstraint("purpose IN ('reset','verify','setup')"), CheckConstraint("delivery_status IN ('pending','sent','failed')"),)
    token_hash: Mapped[str] = mapped_column(String(64),primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'),index=True)
    purpose: Mapped[str] = mapped_column(String(12))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)
    delivery_status: Mapped[str] = mapped_column(String(12),default='pending')

class OnboardingDraft(Base):
    __tablename__ = 'onboarding_drafts'
    __table_args__ = (
        CheckConstraint('version >= 1'),
        CheckConstraint("status IN ('draft','submitted','changes_requested','approved','published')"),
        ForeignKeyConstraint(['agent_id','business_id'],['agents.id','agents.business_id']),
        ForeignKeyConstraint(['knowledge_id','business_id'],['knowledge_documents.id','knowledge_documents.business_id']),
    )
    business_id: Mapped[str] = mapped_column(ForeignKey('businesses.id'),primary_key=True)
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(20),default='draft')
    profile: Mapped[dict] = mapped_column(JSON,default=dict)
    reviewer_notes: Mapped[str] = mapped_column(Text,default='')
    agent_id: Mapped[str | None] = mapped_column(String(36))
    knowledge_id: Mapped[str | None] = mapped_column(String(36))
    published_source_version: Mapped[int | None]
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    published_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    template_version: Mapped[int] = mapped_column(default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
