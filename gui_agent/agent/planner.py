"""LangChain task planner for desktop GUI agent tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any


@dataclass(frozen=True)
class PlanStep:
    """One planned tool call."""

    tool: str
    description: str
    args: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskPlan:
    """A structured plan for a user task."""

    task: str
    steps: list[PlanStep]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "steps": [step.to_dict() for step in self.steps],
        }


class LangChainTaskPlanner:
    """Create TaskPlan objects by calling a LangChain-compatible chat model."""

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    def plan(self, task: str) -> TaskPlan:
        task = task.strip()
        if not task:
            raise ValueError("task must not be empty")

        try:
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError as exc:
            raise RuntimeError("langchain-core is required to use LangChainTaskPlanner") from exc

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _PLANNER_SYSTEM_PROMPT),
                ("human", "Task: {task}"),
            ]
        )
        response = (prompt | self.llm).invoke({"task": task})
        content = getattr(response, "content", response)
        data = _parse_plan_json(str(content))
        return _task_plan_from_data(task, data)


_ALLOWED_TOOLS = {
    "open_app",
    "open_url",
    "capture_screen",
    "ocr_screen",
    "find_text",
    "click_text",
    "click_point",
    "type_text",
    "press_key",
    "hotkey",
    "scroll",
    "drag",
    "wait",
}

_PLANNER_SYSTEM_PROMPT = """
You are a desktop GUI agent planner. Convert the user task into a JSON plan.
Only use these tools: open_app, open_url, capture_screen, ocr_screen, find_text,
click_text, click_point, type_text, press_key, hotkey, scroll, drag, wait.
Return JSON only, with this format:
{{
  "steps": [
    {{"tool": "ocr_screen", "description": "Observe visible screen text.", "args": {{}}}}
  ]
}}
Tool argument examples:
- open_app: {{"command": "notepad", "wait_seconds": 1.0}}
- open_url: {{"url": "https://www.google.com", "wait_seconds": 2.0}}
- type_text: {{"text": "Hello", "press_enter": true}}
- press_key: {{"key": "enter"}}
- hotkey: {{"keys": ["ctrl", "a"]}}
- scroll: {{"amount": -500}}
- wait: {{"seconds": 1.0}}
Rules:
- Use open_app or open_url when the task asks to open an application or web page.
- Use wait after launching apps, opening URLs, or triggering navigation.
- Prefer ocr_screen before text-based actions.
- Prefer click_text when the target can be described by visible text.
- Use type_text for text input and press_key or hotkey for keyboard commands.
- Keep steps short and executable.
""".strip()


def _parse_plan_json(content: str) -> dict[str, Any]:
    content = content.strip()
    fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        content = fenced_match.group(1).strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"planner output is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("planner output must be a JSON object")
    return data


def _task_plan_from_data(task: str, data: dict[str, Any]) -> TaskPlan:
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("planner output must contain a non-empty steps list")

    steps: list[PlanStep] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, dict):
            raise ValueError(f"step {index} must be a JSON object")

        tool = raw_step.get("tool")
        if tool not in _ALLOWED_TOOLS:
            raise ValueError(f"step {index} uses unsupported tool: {tool!r}")

        description = raw_step.get("description") or f"Run {tool}."
        args = raw_step.get("args") or {}
        if not isinstance(args, dict):
            raise ValueError(f"step {index} args must be a JSON object")

        steps.append(PlanStep(tool=tool, description=str(description), args=args))

    return TaskPlan(task=task, steps=steps)
