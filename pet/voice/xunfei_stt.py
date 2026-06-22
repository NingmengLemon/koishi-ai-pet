"""讯飞语音听写 (iat) WebSocket API 封装"""

import base64
import hashlib
import hmac
import json
import logging
import ssl
import threading
import time
from datetime import datetime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from time import mktime

import websocket
from PySide6.QtCore import QObject, Signal

from config import config

logger = logging.getLogger(__name__)

STATUS_FIRST_FRAME = 0
STATUS_CONTINUE_FRAME = 1
STATUS_LAST_FRAME = 2


class XunfeiSTT(QObject):
    """讯飞语音听写流式 WebSocket 客户端。

    每次 start() → send_audio()*N → stop() 为一个会话。
    返回的文字实时通过 partial_result 发出。
    """

    partial_result = Signal(str)  # 中间识别结果
    done = Signal(str)            # 最终完整结果
    error_occurred = Signal(str)  # 错误信息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._result_text = ""
        self._final_text = ""

    def start(self):
        """建立 WebSocket 连接，发送第一帧音频。"""
        if self._running:
            return
        self._result_text = ""
        self._final_text = ""

        if not config.XF_APPID or not config.XF_API_KEY or not config.XF_API_SECRET:
            logger.error("[XunfeiSTT] missing API credentials")
            self.error_occurred.emit("讯飞 API 凭证未配置")
            return

        url = self._build_url()
        self._running = True

        self._ws = websocket.WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._ws.on_open = self._on_open

        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()
        logger.info("[XunfeiSTT] connecting...")

    def _run_forever(self):
        self._ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def _build_url(self) -> str:
        base = "wss://ws-api.xfyun.cn/v2/iat"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        sig_str = f"host: ws-api.xfyun.cn\ndate: {date}\nGET /v2/iat HTTP/1.1"
        sig = hmac.new(
            config.XF_API_SECRET.encode("utf-8"),
            sig_str.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sig_b64 = base64.b64encode(sig).decode("utf-8")

        auth = f'api_key="{config.XF_API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{sig_b64}"'
        auth_b64 = base64.b64encode(auth.encode("utf-8")).decode("utf-8")

        params = {"authorization": auth_b64, "date": date, "host": "ws-api.xfyun.cn"}
        return base + "?" + urlencode(params)

    def _on_open(self, ws):
        """WebSocket 已打开，等待 send_audio 推送数据。"""
        logger.info("[XunfeiSTT] connected")

    def send_audio(self, data: bytes, status: int = STATUS_CONTINUE_FRAME):
        """推送一帧音频数据到讯飞。

        Args:
            data: PCM 16kHz 16bit mono bytes
            status: 0=第一帧, 1=中间帧, 2=最后一帧
        """
        if not self._ws or not self._ws.sock:
            return
        b64 = base64.b64encode(data).decode("utf-8")

        if status == STATUS_FIRST_FRAME:
            payload = {
                "common": {"app_id": config.XF_APPID},
                "business": {
                    "domain": "iat",
                    "language": "zh_cn",
                    "accent": "mandarin",
                    "vinfo": 1,
                    "vad_eos": 10000,
                },
                "data": {
                    "status": 0,
                    "format": "audio/L16;rate=16000",
                    "audio": b64,
                    "encoding": "raw",
                },
            }
        else:
            payload = {
                "data": {
                    "status": status,
                    "format": "audio/L16;rate=16000",
                    "audio": b64,
                    "encoding": "raw",
                }
            }

        try:
            self._ws.send(json.dumps(payload))
        except Exception as e:
            logger.error(f"[XunfeiSTT] send failed: {e}")

    def stop(self):
        """发送最后一帧，等待结果后关闭连接。"""
        if not self._running:
            return
        self._running = False
        # 发送空最后一帧通知讯飞结束
        if self._ws and self._ws.sock:
            payload = {
                "data": {
                    "status": STATUS_LAST_FRAME,
                    "format": "audio/L16;rate=16000",
                    "audio": "",
                    "encoding": "raw",
                }
            }
            try:
                self._ws.send(json.dumps(payload))
            except Exception:
                pass
        logger.info("[XunfeiSTT] waiting for final result...")

    def _on_message(self, ws, message):
        """解析讯飞返回的 JSON。"""
        try:
            msg = json.loads(message)
            code = msg.get("code", -1)
            if code != 0:
                err = msg.get("message", "unknown")
                logger.error(f"[XunfeiSTT] server error: {code} {err}")
                self.error_occurred.emit(f"讯飞错误: {err}")
                ws.close()
                return

            data = msg.get("data", {})
            status = data.get("status", -1)

            # 解析识别文字
            result = data.get("result", {})
            ws_list = result.get("ws", [])
            text = ""
            for item in ws_list:
                for cw in item.get("cw", []):
                    text += cw.get("w", "")

            if text:
                self._result_text = text
                self.partial_result.emit(text)

            # 最后一帧，发出最终结果
            if status == 2:
                final = data.get("result", {}).get("text", "")
                if not final and self._result_text:
                    final = self._result_text
                self._final_text = final
                self.done.emit(final)
                logger.info(f"[XunfeiSTT] final result: {final}")

        except Exception as e:
            logger.error(f"[XunfeiSTT] parse error: {e}")

    def _on_error(self, ws, error):
        logger.error(f"[XunfeiSTT] websocket error: {error}")
        self.error_occurred.emit(str(error))

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"[XunfeiSTT] closed ({close_status_code})")
        self._running = False
        # 如果还没有发出 final，有 partial 就用 partial
        if self._result_text and not self._final_text:
            self.done.emit(self._result_text)

    def force_stop(self):
        """立即关闭连接，不等待结果。"""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
