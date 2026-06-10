"""Manual test: create a simple tool plan from a task string."""

from __future__ import annotations

import argparse
import json

from gui_agent.agent import SimpleTaskPlanner


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan a desktop GUI task with the rule-based planner.")
    parser.add_argument("task", help="Natural-language desktop task.")
    args = parser.parse_args()

    plan = SimpleTaskPlanner().plan(args.task)
    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
