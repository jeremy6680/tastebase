# agent/app.py

"""
Chainlit entry point for the TasteBase LangGraph agent.

Chainlit version: 2.x
LangGraph version: 1.x

Session lifecycle:
  - on_chat_start: initialise l'état LangGraph dans la session utilisateur
  - on_message: passe le message au graph, stream la réponse token par token

Language detection:
  - Detected from the first user message.
  - Stored in cl.user_session and passed as part of the LangGraph state.

Streaming:
  - Uses graph.astream_events() to stream tokens as they are generated.
  - Tool calls are shown as Chainlit Steps (collapsible in the UI).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path fix: ensure the project root is in sys.path.
# Chainlit adds agent/ to sys.path when running agent/app.py, which breaks
# absolute imports like "from agent.graph import graph". This line adds the
# project root (one level above agent/) so all imports resolve correctly.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env from the project root before any module that reads env vars at import time
# (graph.py, tools/*.py all read DUCKDB_PATH, API_BASE_URL, AGENT_MODEL on import).
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

import chainlit as cl
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage


def _extract_text(content: object) -> str:
    """Extract a plain string from an AIMessage content field.

    LangChain / Anthropic messages can return content as either:
    - A plain string: "Hello"
    - A list of content blocks: [{"type": "text", "text": "Hello"}, ...]

    Chainlit expects a plain string and will throw "t.trim is not a function"
    if it receives a list. This helper normalises both formats.

    Args:
        content: The raw content field from an AIMessage.

    Returns:
        str: Extracted plain text, or empty string if nothing found.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content) if content else ""


from agent.graph import graph

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_FRENCH_MARKERS = {
    "bonjour", "salut", "quels", "quelle", "quoi", "est-ce",
    "combien", "montre", "donne", "trouve", "recommande", "note",
    "je", "tu", "les", "des", "une", "mon",
}


def _detect_language(text: str) -> str:
    """Detect whether a message is in French or English.

    Uses a simple word-overlap heuristic against a set of common French words.
    Defaults to French if detection is ambiguous, since FR is the app default.

    Args:
        text: Raw message text from the user.

    Returns:
        str: "fr" or "en".
    """
    words = set(text.lower().split())
    overlap = words & _FRENCH_MARKERS
    return "fr" if overlap else "en"


# ---------------------------------------------------------------------------
# Chainlit lifecycle hooks
# ---------------------------------------------------------------------------


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialise the agent session when a new chat starts.

    Stores the conversation history and detected language in the Chainlit
    user session so they persist across messages within the same chat.
    """
    cl.user_session.set("messages", [])
    cl.user_session.set("language", "fr")  # default, updated on first message

    # Welcome message with quick access links to companion apps
    await cl.Message(
        content=(
            "👋 Bienvenue sur **TasteBase** !\n\n"
            "Je peux répondre à tes questions sur ta collection, "
            "mettre à jour tes notes, et te faire des recommandations.\n\n"
            "_Exemples : « Quels sont mes films préférés ? », "
            "« Note Dune à 5 étoiles », « Recommande-moi des livres de SF »_\n\n"
            "---\n\n"
            "🔗 **Accès rapide :** "
            "[📊 Dashboard](http://localhost:3000) · "
            "[📚 Bibliothèque](http://localhost:5173)"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle an incoming user message.

    Flow:
      1. Detect language on the first message.
      2. Append the user message to the conversation history.
      3. Run the graph, surfacing tool calls as collapsible Chainlit Steps.
      4. Display the final AI response in the main message bubble.
      5. Append the final AI response to the history.

    Streaming strategy:
      We use astream_events to surface tool call Steps in real time while the
      graph runs. Token streaming is intentionally disabled: the LLM emits
      tokens across multiple call_model passes (pre-tool and post-tool) and it
      is impossible to distinguish which pass is the final user-facing response
      without buffering everything. Instead, we collect the full final answer
      from the last AIMessage in the graph output and update the response
      bubble once at the end. This guarantees the displayed text is always the
      correct reformulated answer, never raw SQL or intermediate reasoning.

    Args:
        message: Incoming Chainlit message from the user.
    """
    messages: list = cl.user_session.get("messages") or []
    language: str = cl.user_session.get("language") or "fr"

    # Detect language on the first real message
    if not messages:
        language = _detect_language(message.content)
        cl.user_session.set("language", language)

    # Append new user message to history
    human_message = HumanMessage(content=message.content)
    messages.append(human_message)

    # Prepare the LangGraph input state
    graph_input = {
        "messages": messages,
        "language": language,
    }

    # Placeholder bubble shown while the graph runs
    response_message = cl.Message(content="")
    await response_message.send()

    # Track open tool Steps by run_id so we can close them on tool_end
    tool_steps: dict[str, cl.Step] = {}
    final_content = ""

    async for event in graph.astream_events(graph_input, version="v2"):
        kind = event["event"]
        name = event.get("name", "")

        # --- Tool call started: open a collapsible Step ---
        if kind == "on_tool_start":
            tool_name = name or "tool"
            input_data = event["data"].get("input", {})
            step = cl.Step(name=tool_name, type="tool")
            if isinstance(input_data, dict):
                # Render input as readable "key: value" lines
                step.input = "\n".join(f"{k}: {v}" for k, v in input_data.items())
            else:
                step.input = str(input_data)
            await step.send()
            tool_steps[event.get("run_id", tool_name)] = step

        # --- Tool call completed: close the Step with its output ---
        elif kind == "on_tool_end":
            run_id = event.get("run_id", "")
            step = tool_steps.pop(run_id, None)
            if step:
                step.output = str(event["data"].get("output", ""))
                await step.update()

        # --- Capture final AI message from the graph output ---
        # on_chain_end fires when a LangGraph node completes.
        # We watch for call_model completing and extract the last AIMessage.
        elif kind == "on_chain_end" and name == "call_model":
            output = event["data"].get("output", {})
            node_messages = output.get("messages", [])
            for msg in reversed(node_messages):
                if isinstance(msg, AIMessage):
                    # Only capture if this message has no tool_calls
                    # (i.e. it is the final user-facing response, not an
                    # intermediate "I will call sql_tool" message).
                    if not getattr(msg, "tool_calls", None):
                        text = _extract_text(msg.content)
                        if text:
                            final_content = text
                            break

    # Update the response bubble with the final reformulated answer
    if final_content:
        response_message.content = final_content
        await response_message.update()
        messages.append(AIMessage(content=final_content))
        cl.user_session.set("messages", messages)
    else:
        # Fallback: should not happen in normal operation
        response_message.content = "_(Aucune réponse générée — vérifie les logs du serveur.)_"
        await response_message.update()