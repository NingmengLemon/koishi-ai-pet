"""PetAgent — 编排 Brain，通过 Signal 驱动 UI。"""

from datetime import datetime
from PySide6.QtCore import QObject, QThread, Signal

from pet.brain.behavior import Behavior, BehaviorOutput
from pet.brain.view import ViewBrain
from pet.agent.scheduler import Scheduler
from pet.agent.state import StateMachine


class BrainWorker(QObject):
    """在 QThread 中执行单次 Brain 调用。"""

    finished = Signal(object)
    error    = Signal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args
        self._name = getattr(fn, "__name__", repr(fn))

    def run(self):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [BrainWorker] run: {self._name}({self._args})")
        try:
            result = self._fn(*self._args)
            print(f"[{ts}] [BrainWorker] done: {self._name} → {type(result).__name__}")
            self.finished.emit(result)
        except Exception as e:
            print(f"[{ts}] [BrainWorker] ERROR: {self._name}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class PetAgent(QObject):
    """Agent 调度层 —— 编排 Brain，通过 Signal 驱动 UI。"""

    action_requested = Signal(str)
    speak_requested  = Signal(str, int)
    state_changed    = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.behavior = Behavior()
        self.view_brain = ViewBrain()
        self.scheduler = Scheduler(self)
        self.state_machine = StateMachine()

        self.scheduler.mid_tick.connect(self._on_mid_tick)
        self.scheduler.fast_tick.connect(self._on_fast_tick)

        self._thread: QThread | None = None
        self._worker: BrainWorker | None = None

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.stop()

    def trigger(self, intent: str, **kwargs):
        handlers = {
            "decide": self._trigger_decide,
            "think":  self._trigger_think,
            "greet":  self._trigger_greet,
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
        print(f"[{ts}] [PetAgent] [mid_tick] → decide()")
        self._async_brain(self.behavior.decide, "")

    def _on_fast_tick(self):
        pass

    def _trigger_decide(self, context: str = ""):
        self._async_brain(self.behavior.decide, context)

    def _trigger_think(self, prompt: str = ""):
        self._async_brain(self.behavior.think, prompt)

    def _trigger_greet(self):
        self._async_brain(self.behavior.greet)

    def _async_brain(self, fn, *args):
        fn_name = getattr(fn, "__name__", repr(fn))
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [PetAgent] _async_brain: {fn_name}")
        self._worker = BrainWorker(fn, *args)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_brain_result)
        self._worker.error.connect(self._on_brain_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_brain_result(self, result):
        ts = datetime.now().strftime("%H:%M:%S")
        if isinstance(result, BehaviorOutput):
            print(f"[{ts}] [PetAgent] ← {result}")
            if result.action:
                self.action_requested.emit(result.action)
            if result.speech:
                self.speak_requested.emit(result.speech, 4000)
        elif isinstance(result, str):
            print(f"[{ts}] [PetAgent] ← \"{result[:60]}\"")
            self.speak_requested.emit(result, 5000)

    def _on_brain_error(self, msg: str):
        print(f"[PetAgent] ERROR: {msg}")
