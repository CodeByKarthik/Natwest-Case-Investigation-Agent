from typing import Any, Optional, cast

from langchain_core.tools import BaseTool
from natwest_shared.utils.logger import get_logger
from pydantic import BaseModel, Field, create_model

from ..mcp_client import MCPConnection

logger = get_logger(__name__)


_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _resolve_type(prop: dict[str, Any]) -> type:
    """
    Map a single JSON Schema property to a Python type.

    Handles ``anyOf`` (nullable unions) by extracting the
    non-null branch.
    """
    if "anyOf" in prop:
        non_null = [s for s in prop["anyOf"] if s.get("type") != "null"]
        if non_null:
            return _JSON_TYPE_MAP.get(non_null[0].get("type", "string"), str)
        return str

    json_type: Any = prop.get("type", "string")

    if isinstance(json_type, list):
        json_type_list = cast(list[Any], json_type)
        json_type_options: list[str] = []
        for item_any in json_type_list:
            if isinstance(item_any, str):
                json_type_options.append(item_any)
        json_type = next(
            (item for item in json_type_options if item != "null"),
            "string",
        )

    if not isinstance(json_type, str):
        json_type = "string"

    return _JSON_TYPE_MAP.get(json_type, str)


def _build_field_description(prop: dict[str, Any]) -> str:
    """
    Combine the property description with enum values and
    format hints so the LLM knows what to pass.
    """
    parts: list[str] = []

    if desc := prop.get("description"):
        parts.append(desc)

    if enum_vals := prop.get("enum"):
        parts.append(f"Valid values: {enum_vals}")

    # Check inside anyOf branches for enums
    for branch in prop.get("anyOf", []):
        if branch_enum := branch.get("enum"):
            parts.append(f"Valid values: {branch_enum}")

    if fmt := prop.get("format"):
        parts.append(f"Format: {fmt}")

    return ". ".join(parts)


def _is_nullable(prop: dict[str, Any]) -> bool:
    """
    Return True if the property accepts null.
    """
    if "anyOf" in prop:
        return any(s.get("type") == "null" for s in prop["anyOf"])
    json_type = prop.get("type")
    if isinstance(json_type, list):
        return "null" in json_type
    return False


def mcp_schema_to_pydantic(
    tool_name: str,
    schema: dict[str, Any],
) -> type[BaseModel]:
    """
    Build a Pydantic model from an MCP tool's ``inputSchema``.

    Required fields have no default; optional fields default
    to ``None``; fields with an explicit ``default`` in the
    schema keep that value.
    """
    properties = schema.get("properties", {})
    required_names = set(schema.get("required", []))

    field_definitions: dict[str, Any] = {}

    for name, prop in properties.items():
        python_type = _resolve_type(prop)
        description = _build_field_description(prop)
        nullable = _is_nullable(prop)

        if name in required_names and not nullable:
            field_definitions[name] = (
                python_type,
                Field(description=description),
            )
        elif "default" in prop:
            default = prop["default"]
            if nullable:
                field_definitions[name] = (
                    Optional[python_type],
                    Field(default=default, description=description),
                )
            else:
                field_definitions[name] = (
                    python_type,
                    Field(default=default, description=description),
                )
        else:
            field_definitions[name] = (
                Optional[python_type],
                Field(default=None, description=description),
            )

    model_name = f"{tool_name}_Input"
    return create_model(model_name, **field_definitions)


class MCPToolWrapper(BaseTool):
    """
    LangChain tool that delegates execution to an MCP tool
    via the authenticated MCP connection.
    """

    name: str = ""
    description: str = ""
    args_schema: type[BaseModel] | dict[str, Any] | None = None
    connection: MCPConnection

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, **kwargs: Any) -> str:
        raise NotImplementedError("Use async invocation via _arun")

    async def _arun(self, **kwargs: Any) -> str:
        """
        Forward the validated arguments to the MCP server.

        ``None`` values are stripped so the MCP server uses
        its own defaults for optional parameters.
        """
        clean_args = {k: v for k, v in kwargs.items() if v is not None}
        return await self.connection.call_tool(self.name, clean_args)


async def create_mcp_tools(connection: MCPConnection) -> list[BaseTool]:
    """
    Discover all MCP tools and return LangChain wrappers.
    """
    mcp_tools = await connection.list_tools()
    langchain_tools: list[BaseTool] = []

    for tool_def in mcp_tools:
        schema = tool_def.input_schema or {"properties": {}, "required": []}

        try:
            args_model = mcp_schema_to_pydantic(tool_def.name, schema)
        except Exception:
            logger.warning(
                "Skipping tool %s — schema conversion failed",
                tool_def.name,
                exc_info=True,
            )
            continue

        wrapper = MCPToolWrapper(
            name=tool_def.name,
            description=tool_def.description or tool_def.name,
            args_schema=args_model,
            connection=connection,
        )
        langchain_tools.append(wrapper)
        logger.info("Registered LangChain tool: %s", tool_def.name)

    return langchain_tools
