import pytest

from gui_agent.agent import LangChainTaskPlanner, QwenVLChatClient, QwenVLResponse
from gui_agent.agent.qwen_vl_client import DEFAULT_QWEN_VL_MODEL, _prompt_value_to_text


class FakeQwenClient(QwenVLChatClient):
    def __init__(self, text):
        super().__init__(model_name="fake-model")
        self.text = text
        self.prompts = []

    def generate(self, prompt, *, image_path=None, history=None):
        self.prompts.append(prompt)
        return QwenVLResponse(text=self.text, history=[])


def test_qwen_client_defaults_to_official_model_name():
    client = QwenVLChatClient()

    assert client.model_name == DEFAULT_QWEN_VL_MODEL
    assert client.device_map == "auto"


def test_qwen_client_builds_image_query_with_tokenizer():
    class FakeTokenizer:
        def from_list_format(self, items):
            return items

    query = QwenVLChatClient._build_query(FakeTokenizer(), "describe screen", "artifacts/screen.png")

    assert query == [
        {"image": "artifacts\\screen.png"},
        {"text": "describe screen"},
    ]


def test_qwen_client_callable_works_with_langchain_planner():
    pytest.importorskip("langchain_core")
    client = FakeQwenClient(
        '{"steps": [{"tool": "ocr_screen", "description": "observe", "args": {}}]}'
    )

    plan = LangChainTaskPlanner(client).plan("observe the screen")

    assert plan.task == "observe the screen"
    assert plan.steps[0].tool == "ocr_screen"
    assert "observe the screen" in client.prompts[0]


def test_prompt_value_to_text_accepts_plain_string():
    assert _prompt_value_to_text("hello") == "hello"


def test_prompt_value_to_text_accepts_object_with_to_string():
    class FakePromptValue:
        def to_string(self):
            return "system prompt\nhuman prompt"

    assert _prompt_value_to_text(FakePromptValue()) == "system prompt\nhuman prompt"
