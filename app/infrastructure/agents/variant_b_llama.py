"""Variant B — ReAct agent powered by Llama 3.1 8B via Groq API (OpenAI-compatible)."""

import json
import os
import time
from typing import Any

import chromadb
import redis as redis_lib
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent
from openai import BadRequestError, RateLimitError
from sqlalchemy.orm import Session

from app.agents.variant_b.system_prompt import build_system_prompt
from app.domain.entities.agent_trace import TraceStep
from app.infrastructure.agents.tools import make_tools

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_MODEL = os.environ.get("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
_MAX_ITERATIONS = 10
_HISTORY_TTL = 3600
_HISTORY_MAX_MSGS = 20
_HISTORY_KEY = "agent_history:{session_token}"
_RETRY_DELAYS = (5.0, 15.0, 30.0)

_SLEEP = time.sleep


class VariantBLlama:
    def __init__(
        self,
        actor_context: dict[str, Any],
        db: Session,
        chroma: chromadb.ClientAPI,
        redis_client: redis_lib.Redis,
        temperature: float = 0.0,
    ) -> None:
        self._actor_context = actor_context
        self._redis = redis_client
        self._session_token = actor_context["session_token"]

        tools = make_tools(actor_context, db, chroma)
        api_key = os.environ.get("GROQ_API_KEY", "placeholder")
        llm = ChatOpenAI(
            base_url=_GROQ_BASE_URL,
            api_key=api_key,
            model=_MODEL,
            max_retries=0,
            temperature=temperature,
        )
        system_prompt = build_system_prompt(actor_context)
        self._graph = create_react_agent(llm, tools, prompt=system_prompt)

    def run(self, message: str) -> tuple[str, list[TraceStep]]:
        history = self._load_history()
        history.append(HumanMessage(content=message))

        try:
            result = _invoke_with_retry(
                self._graph,
                {"messages": history},
                {"recursion_limit": _MAX_ITERATIONS},
            )
        except GraphRecursionError:
            return "max_iterations_reached", [
                TraceStep(type="final", content="max_iterations_reached")
            ]
        except BadRequestError as exc:
            if "tool_use_failed" in str(exc):
                return "tool_call_error", [TraceStep(type="final", content="tool_call_error")]
            raise

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
        serializable = serializable[-_HISTORY_MAX_MSGS:]
        key = _HISTORY_KEY.format(session_token=self._session_token)
        self._redis.setex(key, _HISTORY_TTL, json.dumps(serializable))


def _invoke_with_retry(graph: Any, inputs: dict, config: dict) -> dict:
    """Invoke graph with exponential backoff retry on Groq 429."""
    for attempt in range(len(_RETRY_DELAYS) + 1):
        try:
            return graph.invoke(inputs, config=config)  # type: ignore[no-any-return]
        except RateLimitError:
            if attempt == len(_RETRY_DELAYS):
                raise
            _SLEEP(_RETRY_DELAYS[attempt])
    raise RuntimeError("unreachable")  # pragma: no cover


def _msg_text(msg: BaseMessage) -> str:
    if isinstance(msg.content, str):
        return msg.content
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
