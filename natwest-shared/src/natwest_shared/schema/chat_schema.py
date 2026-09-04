from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    User query submitted to the Acme Operations Agent.
    """

    message: str = Field(min_length=1, max_length=5000)
    conversation_id: UUID | None = None


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
