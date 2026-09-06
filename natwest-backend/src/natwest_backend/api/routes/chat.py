from datetime import UTC, datetime
from uuid import uuid4

from natwest_backend.agent.evaluation import run_background_evaluation
from natwest_backend.agent.service import AgentService
from natwest_backend.api.auth import extract_bearer_token, get_auth_context
from natwest_shared.schema.auth_schema import AuthContext
from natwest_shared.schema.chat_schema import ChatRequest, ChatResponse
from fastapi import APIRouter, BackgroundTasks, Depends, Header

router = APIRouter(prefix="/api", tags=["chat"])

_agent_service = AgentService()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
    auth_context: AuthContext = Depends(get_auth_context),
) -> ChatResponse:
    """
    Accept a user message, run the agent, and return the response.

    After the response is sent, a background task evaluates
    the agent's output and logs scores to LangSmith.
    """
    token = extract_bearer_token(authorization)
    conversation_id = request.conversation_id or uuid4()

    result = await _agent_service.run(
        message=request.message,
        token=token,
        auth_context=auth_context,
        conversation_id=str(conversation_id),
        extra_metadata=request.metadata,
    )

    background_tasks.add_task(
        run_background_evaluation,
        messages=result.messages,
        run_id=result.run_id,
        user_role=auth_context.role.value,
        skill_context=result.skill_context,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=uuid4(),
        answer=result.answer,
        authenticated_username=auth_context.username,
        authenticated_role=auth_context.role.value,
        created_at=datetime.now(UTC),
        run_id=result.run_id,
        tools_called=result.tools_called,
        rbac_denied=result.rbac_denied,
    )
