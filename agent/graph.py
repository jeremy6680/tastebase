# agent/graph.py

"""
LangGraph agent graph for TasteBase.

Defines the state, nodes, edges, and compilation of the conversational agent.
The agent has access to three tools:
  - sql_tool: query the gold layer via natural language
  - search_item_for_rating: find an item before rating
  - submit_rating: persist a rating via the FastAPI backend
  - recommend_tool: generate cross-domain recommendations

Graph flow:
    user message → call_model → (tool chosen?) → call_tools → call_model → ...
                                               → (no tool)  → END

Design rules:
  - The agent queries gold models only (enforced by sql_tool's read-only DuckDB connection).
  - All writes go through FastAPI (enforced by rating_tool using httpx, not duckdb directly).
  - Memory persists across turns within a session via LangGraph's message history.
"""

from __future__ import annotations

import logging
import os
from typing import Annotated, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from agent.prompts import get_system_prompt
from agent.tools.rating_tool import search_item_for_rating, submit_rating
from agent.tools.recommend_tool import recommend_tool
from agent.tools.sql_tool import sql_tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# All tools registered with the agent
# ---------------------------------------------------------------------------

TOOLS = [
    sql_tool,
    search_item_for_rating,
    submit_rating,
    recommend_tool,
]

# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    """State that persists across every node in the graph.

    Attributes:
        messages: Full conversation history. The add_messages annotation
            tells LangGraph to append new messages rather than replace the list.
        language: Detected UI language ("fr" or "en"). Defaults to "fr".
            Set once at the start of a session, used to select the system prompt.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    language: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def call_model(state: AgentState, config: RunnableConfig) -> dict:
    """Invoke the LLM with the current conversation history.

    Prepends the system prompt (language-aware) to the message list,
    then calls the LLM bound with all available tools.

    The LLM either:
    - Returns a plain text response (conversation ends or continues).
    - Returns a tool_call (graph routes to call_tools next).

    Args:
        state: Current agent state (messages + language).
        config: LangGraph runnable config (passed through automatically).

    Returns:
        dict: {"messages": [ai_message]} — appended to state by add_messages.
    """
    language = state.get("language", "fr")
    system_prompt = get_system_prompt(language)

    # Build the full message list: system prompt + conversation history
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    llm = _get_llm()
    response: AIMessage = llm.invoke(messages, config)

    logger.debug(
        "call_model response — tool_calls: %s",
        bool(getattr(response, "tool_calls", None)),
    )

    return {"messages": [response]}


def _should_continue(state: AgentState) -> Literal["call_tools", "__end__"]:
    """Routing function: decide whether to call a tool or end the turn.

    Inspects the last message in state. If it contains tool_calls,
    routes to the tool execution node. Otherwise, the turn is complete.

    Args:
        state: Current agent state.

    Returns:
        str: "call_tools" if the LLM requested a tool, "__end__" otherwise.
    """
    last_message = state["messages"][-1]

    # AIMessage.tool_calls is a list; non-empty means the LLM wants a tool
    if getattr(last_message, "tool_calls", None):
        return "call_tools"

    return "__end__"


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------


def _get_llm() -> ChatAnthropic:
    """Instantiate the Anthropic LLM bound with all agent tools.

    Uses the ANTHROPIC_API_KEY environment variable (set via .env).
    Temperature 0 for deterministic tool selection and SQL generation.

    Returns:
        ChatAnthropic: LLM instance with tools bound.
    """
    llm = ChatAnthropic(
        model=os.environ.get("AGENT_MODEL", "claude-3-5-haiku-20241022"),
        temperature=0,
        max_tokens=2048,
    )
    return llm.bind_tools(TOOLS)


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """Build and compile the TasteBase LangGraph agent.

    Graph structure:
        START → call_model → (tool_calls?) → call_tools → call_model → ...
                                           → (no tools)  → END

    The ToolNode handles all four tools automatically based on the
    tool_call name returned by the LLM.

    Returns:
        Compiled StateGraph ready to be used by Chainlit or tests.
    """
    # ToolNode automatically routes tool_call names to the right function
    tool_node = ToolNode(TOOLS)

    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("call_model", call_model)
    graph.add_node("call_tools", tool_node)

    # Entry point
    graph.add_edge(START, "call_model")

    # After call_model: check if a tool was requested
    graph.add_conditional_edges(
        "call_model",
        _should_continue,
        {
            "call_tools": "call_tools",
            "__end__": END,
        },
    )

    # After tools execute: always go back to the model to process the result
    graph.add_edge("call_tools", "call_model")

    return graph.compile()


# ---------------------------------------------------------------------------
# Module-level compiled graph (used by app.py)
# ---------------------------------------------------------------------------

# Compiled once at import time — Chainlit reuses this instance across sessions.
graph = build_graph()