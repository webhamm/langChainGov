"""``GuardedChain``: input guards, then the model, then output guards."""

from collections.abc import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from langchaingov.guards.base import GuardedResult, Guardrail, Stage, Verdict
from langchaingov.llm import message_text


class GuardedChain:
    """Applies each guardrail in order to the prompt, calls the model, then applies each
    guardrail in order to the reply.

    - The first ``block`` stops everything and the model is not called (for input) or its
      reply is withheld (for output).
    - A ``modify`` verdict's text is what the next guard, and the model, see.
    - A guard that raises is treated as a ``block`` (fail closed), with the error as reason.
    """

    def __init__(
        self,
        model: BaseChatModel,
        guards: Sequence[Guardrail],
        system: str | None = None,
    ) -> None:
        self.model = model
        self.guards = list(guards)
        self.system = system

    def check_prompt(self, prompt: str) -> GuardedResult:
        """Run only the input guards. ``reply`` is always ``None``."""
        verdicts: list[Verdict] = []
        text = prompt
        for guard in self.guards:
            verdict = _run_check(guard, "input", guard.check_input, text)
            verdicts.append(verdict)
            if verdict.action == "block":
                break
            text = verdict.text
        return GuardedResult(prompt=prompt, reply=None, verdicts=verdicts)

    def invoke(self, prompt: str) -> GuardedResult:
        screened = self.check_prompt(prompt)
        verdicts = list(screened.verdicts)
        if screened.blocked:
            return screened
        text = verdicts[-1].text if verdicts else prompt

        reply = message_text(self.model.invoke(self._messages(text)))

        for guard in self.guards:
            verdict = _run_check(guard, "output", guard.check_output, reply)
            verdicts.append(verdict)
            if verdict.action == "block":
                return GuardedResult(prompt=prompt, reply=None, verdicts=verdicts)
            reply = verdict.text

        return GuardedResult(prompt=prompt, reply=reply, verdicts=verdicts)

    def _messages(self, prompt: str) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        if self.system:
            messages.append(SystemMessage(content=self.system))
        messages.append(HumanMessage(content=prompt))
        return messages


def _run_check(
    guard: Guardrail, stage: Stage, check: Callable[[str], Verdict], text: str
) -> Verdict:
    try:
        return check(text)
    except Exception as exc:  # fail closed on any guard failure
        return Verdict.block(
            guard.name, stage, text, reason=f"guard failed: {type(exc).__name__}: {exc}"
        )
