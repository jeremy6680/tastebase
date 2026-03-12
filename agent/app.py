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

import chainlit as cl
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

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

    # Welcome message
    await cl.Message(
        content=(
            "👋 Bienvenue sur **TasteBase** !\n\n"
            "Je peux répondre à tes questions sur ta collection, "
            "mettre à jour tes notes, et te faire des recommandations.\n\n"
            "_Exemples : « Quels sont mes films préférés ? », "
            "« Note Dune à 5 étoiles », « Recommande-moi des livres de SF »_"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle an incoming user message.

    Flow:
      1. Detect language on the first message.
      2. Append the user message to the conversation history.
      3. Stream the graph response token by token.
      4. Show tool calls as collapsible Chainlit Steps.
      5. Append the final AI response to the history.

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

    # Prepare the streaming response message
    response_message = cl.Message(content="")
    await response_message.send()

    # Stream graph events
    final_content = ""
    tool_steps: dict[str, cl.Step] = {}

    async for event in graph.astream_events(graph_input, version="v2"):
        kind = event["event"]
        name = event.get("name", "")

        # --- Token streaming from the LLM ---
        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                token = chunk.content
                # Skip tool-call metadata chunks (they have no display text)
                if isinstance(token, str):
                    await response_message.stream_token(token)
                    final_content += token

        # --- Tool call started ---
        elif kind == "on_tool_start":
            tool_name = name or "tool"
            tool_input = event["data"].get("input", {})
            step = cl.Step(name=tool_name, type="tool")
            step.input = str(tool_input)
            await step.send()
            run_id = event.get("run_id", tool_name)
            tool_steps[run_id] = step

        # --- Tool call completed ---
        elif kind == "on_tool_end":
            run_id = event.get("run_id", "")
            step = tool_steps.pop(run_id, None)
            if step:
                output = event["data"].get("output", "")
                step.output = str(output)
                await step.update()

    # Persist the final AI response in the conversation history
    if final_content:
        messages.append(AIMessage(content=final_content))
        cl.user_session.set("messages", messages)