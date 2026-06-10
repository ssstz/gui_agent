"""Simple rule-based task planner for desktop GUI agent tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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


class SimpleTaskPlanner:
    """Create a conservative tool plan from a natural-language task.

    This rule-based planner is intentionally small. It gives the project a
    deterministic planning baseline before adding LLM-based planning.
    """

    def plan(self, task: str) -> TaskPlan:
        task = task.strip()
        if not task:
            raise ValueError("task must not be empty")

        steps = [
            PlanStep(
                tool="ocr_screen",
                description="Observe the current screen and extract visible UI text.",
            )
        ]

        search_query = _extract_search_query(task)
        text_to_type = _extract_text_to_type(task)
        click_target = _extract_click_target(task)
        scroll_amount = _extract_scroll_amount(task)

        if click_target:
            steps.append(
                PlanStep(
                    tool="click_text",
                    description=f"Click the UI element matching {click_target!r}.",
                    args={"keyword": click_target, "fuzzy_threshold": 0.8},
                )
            )

        if search_query:
            steps.append(
                PlanStep(
                    tool="type_text",
                    description=f"Type search query {search_query!r} and press Enter.",
                    args={"text": search_query, "press_enter": True},
                )
            )
        elif text_to_type:
            steps.append(
                PlanStep(
                    tool="type_text",
                    description=f"Type text {text_to_type!r}.",
                    args={"text": text_to_type, "press_enter": False},
                )
            )

        if scroll_amount is not None:
            steps.append(
                PlanStep(
                    tool="scroll",
                    description="Scroll the active page or window.",
                    args={"amount": scroll_amount},
                )
            )

        steps.append(
            PlanStep(
                tool="ocr_screen",
                description="Observe the screen again to verify the result.",
            )
        )
        return TaskPlan(task=task, steps=steps)


def _extract_search_query(task: str) -> str | None:
    patterns = [
        r"search(?: for)?\s+(.+)$",
        r"google\s+(.+)$",
        r"搜索\s*(.+)$",
        r"查询\s*(.+)$",
    ]
    return _first_match(task, patterns)


def _extract_text_to_type(task: str) -> str | None:
    quoted = _first_match(task, [r"['\"](.+?)['\"]", r"“(.+?)”", r"‘(.+?)’"])
    if quoted:
        return quoted
    patterns = [
        r"type\s+(.+)$",
        r"write\s+(.+)$",
        r"input\s+(.+)$",
        r"输入\s*(.+)$",
        r"写入\s*(.+)$",
        r"写下\s*(.+)$",
    ]
    return _first_match(task, patterns)


def _extract_click_target(task: str) -> str | None:
    patterns = [
        r"click\s+(.+?)(?:\s+then|\s+and|$)",
        r"open\s+(.+?)(?:\s+then|\s+and|$)",
        r"点击\s*(.+?)(?:，|,|然后|$)",
        r"打开\s*(.+?)(?:，|,|然后|$)",
    ]
    target = _first_match(task, patterns)
    if target:
        return _clean_target(target)
    if _contains_any(task, ["search", "搜索", "查询"]):
        return "search"
    return None


def _extract_scroll_amount(task: str) -> int | None:
    lowered = task.lower()
    if "scroll down" in lowered or "向下滚" in task or "下滑" in task:
        return -500
    if "scroll up" in lowered or "向上滚" in task or "上滑" in task:
        return 500
    return None


def _first_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return value.rstrip(".。") if value else None
    return None


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _clean_target(target: str) -> str:
    target = target.strip().strip("'\"“”‘’")
    return target.rstrip(".。")
