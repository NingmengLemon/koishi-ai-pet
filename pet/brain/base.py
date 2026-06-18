class BrainMixin:

    def __init__(self):
        self._context: list[str] = []

    def add_context(self, message: str):
        self._context.append(message)

    def clear_context(self):
        self._context.clear()
