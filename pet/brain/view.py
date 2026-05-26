"""屏幕分析 brain —— 接收屏幕截图，base64 编码后调用视觉模型分析。"""

import base64
from datetime import datetime
import io
import logging
import threading
import traceback

from PIL import Image
from openai import OpenAI
from config import config

logger = logging.getLogger(__name__)


class ViewBrain:

    def __init__(self):
        brain = config.BRAIN or "local"
        logger.info(f"[ViewBrain] __init__: BRAIN={brain}, KEY={'***' if config.LLM_KEY else 'EMPTY'}, URL={config.LLM_URL or '(empty)'}")
        if brain == "ollama":
            self._client = OpenAI(
                api_key="ollama",
                base_url=config.OLLAMA_BASE_URL,
            )
            self._model = config.LLM_MODEL or "llama3.2-vision"
        elif brain == "llm" and config.LLM_KEY:
            self._client = OpenAI(
                api_key=config.LLM_KEY,
                base_url=config.LLM_URL or "",
            )
            self._model = config.LLM_MODEL
        else:
            self._client = None

    def analyze(self, image: Image.Image, prompt: str = "") -> str:
        if not self._client:
            return ""
        logger.debug(f"[ViewBrain.analyze] image={image.size}, prompt=\"{prompt[:50]}\"")
        base64_img = self._encode_base64(image)
        logger.debug(f"[ViewBrain.analyze] base64 encoded, length={len(base64_img)}")
        result = self._call_vision_api(base64_img, prompt)
        logger.debug(f"[ViewBrain.analyze] result=\"{result[:100]}\"")
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
            logger.info(f"[{t}] [ViewBrain] LLM REQ model={self._model} base64={len(base64_img)}b")
            logger.debug(f"[{t}] [ViewBrain]   system: \"{config.VIEW_PROMPT_SYSTEM[:80]}...\"")
            logger.debug(f"[{t}] [ViewBrain]   user.text: \"{(prompt or config.VIEW_PROMPT_VISION)[:80]}...\"")
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=500,
            )
            logger.info(f"[{t}] [ViewBrain] LLM RESP finish={resp.choices[0].finish_reason if resp.choices else 'N/A'} "
                        f"usage={resp.usage}")
            logger.debug(f"[{t}] [ViewBrain]   id={resp.id} model={resp.model} created={resp.created}")
            if resp.choices:
                choice = resp.choices[0]
                content = choice.message.content
                logger.debug(f"[{t}] [ViewBrain]   raw: {content}")
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    logger.debug(f"[{t}] [ViewBrain]   tool_calls: {choice.message.tool_calls}")

            content = resp.choices[0].message.content
            if content is None:
                logger.warning(f"[{t}] [ViewBrain] WARNING: content is None, finish_reason={resp.choices[0].finish_reason}")
                return ""
            if resp.choices[0].finish_reason not in ("stop", "length", None):
                logger.warning(f"[{t}] [ViewBrain] WARNING: unexpected finish_reason={resp.choices[0].finish_reason}")
            return content
        except Exception as e:
            logger.error(f"[{t}] [ViewBrain] EXCEPTION: {type(e).__name__}: {e}")
            traceback.print_exc()
            return ""


class OcrReader:
    """EasyOCR 屏幕文字提取 —— 桌宠的基本感知能力。"""

    def __init__(self, languages: list[str] = None, gpu: bool = False):
        self._languages = languages or ["ch_sim", "en"]
        self._gpu = gpu
        self._reader = None
        self._loading = False          # 后台正在加载标志
        self._lock = threading.Lock()  # 保护 _loading 读写

    def _get_reader(self):
        """获取已加载的 reader。首次调用触发模型加载（可被后台预加载）。

        线程安全：后台线程加载时，主线程不会重复触发加载阻塞 UI。
        """
        # 快速路径：已加载完成
        if self._reader is not None:
            return self._reader

        with self._lock:
            # 双重检查：获得锁后可能已经被加载
            if self._reader is not None:
                return self._reader
            # 后台正在加载中，主线程返回 None，不阻塞 UI
            if self._loading:
                return None
            self._loading = True

        try:
            import easyocr
            self._reader = easyocr.Reader(self._languages, gpu=self._gpu)
            logger.info(f"[OcrReader] model loaded, languages={self._languages}, gpu={self._gpu}")
        except ImportError:
            logger.warning("[OcrReader] easyocr not installed, OCR disabled")
        except Exception as e:
            logger.warning(f"[OcrReader] model load failed: {e}")
        finally:
            with self._lock:
                self._loading = False
        return self._reader

    def extract_text(self, image: Image.Image, min_confidence: float = 0.5) -> str:
        """从 PIL Image 提取文字，返回拼接后的字符串。失败时返回空串。

        内置过滤：
          - 置信度低于 min_confidence 的丢弃
          - 纯符号/单字符非字母数字的丢弃
        """
        try:
            import numpy as np
            img_array = np.array(image)
            reader = self._get_reader()
            if reader is None:
                return ""
            results = reader.readtext(img_array, detail=1)

            parts = []
            for bbox, text, conf in results:
                if conf < min_confidence:
                    continue
                text = text.strip()
                if len(text) <= 1 and not text.isalnum():
                    continue
                parts.append(text)

            return " ｜ ".join(parts)
        except Exception as e:
            logger.error(f"[OcrReader] extract failed: {e}")
            return ""
