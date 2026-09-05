from __future__ import annotations

from dataclasses import dataclass, field

from natwest_backend.agent.mcp_client import MCPConnection, safe_json_parse
from natwest_backend.agent.prompts.skills import (
    CUSTOMER_NAME_EXTRACTION_PROMPT,
    ESCALATION_SUMMARY_PROMPT,
)
from natwest_backend.agent.shared.fallback_response import (
    DataFallbackContext,
    build_data_fallback_response,
)
from natwest_backend.agent.shared.parsing import content_to_text, parse_issue_list
from natwest_backend.agent.shared.skill_limits import DEFAULT_SKILL_LIMITS, SkillLimits
from natwest_shared.utils.logger import get_logger
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = get_logger(__name__)


@dataclass
class SkillResult:
    answer: str
    raw_data: str = field(default="")


class EscalationSummarySkill:
    """
    Orchestrates a full customer escalation summary.

    Input:  User message containing a customer name.
    Output: Structured executive summary with risk level,
            recommendations, and identified gaps.

    TODO: This skill calls removed legacy MCP tools (get_customer_by_name,
    list_open_issues, list_issue_updates, list_next_actions) which no longer
    exist under the new 8-tool contract and 9-table schema. It will be
    deleted and replaced by an investigation workflow in a separate task.
    """

    def __init__(
        self,
        connection: MCPConnection,
        llm: ChatOpenAI,
        limits: SkillLimits = DEFAULT_SKILL_LIMITS,
    ) -> None:
        self._connection = connection
        self._llm = llm
        self._limits = limits
        self._mcp_call_count = 0

    async def execute(self, user_message: str) -> SkillResult:
        """
        Run the full escalation summary workflow.

        Steps:
        1. Extract customer name from the user message (LLM)
        2. Fetch customer profile (MCP)
        3. Fetch open issues (MCP)
        4. For each issue, fetch updates and next actions (MCP)
        5. Synthesise executive summary (LLM)
        """
        logger.info(
            "Escalation Summary Skill started | limits: max_issues=%d, max_updates=%d, max_actions=%d, max_mcp_calls=%d",
            self._limits.max_issues,
            self._limits.max_updates_per_issue,
            self._limits.max_actions_per_issue,
            self._limits.max_mcp_calls,
        )

        # --- Step 1: Extract customer name ---
        customer_name = await self._extract_customer_name(user_message)
        if customer_name == "UNKNOWN":
            return await self._build_fallback_response(
                user_message=user_message,
                context=DataFallbackContext(
                    reason="missing_customer_name",
                    entity_type="customer",
                    details="The request did not contain a customer name that could be extracted confidently.",
                ),
            )
        logger.info("Extracted customer name: %s", customer_name)

        # --- Step 2: Fetch customer profile ---
        customer_raw = await self._guarded_mcp_call(
            "get_customer_by_name", {"name": customer_name}
        )

        if customer_raw is None:
            return await self._build_fallback_response(
                user_message=user_message,
                context=DataFallbackContext(
                    reason="tool_limit_reached",
                    entity_type="customer",
                    requested_value=customer_name,
                    tool_name="get_customer_by_name",
                    details="The MCP call limit was reached before the customer profile could be retrieved.",
                ),
            )

        if customer_raw.startswith("Error:") or customer_raw in (
            "null",
            "None",
            "",
            "No output returned",
        ):
            return await self._build_fallback_response(
                user_message=user_message,
                context=DataFallbackContext(
                    reason="not_found",
                    entity_type="customer",
                    requested_value=customer_name,
                    tool_name="get_customer_by_name",
                    raw_result=customer_raw,
                ),
            )

        customer = safe_json_parse(customer_raw)
        if customer is None:
            return await self._build_fallback_response(
                user_message=user_message,
                context=DataFallbackContext(
                    reason="unreadable_data",
                    entity_type="customer",
                    requested_value=customer_name,
                    tool_name="get_customer_by_name",
                    raw_result=customer_raw,
                ),
            )

        customer_id = customer.get("id")
        if not customer_id:
            return await self._build_fallback_response(
                user_message=user_message,
                context=DataFallbackContext(
                    reason="missing_identifier",
                    entity_type="customer",
                    requested_value=customer_name,
                    tool_name="get_customer_by_name",
                    raw_result=customer_raw,
                    details="The customer record was returned without an id field.",
                ),
            )

        logger.info("Fetched customer profile: %s (id=%s)", customer_name, customer_id)

        # --- Step 3: Fetch open issues ---
        issues_raw = await self._guarded_mcp_call(
            "list_open_issues",
            {"customer_id": customer_id, "limit": self._limits.max_issues},
        )

        if issues_raw is None:
            return await self._build_fallback_response(
                user_message=user_message,
                context=DataFallbackContext(
                    reason="tool_limit_reached",
                    entity_type="issue_data",
                    requested_value=customer_name,
                    tool_name="list_open_issues",
                    details="The MCP call limit was reached before open issues could be retrieved.",
                ),
            )

        issues = parse_issue_list(safe_json_parse(issues_raw))
        total_issues = len(issues)
        issues = issues[: self._limits.max_issues]
        truncated_issues = total_issues > len(issues)
        logger.info(
            "Fetched %d open issues (showing %d, truncated=%s)",
            total_issues,
            len(issues),
            truncated_issues,
        )

        # --- Step 4: Fetch updates and actions per issue ---
        updates_sections: list[str] = []
        actions_sections: list[str] = []

        for issue in issues:
            issue_id = issue.get("id")
            ref = issue.get("external_ref", "???")

            if not issue_id:
                continue

            updates_raw = await self._guarded_mcp_call(
                "list_issue_updates",
                {
                    "issue_id": issue_id,
                    "limit": self._limits.max_updates_per_issue,
                },
            )
            actions_raw = await self._guarded_mcp_call(
                "list_next_actions",
                {
                    "issue_id": issue_id,
                    "limit": self._limits.max_actions_per_issue,
                },
            )

            if updates_raw is None or actions_raw is None:
                logger.warning(
                    "MCP call limit reached during issue %s, stopping",
                    ref,
                )
                updates_sections.append(
                    f"### {ref}\nData gathering stopped — MCP call limit reached."
                )
                break

            updates_sections.append(f"### {ref}\n{updates_raw}")
            actions_sections.append(f"### {ref}\n{actions_raw}")

        logger.info(
            "Fetched updates for %d issues, actions for %d issues | total MCP calls: %d / %d",
            len(updates_sections),
            len(actions_sections),
            self._mcp_call_count,
            self._limits.max_mcp_calls,
        )

        # --- Step 5: Synthesise executive summary ---
        truncation_note = ""
        if truncated_issues:
            truncation_note = (
                f"\n\n**Note:** Only the first {self._limits.max_issues} of "
                f"{total_issues} open issues are included in this summary."
            )

        summary = await self._synthesise(
            customer_data=customer_raw,
            issues_data=issues_raw,
            issue_count=total_issues,
            updates_data="\n\n".join(updates_sections) or "No updates found.",
            actions_data="\n\n".join(actions_sections) or "No pending actions.",
        )

        raw_data = "\n\n".join(
            [
                f"[customer]\n{customer_raw}",
                f"[issues]\n{issues_raw}",
                f"[updates]\n{chr(10).join(updates_sections) or 'No updates found.'}",
                f"[actions]\n{chr(10).join(actions_sections) or 'No pending actions.'}",
            ]
        )
        logger.info("Escalation Summary Skill completed")
        return SkillResult(answer=summary + truncation_note, raw_data=raw_data)

    async def _build_fallback_response(
        self,
        *,
        user_message: str,
        context: DataFallbackContext,
    ) -> SkillResult:
        """Delegate fallback user messaging to the LLM using structured context."""
        answer = await build_data_fallback_response(
            self._llm,
            user_message=user_message,
            context=context,
        )
        return SkillResult(answer=answer)

    async def _guarded_mcp_call(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> str | None:
        """Call an MCP tool with safety limit enforcement."""
        if self._mcp_call_count >= self._limits.max_mcp_calls:
            logger.warning(
                "Skill MCP call limit reached (%d/%d), skipping %s",
                self._mcp_call_count,
                self._limits.max_mcp_calls,
                name,
            )
            return None

        self._mcp_call_count += 1
        return await self._connection.call_tool(name, arguments)

    async def _extract_customer_name(self, message: str) -> str:
        """Use the LLM to pull the customer name from free text."""
        prompt = CUSTOMER_NAME_EXTRACTION_PROMPT.format(message=message)
        response = await self._llm.ainvoke([HumanMessage(content=prompt)])
        return content_to_text(getattr(response, "content")).strip()  # type: ignore[arg-type]

    async def _synthesise(
        self,
        customer_data: str,
        issues_data: str,
        issue_count: int,
        updates_data: str,
        actions_data: str,
    ) -> str:
        """Feed all gathered data into the synthesis prompt."""
        prompt = ESCALATION_SUMMARY_PROMPT.format(
            customer_data=customer_data,
            issues_data=issues_data,
            issue_count=issue_count,
            updates_data=updates_data,
            actions_data=actions_data,
        )
        response = await self._llm.ainvoke([SystemMessage(content=prompt)])
        return content_to_text(getattr(response, "content"))  # type: ignore[arg-type]
