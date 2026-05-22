from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from pet.brain.base import BrainMixin
from config import config


@dataclass
class BehaviorOutput:
    action: str
    speech: Optional[str] = None


class Behavior(BrainMixin):

    def __init__(self):
        super().__init__()
        self._client = None
        self._model = None
        self._setup()

        self._responses = {
            "greet": [
                "Hello! Nice to see you!",
                "Hi there! How are you?",
                "Hey! Good to be here!",
            ],
            "idle": [
                "Just hanging out...",
                "What a nice day!",
                "Watching you work is fun!",
            ],
        }
        self._idx = 0

        self._actions = [
            "idle", "bounce", "walk", "look_around",
            "stretch", "sit", "sleep", "greet_user",
        ]

        t = datetime.now().strftime("%H:%M:%S")
        client_type = "None (local)" if self._client is None else f"{type(self._client).__name__}(model={self._model})"
        print(f"[{t}] [Behavior] init: {len(self._actions)} actions, client={client_type}")

    def _setup(self):
        brain = config.BRAIN or "local"
        key = config.LLM_KEY
        url = config.LLM_URL
        model = config.LLM_MODEL

        print(f"[Behavior] _setup: BRAIN={brain}, model={model}, "
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
            print(f"[Behavior] No client (BRAIN={brain}, key empty={not bool(key)}) → local fallback")

    def decide(self, context: str = "") -> BehaviorOutput:
        t = datetime.now().strftime("%H:%M:%S")
        ctx_preview = context[:60] if context else "(empty)"
        print(f"[{t}] [Behavior] decide(context={ctx_preview})")
        if self._client:
            result = self._decide_remote(context)
        else:
            result = self._decide_local()
        print(f"[{t}] [Behavior] decide → {result}")
        return result

    def _decide_remote(self, context: str) -> BehaviorOutput:
        t = datetime.now().strftime("%H:%M:%S")
        print(f"[{t}] [Behavior] === LLM REQUEST (decide) ===")
        print(f"[{t}] [Behavior]   model: {self._model}")
        prompt = config.BEHAVIOR_PROMPT_DECIDE.format(
            actions=", ".join(self._actions),
            context=context or "no context",
        )
        messages = [
            {"role": "system", "content": config.BEHAVIOR_PROMPT_SYSTEM},
            {"role": "user", "content": prompt},
        ]
        for i, m in enumerate(messages):
            preview = m["content"][:120].replace("\n", "\\n")
            print(f"[{t}] [Behavior]   msg[{i}] role={m['role']}: \"{preview}...\"")
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=150,
            )
            content = resp.choices[0].message.content or ""
            print(f"[{t}] [Behavior] === LLM RESPONSE ===")
            print(f"[{t}] [Behavior]   finish_reason: {resp.choices[0].finish_reason}")
            if hasattr(resp, 'usage') and resp.usage:
                print(f"[{t}] [Behavior]   usage: {resp.usage}")
            print(f"[{t}] [Behavior]   raw: {content}")
            result = self._parse_behavior(content)
            print(f"[{t}] [Behavior]   parsed → {result}")
            return result
        except Exception as e:
            print(f"[{t}] [Behavior]   LLM call failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            print(f"[{t}] [Behavior]   falling back to local")
            return self._decide_local()

    def _parse_behavior(self, content: str) -> BehaviorOutput:
        action = "idle"
        speech = None
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            lower = line.lower()
            if lower.startswith("action:"):
                raw = line.split(":", 1)[1].strip().lower()
                if raw in self._actions:
                    action = raw
                else:
                    t = datetime.now().strftime("%H:%M:%S")
                    print(f"[{t}] [Behavior]   ⚠ unknown action from LLM: {raw!r}, using 'idle'")
            elif lower.startswith("speech:"):
                raw = line.split(":", 1)[1].strip()
                if raw.lower() not in ("none", "", "null"):
                    speech = raw
        return BehaviorOutput(action=action, speech=speech)

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
            "greet_user": "Hey, nice to see you!",
        }
        speech = action_speech.get(action, "...")
        t = datetime.now().strftime("%H:%M:%S")
        print(f"[{t}] [Behavior] _decide_local → {action} / {speech}")
        return BehaviorOutput(
            action=action,
            speech=speech,
        )

    def decide_action(self, context: str = "") -> str:
        return self.decide(context).action

    def think(self, prompt: str) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        print(f"[{t}] [Behavior] think(prompt={prompt[:50]})")
        if self._client:
            reply = self._think_remote(prompt)
        else:
            reply = self._think_local(prompt)
        print(f"[{t}] [Behavior] think → \"{reply[:60]}\"")
        return reply

    def greet(self) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        print(f"[{t}] [Behavior] greet()")
        if self._client:
            reply = self.think(config.CHAT_PROMPT_GREET)
        else:
            reply = self._rotate("greet")
        print(f"[{t}] [Behavior] greet → \"{reply[:60]}\"")
        return reply

    def _think_remote(self, prompt: str) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        print(f"[{t}] [Behavior] === LLM REQUEST (think) ===")
        print(f"[{t}] [Behavior]   model: {self._model}, ctx_len={len(self._context)}")
        messages = [
            {"role": "system", "content": config.CHAT_PROMPT_SYSTEM},
        ]
        for ctx in self._context:
            messages.append({"role": "user", "content": ctx})
        messages.append({"role": "user", "content": prompt})
        for i, m in enumerate(messages):
            preview = m["content"][:120].replace("\n", "\\n")
            print(f"[{t}] [Behavior]   msg[{i}] role={m['role']}: \"{preview}...\"")

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=100,
        )
        content = response.choices[0].message.content or ""
        print(f"[{t}] [Behavior] === LLM RESPONSE ===")
        print(f"[{t}] [Behavior]   finish_reason: {response.choices[0].finish_reason}")
        if hasattr(response, 'usage') and response.usage:
            print(f"[{t}] [Behavior]   usage: {response.usage}")
        print(f"[{t}] [Behavior]   raw: {content}")
        return content

    def _think_local(self, prompt: str) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        if "greet" in prompt.lower():
            reply = self._rotate("greet")
            print(f"[{t}] [Behavior] _think_local (greet match) → \"{reply}\"")
            return reply
        reply = self._rotate("idle")
        print(f"[{t}] [Behavior] _think_local → \"{reply}\"")
        return reply

    def _rotate(self, key: str) -> str:
        responses = self._responses.get(key, ["Hmm..."])
        resp = responses[self._idx % len(responses)]
        self._idx += 1
        return resp
