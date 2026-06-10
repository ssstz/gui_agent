"""Manual end-to-end desktop GUI agent run.

This script uses Qwen-VL-Chat through create_qwen_desktop_agent(). The first real
run may download model weights from Hugging Face and use GPU memory.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from gui_agent.agent import create_qwen_desktop_agent, save_agent_run_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one end-to-end desktop GUI agent task.")
    parser.add_argument("task", help="Natural-language desktop task to execute.")
    parser.add_argument("--model", default="Qwen/Qwen-VL-Chat", help="Hugging Face model name or local model path.")
    parser.add_argument("--artifacts-dir", default="artifacts/agent_runs", help="Directory for screenshots and result JSON.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue executing later steps after a failed step.")
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = artifacts_dir / f"{timestamp}_agent_run.json"

    agent = create_qwen_desktop_agent(model_name=args.model, artifacts_dir=artifacts_dir)
    result = agent.run(args.task, stop_on_error=not args.continue_on_error)
    save_agent_run_result(result, result_path)

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    print(f"saved_result: {result_path}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
