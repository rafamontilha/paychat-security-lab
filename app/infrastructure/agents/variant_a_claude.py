"""Variant A — ReAct agent powered by Claude via Anthropic API (LangGraph)."""

import json
from typing import Any

import chromadb
import redis as redis_lib
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session

from app.agents.variant_a.system_prompt import build_system_prompt
from app.domain.entities.agent_trace import TraceStep
from app.infrastructure.agents.tools import make_tools

_MODEL = "claude-sonnet-4-6"
_MAX_ITERATIONS = 10
_HISTORY_TTL = 3600
_HISTORY_MAX_MSGS = 20
_HISTORY_KEY = "agent_history:{session_token}"


class VariantAClaude:
    def __init__(
        self,
        actor_context: dict[str, Any],
        db: Session,
        chroma: chromadb.ClientAPI,
        redis_client: redis_lib.Redis,
    ) -> None:
        self._actor_context = actor_context
        self._redis = redis_client
        self._session_token = actor_context["session_token"]

        tools = make_tools(actor_context, db, chroma)
        llm = ChatAnthropic(model=_MODEL, max_tokens=4096)
        system_prompt = build_system_prompt(actor_context)
        self._graph = create_react_agent(llm, tools, prompt=system_prompt)

    def run(self, message: str) -> tuple[str, list[TraceStep]]:
        history = self._load_history()
        history.append(HumanMessage(content=message))

        try:
            result = self._graph.invoke(
                {"messages": history},
                config={"recursion_limit": _MAX_ITERATIONS},
            )
        except GraphRecursionError:
            return "max_iterations_reached", [
                TraceStep(type="final", content="max_iterations_reached")
            ]

        new_messages: list[BaseMessage] = result["messages"][len(history) :]
        trace = _extract_trace(new_messages)

        final_response = _extract_final_response(new_messages)
        updated = history + new_messages
        self._save_history(updated)
        return final_response, trace

    def _load_history(self) -> list[BaseMessage]:
        key = _HISTORY_KEY.format(session_token=self._session_token)
        raw = self._redis.get(key)
        if not raw:
            return []
        assert isinstance(raw, (str, bytes, bytearray))
        data: list[dict] = json.loads(raw)
        messages: list[BaseMessage] = []
        for item in data:
            if item["role"] == "human":
                messages.append(HumanMessage(content=item["content"]))
            else:
                messages.append(AIMessage(content=item["content"]))
        return messages

    def _save_history(self, messages: list[BaseMessage]) -> None:
        serializable = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                serializable.append({"role": "human", "content": _msg_text(msg)})
            elif isinstance(msg, AIMessage) and not msg.tool_calls:
                serializable.append({"role": "ai", "content": _msg_text(msg)})
        # Keep last N messages
        serializable = serializable[-_HISTORY_MAX_MSGS:]
        key = _HISTORY_KEY.format(session_token=self._session_token)
        self._redis.setex(key, _HISTORY_TTL, json.dumps(serializable))


def _msg_text(msg: BaseMessage) -> str:
    if isinstance(msg.content, str):
        return msg.content
    # Claude sometimes returns list[dict] for content
    parts = []
    for block in msg.content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return " ".join(parts)


def _extract_trace(messages: list[BaseMessage]) -> list[TraceStep]:
    trace: list[TraceStep] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                trace.append(
                    TraceStep(
                        type="tool_call",
                        content=f"Calling {tc['name']}",
                        tool_name=tc["name"],
                        tool_args=dict(tc["args"]),
                    )
                )
        elif isinstance(msg, ToolMessage):
            trace.append(
                TraceStep(
                    type="tool_return",
                    content=str(msg.content),
                    tool_name=msg.name,
                    tool_result=str(msg.content),
                )
            )
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            trace.append(TraceStep(type="final", content=_msg_text(msg)))
    return trace


def _extract_final_response(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            return _msg_text(msg)
    return ""
