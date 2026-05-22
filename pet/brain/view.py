"""屏幕分析 brain —— 接收屏幕截图，base64 编码后调用视觉模型分析。"""

import base64
from datetime import datetime
import io
import traceback

from PIL import Image
from openai import OpenAI
from config import config


class ViewBrain:

    def __init__(self):
        brain = config.VIEW_BRAIN or "local"
        print(f"[ViewBrain] __init__: BRAIN={brain}, KEY={'***' if config.VIEW_MODEL_KEY else 'EMPTY'}, URL={config.VIEW_MODEL_URL or '(empty)'}")
        if brain == "ollama":
            self._client = OpenAI(
                api_key="ollama",
                base_url=config.OLLAMA_BASE_URL,
            )
            self._model = config.VIEW_MODEL or config.CHAT_MODEL or "llama3.2-vision"
        elif brain == "llm" and config.VIEW_MODEL_KEY:
            self._client = OpenAI(
                api_key=config.VIEW_MODEL_KEY,
                base_url=config.VIEW_MODEL_URL or "",
            )
            self._model = config.VIEW_MODEL or config.CHAT_MODEL
        else:
            self._client = None

    def analyze(self, image: Image.Image, prompt: str = "") -> str:
        if not self._client:
            return ""
        print(f"[ViewBrain.analyze] image={image.size}, prompt=\"{prompt[:50]}\"")
        base64_img = self._encode_base64(image)
        print(f"[ViewBrain.analyze] base64 encoded, length={len(base64_img)}")
        result = self._call_vision_api(base64_img, prompt)
        print(f"[ViewBrain.analyze] result=\"{result[:100]}\"")
        return result

    def analyze_bytes(self, image_data: bytes, prompt: str = "") -> str:
        if not self._client:
            return ""
        try:
            image = Image.open(io.BytesIO(image_data))
            return self.analyze(image, prompt)
        except Exception:
            traceback.print_exc()
            return ""

    def _encode_base64(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _call_vision_api(self, base64_img: str, prompt: str) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        try:
            messages = [
                {"role": "system", "content": config.VIEW_PROMPT_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or config.VIEW_PROMPT_VISION},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_img}"},
                        },
                    ],
                },
            ]
            print(f"[{t}] [ViewBrain] === LLM REQUEST (vision) ===")
            print(f"[{t}] [ViewBrain]   model: {self._model}")
            print(f"[{t}] [ViewBrain]   system: \"{config.VIEW_PROMPT_SYSTEM[:80]}...\"")
            print(f"[{t}] [ViewBrain]   user.text: \"{(prompt or config.VIEW_PROMPT_VISION)[:80]}...\"")
            print(f"[{t}] [ViewBrain]   user.image: base64, {len(base64_img)} bytes")
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=500,
            )
            print(f"[{t}] [ViewBrain] === LLM RESPONSE (vision) ===")
            print(f"[{t}] [ViewBrain]   id: {resp.id}")
            print(f"[{t}] [ViewBrain]   model: {resp.model}")
            print(f"[{t}] [ViewBrain]   created: {resp.created}")
            print(f"[{t}] [ViewBrain]   usage: {resp.usage}")
            print(f"[{t}] [ViewBrain]   finish_reason: {resp.choices[0].finish_reason if resp.choices else 'N/A'}")
            if resp.choices:
                choice = resp.choices[0]
                content = choice.message.content
                print(f"[{t}] [ViewBrain]   raw: {content}")
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    print(f"[{t}] [ViewBrain]   tool_calls: {choice.message.tool_calls}")

            content = resp.choices[0].message.content
            if content is None:
                print(f"[{t}] [ViewBrain] WARNING: content is None, finish_reason={resp.choices[0].finish_reason}")
                return ""
            if resp.choices[0].finish_reason not in ("stop", "length", None):
                print(f"[{t}] [ViewBrain] WARNING: unexpected finish_reason={resp.choices[0].finish_reason}")
            return content
        except Exception as e:
            print(f"[{t}] [ViewBrain] EXCEPTION: {type(e).__name__}: {e}")
            traceback.print_exc()
            return ""
