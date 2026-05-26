"""PetAgent — 编排 Brain，通过 Signal 驱动 UI。"""

import logging
from datetime import datetime
from PySide6.QtCore import QObject, QThread, QThreadPool, QTimer, Signal

from pet.brain.behavior import Behavior, BehaviorOutput
from pet.brain.view import ViewBrain, OcrReader
from pet.agent.scheduler import Scheduler
from pet.agent.state import StateMachine
from pet.agent.screen_reader import ScreenReader
from config import config

logger = logging.getLogger(__name__)


class BrainWorker(QObject):

    finished = Signal(object)
    error    = Signal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args
        self._name = getattr(fn, "__name__", repr(fn))

    def run(self):
        ts = datetime.now().strftime("%H:%M:%S")
        logger.debug(f"[{ts}] [BrainWorker] run: {self._name}({self._args})")
        try:
            result = self._fn(*self._args)
            logger.debug(f"[{ts}] [BrainWorker] done: {self._name} → {type(result).__name__}")
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"[{ts}] [BrainWorker] ERROR: {self._name}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class PetAgent(QObject):
    """Agent 调度层"""

    action_requested = Signal(str, object, object)
    speak_requested  = Signal(str, int)
    state_changed    = Signal(str)
    view_ready       = Signal(str)
    view_error       = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.behavior = Behavior()
        self.view_brain = ViewBrain()
        self.screen_reader = ScreenReader()
        self.screen_reader.enable()
        self.ocr_reader = OcrReader(languages=config.OCR_LANGUAGES)
        self.scheduler = Scheduler(self)
        self.state_machine = StateMachine()

        self.scheduler.mid_tick.connect(self._on_mid_tick)
        self.scheduler.fast_tick.connect(self._on_fast_tick)
        self.scheduler.slow_tick.connect(self._on_slow_tick)

        self._thread: QThread | None = None
        self._worker: BrainWorker | None = None

        # 后台预加载 OCR 模型，避免首次 mid_tick 卡 UI
        QThreadPool.globalInstance().start(
            lambda: self.ocr_reader._get_reader()
        )

    def start(self):
        if config.SCHEDULER_AUTO_START:
            self.scheduler.start()
            logger.info("[PetAgent] scheduler auto-started")
            # 启动后延迟 5 秒再触发首次决策
            QTimer.singleShot(5000, self._on_mid_tick)
        else:
            logger.info("[PetAgent] scheduler auto-start disabled (SCHEDULER_AUTO_START=false)")

    def stop(self):
        self.scheduler.stop()
        self.screen_reader.disable()
        try:
            if self._thread and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(3000)
        except RuntimeError:
            pass  # QThread C++ 对象可能已被 Qt 销毁
        logger.info("[PetAgent] stopped")

    def trigger(self, intent: str, **kwargs):
        handlers = {
            "decide":              self._trigger_decide,
            "decide_with_vision":  self._trigger_vision_decide,
            "think":               self._trigger_think,
            "view":                self._trigger_view,
        }
        handler = handlers.get(intent)
        if handler:
            handler(**kwargs)

    def force_state(self, state_name: str):
        from pet.agent.state import PetState
        try:
            st = PetState(state_name)
        except ValueError:
            return
        self.state_machine.force(st)
        self.state_changed.emit(st.value)

    def _on_mid_tick(self):
        ts = datetime.now().strftime("%H:%M:%S")
        if not self.state_machine.can_decide:
            logger.info(f"[{ts}] [PetAgent] [mid_tick] skipped (state={self.state_machine.state.value})")
            return

        image = self.screen_reader.capture_fullscreen()

        # OCR 提取屏幕文字（模型未就绪时静默跳过）
        ocr_text = ""
        if image:
            try:
                ocr_text = self.ocr_reader.extract_text(image)
                if ocr_text:
                    logger.info(f"[{ts}] [PetAgent] OCR({len(ocr_text)} chars): {ocr_text[:100]}")
            except Exception as e:
                logger.warning(f"[{ts}] [PetAgent] OCR failed, skipped: {e}")

        # 视觉模式：截图 + OCR 文字一起送 LLM
        if self.behavior.has_vision and image:
            context = f"屏幕文字(OCR): {ocr_text[:500]}" if ocr_text else ""
            self._async_brain(self.behavior.decide_with_vision, image, context)
            return

        # 纯文本 fallback：OCR 文字作为 context
        context = f"屏幕文字(OCR): {ocr_text[:500]}" if ocr_text else ""
        self._async_brain(self.behavior.decide, context)

    def _on_fast_tick(self):
        pass

    def _on_slow_tick(self):
        from pet.agent.state import PetState
        ts = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{ts}] [PetAgent] [slow_tick]")
        if self.state_machine.state == PetState.SLEEPING:
            self.state_machine.transition(PetState.IDLE)
            self.state_changed.emit(PetState.IDLE.value)
            logger.info(f"[{ts}] [PetAgent] slow_tick: woke up, emitting stretch")
        self.action_requested.emit("stretch", (), {})


    def _trigger_decide(self, context: str = ""):
        self._async_brain(self.behavior.decide, context)

    def _trigger_vision_decide(self, image, context: str = ""):
        self._async_brain(self.behavior.decide_with_vision, image, context)

    def _trigger_think(self, prompt: str = ""):
        self._async_brain(self.behavior.think, prompt)

    def _trigger_view(self, image, prompt: str = ""):
        self._async_brain(
            self.view_brain.analyze, image, prompt,
            on_result=self._on_view_result,
            on_error=self._on_view_error,
        )

    def _async_brain(self, fn, *args, on_result=None, on_error=None):
        fn_name = getattr(fn, "__name__", repr(fn))
        ts = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{ts}] [PetAgent] _async_brain: {fn_name}")
        # 如果有旧线程还在跑，先断开信号避免结果乱序
        if self._worker is not None:
            try:
                self._worker.finished.disconnect()
                self._worker.error.disconnect()
            except (RuntimeError, TypeError):
                pass
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1000)
        self._worker = BrainWorker(fn, *args)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(on_result or self._on_brain_result)
        self._worker.error.connect(on_error or self._on_brain_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_brain_result(self, result):
        ts = datetime.now().strftime("%H:%M:%S")
        if isinstance(result, BehaviorOutput):
            logger.info(f"[{ts}] [PetAgent] ← {result}")
            action_names = [a.name for a in result.actions]
            self.behavior.add_context(
                f"[{ts}] did {', '.join(action_names)}, said: {result.speech or '(silent)'}")
            if result.speech:
                self.speak_requested.emit(result.speech, 4000)
            for step in result.actions:
                self.action_requested.emit(step.name, step.args, step.kwargs)
        elif isinstance(result, str):
            logger.info(f"[{ts}] [PetAgent] ← \"{result[:60]}\"")
            self.behavior.add_context(f"[{ts}] said: {result[:100]}")
            self.speak_requested.emit(result, 5000)

    def _on_brain_error(self, msg: str):
        logger.error(f"[PetAgent] ERROR: {msg}")

    def _on_view_result(self, result):
        if isinstance(result, str):
            self.view_ready.emit(result)

    def _on_view_error(self, msg: str):
        self.view_error.emit(msg)

    # 保留方法（当前 mid_tick 不使用两步链，但保留供未来使用）
    def _on_view_decide_result(self, result):
        ts = datetime.now().strftime("%H:%M:%S")
        if isinstance(result, str):
            self.view_ready.emit(result)
            self.behavior.add_context(f"[{ts}] {result}")
            logger.info(f"[{ts}] [PetAgent] view result → chaining into decide()")
            self._async_brain(self.behavior.decide, result)
        else:
            logger.info(f"[{ts}] [PetAgent] view returned non-string, fallback to decide()")
            self._async_brain(self.behavior.decide, "")

    def _on_view_decide_error(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.view_error.emit(msg)
        logger.error(f"[{ts}] [PetAgent] view error: {msg} → fallback to decide()")
        self._async_brain(self.behavior.decide, "")


