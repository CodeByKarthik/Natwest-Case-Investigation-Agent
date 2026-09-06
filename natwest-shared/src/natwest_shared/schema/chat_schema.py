from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    User query submitted to the Acme Operations Agent.
    """

    message: str = Field(min_length=1, max_length=5000)
    conversation_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    """
    Structured response returned by the Acme Operations Agent API.
    """

    conversation_id: UUID
    message_id: UUID
    answer: str
    authenticated_username: str
    authenticated_role: str
    created_at: datetime
    run_id: str = ""
    tools_called: list[str] = Field(default_factory=list)
    rbac_denied: bool = False
