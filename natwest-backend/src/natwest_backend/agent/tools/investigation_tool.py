from __future__ import annotations

from typing import Any
from uuid import UUID

from natwest_backend.agent.mcp_client import MCPConnection
from natwest_backend.agent.skills.investigation_workflow import (
    CaseInvestigationWorkflow,
    InvestigationInput,
    render_report_markdown,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class InvestigationToolInput(BaseModel):
    """Arguments for the investigation workflow tool."""

    case_id: UUID | None = Field(
        default=None,
        description="UUID of the case (rare — usually only from previous tool results)",
    )
    case_ref: str | None = Field(
        default=None,
        description="Human-readable case reference like CASE-1001 or CASE-1234",
    )
    customer_name: str | None = Field(
        default=None,
        description="Customer name — first name only, first + last, or 'the customer named X'",
    )


class InvestigationWorkflowTool(BaseTool):
    """
    LangChain tool that invokes the case investigation workflow.

    The agent calls this tool when the router has classified the message
    as an INVESTIGATION request. The agent is responsible for extracting
    exactly one identifier (case_id, case_ref, or customer_name) from the
    message or conversation history.
    """

    name: str = "invoke_investigation_workflow"
    description: str = (
        "Run a full 9-step case investigation. Provide exactly one of "
        "case_id, case_ref, or customer_name. Use case_ref when the user "
        "gives a case reference like CASE-1001. Use customer_name when the "
        "user references a person by name (e.g. 'Aisha', 'Aisha Rahman', "
        "'David Thompson'). Use case_id when working with UUIDs (rare — "
        "usually only from previous tool results). The workflow returns a "
        "structured investigation report with case summary, customer "
        "context, vulnerability context, risk indicators, evidence gaps, "
        "and a recommended action."
    )
    args_schema: type[BaseModel] = InvestigationToolInput

    # Typed as Any so duck-typed connections and chat-model-like objects
    # (including test doubles) are accepted without pydantic validation.
    connection: Any
    llm: Any

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, **kwargs: Any) -> str:
        raise NotImplementedError("Use async invocation via _arun")

    async def _arun(self, **kwargs: Any) -> str:
        """Run the investigation workflow and return the rendered report."""
        workflow_input = InvestigationInput(**kwargs)
        workflow = CaseInvestigationWorkflow(
            connection=self.connection,
            llm=self.llm,
        )
        report = await workflow.execute(workflow_input)
        return render_report_markdown(report)


def create_investigation_tool(
    connection: MCPConnection,
    llm: Any,
) -> InvestigationWorkflowTool:
    """Build the investigation workflow tool for the current request."""
    return InvestigationWorkflowTool(connection=connection, llm=llm)
