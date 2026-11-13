from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=128)
class ClientCreate(Credentials):
    business_id: str
class BusinessInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
class AgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=100)
    system_prompt: str = Field(min_length=1, max_length=12000)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    enabled: bool = True
class ChatInput(BaseModel):
    capture_lead: bool = False
    content: str = Field(min_length=1, max_length=12000)
class LeadInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    notes: str = Field(default="", max_length=4000)

class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

class Registration(Credentials):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    business_name: str = Field(min_length=1,max_length=120,pattern=r"\S")
    setup_token: str = Field(default="",max_length=256)

class KnowledgeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1,max_length=200,pattern=r"\S")
    content: str = Field(min_length=1,max_length=20000,pattern=r"\S")
    enabled: bool = True
class HandoffInput(BaseModel):
    reason: str = Field(min_length=1,max_length=2000,pattern=r"\S")
class HandoffStatus(BaseModel):
    status: Literal["ai","human","resolved"]
class HumanReply(BaseModel):
    content: str = Field(min_length=1,max_length=12000,pattern=r"\S")
