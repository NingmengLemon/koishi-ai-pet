from datetime import datetime
import logging
from dataclasses import dataclass, field
from typing import Optional

from openai import OpenAI
from pet.brain.base import BrainMixin
from config import config

logger = logging.getLogger(__name__)


@dataclass
class ActionStep:
    name: str
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)


@dataclass
class BehaviorOutput:
    actions: list = field(default_factory=list)
    speech: Optional[str] = None


class Behavior(BrainMixin):

    def __init__(self):
        super().__init__()
        self._client = None
        self._model = None
        self._setup()

        self._responses = {
            "idle": [
                "Just hanging out...",
                "What a nice day!",
                "Watching you work is fun!",
            ],
        }
        self._idx = 0

        self._actions = [
            "idle", "bounce", "walk", "look_around",
            "stretch", "sit", "sleep",
        ]

        t = datetime.now().strftime("%H:%M:%S")
        client_type = "None (local)" if self._client is None else f"{type(self._client).__name__}(model={self._model})"
        logger.info(f"[{t}] [Behavior] init: {len(self._actions)} actions, client={client_type}")

    def _setup(self):
        brain = config.BRAIN or "local"
        key = config.LLM_KEY
        url = config.LLM_URL
        model = config.LLM_MODEL

        logger.debug(f"[Behavior] _setup: BRAIN={brain}, model={model}, "
                     f"key={'***' if key else 'EMPTY'}, URL={url or '(empty)'}")

        if brain == "ollama":
            self._client = OpenAI(
                api_key="ollama",
                base_url=config.OLLAMA_BASE_URL,
            )
            self._model = model or "llama3.2"
        elif brain == "llm" and key:
            self._client = OpenAI(
                api_key=key,
                base_url=url or "",
            )
            self._model = model
        else:
            self._client = None
            logger.warning(f"[Behavior] No client (BRAIN={brain}, key empty={not bool(key)}) → local fallback")

    def decide(self, context: str = "") -> BehaviorOutput:
        t = datetime.now().strftime("%H:%M:%S")
        ctx_preview = context[:60] if context else "(empty)"
        logger.info(f"[{t}] [Behavior] decide(context={ctx_preview})")
        if self._client:
            result = self._decide_remote(context)
        else:
            result = self._decide_local()
        logger.info(f"[{t}] [Behavior] decide → {result}")
        return result

    def _decide_remote(self, context: str) -> BehaviorOutput:
        t = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{t}] [Behavior] === LLM REQUEST (decide) ===")
        logger.info(f"[{t}] [Behavior]   model: {self._model}")
        logger.info(f"[{t}] [Behavior]   context({len(context)} chars): \"{context[:80]}\"")
        logger.info(f"[{t}] [Behavior]   history: {len(self._context)} entries")

        # 限制上下文条数
        if len(self._context) > 10:
            self._context[:] = self._context[-10:]

        prompt = config.BEHAVIOR_PROMPT_DECIDE.format(
            actions=", ".join(self._actions),
            context=(context or "no context")
            + (f"\nRecent: {', '.join(self._context[-6:-1])}" if len(self._context) > 1 else ""),
        )
        system_content = config.BEHAVIOR_PROMPT_SYSTEM
        if config.PET_PERSONALITY:
            system_content += f"\n\n=== 你的性格 ===\n{config.PET_PERSONALITY}"
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]
        for i, m in enumerate(messages):
            preview = m["content"][:120].replace("\n", "\\n")
            logger.info(f"[{t}] [Behavior]   msg[{i}] role={m['role']}: \"{preview}...\"")
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=4000,
            )
            content = resp.choices[0].message.content or ""
            logger.info(f"[{t}] [Behavior] === LLM RESPONSE ===")
            logger.info(f"[{t}] [Behavior]   finish_reason: {resp.choices[0].finish_reason}")
            if hasattr(resp, 'usage') and resp.usage:
                logger.info(f"[{t}] [Behavior]   usage: {resp.usage}")
            logger.info(f"[{t}] [Behavior]   raw: {content}")
            result = self._parse_behavior(content)
            logger.info(f"[{t}] [Behavior]   parsed → {result}")
            return result
        except Exception as e:
            logger.error(f"[{t}] [Behavior]   LLM call failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            logger.warning(f"[{t}] [Behavior]   falling back to local")
            return self._decide_local()

    def _parse_behavior(self, content: str) -> BehaviorOutput:
        actions: list = []
        speech = None
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            lower = line.lower()
            if lower.startswith("action:"):
                raw = line.split(":", 1)[1].strip()
                step = self._parse_action_line(raw)
                if step:
                    actions.append(step)
            elif lower.startswith("speech:"):
                raw = line.split(":", 1)[1].strip()
                if raw.lower() not in ("none", "", "null"):
                    speech = raw
        if not actions:
            actions.append(ActionStep("idle"))
        return BehaviorOutput(actions=actions, speech=speech)

    def _parse_action_line(self, raw: str) -> ActionStep | None:
        parts = raw.split()
        if not parts:
            return None
        name = parts[0].lower()
        if name not in self._actions:
            t = datetime.now().strftime("%H:%M:%S")
            logger.warning(f"[{t}] [Behavior]   ⚠ unknown action: {name!r}, skipped")
            return None
        args: list = []
        kwargs: dict = {}
        for token in parts[1:]:
            if "=" in token:
                k, v = token.split("=", 1)
                try:
                    v = int(v)
                except ValueError:
                    pass
                kwargs[k] = v
            else:
                try:
                    token = int(token)
                except ValueError:
                    pass
                args.append(token)
        return ActionStep(name, tuple(args), kwargs)

    def _decide_local(self) -> BehaviorOutput:
        import random
        action = random.choice(self._actions)
        action_speech = {
            "idle": "Just hanging out...",
            "bounce": "Boing boing!",
            "walk": "Time to stretch my legs!",
            "look_around": "What's going on over there?",
            "stretch": "Ahh, that's better...",
            "sit": "Taking a little break.",
            "sleep": "Getting sleepy... zzz...",
        }
        speech = action_speech.get(action, "...")
        t = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{t}] [Behavior] _decide_local → {action} / {speech}")
        return BehaviorOutput(
            actions=[ActionStep(action)],
            speech=speech,
        )

    def decide_action(self, context: str = "") -> str:
        result = self.decide(context)
        return result.actions[0].name if result.actions else "idle"

    def think(self, prompt: str) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{t}] [Behavior] think(prompt={prompt[:50]})")
        if self._client:
            reply = self._think_remote(prompt)
        else:
            reply = self._think_local(prompt)
        logger.info(f"[{t}] [Behavior] think → \"{reply[:60]}\"")
        return reply

    def _think_remote(self, prompt: str) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{t}] [Behavior] === LLM REQUEST (think) ===")
        logger.info(f"[{t}] [Behavior]   model: {self._model}, ctx_len={len(self._context)}")
        messages = [
            {"role": "system", "content": config.CHAT_PROMPT_SYSTEM},
        ]
        for ctx in self._context:
            messages.append({"role": "user", "content": ctx})
        messages.append({"role": "user", "content": prompt})
        for i, m in enumerate(messages):
            preview = m["content"][:120].replace("\n", "\\n")
            logger.info(f"[{t}] [Behavior]   msg[{i}] role={m['role']}: \"{preview}...\"")

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=4000,
        )
        content = response.choices[0].message.content or ""
        logger.info(f"[{t}] [Behavior] === LLM RESPONSE ===")
        logger.info(f"[{t}] [Behavior]   finish_reason: {response.choices[0].finish_reason}")
        if hasattr(response, 'usage') and response.usage:
            logger.info(f"[{t}] [Behavior]   usage: {response.usage}")
        logger.info(f"[{t}] [Behavior]   raw: {content}")
        return content

    def _think_local(self, prompt: str) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        reply = self._rotate("idle")
        logger.info(f"[{t}] [Behavior] _think_local → \"{reply}\"")
        return reply

    def _rotate(self, key: str) -> str:
        responses = self._responses.get(key, ["Hmm..."])
        resp = responses[self._idx % len(responses)]
        self._idx += 1
        return resp
