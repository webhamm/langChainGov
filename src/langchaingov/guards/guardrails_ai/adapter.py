"""Map a Guardrails AI ``Guard`` to the ``Guardrail`` protocol."""

from guardrails import Guard
from guardrails.errors import ValidationError
from guardrails.settings import settings as guardrails_settings
from guardrails.utils.hub_telemetry_utils import HubTelemetry

from langchaingov.guards.base import Stage, Verdict


def disable_telemetry() -> None:
    """Guardrails AI sends hub telemetry to a remote collector when ``enable_metrics``
    is true in ``~/.guardrailsrc`` (the default). The ``_enabled`` flag on the
    process-wide ``HubTelemetry`` singleton is re-set by every ``Guard()`` and every
    ``validate()``, so flipping it does not hold. The tracer is created once, in the
    singleton's constructor, and both span paths return early when it is ``None``, so
    dropping it switches telemetry off for the process. The rc file on disk is left
    alone; ``guardrails configure --disable-metrics`` makes it permanent."""
    telemetry = HubTelemetry(enabled=False)
    telemetry._enabled = False
    telemetry._tracer = None
    guardrails_settings.disable_tracing = True


disable_telemetry()


class GuardrailsAiGuard:
    """Runs ``guard.validate(text)`` and reads the ``ValidationOutcome``.

    - ``OnFailAction.FIX`` validators return a changed ``validated_output``: modify.
    - ``OnFailAction.EXCEPTION`` validators raise ``ValidationError``: block.
    - Any other failure (``NOOP``, ``FILTER``...) leaves ``validation_passed`` false: block.
    """

    def __init__(
        self, name: str, description: str, guard: Guard, check_output: bool = True
    ) -> None:
        self.name = name
        self.description = description
        self.guard = guard
        self.applies_to_output = check_output
        disable_telemetry()

    def check_input(self, text: str) -> Verdict:
        return self._validate(text, "input")

    def check_output(self, text: str) -> Verdict:
        if not self.applies_to_output:
            return Verdict.allow(self.name, "output", text)
        return self._validate(text, "output")

    def _validate(self, text: str, stage: Stage) -> Verdict:
        try:
            outcome = self.guard.validate(text)
        except ValidationError as exc:
            return Verdict.block(self.name, stage, text, reason=_clean(str(exc)))
        if not outcome.validation_passed:
            return Verdict.block(
                self.name, stage, text, reason=_clean(outcome.error or "validation failed")
            )
        fixed = outcome.validated_output
        if isinstance(fixed, str) and fixed != text:
            return Verdict.modify(self.name, stage, fixed, reason="fixed by validator")
        return Verdict.allow(self.name, stage, text)


def _clean(message: str) -> str:
    prefix = "Validation failed for field with errors: "
    return message.removeprefix(prefix).strip()
