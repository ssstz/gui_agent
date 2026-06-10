"""Qwen-VL-Chat client used by the LangChain planner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_QWEN_VL_MODEL = "Qwen/Qwen-VL-Chat"


@dataclass(frozen=True)
class QwenVLResponse:
    """Text response returned by Qwen-VL-Chat."""

    text: str
    history: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "history": self.history}


class QwenVLChatClient:
    """Lazy-loading local Qwen-VL-Chat client.
    The model is loaded only when generate() is called.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_QWEN_VL_MODEL,
        *,
        device_map: str = "auto",
        trust_remote_code: bool = True,
        model_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.device_map = device_map
        self.trust_remote_code = trust_remote_code
        self.model_kwargs = model_kwargs or {}
        self._tokenizer: Any = None
        self._model: Any = None

    def generate(
        self,
        prompt: str,
        *,
        image_path: str | Path | None = None,
        history: Any = None,
    ) -> QwenVLResponse:
        """Run Qwen-VL-Chat on a text prompt and optional image."""

        prompt = prompt.strip()
        if not prompt:
            raise ValueError("prompt must not be empty")

        tokenizer, model = self._load_model()
        query = self._build_query(tokenizer, prompt, image_path)
        response, new_history = model.chat(tokenizer, query=query, history=history)
        return QwenVLResponse(text=str(response), history=new_history)

    def invoke(self, value: Any, **kwargs: Any) -> str:
        """LangChain-compatible invoke method."""

        prompt = _prompt_value_to_text(value)
        image_path = kwargs.get("image_path")
        history = kwargs.get("history")
        return self.generate(prompt, image_path=image_path, history=history).text

    def __call__(self, value: Any) -> str:
        return self.invoke(value)

    def unload(self) -> None:
        """Release Python references to the tokenizer and model."""

        self._tokenizer = None
        self._model = None

    def _load_model(self) -> tuple[Any, Any]:
        if self._tokenizer is not None and self._model is not None:
            return self._tokenizer, self._model

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Qwen-VL-Chat requires transformers. Install project requirements before running the model."
            ) from exc

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=self.trust_remote_code,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map=self.device_map,
            trust_remote_code=self.trust_remote_code,
            **self.model_kwargs,
        ).eval()
        return self._tokenizer, self._model

    @staticmethod
    def _build_query(tokenizer: Any, prompt: str, image_path: str | Path | None) -> str:
        if image_path is None:
            return prompt

        path = str(Path(image_path))
        return tokenizer.from_list_format([
            {"image": path},
            {"text": prompt},
        ])


def _prompt_value_to_text(value: Any) -> str:
    """Convert LangChain prompt values or plain strings to text."""

    if isinstance(value, str):
        return value

    if hasattr(value, "to_string"):
        return str(value.to_string())

    if hasattr(value, "messages"):
        parts = []
        for message in value.messages:
            content = getattr(message, "content", "")
            if isinstance(content, str):
                parts.append(content)
            else:
                parts.append(str(content))
        return "\n".join(parts)

    return str(value)
